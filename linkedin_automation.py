import time
import json
from selenium import webdriver
from selenium.webdriver.common.by import By
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
from selenium.webdriver.chrome.service import Service
from selenium.webdriver.chrome.options import Options
from selenium.common.exceptions import TimeoutException, NoSuchElementException
from webdriver_manager.chrome import ChromeDriverManager
from bs4 import BeautifulSoup
import re
from typing import List, Dict, Optional
from config import Config, SearchFilters
from database import JobDatabase

class LinkedInAutomation:
    def __init__(self, config: Config):
        self.config = config
        self.driver = None
        self.db = JobDatabase()
        self.setup_driver()
    
    def setup_driver(self):
        chrome_options = Options()
        
        if self.config.headless_browser:
            chrome_options.add_argument("--headless")
        
        chrome_options.add_argument("--no-sandbox")
        chrome_options.add_argument("--disable-dev-shm-usage")
        chrome_options.add_argument("--disable-blink-features=AutomationControlled")
        chrome_options.add_experimental_option("excludeSwitches", ["enable-automation"])
        chrome_options.add_experimental_option('useAutomationExtension', False)
        
        try:
            # Custom ChromeDriver setup to fix webdriver-manager bug
            import os
            import stat
            import glob
            
            # Get base driver path from webdriver-manager
            base_path = ChromeDriverManager().install()
            base_dir = os.path.dirname(base_path)
            
            # Find the actual chromedriver executable
            chromedriver_files = glob.glob(os.path.join(base_dir, "**/chromedriver"), recursive=True)
            
            if chromedriver_files:
                driver_path = chromedriver_files[0]
                print(f"Found chromedriver at: {driver_path}")
                
                # Make sure the driver is executable
                os.chmod(driver_path, stat.S_IRWXU | stat.S_IRGRP | stat.S_IROTH)
                
                service = Service(driver_path)
                self.driver = webdriver.Chrome(service=service, options=chrome_options)
                self.driver.execute_script("Object.defineProperty(navigator, 'webdriver', {get: () => undefined})")
            else:
                raise Exception("Could not find chromedriver executable")
                
        except Exception as e:
            print(f"Error setting up ChromeDriver: {e}")
            try:
                # Fallback: try system Chrome installation
                print("Trying system Chrome installation...")
                self.driver = webdriver.Chrome(options=chrome_options)
                self.driver.execute_script("Object.defineProperty(navigator, 'webdriver', {get: () => undefined})")
            except Exception as e2:
                print(f"System Chrome also failed: {e2}")
                raise Exception("Could not initialize ChromeDriver")
    
    def login(self) -> bool:
        try:
            self.driver.get("https://www.linkedin.com/login")
            
            # Wait for login form to load
            email_field = WebDriverWait(self.driver, 15).until(
                EC.presence_of_element_located((By.ID, "username"))
            )
            password_field = self.driver.find_element(By.ID, "password")
            
            email_field.send_keys(self.config.linkedin_email)
            password_field.send_keys(self.config.linkedin_password)
            
            login_button = self.driver.find_element(By.XPATH, '//button[@type="submit"]')
            login_button.click()
            
            print("Login submitted, waiting for verification or redirect...")
            
            # Wait longer for potential verification steps
            max_wait_time = 120  # 2 minutes for user verification
            wait_interval = 5
            elapsed_time = 0
            
            while elapsed_time < max_wait_time:
                try:
                    # Check if we're on the main LinkedIn page (successful login)
                    if self.driver.find_elements(By.CLASS_NAME, "global-nav"):
                        print("Successfully logged in to LinkedIn")
                        return True
                    
                    # Check for challenge/verification page
                    if "challenge" in self.driver.current_url or "checkpoint" in self.driver.current_url:
                        print(f"Verification required. Please complete verification in browser. Waiting... ({elapsed_time}s/{max_wait_time}s)")
                    
                    # Check for login error messages
                    error_elements = self.driver.find_elements(By.CLASS_NAME, "form__label--error")
                    if error_elements:
                        print(f"Login error: {error_elements[0].text}")
                        return False
                    
                    time.sleep(wait_interval)
                    elapsed_time += wait_interval
                    
                except Exception as e:
                    print(f"Waiting for login completion... ({elapsed_time}s/{max_wait_time}s)")
                    time.sleep(wait_interval)
                    elapsed_time += wait_interval
            
            # Final check after timeout
            if self.driver.find_elements(By.CLASS_NAME, "global-nav"):
                print("Login completed successfully after verification")
                return True
            else:
                print("Login failed - timeout waiting for verification completion")
                return False
            
        except TimeoutException:
            print("Login failed - initial page load timeout")
            return False
        except Exception as e:
            print(f"Login failed: {str(e)}")
            return False
    
    def search_jobs(self, filters: SearchFilters) -> List[Dict]:
        try:
            search_url = self._build_search_url(filters)
            print(f"Searching with URL: {search_url}")
            self.driver.get(search_url)
            
            # Wait for page to load
            time.sleep(5)
            
            # Debug: check current URL and page title
            print(f"Current URL: {self.driver.current_url}")
            print(f"Page title: {self.driver.title}")
            
            jobs = []
            page_num = 1
            total_saved = 0
            
            # Try multiple selectors for job cards
            job_selectors = [
                ".job-search-card",
                ".jobs-search-results__list-item",
                ".job-result-card",
                "[data-job-id]",
                ".jobs-search-results-list .jobs-search-results__list-item"
            ]
            
            job_cards = []
            for selector in job_selectors:
                job_cards = self.driver.find_elements(By.CSS_SELECTOR, selector)
                print(f"Found {len(job_cards)} job cards with selector: {selector}")
                if job_cards:
                    break
            
            if not job_cards:
                # Debug: save page source to see what we're getting
                print("No job cards found. Checking page content...")
                page_source = self.driver.page_source
                if "sign-in" in page_source.lower() or "login" in page_source.lower():
                    print("Warning: Might be redirected to login page")
                elif "no jobs found" in page_source.lower():
                    print("LinkedIn reports no jobs found for this search")
                else:
                    print("Page loaded but job cards not found with current selectors")
                return []
            
            pages_processed = 0
            max_pages = 25  # Limit to prevent infinite loops
            
            while total_saved < self.config.max_jobs_per_search and pages_processed < max_pages:
                pages_processed += 1
                print(f"\n--- Processing page {page_num} (attempt {pages_processed}) ---")
                
                # Process current page jobs
                page_jobs = []
                print(f"Attempting to extract from {len(job_cards)} job cards...")
                
                for i, card in enumerate(job_cards):
                    job_data = self._extract_job_card_data(card)
                    if job_data:
                        page_jobs.append(job_data)
                        print(f"✓ Extracted job {i+1}: {job_data['job_title']} at {job_data['company_name']}")
                    else:
                        print(f"❌ Failed to extract job {i+1}")
                
                print(f"Successfully extracted {len(page_jobs)} out of {len(job_cards)} job cards")
                
                # Save current page jobs to database incrementally
                if page_jobs:
                    print(f"Processing {len(page_jobs)} jobs from page {page_num}...")
                    saved_count = self.save_jobs_to_database(page_jobs)
                    total_saved += saved_count
                    jobs.extend(page_jobs)
                    
                    print(f"Progress: {total_saved}/{self.config.max_jobs_per_search} new jobs saved")
                else:
                    print("❌ No jobs extracted from current page - this is a problem!")
                
                # Check if we need more jobs
                print(f"Current status: {total_saved}/{self.config.max_jobs_per_search} new jobs saved")
                if total_saved >= self.config.max_jobs_per_search:
                    print(f"✓ Reached target of {self.config.max_jobs_per_search} new jobs saved")
                    break
                else:
                    print(f"Need {self.config.max_jobs_per_search - total_saved} more jobs, continuing to next page...")
                
                # Try to navigate to next page
                try:
                    next_selectors = [
                        'button[aria-label="View next page"]',
                        'button[aria-label="Next"]',
                        'button[aria-label="Next page"]',
                        '.jobs-search-results-list__pagination button:last-child',
                        '.pv2 .artdeco-button--secondary'
                    ]
                    
                    next_button = None
                    for selector in next_selectors:
                        buttons = self.driver.find_elements(By.CSS_SELECTOR, selector)
                        print(f"Found {len(buttons)} buttons with selector: {selector}")
                        if buttons:
                            for button in buttons:
                                if button.is_enabled() and button.is_displayed():
                                    next_button = button
                                    print(f"Found working next button: {selector}")
                                    break
                        if next_button:
                            break
                    
                    if next_button:
                        print(f"Clicking next button to go to page {page_num + 1}")
                        next_button.click()
                        time.sleep(self.config.delay_between_requests)
                        page_num += 1
                        print(f"Now on page {page_num}")
                        
                        # Wait for new page to load
                        time.sleep(3)
                        
                        # Get fresh job cards for next page (avoid stale references)
                        job_cards = []
                        for selector in job_selectors:
                            job_cards = self.driver.find_elements(By.CSS_SELECTOR, selector)
                            if job_cards:
                                print(f"Found {len(job_cards)} job cards on page {page_num}")
                                break
                                
                        if not job_cards:
                            print("No more job cards found on next page")
                            # Try to continue for a few more attempts
                            if page_num < 10:  # Don't give up too easily
                                print("Trying to continue anyway...")
                                # Wait a bit more and try again
                                time.sleep(2)
                                for selector in job_selectors:
                                    job_cards = self.driver.find_elements(By.CSS_SELECTOR, selector)
                                    if job_cards:
                                        print(f"Found {len(job_cards)} job cards after retry")
                                        break
                                if not job_cards:
                                    print("Still no job cards after retry, continuing to next page")
                                    continue
                            else:
                                break
                    else:
                        print("No next button found or all buttons disabled")
                        # Check if we're actually at the end or if there's another way to continue
                        page_source = self.driver.page_source
                        if "no more results" in page_source.lower() or "end of results" in page_source.lower():
                            print("Reached end of results")
                            break
                        else:
                            print("No pagination found, but may not be at end")
                            break
                        
                except Exception as e:
                    print(f"Error navigating to next page: {str(e)}")
                    # Don't break immediately, try to continue
                    print("Attempting to continue despite navigation error...")
                    # Wait and try to find jobs on current page again
                    time.sleep(3)
                    for selector in job_selectors:
                        job_cards = self.driver.find_elements(By.CSS_SELECTOR, selector)
                        if job_cards:
                            print(f"Found {len(job_cards)} job cards after error recovery")
                            break
                    if not job_cards:
                        print("No job cards found after error recovery, stopping")
                        break
            
            print(f"\n=== SEARCH COMPLETED ===")
            print(f"Pages processed: {pages_processed}")
            print(f"Total jobs processed: {len(jobs)}")
            print(f"Total jobs saved: {total_saved}")
            print(f"Target was: {self.config.max_jobs_per_search}")
            
            if total_saved < self.config.max_jobs_per_search:
                print(f"⚠️  WARNING: Only saved {total_saved} jobs, target was {self.config.max_jobs_per_search}")
            
            return jobs
            
        except Exception as e:
            print(f"Job search failed: {str(e)}")
            return []
    
    def _build_search_url(self, filters: SearchFilters) -> str:
        base_url = "https://www.linkedin.com/jobs/search/?"
        params = []
        
        if filters.job_title:
            params.append(f"keywords={filters.job_title.replace(' ', '%20')}")
        
        if filters.location:
            params.append(f"location={filters.location.replace(' ', '%20')}")
        
        if filters.experience_level:
            exp_map = {
                "internship": "1",
                "entry": "2", 
                "associate": "3",
                "mid": "4",
                "director": "5",
                "executive": "6"
            }
            if filters.experience_level.lower() in exp_map:
                params.append(f"f_E={exp_map[filters.experience_level.lower()]}")
        
        if filters.time_posted:
            time_map = {
                "24h": "r86400",
                "week": "r604800",
                "month": "r2592000"
            }
            if filters.time_posted.lower() in time_map:
                params.append(f"f_TPR={time_map[filters.time_posted.lower()]}")
        
        return base_url + "&".join(params)
    
    def _extract_job_card_data(self, card) -> Optional[Dict]:
        try:
            # Try multiple selectors for job title and link (updated for current LinkedIn structure)
            job_title = ""
            job_url = ""
            
            title_selectors = [
                ".job-card-container__link",
                "a[aria-label]",
                ".job-card-list__title a",
                ".job-search-card__title a",
                ".job-result-card__title a",
                "h3 a[data-control-name*='job']"
            ]
            
            for selector in title_selectors:
                try:
                    title_element = card.find_element(By.CSS_SELECTOR, selector)
                    job_title = title_element.text.strip()
                    job_url = title_element.get_attribute("href")
                    
                    # Clean up job title (remove extra whitespace and newlines)
                    job_title = " ".join(job_title.split())
                    
                    # Extract main job title (first line if multiple lines)
                    if "\n" in job_title:
                        job_title = job_title.split("\n")[0].strip()
                    
                    break
                except:
                    continue
            
            if not job_title:
                print("Could not find job title in card")
                return None
            
            # Extract company name and location from span elements
            company_name = ""
            location = ""
            
            try:
                # Get all span elements in the card
                spans = card.find_elements(By.TAG_NAME, "span")
                span_texts = [span.text.strip() for span in spans if span.text.strip()]
                
                print(f"   Debug - All span texts: {span_texts}")
                
                # Clean job title for comparison (remove extra text)
                clean_job_title = job_title.split("\n")[0].strip()
                if " with verification" in clean_job_title:
                    clean_job_title = clean_job_title.replace(" with verification", "")
                
                # Based on debug output, company is typically around index 2-3, location around index 3-4
                skip_texts = [job_title, clean_job_title, "Promoted", "Easy Apply", "Actively hiring"]
                # Also skip variations of the job title
                if " with verification" in job_title:
                    skip_texts.append(job_title.replace(" with verification", ""))
                
                # Add the individual components that might appear in spans
                job_title_parts = job_title.split()
                job_title_first_part = job_title_parts[0] if job_title_parts else ""
                if job_title_first_part:
                    # Find the base job title (first occurrence before repetition)
                    job_title_base = job_title.split(" " + job_title_first_part)[0].strip()
                    if job_title_base:
                        skip_texts.append(job_title_base)
                        skip_texts.append(job_title_base + " with verification")
                
                for i, text in enumerate(span_texts):
                    print(f"   Debug - Checking span {i}: '{text}'")
                    # Skip job titles, "Promoted", "Easy Apply", etc.
                    if text and text not in skip_texts and len(text) > 2:
                        # Check if this looks like a location
                        location_indicators = ["CA", "NY", "TX", "FL", "IL", "Remote", "Hybrid", "On-site", "Metropolitan Area", "United States", "(", ")"]
                        is_location = any(indicator in text for indicator in location_indicators)
                        
                        if is_location:
                            # This looks like a location
                            if not location:
                                location = text
                                print(f"   Debug - Found location: {location}")
                        else:
                            # This looks like a company name
                            if not company_name:
                                company_name = text
                                print(f"   Debug - Found company: {company_name}")
                            elif not location:
                                # If we already have a company, this might be location
                                location = text
                                print(f"   Debug - Found location (fallback): {location}")
                
                # If we still don't have a company name, try alternative extraction
                if not company_name:
                    # Try finding company name in specific elements
                    company_selectors = [
                        ".artdeco-entity-lockup__subtitle",
                        ".job-card-container__company-name",
                        ".job-card-list__company-name",
                        "h4 a"
                    ]
                    for selector in company_selectors:
                        try:
                            element = card.find_element(By.CSS_SELECTOR, selector)
                            company_name = element.text.strip()
                            if company_name and company_name != clean_job_title:
                                print(f"   Debug - Found company via selector {selector}: {company_name}")
                                break
                        except:
                            continue
                
                if not location:
                    location_selectors = [
                        ".job-card-container__metadata-item",
                        ".job-card-list__location"
                    ]
                    for selector in location_selectors:
                        try:
                            location = card.find_element(By.CSS_SELECTOR, selector).text.strip()
                            break
                        except:
                            continue
                            
            except Exception as e:
                print(f"Error extracting company/location: {e}")
                pass
            
            # Try to get posted date
            posted_date = ""
            date_selectors = [
                ".job-search-card__listitem--footerItem time",
                ".job-result-card__listitem--footerItem time",
                "time[datetime]"
            ]
            
            for selector in date_selectors:
                try:
                    posted_date = card.find_element(By.CSS_SELECTOR, selector).get_attribute("datetime")
                    break
                except:
                    continue
            
            return {
                "job_title": job_title,
                "company_name": company_name,
                "location": location,
                "job_url": job_url,
                "posted_date": posted_date,
                "application_url": "",
                "job_description": "",
                "salary_range": "",
                "experience_level": "",
                "employment_type": ""
            }
            
        except Exception as e:
            print(f"Error extracting job card data: {str(e)}")
            return None
    
    def get_job_details(self, job_url: str) -> Dict:
        try:
            self.driver.get(job_url)
            time.sleep(2)
            
            job_details = {}
            
            try:
                description_element = self.driver.find_element(By.CSS_SELECTOR, ".job-details__description-text")
                job_details["job_description"] = description_element.text.strip()
            except:
                job_details["job_description"] = ""
            
            try:
                apply_button = self.driver.find_element(By.CSS_SELECTOR, 'a[data-control-name="jobdetails_topcard_inapply"]')
                job_details["application_url"] = apply_button.get_attribute("href")
            except:
                try:
                    apply_button = self.driver.find_element(By.CSS_SELECTOR, '.jobs-apply-button')
                    job_details["application_url"] = job_url
                except:
                    job_details["application_url"] = ""
            
            try:
                salary_element = self.driver.find_element(By.CSS_SELECTOR, ".job-details-jobs-unified-top-card__job-insight span")
                job_details["salary_range"] = salary_element.text.strip()
            except:
                job_details["salary_range"] = ""
            
            return job_details
            
        except Exception as e:
            print(f"Error getting job details: {str(e)}")
            return {}
    
    def save_jobs_to_database(self, jobs: List[Dict]):
        saved_count = 0
        duplicate_count = 0
        error_count = 0
        
        print(f"Attempting to save {len(jobs)} jobs...")
        
        for i, job in enumerate(jobs):
            print(f"\n--- Processing job {i+1}/{len(jobs)} ---")
            print(f"Title: {job['job_title']}")
            print(f"Company: {job['company_name']}")
            print(f"Location: {job['location']}")
            print(f"URL: {job['job_url']}")
            
            # Check if job already exists in database (by URL or by details)
            url_exists = self.db.job_exists(job["job_url"])
            details_exist = self.db.job_exists_by_details(
                job["job_title"], job["company_name"], job["location"]
            )
            
            if url_exists or details_exist:
                duplicate_count += 1
                duplicate_reason = "URL" if url_exists else "details"
                print(f"❌ DUPLICATE ({duplicate_reason}): {job['job_title']} at {job['company_name']}")
                continue
            
            print(f"✓ New job, getting details...")
            try:
                job_details = self.get_job_details(job["job_url"])
                job.update(job_details)
                
                if self.db.add_job(job):
                    saved_count += 1
                    print(f"✓ SAVED job {saved_count}: {job['job_title']} at {job['company_name']}")
                else:
                    error_count += 1
                    print(f"❌ FAILED to save to database: {job['job_title']}")
                    
            except Exception as e:
                error_count += 1
                print(f"❌ ERROR getting job details: {str(e)}")
            
            time.sleep(self.config.delay_between_requests)
        
        print(f"\n=== SAVE SUMMARY ===")
        print(f"Total processed: {len(jobs)}")
        print(f"Saved: {saved_count}")
        print(f"Duplicates: {duplicate_count}")
        print(f"Errors: {error_count}")
        
        return saved_count
    
    def close(self):
        if self.driver:
            self.driver.quit()
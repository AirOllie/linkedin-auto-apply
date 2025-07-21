#!/usr/bin/env python3

import sys
import os
from gui import main as gui_main
from config import load_config
from linkedin_automation import LinkedInAutomation
from database import JobDatabase

def main():
    if len(sys.argv) > 1 and sys.argv[1] == "--cli":
        run_cli()
    else:
        gui_main()

def run_cli():
    print("LinkedIn Job Auto-Apply - CLI Mode")
    print("=" * 40)
    
    config = load_config()
    
    if not config.linkedin_email or not config.linkedin_password:
        print("Please set LINKEDIN_EMAIL and LINKEDIN_PASSWORD in .env file")
        return
    
    automation = LinkedInAutomation(config)
    
    try:
        print("Logging in to LinkedIn...")
        if not automation.login():
            print("Login failed!")
            return
        
        print("Login successful!")
        
        job_title = input("Enter job title to search for: ")
        location = input("Enter location (optional): ")
        
        from config import SearchFilters
        filters = SearchFilters(
            job_title=job_title,
            location=location
        )
        
        print(f"Searching for jobs...")
        jobs = automation.search_jobs(filters)
        
        print(f"Found {len(jobs)} jobs. Getting detailed information...")
        automation.save_jobs_to_database(jobs)
        
        print(f"Search completed! {len(jobs)} jobs saved to database.")
        
        db = JobDatabase()
        all_jobs = db.get_all_jobs()
        
        print(f"\nTotal jobs in database: {len(all_jobs)}")
        for job in all_jobs[-5:]:  # Show last 5 jobs
            print(f"- {job['job_title']} at {job['company_name']} ({job['location']})")
            if job['application_url']:
                print(f"  Apply: {job['application_url']}")
        
    except Exception as e:
        print(f"Error: {str(e)}")
    finally:
        automation.close()

if __name__ == "__main__":
    main()
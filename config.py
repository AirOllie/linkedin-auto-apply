import os
from dataclasses import dataclass
from typing import List, Optional

@dataclass
class SearchFilters:
    job_title: str = ""
    experience_level: str = ""
    location: str = ""
    company_size: str = ""
    time_posted: str = ""
    remote_option: str = ""
    salary_range: str = ""

@dataclass
class Config:
    linkedin_email: str = ""
    linkedin_password: str = ""
    search_filters: SearchFilters = None
    max_jobs_per_search: int = 50
    delay_between_requests: int = 3
    headless_browser: bool = False
    
    def __post_init__(self):
        if self.search_filters is None:
            self.search_filters = SearchFilters()

def load_config():
    from dotenv import load_dotenv
    load_dotenv()
    
    config = Config()
    config.linkedin_email = os.getenv('LINKEDIN_EMAIL', '')
    config.linkedin_password = os.getenv('LINKEDIN_PASSWORD', '')
    config.headless_browser = os.getenv('HEADLESS_BROWSER', 'False').lower() == 'true'
    
    return config
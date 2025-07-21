import sqlite3
import json
from datetime import datetime
from typing import List, Dict, Optional

class JobDatabase:
    def __init__(self, db_path: str = "jobs.db"):
        self.db_path = db_path
        self.init_database()
    
    def init_database(self):
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        
        cursor.execute('''
            CREATE TABLE IF NOT EXISTS jobs (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                job_title TEXT NOT NULL,
                company_name TEXT NOT NULL,
                location TEXT,
                job_url TEXT UNIQUE NOT NULL,
                application_url TEXT,
                job_description TEXT,
                salary_range TEXT,
                experience_level TEXT,
                employment_type TEXT,
                posted_date TEXT,
                scraped_date TEXT,
                applied BOOLEAN DEFAULT FALSE,
                applied_date TEXT,
                status TEXT DEFAULT 'found'
            )
        ''')
        
        conn.commit()
        conn.close()
    
    def add_job(self, job_data: Dict) -> bool:
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        
        try:
            cursor.execute('''
                INSERT OR REPLACE INTO jobs 
                (job_title, company_name, location, job_url, application_url, 
                 job_description, salary_range, experience_level, employment_type, 
                 posted_date, scraped_date)
                VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            ''', (
                job_data.get('job_title'),
                job_data.get('company_name'),
                job_data.get('location'),
                job_data.get('job_url'),
                job_data.get('application_url'),
                job_data.get('job_description'),
                job_data.get('salary_range'),
                job_data.get('experience_level'),
                job_data.get('employment_type'),
                job_data.get('posted_date'),
                datetime.now().isoformat()
            ))
            
            conn.commit()
            return True
            
        except sqlite3.IntegrityError:
            return False
        finally:
            conn.close()
    
    def get_all_jobs(self) -> List[Dict]:
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        
        cursor.execute('SELECT * FROM jobs ORDER BY scraped_date DESC')
        jobs = cursor.fetchall()
        
        conn.close()
        
        columns = ['id', 'job_title', 'company_name', 'location', 'job_url', 
                  'application_url', 'job_description', 'salary_range', 
                  'experience_level', 'employment_type', 'posted_date', 
                  'scraped_date', 'applied', 'applied_date', 'status']
        
        return [dict(zip(columns, job)) for job in jobs]
    
    def job_exists(self, job_url: str) -> bool:
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        
        cursor.execute('SELECT id FROM jobs WHERE job_url = ?', (job_url,))
        exists = cursor.fetchone() is not None
        
        conn.close()
        return exists
    
    def job_exists_by_details(self, job_title: str, company_name: str, location: str) -> bool:
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        
        cursor.execute('''
            SELECT id FROM jobs 
            WHERE job_title = ? AND company_name = ? AND location = ?
        ''', (job_title, company_name, location))
        exists = cursor.fetchone() is not None
        
        conn.close()
        return exists
    
    def clear_duplicates(self) -> int:
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        
        # Find and delete duplicate jobs (keeping the first occurrence)
        cursor.execute('''
            DELETE FROM jobs 
            WHERE id NOT IN (
                SELECT MIN(id) 
                FROM jobs 
                GROUP BY job_title, company_name, location
            )
        ''')
        
        deleted_count = cursor.rowcount
        conn.commit()
        conn.close()
        
        return deleted_count
    
    def mark_applied(self, job_id: int) -> bool:
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        
        cursor.execute('''
            UPDATE jobs 
            SET applied = TRUE, applied_date = ?, status = 'applied'
            WHERE id = ?
        ''', (datetime.now().isoformat(), job_id))
        
        conn.commit()
        success = cursor.rowcount > 0
        conn.close()
        
        return success
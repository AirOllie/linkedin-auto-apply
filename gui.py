import tkinter as tk
from tkinter import ttk, messagebox, scrolledtext
import threading
import webbrowser
from config import Config, SearchFilters, load_config
from linkedin_automation import LinkedInAutomation
from database import JobDatabase

class JobSearchGUI:
    def __init__(self, root):
        self.root = root
        self.root.title("LinkedIn Job Auto-Apply")
        self.root.geometry("1200x800")
        
        self.config = load_config()
        self.db = JobDatabase()
        self.automation = None
        
        self.setup_ui()
        self.load_jobs()
    
    def setup_ui(self):
        self.notebook = ttk.Notebook(self.root)
        self.notebook.pack(fill="both", expand=True, padx=10, pady=10)
        
        self.setup_search_tab()
        self.setup_jobs_tab()
        self.setup_config_tab()
    
    def setup_search_tab(self):
        search_frame = ttk.Frame(self.notebook)
        self.notebook.add(search_frame, text="Job Search")
        
        search_params_frame = ttk.LabelFrame(search_frame, text="Search Parameters")
        search_params_frame.pack(fill="x", padx=10, pady=5)
        
        ttk.Label(search_params_frame, text="Job Title:").grid(row=0, column=0, sticky="w", padx=5, pady=5)
        self.job_title_var = tk.StringVar(value="Robotics Engineer")
        ttk.Entry(search_params_frame, textvariable=self.job_title_var, width=30).grid(row=0, column=1, padx=5, pady=5)
        
        ttk.Label(search_params_frame, text="Location:").grid(row=0, column=2, sticky="w", padx=5, pady=5)
        self.location_var = tk.StringVar(value="United States")
        ttk.Entry(search_params_frame, textvariable=self.location_var, width=30).grid(row=0, column=3, padx=5, pady=5)
        
        ttk.Label(search_params_frame, text="Experience Level:").grid(row=1, column=0, sticky="w", padx=5, pady=5)
        self.experience_var = tk.StringVar()
        experience_combo = ttk.Combobox(search_params_frame, textvariable=self.experience_var, 
                                      values=["", "Internship", "Entry", "Associate", "Mid", "Director", "Executive"])
        experience_combo.grid(row=1, column=1, padx=5, pady=5)
        
        ttk.Label(search_params_frame, text="Time Posted:").grid(row=1, column=2, sticky="w", padx=5, pady=5)
        self.time_posted_var = tk.StringVar(value="24h")
        time_combo = ttk.Combobox(search_params_frame, textvariable=self.time_posted_var, 
                                values=["", "24h", "Week", "Month"])
        time_combo.grid(row=1, column=3, padx=5, pady=5)
        
        ttk.Label(search_params_frame, text="Max Jobs:").grid(row=2, column=0, sticky="w", padx=5, pady=5)
        self.max_jobs_var = tk.StringVar(value="50")
        ttk.Entry(search_params_frame, textvariable=self.max_jobs_var, width=10).grid(row=2, column=1, padx=5, pady=5)
        
        button_frame = ttk.Frame(search_frame)
        button_frame.pack(fill="x", padx=10, pady=5)
        
        self.search_button = ttk.Button(button_frame, text="Start Job Search", command=self.start_search)
        self.search_button.pack(side="left", padx=5)
        
        self.stop_button = ttk.Button(button_frame, text="Stop Search", command=self.stop_search, state="disabled")
        self.stop_button.pack(side="left", padx=5)
        
        self.progress_var = tk.StringVar(value="Ready to search")
        ttk.Label(button_frame, textvariable=self.progress_var).pack(side="left", padx=20)
        
        self.progress_bar = ttk.Progressbar(search_frame, mode='indeterminate')
        self.progress_bar.pack(fill="x", padx=10, pady=5)
        
        log_frame = ttk.LabelFrame(search_frame, text="Search Log")
        log_frame.pack(fill="both", expand=True, padx=10, pady=5)
        
        self.log_text = scrolledtext.ScrolledText(log_frame, height=10)
        self.log_text.pack(fill="both", expand=True, padx=5, pady=5)
    
    def setup_jobs_tab(self):
        jobs_frame = ttk.Frame(self.notebook)
        self.notebook.add(jobs_frame, text="Job Listings")
        
        toolbar_frame = ttk.Frame(jobs_frame)
        toolbar_frame.pack(fill="x", padx=10, pady=5)
        
        ttk.Button(toolbar_frame, text="Refresh & Clear Duplicates", command=self.refresh_and_clear_duplicates).pack(side="left", padx=5)
        ttk.Button(toolbar_frame, text="Open Job", command=self.open_selected_job).pack(side="left", padx=5)
        ttk.Button(toolbar_frame, text="Open Application", command=self.open_application).pack(side="left", padx=5)
        ttk.Button(toolbar_frame, text="Mark Applied", command=self.mark_applied).pack(side="left", padx=5)
        
        columns = ("ID", "Job Title", "Company", "Location", "Posted Date", "Applied", "Status")
        self.jobs_tree = ttk.Treeview(jobs_frame, columns=columns, show="headings", height=15)
        
        for col in columns:
            self.jobs_tree.heading(col, text=col)
            self.jobs_tree.column(col, width=120)
        
        scrollbar = ttk.Scrollbar(jobs_frame, orient="vertical", command=self.jobs_tree.yview)
        self.jobs_tree.configure(yscrollcommand=scrollbar.set)
        
        self.jobs_tree.pack(side="left", fill="both", expand=True, padx=10, pady=5)
        scrollbar.pack(side="right", fill="y", pady=5)
        
        details_frame = ttk.LabelFrame(jobs_frame, text="Job Details")
        details_frame.pack(fill="x", padx=10, pady=5)
        
        self.details_text = scrolledtext.ScrolledText(details_frame, height=8)
        self.details_text.pack(fill="both", expand=True, padx=5, pady=5)
        
        self.jobs_tree.bind("<<TreeviewSelect>>", self.on_job_select)
    
    def setup_config_tab(self):
        config_frame = ttk.Frame(self.notebook)
        self.notebook.add(config_frame, text="Configuration")
        
        login_frame = ttk.LabelFrame(config_frame, text="LinkedIn Login")
        login_frame.pack(fill="x", padx=10, pady=5)
        
        ttk.Label(login_frame, text="Email:").grid(row=0, column=0, sticky="w", padx=5, pady=5)
        self.email_var = tk.StringVar(value=self.config.linkedin_email)
        ttk.Entry(login_frame, textvariable=self.email_var, width=40).grid(row=0, column=1, padx=5, pady=5)
        
        ttk.Label(login_frame, text="Password:").grid(row=1, column=0, sticky="w", padx=5, pady=5)
        self.password_var = tk.StringVar(value=self.config.linkedin_password)
        ttk.Entry(login_frame, textvariable=self.password_var, width=40, show="*").grid(row=1, column=1, padx=5, pady=5)
        
        settings_frame = ttk.LabelFrame(config_frame, text="Settings")
        settings_frame.pack(fill="x", padx=10, pady=5)
        
        self.headless_var = tk.BooleanVar(value=self.config.headless_browser)
        ttk.Checkbutton(settings_frame, text="Headless Browser", variable=self.headless_var).pack(anchor="w", padx=5, pady=5)
        
        ttk.Label(settings_frame, text="Delay Between Requests (seconds):").pack(anchor="w", padx=5, pady=5)
        self.delay_var = tk.StringVar(value=str(self.config.delay_between_requests))
        ttk.Entry(settings_frame, textvariable=self.delay_var, width=10).pack(anchor="w", padx=5, pady=5)
        
        ttk.Button(config_frame, text="Save Configuration", command=self.save_config).pack(pady=10)
    
    def start_search(self):
        if not self.email_var.get() or not self.password_var.get():
            messagebox.showerror("Error", "Please enter LinkedIn email and password in Configuration tab")
            return
        
        self.search_button.config(state="disabled")
        self.stop_button.config(state="normal")
        self.progress_bar.start()
        self.log_text.delete(1.0, tk.END)
        
        search_thread = threading.Thread(target=self.run_search)
        search_thread.daemon = True
        search_thread.start()
    
    def run_search(self):
        try:
            self.log("Starting LinkedIn automation...")
            
            self.config.linkedin_email = self.email_var.get()
            self.config.linkedin_password = self.password_var.get()
            self.config.headless_browser = self.headless_var.get()
            self.config.delay_between_requests = int(self.delay_var.get())
            self.config.max_jobs_per_search = int(self.max_jobs_var.get())
            
            self.automation = LinkedInAutomation(self.config)
            
            self.log("Logging in to LinkedIn...")
            if not self.automation.login():
                self.log("Login failed!")
                return
            
            self.log("Login successful!")
            
            filters = SearchFilters(
                job_title=self.job_title_var.get(),
                location=self.location_var.get(),
                experience_level=self.experience_var.get(),
                time_posted=self.time_posted_var.get()
            )
            
            self.log(f"Searching for jobs with filters: {filters}")
            jobs = self.automation.search_jobs(filters)
            
            self.log(f"Search completed! {len(jobs)} jobs processed.")
            
        except Exception as e:
            self.log(f"Error during search: {str(e)}")
        finally:
            self.search_complete()
    
    def search_complete(self):
        self.root.after(0, self._search_complete_ui)
    
    def _search_complete_ui(self):
        self.search_button.config(state="normal")
        self.stop_button.config(state="disabled")
        self.progress_bar.stop()
        self.progress_var.set("Search completed")
        
        if self.automation:
            self.automation.close()
            self.automation = None
        
        self.load_jobs()
    
    def stop_search(self):
        if self.automation:
            self.automation.close()
            self.automation = None
        self.search_complete()
    
    def log(self, message):
        self.root.after(0, lambda: self._log_ui(message))
    
    def _log_ui(self, message):
        self.log_text.insert(tk.END, f"{message}\n")
        self.log_text.see(tk.END)
        self.root.update()
    
    def refresh_and_clear_duplicates(self):
        # Clear duplicates from database
        deleted_count = self.db.clear_duplicates()
        
        # Show message about duplicates cleared
        if deleted_count > 0:
            messagebox.showinfo("Duplicates Cleared", f"Removed {deleted_count} duplicate job(s) from the database.")
        else:
            messagebox.showinfo("No Duplicates", "No duplicate jobs found in the database.")
        
        # Refresh the job listing
        self.load_jobs()
    
    def load_jobs(self):
        jobs = self.db.get_all_jobs()
        
        for item in self.jobs_tree.get_children():
            self.jobs_tree.delete(item)
        
        for job in jobs:
            applied_status = "Yes" if job['applied'] else "No"
            self.jobs_tree.insert("", tk.END, values=(
                job['id'],
                job['job_title'],
                job['company_name'],
                job['location'],
                job['posted_date'][:10] if job['posted_date'] else "",
                applied_status,
                job['status']
            ))
    
    def on_job_select(self, event):
        selection = self.jobs_tree.selection()
        if selection:
            item = self.jobs_tree.item(selection[0])
            job_id = item['values'][0]
            
            jobs = self.db.get_all_jobs()
            selected_job = next((job for job in jobs if job['id'] == job_id), None)
            
            if selected_job:
                details = f"Job Title: {selected_job['job_title']}\n"
                details += f"Company: {selected_job['company_name']}\n"
                details += f"Location: {selected_job['location']}\n"
                details += f"Salary: {selected_job['salary_range']}\n"
                details += f"Experience Level: {selected_job['experience_level']}\n"
                details += f"Employment Type: {selected_job['employment_type']}\n"
                details += f"Posted Date: {selected_job['posted_date']}\n"
                details += f"Application URL: {selected_job['application_url']}\n\n"
                details += f"Description:\n{selected_job['job_description']}"
                
                self.details_text.delete(1.0, tk.END)
                self.details_text.insert(1.0, details)
    
    def open_selected_job(self):
        selection = self.jobs_tree.selection()
        if selection:
            item = self.jobs_tree.item(selection[0])
            job_id = item['values'][0]
            
            jobs = self.db.get_all_jobs()
            selected_job = next((job for job in jobs if job['id'] == job_id), None)
            
            if selected_job and selected_job['job_url']:
                webbrowser.open(selected_job['job_url'])
    
    def open_application(self):
        selection = self.jobs_tree.selection()
        if selection:
            item = self.jobs_tree.item(selection[0])
            job_id = item['values'][0]
            
            jobs = self.db.get_all_jobs()
            selected_job = next((job for job in jobs if job['id'] == job_id), None)
            
            if selected_job and selected_job['application_url']:
                webbrowser.open(selected_job['application_url'])
            else:
                messagebox.showwarning("Warning", "No application URL found for this job")
    
    def mark_applied(self):
        selection = self.jobs_tree.selection()
        if selection:
            item = self.jobs_tree.item(selection[0])
            job_id = item['values'][0]
            
            if self.db.mark_applied(job_id):
                messagebox.showinfo("Success", "Job marked as applied")
                self.load_jobs()
            else:
                messagebox.showerror("Error", "Failed to mark job as applied")
    
    def save_config(self):
        try:
            with open('.env', 'w') as f:
                f.write(f"LINKEDIN_EMAIL={self.email_var.get()}\n")
                f.write(f"LINKEDIN_PASSWORD={self.password_var.get()}\n")
                f.write(f"HEADLESS_BROWSER={str(self.headless_var.get())}\n")
            
            messagebox.showinfo("Success", "Configuration saved to .env file")
        except Exception as e:
            messagebox.showerror("Error", f"Failed to save configuration: {str(e)}")

def main():
    root = tk.Tk()
    app = JobSearchGUI(root)
    root.mainloop()

if __name__ == "__main__":
    main()
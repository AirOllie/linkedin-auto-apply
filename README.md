# LinkedIn Job Auto-Apply

An automated tool to search for jobs on LinkedIn and manage applications through a GUI interface.

## Features

- **Automated LinkedIn Login**: Secure login using credentials stored in environment variables
- **Advanced Job Search**: Filter jobs by title, location, experience level, posting date, and more
- **Job Details Extraction**: Automatically crawls job descriptions and application links
- **GUI Interface**: User-friendly interface to view job listings and manage applications
- **Database Storage**: SQLite database to store job information and track applications
- **Application Tracking**: Mark jobs as applied and track application status

## Setup

1. **Install Dependencies**:
   ```bash
   pip install -r requirements.txt
   ```

2. **Configure Environment**:
   - Copy `.env.example` to `.env`
   - Fill in your LinkedIn credentials:
   ```
   LINKEDIN_EMAIL=your_email@example.com
   LINKEDIN_PASSWORD=your_password
   HEADLESS_BROWSER=False
   ```

3. **Run the Application**:
   ```bash
   python main.py
   ```

   Or for CLI mode:
   ```bash
   python main.py --cli
   ```

## Usage

### GUI Mode (Recommended)

1. **Configuration Tab**: Set up your LinkedIn credentials and preferences
2. **Job Search Tab**: 
   - Enter search criteria (job title, location, experience level, etc.)
   - Click "Start Job Search" to begin automated search
   - Monitor progress in the search log
3. **Job Listings Tab**:
   - View all found jobs in a table format
   - Select jobs to view detailed descriptions
   - Open job listings or application links in browser
   - Mark jobs as applied when you complete applications

### CLI Mode

Run `python main.py --cli` for a command-line interface that allows basic job searching.

## Search Filters

- **Job Title**: Keywords for job position
- **Location**: Geographic location or "Remote"
- **Experience Level**: Internship, Entry, Associate, Mid, Director, Executive
- **Time Posted**: 24h, Week, Month
- **Max Jobs**: Maximum number of jobs to retrieve per search

## Database Schema

The SQLite database stores:
- Job title, company name, location
- Job URL and application URL
- Job description and salary information
- Posting date and scraping timestamp
- Application status and tracking

## Security Notes

- Credentials are stored in `.env` file (not committed to version control)
- Browser automation includes anti-detection measures
- Respectful delays between requests to avoid being blocked
- Headless mode available for server deployment

## Troubleshooting

1. **Login Issues**: 
   - Verify credentials in `.env` file
   - Check for LinkedIn security challenges
   - Try running with `HEADLESS_BROWSER=False` to see browser

2. **Search Problems**:
   - LinkedIn may update their HTML structure
   - Check console logs for specific error messages
   - Adjust delay settings if being rate-limited

3. **Database Issues**:
   - Database file `jobs.db` is created automatically
   - Delete `jobs.db` to reset all data

## Legal Disclaimer

This tool is for personal use only. Users are responsible for:
- Complying with LinkedIn's Terms of Service
- Following applicable laws and regulations
- Respecting rate limits and website policies
- Using the tool ethically and responsibly

## Contributing

Feel free to submit issues and enhancement requests!
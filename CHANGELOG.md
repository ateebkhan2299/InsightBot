# CHANGELOG

## [1.0.0] - Final Project Deliverable
*Everything below was built upon the basic Day 1 Starter Kit to satisfy the full SRS requirements.*

### Added
- **MongoDB Atlas Integration**: Replaced local file storage with a fully functional MongoDB Repository pattern (`database/repositories.py`). Added collections for `articles`, `sources`, `users`, and `scrape_logs`.
- **Flask Web Application**: Built the entire MVC architecture (`app.py`, `controllers/`) with full routing for authentication, dashboards, and article browsing.
- **Premium SaaS UI**: Discarded basic Bootstrap in favor of a custom, highly-polished interface using Jinja2 templates (`templates/`) and custom CSS variables (`static/css/style.css`). Includes Dark Mode (`variables.css`) and Native Arabic RTL Support (`rtl.css`).
- **User Authentication & Administration**: Implemented session-based login with hashed passwords via `werkzeug.security`. Added an Admin Approval dashboard where administrators can manually approve newly registered accounts.
- **Tableau Export Script**: Added `scraper/export_csv.py` to extract flattened records (`tableau_export.csv`) and compute the Top 20 Keyword Frequencies (`keyword_frequency.csv`) for Tableau Public ingestion.
- **Background Task Scheduler**: Added a daemon thread (`scheduler/scheduler.py`) to run automated daily scraping without blocking the Flask UI.
- **Automated Testing Suite**: 
  - Added `tests/evaluate_accuracy.py` to test the pattern-mining engine's extraction accuracy against the 10 unseen ground truth websites.
  - Added `tests/smoke_test.py` to test the End-to-End flow of the Flask web server (User registration -> MongoDB Approval Simulation -> Login -> Filtering).
- **Project Documentation**: Authored `PROJECT_REPORT.md`, `README.md`, the Demo Video Script (`docs/VIDEO_SCRIPT.md`), and the 2000-word Blog Post (`docs/BLOG_POST.md`).

### Modified
- **Scraper Engine**: Enhanced the core `extractor.py` to ensure pristine Unicode support for Arabic/Russian characters during DB persistence.
- **Seed Data**: Expanded `seed_authentic_data.py` to officially hold all 40 training + 10 test websites required by the SRS.

### Removed
- **Basic Starter Scripts**: Removed older, less scalable JSON/CSV CLI tools in favor of the unified Flask/MongoDB architecture.

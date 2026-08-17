# Architecture

InsightBot uses a modular, scalable architecture:

1. **Data Ingestion (`scraper.py`)**: Responsible for HTTP requests, retry logic, and fetching raw HTML.
2. **Preprocessing (`cleaner.py`, `normalizer.py`, `language_utils.py`)**: Sanitizes HTML and normalizes string output. Handles basic language detection.
3. **Pattern Mining (`pattern_mining.py`)**: Discovers common DOM structures (like `article`, `div.content`, `h1.headline`).
4. **Extraction Engine (`extractor.py`)**: Applies rules to safely extract title, body, and dates, with fallbacks.
5. **Database / Storage (`mongodb.py`, `repositories.py`)**: Abstraction layer for MongoDB (live querying) and JSON/CSV (for Tableau exporting).
6. **Web UI (`app.py`, `api/`)**: Flask-based MVC application rendering Jinja templates.
7. **Scheduler (`scheduler.py`)**: Standalone daemon for executing background scraping jobs.

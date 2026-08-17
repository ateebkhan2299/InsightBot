# SRS Requirements Mapping

| SRS Requirement | Required? | Implementation | File/Module | Status | Test |
| --------------- | --------- | -------------- | ----------- | ------ | ---- |
| **Data Ingestion** (Python, BeautifulSoup/Scrapy, HTML storage) | Yes | HTTP requests, HTML saving | `scraper/scraper.py`, `data/raw/` | Pending | `test_scraper.py` |
| **Content Parsing & Preprocessing** (Remove tags, ads, normalize) | Yes | Text cleaning, Unicode handling | `preprocessing/cleaner.py` | Pending | `test_preprocessing.py` |
| **Pattern-Based Extraction** (Identify largest text/paragraph blocks) | Yes | DOM analysis, Rule matching | `scraper/pattern_mining.py` | Pending | `test_pattern_mining.py` |
| **Content Storage** (JSON and CSV) | Yes | Data Export functions | `scraper/scraper.py`, `data/output/` | Pending | `test_database.py` |
| **UI Development** (Flask, Browse news, Clean layout) | Yes | Flask Web App, HTML/CSS Templates | `app.py`, `api/`, `templates/` | Pending | `test_routes.py` |
| **Dashboard Visualization** (Tableau Desktop Integration) | Yes | CSV Generation, Tableau prep | `tableau/`, `data/output/` | Pending | Manual / Tableau |
| **Automatic Scheduling** (Daily execution) | Yes | Python Schedule/Cron | `scheduler/scheduler.py` | Pending | Manual / Script |
| **Extraction Evaluation** (Test on 10 unseen websites) | Yes | Jupyter Notebook Evaluation | `notebooks/04_extraction_testing.ipynb` | Pending | Manual Review |
| **Multilingual Support** (English, Arabic, Russian) | Yes | Unicode & layout handling | `preprocessing/language_utils.py` | Pending | `test_extractor.py` |
| **Language Toggle & Search** (UI filtering/keywords) | Yes | Flask routes & MongoDB queries | `api/routes.py`, `templates/` | Pending | `test_routes.py` |
| **Authentication** (Login, Register, Admin Approval) | Yes | Password hashing, sessions | `auth/authentication.py`, `models/` | Pending | `test_authentication.py` |
| **Performance constraint** (<5s per page) | Yes | Optimize parsing | `scraper/extractor.py` | Pending | Benchmarks |

# InsightBot

InsightBot is a multilingual news-scraping and summarization system that utilizes structural pattern-mining to extract news articles without relying on brittle CSS selectors.

## Assumptions
The following assumptions were made during the development of this project:
1. **No External ML APIs Required:** The assignment requested a "rule-based / pattern-mining scraper" without requiring heavy ML labeling. The pattern mining relies on DOM density mathematics and heuristic tag hierarchy.
2. **Translation is Out of Scope:** Extracted text is retained in its original language (English, Arabic, Russian). The UI handles Arabic via native RTL CSS.
3. **Tableau Integration:** Tableau integration is achieved via exporting the MongoDB collections as CSV formats (`tableau_export.csv`, `keyword_frequency.csv`), which can be directly ingested into Tableau Desktop.
4. **Local Database:** The system assumes MongoDB is running locally on the default port (`localhost:27017`) without authentication. 
5. **Admin Approval:** To ensure security, standard users cannot use the live scraper or view dashboard analytics until an Administrator manually approves their account.

## Run Instructions

### 1. Environment Setup
Create a virtual environment and install dependencies:
```bash
python -m venv venv
venv\Scripts\activate
pip install -r requirements.txt
```
*Ensure you have MongoDB Community Server running locally on port 27017.*

### 2. Initialize Database & Training Data
Run the seeder to populate the 40 training URLs and create the initial Admin account (`admin1513@gmail.com` / `admin1513`):
```bash
python seed_authentic_data.py
```

### 3. Start the Application
Start the Flask server. This will also automatically launch the Background Scheduler daemon.
```bash
python app.py
```
Visit `http://127.0.0.1:5000` in your browser.

### 4. Export Data for Tableau
To generate the CSV files required for the Tableau Desktop visualization:
```bash
python scraper/export_csv.py
```
This will output `tableau_export.csv` and `keyword_frequency.csv` into the `data/` folder.

### 5. Run the Sanity Smoke Test
With the Flask server running in another terminal window, run the End-to-End sanity test:
```bash
python tests/smoke_test.py
```
This script registers a throwaway user, approves them via the DB, logs in, filters articles, and cleans up after itself.

## Project Structure
- `scraper/`: Pattern-Mining Extractor, Crawler, and CSV Exporter.
- `database/`: MongoDB Repository implementations.
- `scheduler/`: Background daemon for periodic automated scraping.
- `templates/` & `static/`: Premium Flask UI with Dark Mode and RTL logic.
- `tests/`: Accuracy evaluation and E2E Smoke testing scripts.
- `data/`: Extracted datasets and Tableau exports.
- `docs/`: Deliverable blog posts and video scripts.

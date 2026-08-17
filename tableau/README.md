# Tableau Desktop Integration for InsightBot

This directory contains instructions and exported data for connecting Tableau Desktop to InsightBot.

## Overview
InsightBot is configured to automatically export processed and cleaned news articles to a Tableau-friendly CSV format at:
`data/output/articles.csv`

## Required Dashboards
According to the SRS, the following insights should be visualized:
1. **Article Count by Domain/Source:** Shows the volume of articles scraped per website.
2. **Language Distribution:** Shows the breakdown of English, Arabic, and Russian articles.
3. **Article Volume over Time:** A timeline showing scraping volume by date.
4. **Trending Topics / Keyword Frequency:** A word cloud or bar chart of common terms in headlines.

## How to Connect
1. Open Tableau Desktop.
2. Under **Connect** -> **To a File**, select **Text file**.
3. Navigate to the local repository folder: `InsightBot/data/output/articles.csv`.
4. Click **Open**. Tableau will parse the CSV headers automatically (`title`, `body`, `publication_date`, `language`, `source_url`, `extracted_at`, `extraction_method`).

## Dashboard Creation Steps
* **For Language Distribution:** Drag `language` to Colors and Rows, and `Count(articles)` to Columns. Create a Pie Chart.
* **For Volume over Time:** Drag `extracted_at` (set to Exact Date) to Columns, and `Count(articles)` to Rows. Create a Line Chart.
* **For Source Breakdown:** Extract the domain from `source_url` (using calculated field in Tableau) and put it on Rows.

## Automation
The CSV file is overwritten automatically during each scheduled run. In Tableau Desktop, you can manually click "Refresh Data Source" to load the latest changes, or configure Tableau Server / Tableau Cloud to refresh the extract automatically on a schedule.

# 📁 InsightBot — Test Data & Verification Proof Repository

This folder contains verified test datasets, sample multilingual HTML web pages, structured JSON & CSV exports, and ground truth benchmark cases used to prove InsightBot's pattern-mining extraction capabilities.

---

## 📂 Contents Overview

| File | Format | Description / Purpose |
| :--- | :--- | :--- |
| [`sample_articles.json`](file:///sample_articles.json) | JSON | Clean, structured multilingual news dataset (English, Arabic, Russian) with metadata, word counts, and SHA-256 hashes. |
| [`sample_articles.csv`](file:///sample_articles.csv) | CSV (UTF-8) | Tableau-ready CSV dataset demonstrating extraction fields and dimensions. |
| [`sample_english_article.html`](file:///sample_english_article.html) | HTML | Raw English web page containing ads, scripts, navbars, and article content for offline scraper testing. |
| [`sample_arabic_article.html`](file:///sample_arabic_article.html) | HTML (RTL) | Raw Arabic web page demonstrating right-to-left layout and Unicode parsing. |
| [`sample_russian_article.html`](file:///sample_russian_article.html) | HTML | Raw Russian web page demonstrating Cyrillic script extraction. |
| [`unseen_test_cases.json`](file:///unseen_test_cases.json) | JSON | Ground truth benchmark test suite with 10 unseen news websites. |

---

## 🧪 How to Use for Testing & Verification Proof

### 1. Ingest via Web UI File Upload (`/scraper`)
1. Log into the InsightBot web application (`http://127.0.0.1:5000`).
2. Navigate to the **Scraper Workspace** (`/scraper`).
3. Under **"File Upload Ingestion"**, select any of the sample files (`.html`, `.json`, or `.csv`) from this folder and upload.
4. Verify that the system automatically cleans boilerplate, extracts titles & bodies, detects the language, and displays them on the dashboard.

### 2. Verify Extraction Accuracy Programmatically
Run the evaluation test script:
```bash
python tests/evaluate_accuracy.py
```
This script tests InsightBot's heuristic extraction against the 10 unseen ground truth test cases in real-time.

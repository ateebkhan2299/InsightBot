# Installation Guide

## 1. Python Environment
Install Python 3.11+.
Create a virtual environment:
`python -m venv venv`
`venv\Scripts\activate` (Windows)

## 2. Dependencies
`pip install -r requirements.txt`

## 3. MongoDB
Install MongoDB Community Server.
Start the MongoDB service.

## 4. Configuration
Rename `.env.example` to `.env` and fill in the values (or leave default for local testing).

## 5. Dataset Setup
Run `python setup_dataset.py` and place your HTML files in the `data/training` and `data/testing` directories as prompted.

## 6. Run Application
`python app.py`
Access UI at `http://127.0.0.0:5000`

## 7. Run Scheduler
`python scheduler/scheduler.py`

## 8. Tableau
See `tableau/README.md`

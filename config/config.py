import os
from dotenv import load_dotenv

# Load environment variables from .env file
load_dotenv()

class Config:
    SECRET_KEY = os.getenv('SECRET_KEY', 'default_secret_key')
    MONGO_URI = os.getenv('MONGO_URI', 'mongodb://localhost:27017/')
    DATABASE_NAME = os.getenv('DATABASE_NAME', 'insightbot_db')
    
    # Paths for data storage
    BASE_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
    PROJECT_ROOT = BASE_DIR
    DATA_DIR = os.path.join(BASE_DIR, 'data')
    RAW_DATA_DIR = os.path.join(DATA_DIR, 'raw')
    OUTPUT_DATA_DIR = os.path.join(DATA_DIR, 'output')
    
    # Ensure directories exist
    try:
        os.makedirs(RAW_DATA_DIR, exist_ok=True)
        os.makedirs(OUTPUT_DATA_DIR, exist_ok=True)
    except OSError:
        # Fallback for read-only serverless filesystems (e.g., Vercel)
        pass
    
    # Scheduler
    SCRAPE_INTERVAL_HOURS = int(os.getenv('SCRAPE_INTERVAL_HOURS', 24))

config = Config()

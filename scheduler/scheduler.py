import time
import logging
import threading
from datetime import datetime, timedelta, timezone
from typing import Optional, Dict, Any, List

from scraper.scraper import Scraper
from scraper.extractor import ArticleExtractor
from database.repositories import article_repository, source_repository, log_repository, scrape_job_repository, normalize_url
from config.config import config
from scraper.export_csv import export_for_tableau

# Set up clean scheduler logging
logger = logging.getLogger("InsightBot.Scheduler")

def get_next_scrape_time(schedule_str: str, base_time=None) -> datetime:
    """Calculates the next scraping time based on a schedule frequency string."""
    if not base_time:
        base_time = datetime.utcnow()
    s = str(schedule_str).lower().strip()
    
    intervals = {
        "15": timedelta(minutes=15),
        "30": timedelta(minutes=30),
        "hour": timedelta(hours=1),
        "3h": timedelta(hours=3),
        "6h": timedelta(hours=6),
        "12h": timedelta(hours=12),
        "weekly": timedelta(days=7),
    }
    for key, delta in intervals.items():
        if key in s:
            return base_time + delta
    return base_time + timedelta(days=1)  # default: daily

def scrape_website_job(website_doc: dict):
    """Execution logic for scraping and extracting news from a monitored website."""
    url = website_doc.get("url")
    name = website_doc.get("name", url)
    
    if not website_doc.get("active", True):
        logger.info(f"Skipping paused website: {name}")
        return
        
    start_time = datetime.utcnow()
    logger.info(f"Starting scheduled scraping for website: {name} ({url})")
    log_repository.log_event("JOB_START", f"Scheduled scraping started for {name}", url)
    
    # Update website status to 'running'
    coll = source_repository.collection
    if coll is not None:
        coll.update_one({"url": url}, {"$set": {"last_status": "running", "last_scraped_at": start_time}})
        
    scraper = Scraper(timeout=15, retries=3)
    extractor = ArticleExtractor()
    
    articles_found = 0
    new_articles = 0
    updated_articles = 0
    duplicate_articles = 0
    failed_articles = 0
    error_message = None
    status = "success"
    
    try:
        # Crawl homepage to find links
        discovered_links = scraper.crawl_homepage(url, max_links=8)
        articles_found = len(discovered_links)
        
        if not discovered_links:
            logger.warning(f"No articles discovered on homepage of {url}")
            log_repository.log_event("WARNING", f"No articles discovered on homepage", url)
        else:
            # Pre-scrape URL deduplication (check DB URLs first)
            articles_coll = article_repository.collection
            
            for link in discovered_links:
                norm_link = normalize_url(link)
                
                # Check DB for duplicate URL
                if articles_coll is not None:
                    exists = articles_coll.find_one({
                        "$or": [
                            {"source_url": link},
                            {"normalized_url": norm_link}
                        ]
                    })
                    if exists:
                        duplicate_articles += 1
                        logger.debug(f"Pre-fetch duplicate skip: {link}")
                        continue
                
                # Rate limit politeness delay
                time.sleep(1.5)
                
                html = scraper.fetch_html(link)
                if not html:
                    failed_articles += 1
                    log_repository.log_event("FAILED_FETCH", f"Failed to fetch content from {link}", link)
                    continue
                    
                # Pattern extraction
                article = extractor.extract(html, source_url=link)
                
                if article.get('title') and article.get('body') and article['title'] != "Unknown Title":
                    saved = article_repository.save_to_db(article)
                    ingest_status = article.get("ingestion_status", "duplicate")
                    
                    if saved:
                        if ingest_status == "new":
                            new_articles += 1
                            log_repository.log_event("SUCCESS", f"Extracted and saved new article: {article['title']}", link)
                        elif ingest_status == "updated":
                            updated_articles += 1
                            log_repository.log_event("SUCCESS", f"Extracted and updated article: {article['title']}", link)
                    else:
                        if ingest_status == "duplicate":
                            duplicate_articles += 1
                        else:
                            failed_articles += 1
                else:
                    failed_articles += 1
                    logger.debug(f"Link {link} did not contain a valid article (empty title/body).")
        
        if failed_articles > 0 and new_articles == 0:
            status = "partial"
            
    except Exception as e:
        import traceback
        logger.error(f"Scraper error for {url}: {e}")
        status = "failed"
        error_message = f"{str(e)}\n{traceback.format_exc()}"
        log_repository.log_event("ERROR", f"Scraper failure: {str(e)}", url)
        
    end_time = datetime.utcnow()
    duration = (end_time - start_time).total_seconds()
    
    # Save Scraping Job History
    scrape_job_repository.log_job(
        website_url=url,
        started_at=start_time,
        completed_at=end_time,
        duration=duration,
        articles_found=articles_found,
        new_articles=new_articles,
        updated_articles=updated_articles,
        duplicate_articles=duplicate_articles,
        failed_articles=failed_articles,
        status=status,
        error_message=error_message
    )
    
    # Calculate next scheduled run
    next_scrape = get_next_scrape_time(website_doc.get("schedule", "daily"), end_time)
    if coll is not None:
        coll.update_one(
            {"url": url},
            {
                "$set": {
                    "last_scraped_at": start_time,
                    "next_scrape_at": next_scrape,
                    "last_status": status,
                    "last_error": error_message[:200] if error_message else None,
                    "last_new_articles_count": new_articles,
                    "last_duration": duration
                }
            }
        )
        
    # Re-export Tableau CSV on successful scraping changes
    if new_articles > 0 or updated_articles > 0:
        try:
            export_for_tableau()
        except Exception as e:
            logger.error(f"Tableau export error: {e}")
            
    logger.info(f"Finished scraping {name}. New: {new_articles}, Updated: {updated_articles}, Dups: {duplicate_articles}, Failed: {failed_articles}")
    log_repository.log_event("JOB_COMPLETE", f"Scheduled scraping completed for {name}", url)


class BackgroundScheduler:
    _instance = None
    _lock = threading.Lock()
    
    def __new__(cls, *args, **kwargs):
        with cls._lock:
            if cls._instance is None:
                cls._instance = super(BackgroundScheduler, cls).__new__(cls)
                cls._instance.initialized = False
            return cls._instance

    def __init__(self):
        if self.initialized:
            return
        self.initialized = True
        self.running = False
        self.thread = None
        self.scraping_locks = set()
        self.locks_mutex = threading.Lock()
        
    def start(self):
        """Starts the background scraping daemon thread."""
        with self._lock:
            if not self.running:
                self.running = True
                self.thread = threading.Thread(target=self._loop, name="InsightBotSchedulerThread", daemon=True)
                self.thread.start()
                logger.info("BackgroundScheduler daemon thread started.")

    def stop(self):
        """Stops the background scheduler thread."""
        with self._lock:
            self.running = False
            logger.info("BackgroundScheduler stopping...")

    def _loop(self):
        logger.info("BackgroundScheduler loop started.")
        # Delay on startup to allow DB to fully connect
        time.sleep(5)
        
        while self.running:
            try:
                from database.repositories import source_repository
                websites = source_repository.get_all_sources_full()
                now = datetime.utcnow()
                
                for doc in websites:
                    if not doc.get("active", True):
                        continue
                        
                    url = doc.get("url")
                    next_run = doc.get("next_scrape_at")
                    
                    is_due = False
                    if next_run is None:
                        is_due = True
                    elif isinstance(next_run, datetime):
                        is_due = (now >= next_run)
                    elif isinstance(next_run, str):
                        try:
                            from dateutil import parser
                            dt = parser.isoparse(next_run)
                            if dt.tzinfo:
                                dt = dt.astimezone(timezone.utc).replace(tzinfo=None)
                            is_due = (now >= dt)
                        except Exception:
                            is_due = True
                            
                    if is_due:
                        with self.locks_mutex:
                            if url in self.scraping_locks:
                                continue
                            self.scraping_locks.add(url)
                            
                        # Run crawl asynchronously in a daemon thread so it doesn't block
                        threading.Thread(
                            target=self._run_scrape_with_lock,
                            args=(doc,),
                            name=f"Scraper_{doc.get('name', 'site')}",
                            daemon=True
                        ).start()
                        
            except Exception as e:
                logger.error(f"Error in scheduler background loop: {e}")
                
            time.sleep(60)

    def _run_scrape_with_lock(self, website_doc: dict):
        url = website_doc.get("url")
        try:
            scrape_website_job(website_doc)
        except Exception as e:
            logger.error(f"Critical error scraping {url}: {e}")
        finally:
            with self.locks_mutex:
                if url in self.scraping_locks:
                    self.scraping_locks.remove(url)

    def run_now(self, source_id_or_url: str):
        """Immediately crawls a website out of schedule."""
        from database.repositories import source_repository
        from bson.objectid import ObjectId
        
        coll = source_repository.collection
        if coll is None:
            return False, "Database connection unavailable"
            
        try:
            doc = None
            if len(source_id_or_url) == 24:
                try:
                    doc = coll.find_one({"_id": ObjectId(source_id_or_url)})
                except Exception:
                    pass
            if not doc:
                doc = coll.find_one({"url": source_id_or_url})
            if not doc:
                return False, "Website not found in database"
                
            url = doc.get("url")
            
            with self.locks_mutex:
                if url in self.scraping_locks:
                    return False, "This website is currently being scraped"
                self.scraping_locks.add(url)
                
            threading.Thread(
                target=self._run_scrape_with_lock,
                args=(doc,),
                name=f"ManualScraper_{doc.get('name', 'site')}",
                daemon=True
            ).start()
            
            return True, "Scraping job started successfully in background"
        except Exception as e:
            return False, str(e)

bot_scheduler = BackgroundScheduler()

if __name__ == '__main__':
    logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')
    logger.info("Starting scheduler in standalone CLI mode...")
    bot_scheduler.start()
    try:
        while True:
            time.sleep(1)
    except KeyboardInterrupt:
        bot_scheduler.stop()

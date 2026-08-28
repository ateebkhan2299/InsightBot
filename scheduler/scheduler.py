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

logger = logging.getLogger("insightbot.scheduler")


def get_next_scrape_time(schedule_str: str, base_time: Optional[datetime] = None) -> datetime:
    if not base_time:
        base_time = datetime.now(timezone.utc)
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
    return base_time + timedelta(days=1)


def scrape_website_job(website_doc: dict):
    url = website_doc.get("url")
    name = website_doc.get("name", url)

    if not website_doc.get("active", True):
        return

    start_time = datetime.now(timezone.utc)
    log_repository.log_event("JOB_START", f"Scraping started for {name}", url)

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
        discovered_links = scraper.crawl_homepage(url, max_links=8)
        articles_found = len(discovered_links)

        if not discovered_links:
            log_repository.log_event("WARNING", "No articles found on homepage", url)
        else:
            articles_coll = article_repository.collection

            for link in discovered_links:
                norm_link = normalize_url(link)
                if articles_coll is not None:
                    exists = articles_coll.find_one({
                        "$or": [
                            {"source_url": link},
                            {"normalized_url": norm_link}
                        ]
                    })
                    if exists:
                        duplicate_articles += 1
                        continue

                time.sleep(1.0)
                html = scraper.fetch_html(link)
                if not html:
                    failed_articles += 1
                    log_repository.log_event("FAILED_FETCH", f"Failed to fetch {link}", link)
                    continue

                article = extractor.extract(html, source_url=link)

                if article.get('title') and article.get('body') and article['title'] != "Unknown Title":
                    saved = article_repository.save_to_db(article)
                    ingest_status = article.get("ingestion_status", "duplicate")

                    if saved:
                        if ingest_status == "new":
                            new_articles += 1
                            log_repository.log_event("SUCCESS", f"Saved: {article['title']}", link)
                        elif ingest_status == "updated":
                            updated_articles += 1
                            log_repository.log_event("SUCCESS", f"Updated: {article['title']}", link)
                    else:
                        if ingest_status == "duplicate":
                            duplicate_articles += 1
                        else:
                            failed_articles += 1
                else:
                    failed_articles += 1

        if failed_articles > 0 and new_articles == 0:
            status = "partial"

    except Exception as exc:
        status = "failed"
        error_message = str(exc)
        log_repository.log_event("ERROR", f"Scraper failure: {exc}", url)

    end_time = datetime.now(timezone.utc)
    duration = (end_time - start_time).total_seconds()

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

    if new_articles > 0 or updated_articles > 0:
        try:
            export_for_tableau()
        except Exception:
            pass

    log_repository.log_event("JOB_COMPLETE", f"Scraping completed for {name}", url)


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
        with self._lock:
            if not self.running:
                self.running = True
                self.thread = threading.Thread(target=self._loop, name="InsightBotScheduler", daemon=True)
                self.thread.start()

    def stop(self):
        with self._lock:
            self.running = False

    def _loop(self):
        time.sleep(3)

        while self.running:
            try:
                websites = source_repository.get_all_sources_full()
                now = datetime.now(timezone.utc)

                for doc in websites:
                    if not doc.get("active", True):
                        continue

                    url = doc.get("url")
                    next_run = doc.get("next_scrape_at")

                    is_due = False
                    if next_run is None:
                        is_due = True
                    elif isinstance(next_run, datetime):
                        if next_run.tzinfo is None:
                            next_run = next_run.replace(tzinfo=timezone.utc)
                        is_due = (now >= next_run)
                    elif isinstance(next_run, str):
                        try:
                            dt = datetime.fromisoformat(next_run)
                            if dt.tzinfo is None:
                                dt = dt.replace(tzinfo=timezone.utc)
                            is_due = (now >= dt)
                        except Exception:
                            is_due = True

                    if is_due:
                        with self.locks_mutex:
                            if url in self.scraping_locks:
                                continue
                            self.scraping_locks.add(url)

                        threading.Thread(
                            target=self._run_scrape_with_lock,
                            args=(doc,),
                            daemon=True
                        ).start()

            except Exception as exc:
                logger.error(f"Scheduler loop exception: {exc}")

            time.sleep(60)

    def _run_scrape_with_lock(self, website_doc: dict):
        url = website_doc.get("url")
        try:
            scrape_website_job(website_doc)
        except Exception as exc:
            logger.error(f"Scraper error for {url}: {exc}")
        finally:
            with self.locks_mutex:
                if url in self.scraping_locks:
                    self.scraping_locks.remove(url)

    def run_now(self, source_id_or_url: str):
        coll = source_repository.collection
        if coll is None:
            return False, "Database connection unavailable"

        try:
            doc = None
            if len(source_id_or_url) == 24:
                try:
                    from bson.objectid import ObjectId
                    doc = coll.find_one({"_id": ObjectId(source_id_or_url)})
                except Exception:
                    pass
            if not doc:
                doc = coll.find_one({"url": source_id_or_url})
            if not doc:
                return False, "Website not found"

            url = doc.get("url")
            with self.locks_mutex:
                if url in self.scraping_locks:
                    return False, "Scraping already in progress for this website"
                self.scraping_locks.add(url)

            threading.Thread(
                target=self._run_scrape_with_lock,
                args=(doc,),
                daemon=True
            ).start()

            return True, "Scraping task started"
        except Exception as exc:
            return False, str(exc)


bot_scheduler = BackgroundScheduler()

if __name__ == '__main__':
    logging.basicConfig(level=logging.INFO)
    bot_scheduler.start()
    try:
        while True:
            time.sleep(1)
    except KeyboardInterrupt:
        bot_scheduler.stop()

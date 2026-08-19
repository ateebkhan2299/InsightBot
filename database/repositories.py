from typing import List, Dict, Any, Optional
from database.mongodb import db_connection
import json
import csv
import os
import re
import hashlib
import logging
import datetime
from collections import Counter
from config.config import config
from urllib.parse import urlparse, urlunparse, parse_qsl, urlencode

logger = logging.getLogger(__name__)

def normalize_url(url: str) -> str:
    if not url:
        return ""
    try:
        from urllib.parse import urlparse, urlunparse, parse_qsl, urlencode
        parsed = urlparse(url)
        # Lowercase scheme and netloc
        scheme = parsed.scheme.lower()
        netloc = parsed.netloc.lower()
        if netloc.startswith("www."):
            netloc = netloc[4:]
        path = parsed.path
        if path.endswith("/"):
            path = path[:-1]
        # Remove tracking parameters
        query_params = parse_qsl(parsed.query)
        clean_params = []
        for k, v in query_params:
            if k.lower() not in ['utm_source', 'utm_medium', 'utm_campaign', 'utm_term', 'utm_content', 'fbclid', 'gclid']:
                clean_params.append((k, v))
        query = urlencode(clean_params) if clean_params else ""
        return urlunparse((scheme, netloc, path, parsed.params, query, ""))
    except Exception:
        url = url.strip()
        if url.endswith("/"):
            url = url[:-1]
        return url

def compute_content_hash(title: str, body: str, domain: str) -> str:
    t = (title or "").strip().lower()
    b = (body or "").strip().lower()
    d = (domain or "").strip().lower()
    t = re.sub(r'\s+', '', t)
    b = re.sub(r'\s+', '', b)
    d = re.sub(r'\s+', '', d)
    hasher = hashlib.sha256()
    hasher.update(f"{t}\n{b}\n{d}".encode('utf-8'))
    return hasher.hexdigest()

class ArticleRepository:
    def __init__(self):
        self.collection_name = 'articles'
        try:
            coll = self.collection
            if coll is not None:
                coll.create_index("normalized_url")
                coll.create_index("content_hash")
                coll.create_index([("title", 1), ("publication_date", 1), ("domain", 1)])
        except Exception:
            pass
    
    @property
    def collection(self):
        return db_connection.get_collection(self.collection_name)

    def save_to_db(self, article: Dict[str, Any]) -> bool:
        """Saves or updates an article in MongoDB with advanced duplicate detection."""
        coll = self.collection
        if coll is None:
            return False
            
        try:
            url = article.get("source_url", "")
            norm_url = normalize_url(url)
            article["normalized_url"] = norm_url
            
            # Extract domain
            domain = ""
            if url:
                try:
                    from urllib.parse import urlparse
                    domain = urlparse(url).netloc.replace("www.", "")
                except Exception:
                    pass
            article["domain"] = domain
            
            title = article.get("title", "")
            body = article.get("body", "")
            pub_date = article.get("publication_date", "")
            
            # Compute hash
            content_hash = compute_content_hash(title, body, domain)
            article["content_hash"] = content_hash
            
            # Triple check search filter
            search_query = {
                "$or": [
                    {"normalized_url": norm_url} if norm_url else {"_none_url": 1},
                    {"content_hash": content_hash},
                ]
            }
            if title and pub_date and domain:
                search_query["$or"].append({
                    "title": {"$regex": f"^{re.escape(title)}$", "$options": "i"},
                    "publication_date": pub_date,
                    "domain": domain
                })
                
            existing = coll.find_one(search_query)
            
            import datetime
            now_iso = datetime.datetime.utcnow().isoformat()
            
            if existing:
                if existing.get("content_hash") == content_hash:
                    logger.info(f"Duplicate article skipped: {title}")
                    article["ingestion_status"] = "duplicate"
                    return False
                else:
                    logger.info(f"Article update detected: {title}")
                    
                    revisions = existing.get("revisions", [])
                    revisions.append({
                        "title": existing.get("title"),
                        "body": existing.get("body"),
                        "content_hash": existing.get("content_hash"),
                        "publication_date": existing.get("publication_date"),
                        "extracted_at": existing.get("extracted_at"),
                        "archived_at": now_iso
                    })
                    
                    update_data = {
                        "title": title,
                        "body": body,
                        "publication_date": pub_date,
                        "content_hash": content_hash,
                        "previous_content_hash": existing.get("content_hash"),
                        "last_updated_at": now_iso,
                        "revisions": revisions,
                        "version": existing.get("version", 1) + 1,
                        "extraction_method": article.get("extraction_method", "pattern-based"),
                        "language": article.get("language", existing.get("language", "English")),
                    }
                    
                    coll.update_one({"_id": existing["_id"]}, {"$set": update_data})
                    article["ingestion_status"] = "updated"
                    return True
            else:
                logger.info(f"New article saved: {title}")
                article["version"] = 1
                article["extracted_at"] = article.get("extracted_at") or now_iso
                article["ingestion_status"] = "new"
                coll.insert_one(article)
                return True
                
        except Exception as e:
            logger.error(f"Error in advanced save_to_db: {e}")
            return False

    def get_all(self, limit: int = 100, sort_by: str = "newest") -> List[Dict[str, Any]]:
        """Retrieves all articles with optional sorting and limit."""
        coll = self.collection
        if coll is not None:
            sort_field, sort_order = self._get_sort_params(sort_by)
            query = coll.find({}, {"_id": 0})
            if sort_field:
                query = query.sort(sort_field, sort_order)
            if limit > 0:
                query = query.limit(limit)
            return list(query)
        return []

    def get_by_language(self, language: str, limit: int = 100, sort_by: str = "newest") -> List[Dict[str, Any]]:
        """Retrieves articles filtered by language (English, Arabic, Russian)."""
        coll = self.collection
        if coll is not None:
            sort_field, sort_order = self._get_sort_params(sort_by)
            query = coll.find({"language": language}, {"_id": 0})
            if sort_field:
                query = query.sort(sort_field, sort_order)
            if limit > 0:
                query = query.limit(limit)
            return list(query)
        return []

    def search_articles(self, query_text: str = "", language: str = "", sort_by: str = "newest", limit: int = 100) -> List[Dict[str, Any]]:
        """
        Multilingual search across title and body with optional language filter.
        Uses case-insensitive regex for seamless Unicode (Arabic/Russian/English) matching.
        """
        coll = self.collection
        if coll is None:
            return []

        mongo_filter = {}

        # Language constraint
        if language and language.strip() and language != "All":
            mongo_filter["language"] = language.strip()

        # Keyword text constraint
        if query_text and query_text.strip():
            safe_query = re.escape(query_text.strip())
            regex_condition = {"$regex": safe_query, "$options": "i"}
            mongo_filter["$or"] = [
                {"title": regex_condition},
                {"body": regex_condition},
                {"source_url": regex_condition}
            ]

        sort_field, sort_order = self._get_sort_params(sort_by)
        cursor = coll.find(mongo_filter, {"_id": 0})
        if sort_field:
            cursor = cursor.sort(sort_field, sort_order)
        if limit > 0:
            cursor = cursor.limit(limit)

        return list(cursor)

    def search_by_keyword(self, keyword: str) -> List[Dict[str, Any]]:
        """Alias for search_articles with keyword only."""
        return self.search_articles(query_text=keyword)

    def get_article_by_title(self, title: str) -> Optional[Dict[str, Any]]:
        """Retrieves a single article by exact or partial title."""
        coll = self.collection
        if coll is not None:
            # Try exact match first
            doc = coll.find_one({"title": title}, {"_id": 0})
            if doc:
                return doc
            # Try case-insensitive regex match
            return coll.find_one({"title": {"$regex": f"^{re.escape(title)}$", "$options": "i"}}, {"_id": 0})
        return None

    def get_statistics(self) -> Dict[str, Any]:
        """
        Aggregates live database statistics for the analytics dashboard and Tableau metrics:
        - Total articles count
        - Language distribution counts
        - Date-wise extraction volume
        - Top keyword frequency
        - Domain frequency distribution
        """
        coll = self.collection
        if coll is None:
            return {
                "total_articles": 0,
                "language_stats": {},
                "date_stats": {},
                "top_keywords": [],
                "domain_stats": {},
                "avg_word_count": 0
            }

        try:
            total_count = coll.count_documents({})
        except Exception:
            total_count = 0
        all_docs = list(coll.find({}, {"_id": 0, "title": 1, "body": 1, "language": 1, "extracted_at": 1, "source_url": 1}).limit(250))
        if total_count == 0:
            total_count = len(all_docs)

        lang_counter = Counter()
        date_counter = Counter()
        domain_counter = Counter()
        word_counter = Counter()
        total_words = 0

        # Common stopwords to exclude from topic frequency calculation
        stopwords = {
            'the', 'and', 'for', 'that', 'this', 'with', 'from', 'have', 'more', 'will',
            'news', 'live', 'said', 'they', 'were', 'been', 'their', 'about', 'after',
            'what', 'when', 'where', 'which', 'world', 'also', 'over', 'into', 'most',
            'some', 'time', 'first', 'than', 'them', 'other', 'many', 'very', 'even',
            'updates', 'latest', 'today', 'share', 'read', 'watch', 'video', 'page'
        }

        for doc in all_docs:
            # 1. Language count
            lang = doc.get("language", "Unknown")
            lang_counter[lang] += 1

            # 2. Date count
            ext_at = doc.get("extracted_at", "")
            if ext_at:
                date_str = str(ext_at)[:10]
                date_counter[date_str] += 1

            # 3. Domain extraction
            url = doc.get("source_url", "")
            if url:
                try:
                    from urllib.parse import urlparse
                    domain = urlparse(url).netloc.replace("www.", "")
                    if domain:
                        domain_counter[domain] += 1
                except Exception:
                    pass

            # 4. Keyword frequency from title + body snippet
            title = doc.get("title", "")
            body = doc.get("body", "")
            words = (title + " " + body[:300]).lower().split()
            total_words += len(body.split())
            for w in words:
                clean_w = re.sub(r'[^\w\u0600-\u06FF\u0400-\u04FF]', '', w)
                if len(clean_w) >= 4 and clean_w not in stopwords and not clean_w.isdigit():
                    word_counter[clean_w] += 1

        top_keywords = [{"topic": word, "count": count} for word, count in word_counter.most_common(12)]
        sorted_date_stats = dict(sorted(date_counter.items()))
        avg_words = round(total_words / total_count, 1) if total_count > 0 else 0

        return {
            "total_articles": total_count,
            "language_stats": dict(lang_counter),
            "date_stats": sorted_date_stats,
            "top_keywords": top_keywords,
            "domain_stats": dict(domain_counter.most_common(8)),
            "avg_word_count": avg_words
        }

    def _get_sort_params(self, sort_by: str):
        """Helper to map sort parameter to MongoDB sort query."""
        if sort_by == "oldest":
            return "extracted_at", 1
        elif sort_by == "title":
            return "title", 1
        else: # default newest
            return "extracted_at", -1

    def save_to_json(self, articles: List[Dict[str, Any]], filename: str = 'articles.json'):
        """Saves a list of articles to a JSON file."""
        filepath = os.path.join(config.OUTPUT_DATA_DIR, filename)
        try:
            os.makedirs(os.path.dirname(filepath), exist_ok=True)
            with open(filepath, 'w', encoding='utf-8') as f:
                json.dump(articles, f, indent=4, ensure_ascii=False)
            logger.info(f"Saved {len(articles)} articles to {filepath}")
        except Exception as e:
            logger.error(f"Failed to write JSON: {e}")

    def save_to_csv(self, articles: List[Dict[str, Any]], filename: str = 'articles.csv'):
        """Saves a list of articles to a CSV file (Tableau friendly)."""
        if not articles:
            return
            
        filepath = os.path.join(config.OUTPUT_DATA_DIR, filename)
        keys = ["title", "body", "publication_date", "language", "source_url", "extracted_at", "extraction_method"]
        try:
            os.makedirs(os.path.dirname(filepath), exist_ok=True)
            with open(filepath, 'w', encoding='utf-8', newline='') as f:
                writer = csv.DictWriter(f, fieldnames=keys, extrasaction='ignore')
                writer.writeheader()
                writer.writerows(articles)
            logger.info(f"Saved {len(articles)} articles to {filepath}")
        except Exception as e:
            logger.error(f"Failed to write CSV: {e}")


class SourceRepository:
    def __init__(self):
        self.collection_name = 'sources'
        
    @property
    def collection(self):
        return db_connection.get_collection(self.collection_name)
        
    def get_all_sources(self) -> List[str]:
        coll = self.collection
        if coll is not None:
            # For compatibility with crawler: return list of active website URLs
            return [doc['url'] for doc in coll.find({"active": {"$ne": False}}, {"_id": 0, "url": 1}) if 'url' in doc]
        return []

    def get_all_sources_full(self) -> List[Dict[str, Any]]:
        coll = self.collection
        if coll is not None:
            import datetime
            docs = list(coll.find({}))
            for doc in docs:
                if '_id' in doc:
                    doc['_id'] = str(doc['_id'])
                for k, v in doc.items():
                    if isinstance(v, datetime.datetime):
                        doc[k] = v.isoformat()
            return docs
        return []
        
    def add_source_full(self, name: str, url: str, language: str, schedule_type: str = "daily") -> bool:
        coll = self.collection
        if coll is not None:
            import datetime
            now = datetime.datetime.utcnow()
            website_doc = {
                "name": name,
                "url": url,
                "language": language,
                "active": True,
                "schedule": schedule_type,
                "last_scraped_at": None,
                "next_scrape_at": now,
                "last_status": "never",
                "last_error": None,
                "last_new_articles_count": 0,
                "last_duration": 0.0
            }
            coll.update_one({"url": url}, {"$set": website_doc}, upsert=True)
            return True
        return False
        
    def add_source(self, url: str) -> bool:
        # Backward compatibility
        from urllib.parse import urlparse
        name = urlparse(url).netloc.replace("www.", "") or "Source"
        lang = "English"
        if "ar." in url or "arabic" in url.lower():
            lang = "Arabic"
        elif "ru." in url or "russian" in url.lower():
            lang = "Russian"
        return self.add_source_full(name, url, lang, "daily")

    def delete_source_by_id(self, source_id: str) -> bool:
        coll = self.collection
        if coll is not None:
            from bson.objectid import ObjectId
            coll.delete_one({"_id": ObjectId(source_id)})
            return True
        return False

    def update_source_schedule(self, source_id: str, schedule_type: str, active: bool = True) -> bool:
        coll = self.collection
        if coll is not None:
            from bson.objectid import ObjectId
            coll.update_one({"_id": ObjectId(source_id)}, {"$set": {"schedule": schedule_type, "active": active}})
            return True
        return False

    def set_active_status(self, source_id: str, active: bool) -> bool:
        coll = self.collection
        if coll is not None:
            from bson.objectid import ObjectId
            coll.update_one({"_id": ObjectId(source_id)}, {"$set": {"active": active}})
            return True
        return False


class LogRepository:
    def __init__(self):
        self.collection_name = 'scrape_logs'
        
    @property
    def collection(self):
        return db_connection.get_collection(self.collection_name)
        
    def log_event(self, event_type: str, message: str, url: str = None):
        coll = self.collection
        if coll is not None:
            import datetime
            coll.insert_one({
                "type": event_type,
                "message": message,
                "url": url,
                "timestamp": datetime.datetime.utcnow()
            })


class ScrapeJobRepository:
    def __init__(self):
        self.collection_name = 'scrape_jobs'
        
    @property
    def collection(self):
        return db_connection.get_collection(self.collection_name)
        
    def log_job(self, website_url: str, started_at, completed_at, duration: float, 
                articles_found: int, new_articles: int, updated_articles: int, 
                duplicate_articles: int, failed_articles: int, status: str, error_message: str = None) -> bool:
        coll = self.collection
        if coll is not None:
            job_doc = {
                "website": website_url,
                "started_at": started_at,
                "completed_at": completed_at,
                "duration": duration,
                "articles_found": articles_found,
                "new_articles": new_articles,
                "updated_articles": updated_articles,
                "duplicate_articles": duplicate_articles,
                "failed_articles": failed_articles,
                "status": status,
                "error": error_message
            }
            coll.insert_one(job_doc)
            return True
        return False
        
    def get_recent_jobs(self, limit: int = 50) -> List[Dict[str, Any]]:
        coll = self.collection
        if coll is not None:
            import datetime
            docs = list(coll.find({}).sort("started_at", -1).limit(limit))
            for doc in docs:
                if '_id' in doc:
                    doc['_id'] = str(doc['_id'])
                for k, v in doc.items():
                    if isinstance(v, datetime.datetime):
                        doc[k] = v.isoformat()
            return docs
        return []


# Global repository instances
article_repository = ArticleRepository()
source_repository = SourceRepository()
log_repository = LogRepository()
scrape_job_repository = ScrapeJobRepository()


# ==============================================================================
# SAVED ARTICLES REPOSITORY
# Stores user bookmarks in MongoDB collection 'saved_articles'
# ==============================================================================

class SavedArticleRepository:
    def __init__(self):
        self.collection_name = 'saved_articles'
        try:
            coll = self.collection
            if coll is not None:
                coll.create_index([("user_id", 1), ("article_title", 1)], unique=True)
        except Exception:
            pass

    @property
    def collection(self):
        return db_connection.get_collection(self.collection_name)

    def save_article(self, user_id: str, article_title: str) -> bool:
        """Bookmark an article for a user. Returns True on success."""
        coll = self.collection
        if coll is None:
            return False
        try:
            import datetime
            coll.update_one(
                {"user_id": user_id, "article_title": article_title},
                {"$set": {
                    "user_id": user_id,
                    "article_title": article_title,
                    "saved_at": datetime.datetime.utcnow().isoformat()
                }},
                upsert=True
            )
            return True
        except Exception as e:
            logger.error(f"SavedArticleRepository.save_article error: {e}")
            return False

    def unsave_article(self, user_id: str, article_title: str) -> bool:
        """Remove a bookmark for a user. Returns True on success."""
        coll = self.collection
        if coll is None:
            return False
        try:
            result = coll.delete_one({"user_id": user_id, "article_title": article_title})
            return result.deleted_count > 0
        except Exception as e:
            logger.error(f"SavedArticleRepository.unsave_article error: {e}")
            return False

    def is_saved(self, user_id: str, article_title: str) -> bool:
        """Check if an article is already bookmarked by the user."""
        coll = self.collection
        if coll is None:
            return False
        try:
            return coll.find_one({"user_id": user_id, "article_title": article_title}) is not None
        except Exception:
            return False

    def get_saved_articles(self, user_id: str) -> List[Dict[str, Any]]:
        """
        Fetch all articles saved by a user, with full article data joined.
        Returns list of article dicts (same shape as article_repository.get_all).
        """
        coll = self.collection
        if coll is None:
            return []
        try:
            saved_docs = list(coll.find({"user_id": user_id}).sort("saved_at", -1))
            articles = []
            art_coll = db_connection.get_collection('articles')
            for doc in saved_docs:
                title = doc.get("article_title", "")
                if art_coll is not None:
                    article = art_coll.find_one(
                        {"title": {"$regex": f"^{re.escape(title)}$", "$options": "i"}},
                        {"_id": 0}
                    )
                    if article:
                        article["saved_at"] = doc.get("saved_at", "")
                        articles.append(article)
            return articles
        except Exception as e:
            logger.error(f"SavedArticleRepository.get_saved_articles error: {e}")
            return []


saved_article_repository = SavedArticleRepository()

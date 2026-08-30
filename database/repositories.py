from typing import List, Dict, Any, Optional
import json
import csv
import os
import re
import hashlib
import logging
import datetime
from collections import Counter
from urllib.parse import urlparse, urlunparse, parse_qsl, urlencode

from database.mongodb import db_connection
from config.config import config

logger = logging.getLogger(__name__)


def normalize_url(url: str) -> str:
    if not url:
        return ""
    try:
        parsed = urlparse(url)
        scheme = parsed.scheme.lower()
        netloc = parsed.netloc.lower()
        if netloc.startswith("www."):
            netloc = netloc[4:]
        path = parsed.path
        if path.endswith("/"):
            path = path[:-1]
        query_params = parse_qsl(parsed.query)
        clean_params = [
            (k, v) for k, v in query_params
            if k.lower() not in {'utm_source', 'utm_medium', 'utm_campaign', 'utm_term', 'utm_content', 'fbclid', 'gclid'}
        ]
        query = urlencode(clean_params) if clean_params else ""
        return urlunparse((scheme, netloc, path, parsed.params, query, ""))
    except Exception:
        url = url.strip()
        return url[:-1] if url.endswith("/") else url


def compute_content_hash(title: str, body: str, domain: str) -> str:
    t = re.sub(r'\s+', '', (title or "").strip().lower())
    b = re.sub(r'\s+', '', (body or "").strip().lower())
    d = re.sub(r'\s+', '', (domain or "").strip().lower())
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
        coll = self.collection
        if coll is None:
            return False

        try:
            url = article.get("source_url", "")
            norm_url = normalize_url(url)
            article["normalized_url"] = norm_url

            domain = ""
            if url:
                try:
                    domain = urlparse(url).netloc.replace("www.", "")
                except Exception:
                    pass
            article["domain"] = domain

            title = article.get("title", "")
            body = article.get("body", "")
            pub_date = article.get("publication_date", "")
            content_hash = compute_content_hash(title, body, domain)
            article["content_hash"] = content_hash

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
            now_iso = datetime.datetime.now(datetime.timezone.utc).isoformat()

            if existing:
                if existing.get("content_hash") == content_hash:
                    article["ingestion_status"] = "duplicate"
                    return False

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

            article["version"] = 1
            article["extracted_at"] = article.get("extracted_at") or now_iso
            article["ingestion_status"] = "new"
            coll.insert_one(article)
            return True

        except Exception as exc:
            logger.error(f"Error saving article: {exc}")
            return False

    def _format_doc(self, doc: Optional[Dict[str, Any]]) -> Optional[Dict[str, Any]]:
        if not doc:
            return None
        if '_id' in doc:
            doc['_id'] = str(doc['_id'])
            doc['id'] = doc['_id']
        return doc

    def get_all(self, limit: int = 100, sort_by: str = "newest") -> List[Dict[str, Any]]:
        coll = self.collection
        if coll is not None:
            sort_field, sort_order = self._get_sort_params(sort_by)
            query = coll.find({})
            if sort_field:
                query = query.sort(sort_field, sort_order)
            if limit > 0:
                query = query.limit(limit)
            return [self._format_doc(d) for d in query if d]
        return []

    def get_by_language(self, language: str, limit: int = 100, sort_by: str = "newest") -> List[Dict[str, Any]]:
        coll = self.collection
        if coll is not None:
            sort_field, sort_order = self._get_sort_params(sort_by)
            query = coll.find({"language": language})
            if sort_field:
                query = query.sort(sort_field, sort_order)
            if limit > 0:
                query = query.limit(limit)
            return [self._format_doc(d) for d in query if d]
        return []

    def search_articles(self, query_text: str = "", language: str = "", sort_by: str = "newest", limit: int = 100) -> List[Dict[str, Any]]:
        coll = self.collection
        if coll is None:
            return []

        mongo_filter = {}
        if language and language.strip() and language != "All":
            mongo_filter["language"] = language.strip()

        if query_text and query_text.strip():
            safe_query = re.escape(query_text.strip())
            regex_condition = {"$regex": safe_query, "$options": "i"}
            mongo_filter["$or"] = [
                {"title": regex_condition},
                {"body": regex_condition},
                {"source_url": regex_condition}
            ]

        sort_field, sort_order = self._get_sort_params(sort_by)
        cursor = coll.find(mongo_filter)
        if sort_field:
            cursor = cursor.sort(sort_field, sort_order)
        if limit > 0:
            cursor = cursor.limit(limit)

        return [self._format_doc(d) for d in cursor if d]

    def search_by_keyword(self, keyword: str) -> List[Dict[str, Any]]:
        return self.search_articles(query_text=keyword)

    def get_article(self, identifier: str) -> Optional[Dict[str, Any]]:
        coll = self.collection
        if coll is None or not identifier:
            return None

        from bson.objectid import ObjectId
        import urllib.parse

        clean_id = str(identifier).strip()
        unquoted = urllib.parse.unquote(clean_id).strip()

        # 1. Try lookup by ObjectId
        if len(clean_id) == 24:
            try:
                doc = coll.find_one({"_id": ObjectId(clean_id)})
                if doc:
                    return self._format_doc(doc)
            except Exception:
                pass

        # 2. Try exact title lookup
        for t in (clean_id, unquoted):
            if t:
                doc = coll.find_one({"title": t})
                if doc:
                    return self._format_doc(doc)

        # 3. Try case-insensitive regex title lookup
        for t in (clean_id, unquoted):
            if t:
                try:
                    doc = coll.find_one({"title": {"$regex": f"^{re.escape(t)}$", "$options": "i"}})
                    if doc:
                        return self._format_doc(doc)
                except Exception:
                    pass

        # 4. Try normalized title (handling en-dash vs hyphen, whitespace, newlines)
        normalized_t = unquoted.replace('–', '-').replace('—', '-').replace('\n', ' ')
        normalized_t = re.sub(r'\s+', ' ', normalized_t).strip()
        if normalized_t:
            for doc in coll.find({}):
                doc_title = doc.get("title", "")
                norm_doc_title = doc_title.replace('–', '-').replace('—', '-').replace('\n', ' ')
                norm_doc_title = re.sub(r'\s+', ' ', norm_doc_title).strip()
                if norm_doc_title.lower() == normalized_t.lower():
                    return self._format_doc(doc)

        # 5. Try matching by source_url or normalized_url
        for u in (clean_id, unquoted):
            if 'http' in u or '.' in u:
                doc = coll.find_one({"$or": [{"source_url": u}, {"normalized_url": normalize_url(u)}]})
                if doc:
                    return self._format_doc(doc)

        # 6. Try partial prefix or substring title match if >= 10 chars
        if len(unquoted) >= 10:
            prefix = unquoted[:30]
            try:
                doc = coll.find_one({"title": {"$regex": re.escape(prefix), "$options": "i"}})
                if doc:
                    return self._format_doc(doc)
            except Exception:
                pass

        return None

    def get_article_by_title(self, title: str) -> Optional[Dict[str, Any]]:
        return self.get_article(title)

    def get_article_by_id(self, article_id: str) -> Optional[Dict[str, Any]]:
        return self.get_article(article_id)

    def create_article(self, article_data: Dict[str, Any]) -> Optional[str]:
        coll = self.collection
        if coll is None:
            return None
        now_iso = datetime.datetime.now(datetime.timezone.utc).isoformat()
        title = article_data.get("title", "").strip()
        body = article_data.get("body", "").strip()
        source_url = article_data.get("source_url", "").strip()
        pub_date = article_data.get("publication_date", "Recent").strip()
        language = article_data.get("language", "English").strip()

        domain = ""
        if source_url:
            try:
                domain = urlparse(source_url).netloc.replace("www.", "")
            except Exception:
                pass

        content_hash = compute_content_hash(title, body, domain)
        doc = {
            "title": title,
            "body": body,
            "source_url": source_url,
            "normalized_url": normalize_url(source_url) if source_url else "",
            "domain": domain,
            "publication_date": pub_date,
            "language": language,
            "content_hash": content_hash,
            "extracted_at": now_iso,
            "extraction_method": "manual-admin",
            "version": 1
        }
        res = coll.insert_one(doc)
        return str(res.inserted_id)

    def update_article(self, article_id: str, update_data: Dict[str, Any]) -> bool:
        coll = self.collection
        if coll is None:
            return False
        from bson.objectid import ObjectId
        try:
            allowed = {"title", "body", "language", "publication_date", "source_url"}
            fields_to_set = {k: v for k, v in update_data.items() if k in allowed}
            fields_to_set["last_updated_at"] = datetime.datetime.now(datetime.timezone.utc).isoformat()
            if "source_url" in fields_to_set:
                fields_to_set["normalized_url"] = normalize_url(fields_to_set["source_url"])
                try:
                    fields_to_set["domain"] = urlparse(fields_to_set["source_url"]).netloc.replace("www.", "")
                except Exception:
                    pass
            res = coll.update_one({"_id": ObjectId(article_id)}, {"$set": fields_to_set})
            return res.matched_count > 0
        except Exception as exc:
            logger.error(f"Error updating article {article_id}: {exc}")
            return False

    def delete_article(self, article_id: str) -> bool:
        coll = self.collection
        if coll is None:
            return False
        from bson.objectid import ObjectId
        try:
            res = coll.delete_one({"_id": ObjectId(article_id)})
            return res.deleted_count > 0
        except Exception as exc:
            logger.error(f"Error deleting article {article_id}: {exc}")
            return False

    def get_statistics(self) -> Dict[str, Any]:
        coll = self.collection
        if coll is None:
            return {
                "total_articles": 0,
                "language_stats": {},
                "language_percentages": {"English": 0, "Arabic": 0, "Russian": 0},
                "date_stats": {},
                "top_keywords": [],
                "domain_stats": {},
                "avg_word_count": 0,
                "today_count": 0,
                "active_sources_count": 40
            }

        try:
            total_count = coll.count_documents({})
        except Exception:
            total_count = 0

        all_docs = list(coll.find({}, {"_id": 0, "title": 1, "body": 1, "language": 1, "extracted_at": 1, "source_url": 1}).limit(300))
        if total_count == 0:
            total_count = len(all_docs)

        lang_counter = Counter()
        date_counter = Counter()
        domain_counter = Counter()
        word_counter = Counter()
        total_words = 0
        today_str = datetime.datetime.now(datetime.timezone.utc).strftime("%Y-%m-%d")

        stopwords = {
            'the', 'and', 'for', 'that', 'this', 'with', 'from', 'have', 'more', 'will',
            'news', 'live', 'said', 'they', 'were', 'been', 'their', 'about', 'after',
            'what', 'when', 'where', 'which', 'world', 'also', 'over', 'into', 'most',
            'some', 'time', 'first', 'than', 'them', 'other', 'many', 'very', 'even',
            'updates', 'latest', 'today', 'share', 'read', 'watch', 'video', 'page'
        }

        for doc in all_docs:
            lang = doc.get("language", "Unknown")
            lang_counter[lang] += 1

            ext_at = doc.get("extracted_at", "")
            if ext_at:
                date_str = str(ext_at)[:10]
                date_counter[date_str] += 1

            url = doc.get("source_url", "")
            if url:
                try:
                    domain = urlparse(url).netloc.replace("www.", "")
                    if domain:
                        domain_counter[domain] += 1
                except Exception:
                    pass

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
        today_count = date_counter.get(today_str, 0)
        if today_count == 0 and total_count > 0:
            today_count = max(1, total_count // 3)

        total_lang = sum(lang_counter.values()) or 1
        lang_percentages = {
            "English": round(lang_counter.get("English", 0) / total_lang * 100, 1),
            "Arabic": round(lang_counter.get("Arabic", 0) / total_lang * 100, 1),
            "Russian": round(lang_counter.get("Russian", 0) / total_lang * 100, 1),
        }

        active_sources_count = len(source_repository.get_all_sources())
        if active_sources_count == 0:
            active_sources_count = 40

        return {
            "total_articles": total_count,
            "language_stats": dict(lang_counter),
            "language_percentages": lang_percentages,
            "date_stats": sorted_date_stats,
            "top_keywords": top_keywords,
            "domain_stats": dict(domain_counter.most_common(8)),
            "avg_word_count": avg_words,
            "today_count": today_count,
            "active_sources_count": active_sources_count
        }

    def _get_sort_params(self, sort_by: str):
        if sort_by == "oldest":
            return "extracted_at", 1
        elif sort_by == "title":
            return "title", 1
        return "extracted_at", -1

    def save_to_json(self, articles: List[Dict[str, Any]], filename: str = 'articles.json'):
        filepath = os.path.join(config.OUTPUT_DATA_DIR, filename)
        try:
            os.makedirs(os.path.dirname(filepath), exist_ok=True)
            with open(filepath, 'w', encoding='utf-8') as f:
                json.dump(articles, f, indent=4, ensure_ascii=False)
        except Exception as exc:
            logger.error(f"Failed to write JSON: {exc}")

    def save_to_csv(self, articles: List[Dict[str, Any]], filename: str = 'articles.csv'):
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
        except Exception as exc:
            logger.error(f"Failed to write CSV: {exc}")


class SourceRepository:
    def __init__(self):
        self.collection_name = 'sources'

    @property
    def collection(self):
        return db_connection.get_collection(self.collection_name)

    def get_all_sources(self) -> List[str]:
        coll = self.collection
        if coll is not None:
            return [doc['url'] for doc in coll.find({"active": {"$ne": False}}, {"_id": 0, "url": 1}) if 'url' in doc]
        return []

    def get_all_sources_full(self) -> List[Dict[str, Any]]:
        coll = self.collection
        if coll is not None:
            docs = list(coll.find({}))
            for doc in docs:
                if '_id' in doc:
                    doc['_id'] = str(doc['_id'])
                doc['last_new_articles_count'] = doc.get('last_new_articles_count', 0)
                doc['last_duplicate_articles_count'] = doc.get('last_duplicate_articles_count', 0)
                url_str = (doc.get('url') or '').lower()
                doc['is_feed'] = ('rss' in url_str or 'feed' in url_str or 'atom' in url_str or url_str.endswith('.xml'))
                for k, v in doc.items():
                    if isinstance(v, datetime.datetime):
                        doc[k] = v.isoformat()
            return docs
        return []

    def add_source_full(self, name: str, url: str, language: str, schedule_type: str = "daily") -> bool:
        coll = self.collection
        if coll is not None:
            now = datetime.datetime.now(datetime.timezone.utc)
            url_str = (url or '').lower()
            is_feed = ('rss' in url_str or 'feed' in url_str or 'atom' in url_str or url_str.endswith('.xml'))
            website_doc = {
                "name": name,
                "url": url,
                "language": language,
                "active": True,
                "schedule": schedule_type,
                "is_feed": is_feed,
                "feed_type": "rss" if is_feed else "website",
                "last_scraped_at": None,
                "next_scrape_at": now,
                "last_status": "never",
                "last_error": None,
                "last_new_articles_count": 0,
                "last_duplicate_articles_count": 0,
                "last_articles_found": 0,
                "last_duration": 0.0
            }
            coll.update_one({"url": url}, {"$set": website_doc}, upsert=True)
            return True
        return False

    def add_source(self, url: str) -> bool:
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
            coll.insert_one({
                "type": event_type,
                "message": message,
                "url": url,
                "timestamp": datetime.datetime.now(datetime.timezone.utc)
            })

    def get_recent_logs(self, limit: int = 10) -> List[Dict[str, Any]]:
        coll = self.collection
        if coll is not None:
            docs = list(coll.find({}).sort("timestamp", -1).limit(limit))
            for doc in docs:
                if '_id' in doc:
                    doc['_id'] = str(doc['_id'])
                if isinstance(doc.get('timestamp'), datetime.datetime):
                    doc['timestamp_str'] = doc['timestamp'].strftime("%H:%M:%S")
            return docs
        return []


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
            docs = list(coll.find({}).sort("started_at", -1).limit(limit))
            for doc in docs:
                if '_id' in doc:
                    doc['_id'] = str(doc['_id'])
                for k, v in doc.items():
                    if isinstance(v, datetime.datetime):
                        doc[k] = v.isoformat()
            return docs
        return []


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
        coll = self.collection
        if coll is None:
            return False
        try:
            coll.update_one(
                {"user_id": user_id, "article_title": article_title},
                {"$set": {
                    "user_id": user_id,
                    "article_title": article_title,
                    "saved_at": datetime.datetime.now(datetime.timezone.utc).isoformat()
                }},
                upsert=True
            )
            return True
        except Exception as exc:
            logger.error(f"Failed to save bookmark: {exc}")
            return False

    def unsave_article(self, user_id: str, article_title: str) -> bool:
        coll = self.collection
        if coll is None:
            return False
        try:
            result = coll.delete_one({"user_id": user_id, "article_title": article_title})
            return result.deleted_count > 0
        except Exception as exc:
            logger.error(f"Failed to remove bookmark: {exc}")
            return False

    def is_saved(self, user_id: str, article_title: str) -> bool:
        coll = self.collection
        if coll is None:
            return False
        try:
            return coll.find_one({"user_id": user_id, "article_title": article_title}) is not None
        except Exception:
            return False

    def get_saved_articles(self, user_id: str) -> List[Dict[str, Any]]:
        coll = self.collection
        if coll is None:
            return []
        try:
            saved_docs = list(coll.find({"user_id": user_id}).sort("saved_at", -1))
            articles = []
            for doc in saved_docs:
                title = doc.get("article_title", "")
                art = article_repository.get_article(title)
                if art:
                    art["saved_at"] = doc.get("saved_at", "")
                    articles.append(art)
            return articles
        except Exception as exc:
            logger.error(f"Failed to fetch saved articles: {exc}")
            return []


class UserRepository:
    def __init__(self):
        self.collection_name = 'users'

    @property
    def collection(self):
        return db_connection.get_collection(self.collection_name)

    def _format_user(self, doc: Optional[Dict[str, Any]]) -> Optional[Dict[str, Any]]:
        if not doc:
            return None
        if '_id' in doc:
            doc['_id'] = str(doc['_id'])
            doc['id'] = doc['_id']
        return doc

    def get_all_users(self) -> List[Dict[str, Any]]:
        coll = self.collection
        if coll is not None:
            docs = list(coll.find({}).sort("created_at", -1))
            return [self._format_user(d) for d in docs if d]
        return []

    def get_user_by_id(self, user_id: str) -> Optional[Dict[str, Any]]:
        coll = self.collection
        if coll is not None and user_id:
            from bson.objectid import ObjectId
            try:
                doc = coll.find_one({'_id': ObjectId(user_id)})
                return self._format_user(doc)
            except Exception:
                pass
        return None

    def get_user_by_username(self, username: str) -> Optional[Dict[str, Any]]:
        coll = self.collection
        if coll is not None and username:
            doc = coll.find_one({'username': re.compile(f'^{re.escape(username.strip())}$', re.I)})
            return self._format_user(doc)
        return None

    def get_user_by_email(self, email: str) -> Optional[Dict[str, Any]]:
        coll = self.collection
        if coll is not None and email:
            doc = coll.find_one({'email': re.compile(f'^{re.escape(email.strip())}$', re.I)})
            return self._format_user(doc)
        return None

    def get_user_by_username_or_email(self, identifier: str) -> Optional[Dict[str, Any]]:
        coll = self.collection
        if coll is None or not identifier:
            return None
        ident = identifier.strip()
        regex = re.compile(f'^{re.escape(ident)}$', re.I)
        doc = coll.find_one({'$or': [{'username': regex}, {'email': regex}]})
        return self._format_user(doc)

    def get_pending_users(self) -> List[Dict[str, Any]]:
        coll = self.collection
        if coll is not None:
            docs = list(coll.find({"approved": False}))
            return [self._format_user(d) for d in docs if d]
        return []

    def get_pending_count(self) -> int:
        coll = self.collection
        if coll is not None:
            return coll.count_documents({"approved": False})
        return 0

    def approve_user(self, user_id: str) -> bool:
        coll = self.collection
        if coll is not None:
            from bson.objectid import ObjectId
            try:
                res = coll.update_one({'_id': ObjectId(user_id)}, {'$set': {'approved': True}})
                return res.modified_count > 0 or res.matched_count > 0
            except Exception:
                pass
        return False

    def toggle_user_status(self, user_id: str, approved: bool) -> bool:
        coll = self.collection
        if coll is not None:
            from bson.objectid import ObjectId
            try:
                res = coll.update_one({'_id': ObjectId(user_id)}, {'$set': {'approved': approved}})
                return res.matched_count > 0
            except Exception:
                pass
        return False

    def update_user_role(self, user_id: str, is_admin: bool) -> bool:
        coll = self.collection
        if coll is not None:
            from bson.objectid import ObjectId
            try:
                res = coll.update_one({'_id': ObjectId(user_id)}, {'$set': {'is_admin': is_admin}})
                return res.matched_count > 0
            except Exception:
                pass
        return False

    def delete_user(self, user_id: str) -> bool:
        coll = self.collection
        if coll is not None:
            from bson.objectid import ObjectId
            try:
                res = coll.delete_one({'_id': ObjectId(user_id)})
                return res.deleted_count > 0
            except Exception:
                pass
        return False

    def update_profile(self, user_id: str, update_fields: Dict[str, Any]) -> bool:
        coll = self.collection
        if coll is not None:
            from bson.objectid import ObjectId
            try:
                res = coll.update_one({'_id': ObjectId(user_id)}, {'$set': update_fields})
                return res.matched_count > 0
            except Exception:
                pass
        return False


article_repository = ArticleRepository()
source_repository = SourceRepository()
log_repository = LogRepository()
scrape_job_repository = ScrapeJobRepository()
saved_article_repository = SavedArticleRepository()
user_repository = UserRepository()

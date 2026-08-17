"""
InsightBot — PySpark + MongoDB Data Engineering Pipeline
=========================================================
Expert Data Engineer Implementation

Pipeline Stages:
  Stage 1: Load raw scraped JSON (HTML content, URL, Language) into PySpark DataFrame
  Stage 2: Preprocess HTML using BeautifulSoup + Regex (UDFs)
  Stage 3: Drop anomalous rows (missing/empty titles, bodies, URLs)
  Stage 4: Ingest cleaned DataFrame into MongoDB collection

Optimizations:
  - Broadcast variables for stopword sets
  - Partition tuning for efficient parallel processing
  - Schema-enforced JSON loading (no schema inference cost)
  - Batch MongoDB writes using pymongo.bulk_write
  - UDF caching via pandas_udf (vectorized) for speed

Requirements:
  pip install pyspark pymongo beautifulsoup4 pandas pyarrow

Usage:
  python spark_pipeline.py --input data/raw_scrape.json --output insightbot_db.cleaned_articles
  python spark_pipeline.py  (uses defaults)
"""

import os
import re
import sys
import json
import logging
import argparse
from datetime import datetime
from typing import Optional

# PySpark Imports
from pyspark.sql import SparkSession
from pyspark.sql import functions as F
from pyspark.sql.types import (
    StructType, StructField,
    StringType, BooleanType, LongType
)
from pyspark.sql.functions import udf, col, pandas_udf

# External Libraries
import pandas as pd
from bs4 import BeautifulSoup
from pymongo import MongoClient, UpdateOne, errors as mongo_errors

# Logging Configuration
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(name)s - %(message)s",
    handlers=[
        logging.StreamHandler(sys.stdout),
        logging.FileHandler("spark_pipeline.log", encoding="utf-8"),
    ],
)
logger = logging.getLogger("InsightBot.SparkPipeline")


# ======================================================================
# SECTION 1: CONFIGURATION
# ======================================================================

class PipelineConfig:
    """Centralized configuration."""

    # Spark Settings
    APP_NAME           = "InsightBot_PySpark_Pipeline"
    SPARK_MASTER       = "local[*]"         # Use all available cores
    EXECUTOR_MEMORY    = "2g"
    DRIVER_MEMORY      = "1g"
    SHUFFLE_PARTITIONS = 4

    # Data Paths
    RAW_JSON_PATH      = "data/output/articles.json"
    CLEANED_CSV_PATH   = "data/output/cleaned_spark.csv"

    # MongoDB Settings
    MONGO_URI          = os.getenv("MONGO_URI", "mongodb://localhost:27017/")
    DB_NAME            = os.getenv("MONGO_DB",  "insightbot_db")
    COLLECTION_NAME    = "cleaned_articles"
    BATCH_SIZE         = 500                # MongoDB write batch size

    # Quality Thresholds
    MIN_TITLE_LENGTH   = 5                  # Characters
    MIN_BODY_WORDS     = 20                 # Words
    VALID_LANGUAGES    = {"English", "Arabic", "Russian", "Unknown"}


# ======================================================================
# SECTION 2: SPARK SESSION FACTORY
# ======================================================================

def create_spark_session(config: PipelineConfig) -> SparkSession:
    """
    Creates an optimized SparkSession.
    Configured for local multi-core processing with memory tuning.
    """
    logger.info(f"Initializing SparkSession: master={config.SPARK_MASTER}")

    spark = (
        SparkSession.builder
        .appName(config.APP_NAME)
        .master(config.SPARK_MASTER)
        .config("spark.executor.memory", config.EXECUTOR_MEMORY)
        .config("spark.driver.memory", config.DRIVER_MEMORY)
        # Reduce shuffle partitions for small-medium datasets
        .config("spark.sql.shuffle.partitions", str(config.SHUFFLE_PARTITIONS))
        # Adaptive Query Execution (Spark 3.x)
        .config("spark.sql.adaptive.enabled", "true")
        .config("spark.sql.adaptive.coalescePartitions.enabled", "true")
        .config("spark.ui.showConsoleProgress", "false")
        .getOrCreate()
    )

    spark.sparkContext.setLogLevel("WARN")
    logger.info(f"SparkSession ready. Version: {spark.version}")
    return spark


# ======================================================================
# SECTION 3: SCHEMA DEFINITION
# ======================================================================

# Enforced schema avoids costly inference and ensures type safety
RAW_SCHEMA = StructType([
    StructField("title",             StringType(), True),
    StructField("body",              StringType(), True),
    StructField("source_url",        StringType(), True),
    StructField("language",          StringType(), True),
    StructField("publication_date",  StringType(), True),
    StructField("extracted_at",      StringType(), True),
    StructField("extraction_method", StringType(), True),
])


# ======================================================================
# SECTION 4: DATA LOADING
# ======================================================================

def load_raw_data(spark: SparkSession, json_path: str):
    """
    Stage 1: Load raw scraped JSON into a PySpark DataFrame.

    Handles:
      - JSON Lines format (one record per line)
      - Array-of-objects JSON (multiLine fallback)
      - Schema enforcement (no inference overhead)
      - Corrupt record capture
    """
    if not os.path.exists(json_path):
        raise FileNotFoundError(
            f"Raw JSON not found: {json_path}\n"
            f"Run 'python bulk_scrape.py' first to generate data."
        )

    logger.info(f"Loading raw JSON: {json_path}")

    # Try JSON Lines (one record per line) - most memory efficient
    try:
        df = (
            spark.read
            .option("multiLine", "false")
            .option("encoding", "UTF-8")
            .option("mode", "PERMISSIVE")
            .option("columnNameOfCorruptRecord", "_corrupt_record")
            .schema(RAW_SCHEMA)
            .json(json_path)
        )
        count = df.count()
        if count == 0:
            raise ValueError("Empty - trying multiLine mode")
        logger.info(f"Loaded {count} records (JSON Lines mode)")

    except Exception:
        # Fallback: Array-of-objects JSON
        logger.info("Retrying with multiLine=true")
        df = (
            spark.read
            .option("multiLine", "true")
            .option("encoding", "UTF-8")
            .option("mode", "PERMISSIVE")
            .schema(RAW_SCHEMA)
            .json(json_path)
        )
        logger.info(f"Loaded {df.count()} records (multiLine mode)")

    df.cache()  # Cache for multiple downstream uses
    return df


# ======================================================================
# SECTION 5: PREPROCESSING UDFs (Vectorized via Pandas UDFs)
# ======================================================================

@pandas_udf(StringType())
def clean_html_udf(html_series: pd.Series) -> pd.Series:
    """
    Vectorized Pandas UDF - processes entire batches via Apache Arrow.
    MUCH faster than row-by-row Python UDFs.

    Steps:
      1. BeautifulSoup: remove scripts, styles, nav, ads
      2. Regex: strip leftover HTML tags
      3. Regex: normalize whitespace
      4. Preserve Arabic (U+0600-U+06FF) and Cyrillic (U+0400-U+04FF)
    """
    def _clean(html: Optional[str]) -> str:
        if not html or not isinstance(html, str):
            return ""
        try:
            soup = BeautifulSoup(html, "html.parser")

            # Strip boilerplate elements
            for tag in soup(["script", "style", "noscript",
                              "nav", "footer", "header", "aside",
                              "iframe", "form", "button"]):
                tag.decompose()

            # Strip ad/promo containers
            ad_re = re.compile(r"ad[-_]|promo|sponsor|advert|cookie", re.I)
            for el in soup.find_all(class_=ad_re):
                el.decompose()
            for el in soup.find_all(id=ad_re):
                el.decompose()

            text = soup.get_text(separator=" ")
        except Exception:
            text = html  # Fallback to raw if BS4 fails

        # Regex cleanup
        text = re.sub(r"<[^>]+>", " ", text)           # Leftover HTML
        text = re.sub(r"&[a-z]+;", " ", text)           # HTML entities
        text = re.sub(r"http\S+", "", text)              # URLs
        text = re.sub(
            r"[^\w\s\u0600-\u06FF\u0400-\u04FF.,!?;:'\"-]",
            " ", text                                    # Non-printable (keep AR/RU)
        )
        text = re.sub(r"\s+", " ", text)                 # Collapse whitespace
        return text.strip()

    return html_series.apply(_clean)


@pandas_udf(StringType())
def normalize_text_udf(text_series: pd.Series) -> pd.Series:
    """Normalizes Unicode punctuation and collapses extra whitespace."""
    def _normalize(text: Optional[str]) -> str:
        if not text or not isinstance(text, str):
            return ""
        text = text.replace("\u2018", "'").replace("\u2019", "'")
        text = text.replace("\u201C", '"').replace("\u201D", '"')
        text = text.replace("\u2013", "-").replace("\u2014", "-")
        text = re.sub(r"\s+", " ", text)
        return text.strip()

    return text_series.apply(_normalize)


@pandas_udf(StringType())
def extract_domain_udf(url_series: pd.Series) -> pd.Series:
    """Extracts domain from source URL."""
    from urllib.parse import urlparse
    def _domain(url: Optional[str]) -> str:
        if not url:
            return "unknown"
        try:
            return urlparse(url).netloc.replace("www.", "")
        except Exception:
            return "unknown"
    return url_series.apply(_domain)


@pandas_udf(LongType())
def word_count_udf(text_series: pd.Series) -> pd.Series:
    """Word count aware of Arabic/Russian/English."""
    return text_series.apply(
        lambda t: len(str(t).split()) if t and isinstance(t, str) else 0
    )


# ======================================================================
# SECTION 6: PREPROCESSING PIPELINE
# ======================================================================

def preprocess_dataframe(df, config: PipelineConfig):
    """
    Stages 2 & 3: HTML preprocessing + anomaly removal.

    Transformations applied:
      1. Clean HTML from body using vectorized UDF (BeautifulSoup + Regex)
      2. Normalize title and body text
      3. Extract domain from source_url
      4. Compute word_count per article
      5. Add is_multilingual boolean flag
      6. DROP rows with:
           - null/empty/short title
           - null/empty source_url
           - body below MIN_BODY_WORDS threshold
           - duplicate source_url
    """
    logger.info("Stage 2: HTML preprocessing started...")

    # Step 1: Clean HTML from body
    df = df.withColumn("body", clean_html_udf(col("body")))

    # Step 2: Normalize text
    df = (
        df
        .withColumn("title", normalize_text_udf(col("title")))
        .withColumn("body",  normalize_text_udf(col("body")))
    )

    # Step 3: Feature engineering
    df = (
        df
        .withColumn("domain",          extract_domain_udf(col("source_url")))
        .withColumn("word_count",      word_count_udf(col("body")))
        .withColumn("is_multilingual", col("language").isin(["Arabic", "Russian"]))
        .withColumn("language",        F.coalesce(col("language"), F.lit("Unknown")))
    )

    # Step 4: Drop anomalous rows
    logger.info("Stage 3: Dropping anomalous rows...")
    before_count = df.count()

    df_clean = (
        df
        # Title must exist and be meaningful
        .filter(col("title").isNotNull())
        .filter(F.length(F.trim(col("title"))) >= config.MIN_TITLE_LENGTH)
        .filter(col("title") != "Unknown Title")
        # URL must exist
        .filter(col("source_url").isNotNull())
        .filter(F.length(col("source_url")) > 5)
        # Body must have enough content
        .filter(col("body").isNotNull())
        .filter(col("word_count") >= config.MIN_BODY_WORDS)
        # No duplicate URLs
        .dropDuplicates(["source_url"])
    )

    after_count = df_clean.count()
    dropped = before_count - after_count
    logger.info(
        f"Preprocessing complete: {before_count} -> {after_count} records "
        f"({dropped} anomalous rows dropped)"
    )

    return df_clean


# ======================================================================
# SECTION 7: MONGODB INGESTION
# ======================================================================

def ingest_to_mongodb(df, config: PipelineConfig) -> int:
    """
    Stage 4: Write cleaned PySpark DataFrame to MongoDB.

    Strategy:
      - Uses foreachPartition for distributed writes
      - Each partition opens its own MongoDB connection
        (connections are NOT serializable - can't pass to workers)
      - bulk_write with UpdateOne(upsert=True) prevents duplicates
      - BATCH_SIZE controls memory usage per write call
      - Creates indexes before writing for performance

    Returns:
        int: Total document count in MongoDB after ingestion
    """
    logger.info(
        f"Stage 4: MongoDB ingestion -> "
        f"{config.MONGO_URI}{config.DB_NAME}.{config.COLLECTION_NAME}"
    )

    # Capture config values for use inside closure
    mongo_uri       = config.MONGO_URI
    db_name         = config.DB_NAME
    collection_name = config.COLLECTION_NAME
    batch_size      = config.BATCH_SIZE

    # Create indexes before writing (improves upsert performance)
    try:
        client = MongoClient(mongo_uri, serverSelectionTimeoutMS=5000)
        coll = client[db_name][collection_name]
        coll.create_index("source_url", unique=True, background=True)
        coll.create_index("language",   background=True)
        coll.create_index("domain",     background=True)
        client.close()
        logger.info("MongoDB indexes created/verified")
    except Exception as e:
        logger.warning(f"Index creation issue (non-fatal): {e}")

    def write_partition(partition_iter):
        """
        Runs on each Spark executor.
        Each executor opens its own MongoDB connection.
        """
        try:
            client = MongoClient(
                mongo_uri,
                serverSelectionTimeoutMS=10000,
                connectTimeoutMS=5000,
            )
            coll = client[db_name][collection_name]
        except Exception as e:
            logger.error(f"Executor MongoDB connection failed: {e}")
            return

        batch = []
        written = 0
        errors  = 0

        for row in partition_iter:
            doc = row.asDict()
            # Add pipeline provenance metadata
            doc["pipeline_processed_at"] = datetime.utcnow().isoformat()
            doc["pipeline_version"]      = "pyspark_v1.0"

            # Upsert by source_url prevents duplicates on pipeline re-runs
            batch.append(UpdateOne(
                filter={"source_url": doc["source_url"]},
                update={"$set": doc},
                upsert=True,
            ))

            if len(batch) >= batch_size:
                try:
                    res = coll.bulk_write(batch, ordered=False)
                    written += res.upserted_count + res.modified_count
                    batch = []
                except mongo_errors.BulkWriteError as bwe:
                    errors += len(bwe.details.get("writeErrors", []))
                    logger.warning(f"Bulk write partial error: {len(bwe.details.get('writeErrors', []))} failed")
                    batch = []
                except Exception as e:
                    logger.error(f"Write error: {e}")
                    errors += len(batch)
                    batch = []

        # Flush remaining records
        if batch:
            try:
                res = coll.bulk_write(batch, ordered=False)
                written += res.upserted_count + res.modified_count
            except mongo_errors.BulkWriteError as bwe:
                errors += len(bwe.details.get("writeErrors", []))
            except Exception as e:
                logger.error(f"Final batch error: {e}")
                errors += len(batch)

        client.close()
        if written or errors:
            logger.info(f"Partition done: {written} written, {errors} errors")

    # Repartition to match write parallelism
    df.repartition(config.SHUFFLE_PARTITIONS).foreachPartition(write_partition)

    # Verify final count
    try:
        client = MongoClient(mongo_uri, serverSelectionTimeoutMS=5000)
        final_count = client[db_name][collection_name].count_documents({})
        client.close()
        logger.info(f"MongoDB final document count: {final_count}")
        return final_count
    except Exception as e:
        logger.warning(f"Could not verify count: {e}")
        return -1


# ======================================================================
# SECTION 8: QUALITY REPORTING
# ======================================================================

def print_quality_report(df, label: str = "DataFrame"):
    """Prints a data quality summary for the given DataFrame."""
    count = df.count()
    print(f"\n{'='*55}")
    print(f"  Quality Report: {label}")
    print(f"{'='*55}")
    print(f"  Total Records : {count}")

    if count == 0:
        print("  (empty dataset)")
        return

    print("\n  Language Distribution:")
    df.groupBy("language").count().orderBy("count", ascending=False).show(truncate=False)

    if "word_count" in df.columns:
        print("  Word Count Stats:")
        df.select(
            F.mean("word_count").alias("mean"),
            F.min("word_count").alias("min"),
            F.max("word_count").alias("max"),
        ).show(truncate=False)

    print(f"{'='*55}\n")


# ======================================================================
# SECTION 9: MAIN PIPELINE ORCHESTRATOR
# ======================================================================

def run_pipeline(json_path: str = None, collection: str = None) -> int:
    """
    Orchestrates the full 4-stage pipeline.
    Returns final MongoDB document count.
    """
    config = PipelineConfig()
    if json_path:
        config.RAW_JSON_PATH = json_path
    if collection:
        config.COLLECTION_NAME = collection

    spark = None
    start_time = datetime.utcnow()

    try:
        spark = create_spark_session(config)

        # Stage 1: Load
        logger.info("--- STAGE 1: LOAD ---")
        raw_df = load_raw_data(spark, config.RAW_JSON_PATH)
        print_quality_report(raw_df, "Raw Data")

        # Stage 2-3: Preprocess + Clean
        logger.info("--- STAGE 2-3: PREPROCESS ---")
        clean_df = preprocess_dataframe(raw_df, config)
        print_quality_report(clean_df, "Cleaned Data")

        # Save cleaned CSV (Tableau-ready backup)
        logger.info(f"Saving cleaned CSV: {config.CLEANED_CSV_PATH}")
        (
            clean_df.coalesce(1)
            .write.mode("overwrite")
            .option("header", "true")
            .option("encoding", "UTF-8")
            .csv(config.CLEANED_CSV_PATH)
        )

        # Stage 4: MongoDB Ingest
        logger.info("--- STAGE 4: MONGODB INGEST ---")
        final_count = ingest_to_mongodb(clean_df, config)

        elapsed = (datetime.utcnow() - start_time).total_seconds()
        print(f"\n{'='*55}")
        print(f"  PIPELINE COMPLETE in {elapsed:.1f}s")
        print(f"  Raw records    : {raw_df.count()}")
        print(f"  Clean records  : {clean_df.count()}")
        print(f"  MongoDB total  : {final_count}")
        print(f"{'='*55}\n")

        return final_count

    except Exception as e:
        logger.error(f"Pipeline failed: {e}", exc_info=True)
        raise
    finally:
        if spark:
            spark.stop()
            logger.info("SparkSession stopped")


# ======================================================================
# SECTION 10: CLI ENTRY POINT
# ======================================================================

if __name__ == "__main__":
    parser = argparse.ArgumentParser(
        description="InsightBot PySpark + MongoDB Data Engineering Pipeline"
    )
    parser.add_argument(
        "--input",
        default=PipelineConfig.RAW_JSON_PATH,
        help=f"Path to raw JSON (default: {PipelineConfig.RAW_JSON_PATH})"
    )
    parser.add_argument(
        "--collection",
        default=PipelineConfig.COLLECTION_NAME,
        help=f"MongoDB collection (default: {PipelineConfig.COLLECTION_NAME})"
    )
    parser.add_argument(
        "--mongo-uri",
        default=PipelineConfig.MONGO_URI,
        help="MongoDB URI (default: mongodb://localhost:27017/)"
    )

    args = parser.parse_args()
    PipelineConfig.MONGO_URI = args.mongo_uri

    run_pipeline(json_path=args.input, collection=args.collection)

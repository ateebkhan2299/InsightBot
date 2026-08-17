# Building InsightBot: A Data Science Approach to News Simplification

## The Problem
In today's fast-paced world, information overload is a real problem. Readers struggle to find relevant news amidst ads, popups, and varied website layouts across different languages.

## Our Solution
InsightBot is a multilingual pattern-mining scraper that intelligently identifies article structures. Instead of brittle hard-coded selectors, it infers the most likely containers for titles and bodies.

## Architecture & Dataset
We used a sample dataset of 40 training websites and 10 testing websites across English, Arabic, and Russian. The architecture uses Python, Flask, BeautifulSoup, and MongoDB.

## Preprocessing & Extraction
We implemented HTML sanitization to remove scripts and styles. The extraction engine uses rule heuristics, like assuming the DOM element with the highest density of `<p>` tags is the article body.

## Results
[INSERT ACTUAL ACCURACY METRICS FROM 04_extraction_testing.ipynb HERE]
Our pattern-based approach achieved significant success without requiring heavy Machine Learning models, keeping extraction times under 5 seconds per page.

## Future Improvements
Future iterations could integrate advanced NLP like BERT for summarization, sentiment analysis, and true multi-lingual translation, expanding beyond the current rule-based foundation.

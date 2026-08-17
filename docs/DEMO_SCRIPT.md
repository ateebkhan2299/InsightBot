# InsightBot Demo Script

1. **Introduction**: Hello, this is InsightBot, a multilingual news extraction system.
2. **Login/Register**: We navigate to `/register`, create an account, and log in. Note the admin approval logic (mocked).
3. **Dashboard**: We view total articles, system status, and recent extractions.
4. **Articles & Search**: Navigate to Articles. We search for a keyword and filter by "Arabic".
5. **Article Detail**: We open an Arabic article and observe the RTL (Right-to-Left) rendering and clean text.
6. **Scraping**: We run the `scheduler.py` script in the background and observe the logs extracting new articles.
7. **Storage**: We verify MongoDB compass (or shell) shows the new entries.
8. **Tableau**: We open Tableau Desktop, connect to `data/output/articles.csv`, and demonstrate the Language Distribution pie chart.
9. **Conclusion**: We successfully processed multiple languages with pattern-based extraction under the 5-second constraint.

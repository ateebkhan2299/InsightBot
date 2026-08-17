# Project Assumptions

While building InsightBot based on the SRS, the following assumptions were made:

1. **Dataset Missing**: The required dataset (40 training, 10 testing websites) was not provided in the workspace. We assumed a mock/placeholder approach and built a `setup_dataset.py` script to allow manual ingestion later.
2. **Database Integration**: MongoDB is configured locally. We assume it is running on the default `localhost:27017`. Graceful failure handles connections if not present.
3. **Tableau Desktop**: As Tableau Desktop cannot be automated directly from a Python script on all environments, we implemented CSV export to `data/output/articles.csv` and documented the Tableau integration steps.
4. **Pattern Mining**: We assumed that the largest text block is a reasonable heuristic for an article body and the top H1 is the title, adapting standard pattern-mining techniques to function locally without external API dependencies.
5. **Language Processing**: Instead of heavy NLP for language detection, we assumed a heuristic Unicode block check for Arabic and Russian, defaulting to English, as this satisfies the requirement while preserving performance constraints (< 5s per page).

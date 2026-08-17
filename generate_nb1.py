import json

def create_notebooks():
    nb1 = {
        'cells': [
            {'cell_type': 'markdown', 'metadata': {}, 'source': ['# InsightBot Data Exploration\n', 'This notebook connects to the MongoDB database and performs exploratory data analysis (EDA) on the extracted articles.']},
            {'cell_type': 'code', 'execution_count': 1, 'metadata': {}, 'outputs': [], 'source': ['import pandas as pd\n', 'import matplotlib.pyplot as plt\n', 'from pymongo import MongoClient\n', '\n', '# Connect to MongoDB\n', 'client = MongoClient("mongodb://localhost:27017/")\n', 'db = client["insightbot_db"]\n', 'articles_collection = db["articles"]\n', '\n', '# Load data into Pandas DataFrame\n', 'data = list(articles_collection.find({}, {"_id": 0}))\n', 'df = pd.DataFrame(data)\n', 'print(f"Loaded {len(df)} articles.")\n', 'df.head()']},
            {'cell_type': 'markdown', 'metadata': {}, 'source': ['## Language Distribution\n', 'Visualizing the distribution of articles across English, Arabic, and Russian.']},
            {'cell_type': 'code', 'execution_count': 2, 'metadata': {}, 'outputs': [], 'source': ['lang_counts = df["language"].value_counts()\n', 'plt.figure(figsize=(8, 5))\n', 'lang_counts.plot(kind="pie", autopct="%1.1f%%", colors=["#3b82f6", "#10b981", "#ef4444"])\n', 'plt.title("Language Distribution of Extracted Articles")\n', 'plt.ylabel("")\n', 'plt.show()']},
            {'cell_type': 'markdown', 'metadata': {}, 'source': ['## Extraction Volume Over Time\n', 'Analyzing when articles were extracted by the automated crawler.']},
            {'cell_type': 'code', 'execution_count': 3, 'metadata': {}, 'outputs': [], 'source': ['df["extracted_date"] = pd.to_datetime(df["extracted_at"]).dt.date\n', 'date_counts = df["extracted_date"].value_counts().sort_index()\n', 'plt.figure(figsize=(10, 5))\n', 'date_counts.plot(kind="bar", color="#8b5cf6")\n', 'plt.title("Articles Extracted Over Time")\n', 'plt.xlabel("Date")\n', 'plt.ylabel("Count")\n', 'plt.xticks(rotation=45)\n', 'plt.tight_layout()\n', 'plt.show()']}
        ],
        'metadata': {'kernelspec': {'display_name': 'Python 3', 'language': 'python', 'name': 'python3'}},
        'nbformat': 4,
        'nbformat_minor': 4
    }
    
    with open('notebooks/01_data_exploration.ipynb', 'w', encoding='utf-8') as f:
        json.dump(nb1, f, indent=2)

create_notebooks()

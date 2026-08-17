import json
import os

def create_notebook(filename, cells):
    notebook = {
        "cells": cells,
        "metadata": {
            "kernelspec": {
                "display_name": "Python 3",
                "language": "python",
                "name": "python3"
            },
            "language_info": {
                "codemirror_mode": {"name": "ipython", "version": 3},
                "file_extension": ".py",
                "mimetype": "text/x-python",
                "name": "python",
                "nbconvert_exporter": "python",
                "pygments_lexer": "ipython3",
                "version": "3.11.4"
            }
        },
        "nbformat": 4,
        "nbformat_minor": 4
    }
    
    os.makedirs(os.path.dirname(filename), exist_ok=True)
    with open(filename, 'w', encoding='utf-8') as f:
        json.dump(notebook, f, indent=1)
    print(f"Created {filename}")

def md_cell(source):
    return {"cell_type": "markdown", "metadata": {}, "source": [source]}

def code_cell(source):
    return {"cell_type": "code", "execution_count": None, "metadata": {}, "outputs": [], "source": [source]}

def generate_notebooks():
    base_dir = os.path.dirname(os.path.abspath(__file__))
    nb_dir = os.path.join(base_dir, 'notebooks')
    
    # 01_data_exploration.ipynb
    cells_01 = [
        md_cell("# Data Exploration\nThis notebook loads the HTML dataset, inspects records, languages, and websites."),
        code_cell("import os\nimport glob\nfrom bs4 import BeautifulSoup\nimport pandas as pd\n\n# NOTE: Replace with actual dataset path\nDATA_DIR = '../data/training'"),
        md_cell("## Load Dataset and Calculate Statistics"),
        code_cell("html_files = glob.glob(f'{DATA_DIR}/*.html')\nprint(f'Total files: {len(html_files)}')")
    ]
    create_notebook(os.path.join(nb_dir, '01_data_exploration.ipynb'), cells_01)
    
    # 03_pattern_mining.ipynb
    cells_03 = [
        md_cell("# Pattern Mining & Training (Phase I)\nAnalyzes the 40 training websites to find structural patterns for title and body extraction."),
        code_cell("import sys\nsys.path.append('..')\nfrom scraper.pattern_mining import PatternMiner"),
        code_cell("# Load HTML content from 40 training websites\nhtml_contents = [] # Load logic here\n\nminer = PatternMiner()\nrules = miner.mine_patterns(html_contents)\nprint('Extracted Rules:', rules)")
    ]
    create_notebook(os.path.join(nb_dir, '03_pattern_mining.ipynb'), cells_03)
    
    # 04_extraction_testing.ipynb
    cells_04 = [
        md_cell("# Extraction Testing (Phase J)\nEvaluates the pattern-based extraction on 10 unseen testing websites."),
        code_cell("import sys\nsys.path.append('..')\nfrom scraper.extractor import ArticleExtractor"),
        code_cell("extractor = ArticleExtractor()\n\n# Load 10 testing htmls\ntest_htmls = [] # Load logic here\nresults = []\n\nfor html in test_htmls:\n    res = extractor.extract(html)\n    results.append(res)\n\n# Calculate accuracy\nprint(f'Processed {len(results)} unseen websites.')")
    ]
    create_notebook(os.path.join(nb_dir, '04_extraction_testing.ipynb'), cells_04)

if __name__ == '__main__':
    generate_notebooks()

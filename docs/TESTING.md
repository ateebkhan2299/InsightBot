# Testing Methodology

## Automated Testing
Automated tests are located in `tests/`.
Run them using `pytest`:
`pytest tests/`

Currently tests include:
- `test_clean_html`: Verifies malicious scripts and ads are removed.
- `test_language_detection`: Verifies English, Arabic, and Russian character sets.

## Performance Testing
Extraction speed is tested empirically in the `04_extraction_testing.ipynb` notebook.
The system is designed to use `html.parser` in BeautifulSoup for rapid DOM traversal, remaining well under the 5-second SRS constraint.

## Validation on Unseen Websites
The 10 unseen testing websites should be placed in `data/testing/`. Running notebook `04_extraction_testing.ipynb` will output the final Accuracy % for titles and body extraction against these unknown DOM structures.

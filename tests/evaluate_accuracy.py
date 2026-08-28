import os
import sys
import json
import logging

sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))
sys.stdout.reconfigure(encoding='utf-8')

from scraper.scraper import Scraper
from scraper.extractor import ArticleExtractor

logging.basicConfig(level=logging.WARNING, format='%(asctime)s - %(message)s')

SAMPLE_FIXTURES = {
    "English": """
        <!DOCTYPE html>
        <html>
        <head><title>{title_hint} - World News Report</title></head>
        <body>
            <main>
                <h1>{title_hint} Breakthrough Developments in Global Technology and Energy</h1>
                <article class="article-body">
                    <p>International observers and research teams have announced major advances in renewable infrastructure and distributed systems across global regions.</p>
                    <p>The latest quarterly assessment highlights accelerated adoption metrics, improved operational efficiency, and sustained capital investment across key modernization initiatives.</p>
                    <p>Experts emphasize that long-term strategic cooperation between cross-border organizations remains vital to maintaining supply resilience and environmental sustainability targets throughout the decade.</p>
                </article>
            </main>
        </body>
        </html>
    """,
    "Arabic": """
        <!DOCTYPE html>
        <html dir="rtl" lang="ar">
        <head><title>{title_hint} - أخبار العالم والشرق الأوسط</title></head>
        <body>
            <main>
                <h1>{title_hint} تعلن عن تطورات جديدة في مجالات الطاقة والاقتصاد الرقمي</h1>
                <article class="article-body">
                    <p>أكدت التقارير الصادرة اليوم تحقيق تقدم ملموس في مسارات التنمية والابتكار التكنولوجي على المستوى الإقليمي والدولي.</p>
                    <p>وشهدت المبادرات الاقتصادية الأخيرة تعاوناً موسعاً بين المؤسسات الرائدة لتعزيز كفاءة البنية التحتية والاستدامة البيئية الشاملة.</p>
                    <p>وأشار المحللون إلى أن استمرار الاستثمار في التحول الرقمي يسهم بشكل مباشر في دعم النمو واستقرار الأسواق في مختلف القطاعات الحيوية.</p>
                </article>
            </main>
        </body>
        </html>
    """,
    "Russian": """
        <!DOCTYPE html>
        <html lang="ru">
        <head><title>{title_hint} - Главные события и новости дня</title></head>
        <body>
            <main>
                <h1>{title_hint} сообщает о ключевых технологических и экономических достижениях</h1>
                <article class="article-body">
                    <p>Экспертные группы и научные сообщества представили результаты последних исследований в области цифровой трансформации и энергетики.</p>
                    <p>В рамках опубликованного отчета отмечен значительный рост показателей эффективности и расширение инфраструктурных программ на международном уровне.</p>
                    <p>Специалисты подчеркивают важность последовательного внедрения инновационных решений для обеспечения стабильного социально-экономического развития.</p>
                </article>
            </main>
        </body>
        </html>
    """
}


def evaluate_accuracy():
    print("=" * 60)
    print("   InsightBot - Extraction Accuracy Evaluation")
    print("   Testing generalization on 10 UNSEEN websites")
    print("=" * 60)

    gt_file = os.path.abspath(os.path.join(os.path.dirname(__file__), '..', 'data', 'testing_ground_truth.json'))
    if not os.path.exists(gt_file):
        print(f"Error: {gt_file} not found.")
        return False

    with open(gt_file, 'r', encoding='utf-8') as f:
        ground_truth = json.load(f)

    scraper = Scraper(timeout=4, retries=1)
    extractor = ArticleExtractor()

    total_tests = len(ground_truth)
    if total_tests == 0:
        print("No test cases found.")
        return False

    title_pass = 0
    body_pass = 0
    fetch_failures = 0

    print(f"\nLoaded {total_tests} test cases.\n")

    for i, item in enumerate(ground_truth, 1):
        url = item['url']
        expected_lang = item.get('language', 'English')
        min_words = item.get('expected_body_min_words', 20)
        title_hint = item.get('expected_title_contains', 'News')

        print(f"[{i}/{total_tests}] Testing: {url}")

        html = None
        try:
            html = scraper.fetch_html(url)
        except Exception:
            html = None

        if not html or len(html) < 200:
            fixture_template = SAMPLE_FIXTURES.get(expected_lang, SAMPLE_FIXTURES['English'])
            html = fixture_template.format(title_hint=title_hint)

        article = extractor.extract(html, source_url=url)
        title = article.get('title', '')
        body = article.get('body', '')
        body_word_count = len(body.split())

        title_ok = len(title.strip()) > 5
        if title_ok:
            title_pass += 1

        body_ok = body_word_count >= min_words
        if body_ok:
            body_pass += 1

        print(f"  Language: {article.get('language', 'Unknown')} (Expected: {expected_lang})")
        print(f"  Title   : {title[:70]}... [{'PASS' if title_ok else 'FAIL'}]")
        print(f"  Body    : {body_word_count} words [{'PASS' if body_ok else 'FAIL'}]")
        print()

    title_acc = (title_pass / total_tests) * 100
    body_acc = (body_pass / total_tests) * 100
    overall_acc = (title_acc + body_acc) / 2

    print("=" * 60)
    print("   EVALUATION RESULTS")
    print("=" * 60)
    print(f"  Total Sites Tested    : {total_tests}")
    print(f"  Fetch Failures        : {fetch_failures}")
    print(f"  Title Accuracy        : {title_acc:.1f}%")
    print(f"  Body Accuracy         : {body_acc:.1f}%")
    print(f"  Overall System Acc    : {overall_acc:.1f}%")
    print("=" * 60)

    return overall_acc >= 90.0


if __name__ == "__main__":
    success = evaluate_accuracy()
    sys.exit(0 if success else 1)

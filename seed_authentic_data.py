import os
from dotenv import load_dotenv

load_dotenv()

from scraper.scraper import Scraper
from scraper.extractor import ArticleExtractor
from database.repositories import article_repository, source_repository
from database.mongodb import db_connection


def run_seed():
    if not db_connection.connect():
        print("Failed to connect to MongoDB.")
        return

    scraper = Scraper()
    extractor = ArticleExtractor()

    urls_file = os.path.join(os.path.dirname(__file__), 'data', 'training_urls.txt')
    urls = []
    if os.path.exists(urls_file):
        with open(urls_file, 'r', encoding='utf-8') as f:
            urls = [line.strip() for line in f if line.strip() and not line.startswith('#')]

    real_urls = [
        "https://en.wikipedia.org/wiki/Artificial_intelligence",
        "https://en.wikipedia.org/wiki/Space_exploration",
        "https://en.wikipedia.org/wiki/Renewable_energy",
        "https://ar.wikipedia.org/wiki/%D8%A7%D9%84%D8%B0%D9%83%D8%A7%D8%A1_%D8%A7%D9%84%D8%A7%D8%B5%D8%B7%D9%86%D8%A7%D8%B9%D9%8A",
        "https://ar.wikipedia.org/wiki/%D8%A7%D8%B3%D8%AA%D9%83%D8%B4%D8%A7%D9%81_%D8%A7%D9%84%D9%81%D8%B6%D8%A7%D8%A1",
        "https://ru.wikipedia.org/wiki/%D0%98%D1%81%D0%BA%D1%83%D1%81%D1%82%D0%B2%D0%B5%D0%BD%D0%BD%D1%8B%D0%B9_%D0%B8%D0%BD%D1%82%D0%B5%D0%BB%D0%BB%D0%B5%D0%BA%D1%82",
        "https://ru.wikipedia.org/wiki/%D0%98%D1%81%D1%81%D0%BB%D0%B5%D0%B4%D0%BE%D0%B2%D0%B0%D0%BD%D0%B8%D0%B5_%D0%BA%D0%BE%D1%81%D0%BC%D0%BE%D1%81%D0%B0"
    ]

    all_urls = real_urls + [u for u in urls if u not in real_urls]

    for url in all_urls[:40]:
        source_repository.add_source(url)

        if url in real_urls:
            html = scraper.fetch_html(url)
            article = None
            if html:
                article = extractor.extract(html, source_url=url)

            if not article or not article.get('title') or not article.get('body'):
                fallbacks = {
                    "https://en.wikipedia.org/wiki/Artificial_intelligence": {
                        "title": "Artificial Intelligence (AI) Advances",
                        "body": "Artificial intelligence (AI) is intelligence demonstrated by machines, as opposed to natural intelligence displayed by animals including humans. AI research has been defined as the field of study of intelligent agents, which refers to any system that perceives its environment and takes actions that maximize its chance of achieving its goals. Applications of AI include advanced web search engines, recommendation systems, understanding human speech, self-driving cars, and automated decision-making.",
                        "language": "English"
                    },
                    "https://en.wikipedia.org/wiki/Space_exploration": {
                        "title": "Space Exploration and Planetary Missions",
                        "body": "Space exploration is the ongoing discovery and exploration of celestial structures in outer space by means of continuously evolving and growing space technology. While the study of space is carried out mainly by astronomers with telescopes, the physical exploration of space is conducted both by unmanned robotic space probes and human spaceflight.",
                        "language": "English"
                    },
                    "https://en.wikipedia.org/wiki/Renewable_energy": {
                        "title": "Renewable Energy Solutions for Global Climate",
                        "body": "Renewable energy is energy that is collected from renewable resources that are naturally replenished on a human timescale, such as sunlight, wind, rain, tides, waves, and geothermal heat. Renewable energy often provides energy for electricity generation, air and water heating/cooling, transportation, and rural energy services.",
                        "language": "English"
                    },
                    "https://ar.wikipedia.org/wiki/%D8%A7%D9%84%D8%B0%D9%83%D8%A7%D8%A1_%D8%A7%D9%84%D8%A7%D8%B5%D8%B7%D9%86%D8%A7%D8%B9%D9%8A": {
                        "title": "الذكاء الاصطناعي وتطبيقاته العملية",
                        "body": "الذكاء الاصطناعي هو سلوك وخصائص معينة تتسم بها البرامج الحاسوبية تجعلها تحاكي القدرات الذهنية البشرية وأنماط عملها. من أهم هذه الخاصيات القدرة على التعلم والاستنتاج ورد الفعل على أوضاع لم تبرمج في الآلة. أصبح الذكاء الاصطناعي يدخل في مجالات حياتية متعددة مثل الطب والتعليم والصناعة والسيارات ذاتية القيادة.",
                        "language": "Arabic"
                    },
                    "https://ar.wikipedia.org/wiki/%D8%A7%D8%B3%D8%AA%D9%83%D8%B4%D8%A7%D9%81_%D8%A7%D9%84%D9%81%D8%B6%D8%A7%D8%A1": {
                        "title": "استكشاف الفضاء الخارجي والأجرام السماوية",
                        "body": "استكشاف الفضاء هو التطوير المستمر لتقنيات الفضاء الخارجي لاستكشاف الأجرام السماوية والنجوم. دراسة الفضاء تتم بالأساس بواسطة علماء الفلك والرحلات المأهولة وغير المأهولة التي تطلقها وكالات الفضاء مثل ناسا والوكالات الأوروبية والعربية.",
                        "language": "Arabic"
                    },
                    "https://ru.wikipedia.org/wiki/%D0%98%D1%81%D0%BA%D1%83%D1%81%D1%81%D1%82%D0%B2%D0%B5%D0%BD%D0%BD%D1%8B%D0%B9_%D0%B8%D0%BD%D1%82%D0%B5%D0%BB%D0%BB%D0%B5%D0%BA%D1%82": {
                        "title": "Искусственный интеллект и нейронные сети",
                        "body": "Искусственный интеллект — свойство искусственных интеллектуальных систем выполнять творческие функции, которые традиционно считаются прерогативой человека. Это направление науки включает разработку методов интеллектуального анализа данных, машинного обучения и нейронных сетей для решения прикладных задач.",
                        "language": "Russian"
                    },
                    "https://ru.wikipedia.org/wiki/%D0%98%D1%81%D1%81%D0%BB%D0%B5%D0%B4%D0%BE%D0%B2%D0%B0%D0%BD%D0%B8%D0%B5_%D0%BA%D0%BE%D1%81%D0%BC%D0%BE%D1%81%D0%B0": {
                        "title": "Исследование космоса в XXI веке",
                        "body": "Исследование космоса — это физическое исследование космического пространства с помощью автоматических аппаратов и пилотируемых космических кораблей. Современная космонавтика позволяет изучать планеты Солнечной системы, запускать орбитальные станции и планировать полеты на Луну и Марс.",
                        "language": "Russian"
                    }
                }
                fb = fallbacks.get(url)
                if fb:
                    article = {
                        "title": fb["title"],
                        "body": fb["body"],
                        "language": fb["language"],
                        "source_url": url,
                        "publication_date": "Recent"
                    }

            if article and article.get('title') and article.get('body'):
                article_repository.save_to_db(article)

    print("Data seeding completed.")


if __name__ == "__main__":
    run_seed()

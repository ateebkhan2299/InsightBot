import os
import sys
import secrets
import logging
from urllib.parse import urlparse
from flask import Flask, render_template, session, request

try:
    from whitenoise import WhiteNoise
except ImportError:
    WhiteNoise = None

from config.config import config
from database.mongodb import db_connection
from database.repositories import user_repository
from api.routes import api_bp

logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s [%(levelname)s] %(name)s: %(message)s'
)
logger = logging.getLogger("insightbot")


def create_app():
    app = Flask(__name__)
    app.config.from_object(config)

    if not app.secret_key:
        env_key = os.getenv("SECRET_KEY")
        app.secret_key = env_key if env_key else config.SECRET_KEY

    db_connection.connect()

    if not (os.environ.get('VERCEL') or os.environ.get('VERCEL_ENV') or app.config.get('TESTING')):
        if not app.debug or os.environ.get('WERKZEUG_RUN_MAIN') == 'true':
            try:
                from scheduler.scheduler import bot_scheduler
                bot_scheduler.start()
            except Exception as exc:
                logger.error(f"Failed to start scheduler: {exc}")

    @app.context_processor
    def inject_global_data():
        pending_count = 0
        pending_users = []
        if session.get('is_admin'):
            pending_users = user_repository.get_pending_users()
            pending_count = len(pending_users)

        active_lang = request.args.get('lang', '') or session.get('active_lang', '')
        return {
            'pending_users_count': pending_count,
            'pending_users_list': pending_users,
            'current_lang': active_lang
        }

    @app.template_filter('snippet')
    def snippet_filter(text, length=180):
        if not text:
            return ""
        text = str(text).strip()
        if len(text) <= length:
            return text
        return text[:length].rsplit(' ', 1)[0] + "..."

    @app.template_filter('reading_time')
    def reading_time_filter(text):
        if not text:
            return 1
        word_count = len(str(text).split())
        return max(1, round(word_count / 180))

    @app.template_filter('wordcount')
    def wordcount_filter(text):
        return len(str(text).split()) if text else 0

    @app.template_filter('domain_name')
    def domain_filter(url):
        if not url:
            return "news-source"
        try:
            return urlparse(str(url)).netloc.replace("www.", "")
        except Exception:
            return "news-source"

    app.register_blueprint(api_bp)

    @app.errorhandler(403)
    def forbidden(e):
        return render_template('error.html', error_code=403, error_title="Access Denied", error_message="You don't have permission to view this page."), 403

    @app.errorhandler(404)
    def page_not_found(e):
        return render_template('error.html', error_code=404, error_title="Page Not Found", error_message="The requested page could not be located."), 404

    @app.errorhandler(500)
    def internal_server_error(e):
        return render_template('error.html', error_code=500, error_title="Server Error", error_message="An unexpected error occurred while processing your request."), 500

    return app


app = create_app()

if WhiteNoise is not None:
    static_dir = os.path.join(os.path.dirname(__file__), 'static')
    app.wsgi_app = WhiteNoise(app.wsgi_app, root=static_dir, prefix='static', autorefresh=True)

if __name__ == '__main__':
    app.run(host='0.0.0.0', port=5000, debug=True)

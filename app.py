# InsightBot — Flask application entry point.
# Registers blueprints, starts the DB connection, and launches the background scheduler.

import os
import sys
import secrets
import logging
from flask import Flask, render_template
from whitenoise import WhiteNoise
from config.config import config
from database.mongodb import db_connection
from api.routes import api_bp

# Set up clean application logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s [%(levelname)s] %(name)s: %(message)s'
)
logger = logging.getLogger("InsightBot.App")

def create_app():
    """Application factory for InsightBot Flask App."""
    app = Flask(__name__)
    app.config.from_object(config)

    # Ensure secret key is configured for sessions & flash messages
    if not app.secret_key:
        env_key = os.getenv("SECRET_KEY")
        if env_key:
            app.secret_key = env_key
        else:
            app.secret_key = secrets.token_hex(32)
            logger.warning("No SECRET_KEY set — generated random key. Sessions will not persist across restarts.")

    # ── Database Initialization ──────────────────────────────────────────────
    logger.info("Initializing MongoDB connection...")
    connected = db_connection.connect()
    if not connected:
        logger.warning("MongoDB initial connection failed. The app will retry on request.")

    # ── Background Scheduler Initialization ──────────────────────────────────
    if os.environ.get('VERCEL') == '1' or os.environ.get('VERCEL_ENV'):
        logger.info("Serverless Vercel environment detected. Background scheduler thread bypassed.")
    elif app.config.get('TESTING'):
        logger.info("Testing environment detected. Background scheduler thread bypassed.")
    elif not app.debug or os.environ.get('WERKZEUG_RUN_MAIN') == 'true':
        logger.info("Starting background automation scheduler daemon...")
        try:
            from scheduler.scheduler import bot_scheduler
            bot_scheduler.start()
        except Exception as e:
            logger.error(f"Failed to start background scheduler: {e}")

    # ── Custom Jinja2 Filters for Multilingual News ──────────────────────────
    @app.template_filter('snippet')
    def snippet_filter(text, length=180):
        """Generates a clean truncated snippet without splitting words."""
        if not text:
            return ""
        text = str(text).strip()
        if len(text) <= length:
            return text
        truncated = text[:length].rsplit(' ', 1)[0]
        return truncated + "..."

    @app.template_filter('reading_time')
    def reading_time_filter(text):
        """Estimates reading time in minutes based on word count."""
        if not text:
            return 1
        word_count = len(str(text).split())
        minutes = max(1, round(word_count / 180))
        return minutes

    @app.template_filter('wordcount')
    def wordcount_filter(text):
        """Calculates total word count."""
        if not text:
            return 0
        return len(str(text).split())

    @app.template_filter('domain_name')
    def domain_filter(url):
        """Extracts clean domain name from URL."""
        if not url:
            return "news-source"
        try:
            from urllib.parse import urlparse
            netloc = urlparse(str(url)).netloc
            return netloc.replace("www.", "")
        except Exception:
            return "news-source"

    # ── Register Blueprints ──────────────────────────────────────────────────
    app.register_blueprint(api_bp)

    # ── Global Error Handlers ────────────────────────────────────────────────
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

# Wrap with WhiteNoise to serve static files reliably on Vercel
# This eliminates the need for @vercel/static builder configuration
static_dir = os.path.join(os.path.dirname(__file__), 'static')
app.wsgi_app = WhiteNoise(app.wsgi_app, root=static_dir, prefix='static', autorefresh=True)

if __name__ == '__main__':
    print("InsightBot running on http://127.0.0.1:5000")
    app.run(host='0.0.0.0', port=5000, debug=True)

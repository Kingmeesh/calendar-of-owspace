from flask import Flask, send_file, jsonify
from flask_caching import Cache
from datetime import datetime, timedelta
import requests
from io import BytesIO
import logging
from requests.adapters import HTTPAdapter
from requests.packages.urllib3.util.retry import Retry

app = Flask(__name__)
cache = Cache(config={'CACHE_TYPE': 'simple'})
cache.init_app(app)

logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

def get_with_retry(url, timeout=10):
    session = requests.Session()
    retries = Retry(total=3, backoff_factor=1, status_forcelist=[500, 502, 503, 504])
    session.mount('https://', HTTPAdapter(max_retries=retries))
    return session.get(url, timeout=timeout)

def generate_image_url():
    today = datetime.utcnow() + timedelta(hours=8)
    return f'https://img.owspace.com/Public/uploads/Download/{today.year}/{today.month:02d}{today.day:02d}.jpg'

@app.errorhandler(Exception)
def handle_exception(e):
    logger.error("Unexpected error", exc_info=True)
    return jsonify({"error": "Internal server error", "exception": str(e)}), 500

@cache.cached(timeout=86400)
@app.route('/')
def get_calendar_image():
    try:
        image_url = generate_image_url()
        logger.info(f"Attempting to fetch image from: {image_url}")
        response = get_with_retry(image_url)
        
        if response.status_code == 200:
            return send_file(
                BytesIO(response.content),
                mimetype='image/jpeg',
                as_attachment=True,
                attachment_filename=f'calendar_{datetime.utcnow().strftime("%Y_%m_%d")}.jpg'
            )
        else:
            logger.error(f"Failed to fetch image: {response.status_code}")
            return jsonify({"error": "Failed to fetch image", "status_code": response.status_code}), 500
    except requests.RequestException as req_err:
        logger.error("Request error", exc_info=True)
        return jsonify({"error": "Request failed", "details": str(req_err)}), 500

@app.route('/health')
def health_check():
    return jsonify({"status": "ok"}), 200

if __name__ == '__main__':
    app.run(debug=True)

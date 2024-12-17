from flask import Flask, send_file, jsonify
from flask_caching import Cache
from datetime import datetime
from pytz import timezone
import requests
from io import BytesIO
import traceback

app = Flask(__name__)
cache_config = {"CACHE_TYPE": "SimpleCache"}
app.config.from_mapping(cache_config)
cache = Cache(app)

def get_china_now():
    china_tz = timezone('Asia/Shanghai')
    return datetime.now(china_tz)

@app.route('/')
@cache.cached(timeout=3600)
def get_calendar_image():
    try:
        today = get_china_now()
        year, month, day = today.year, today.month, today.day
        image_url = f'https://img.owspace.com/Public/uploads/Download/{year}/{month:02d}{day:02d}.jpg'
        print(f"Attempting to fetch image from: {image_url}")

        response = requests.get(image_url, timeout=10)
        if response.status_code == 200:
            return send_file(BytesIO(response.content), mimetype='image/jpeg')
        else:
            fallback_date = today - timedelta(days=1)
            fallback_url = f'https://img.owspace.com/Public/uploads/Download/{fallback_date.year}/{fallback_date.month:02d}{fallback_date.day:02d}.jpg'
            print(f"Fallback to previous day: {fallback_url}")
            response = requests.get(fallback_url, timeout=10)
            if response.status_code == 200:
                return send_file(BytesIO(response.content), mimetype='image/jpeg')
            else:
                return jsonify({"error": "Failed to fetch image", "url": image_url}), 500
    except Exception as e:
        error_message = traceback.format_exc()
        print("Unexpected error:", error_message)
        return jsonify({"error": "Internal server error", "traceback": error_message}), 500

if __name__ == '__main__':
    app.run(debug=True)

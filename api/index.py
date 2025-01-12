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
def get_calendar_image():
    try:
        today = get_china_now()
        year, month, day = today.year, today.month, today.day
        cache_key = "calendar_image"
        cache_date_key = "calendar_date"

        # 检查缓存的日期是否是今天
        cached_date = cache.get(cache_date_key)
        if cached_date == f"{year}-{month:02d}-{day:02d}":
            cached_image = cache.get(cache_key)
            if cached_image:
                print("Serving cached image")
                return send_file(BytesIO(cached_image), mimetype='image/jpeg')

        # 如果缓存无效或日期已更改，重新获取图片
        image_url = f'https://img.owspace.com/Public/uploads/Download/{year}/{month:02d}{day:02d}.jpg'
        print(f"Attempting to fetch image from: {image_url}")

        response = requests.get(image_url, timeout=10)
        if response.status_code == 200:
            cache.set(cache_key, response.content, timeout=86400)  # 缓存图片，最多缓存一天
            cache.set(cache_date_key, f"{year}-{month:02d}-{day:02d}", timeout=86400)  # 缓存日期
            return send_file(BytesIO(response.content), mimetype='image/jpeg')
        else:
            fixed_date_url = 'https://img.owspace.com/Public/uploads/Download/2024/1210.jpg'
            print(f"Fallback to fixed date: {fixed_date_url}")
            response = requests.get(fixed_date_url, timeout=10)
            if response.status_code == 200:
                cache.set(cache_key, response.content, timeout=86400)  # 缓存固定日期的图片
                cache.set(cache_date_key, f"{year}-{month:02d}-{day:02d}", timeout=86400)  # 更新日期为今天
                return send_file(BytesIO(response.content), mimetype='image/jpeg')
            else:
                return jsonify({"error": "Failed to fetch image", "url": image_url}), 500
    except Exception as e:
        error_message = traceback.format_exc()
        print("Unexpected error:", error_message)
        return jsonify({"error": "Internal server error", "traceback": error_message}), 500

if __name__ == '__main__':
    app.run(debug=True)

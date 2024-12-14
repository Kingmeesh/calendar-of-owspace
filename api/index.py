from flask import Flask, send_file, jsonify
from flask_caching import Cache
from datetime import datetime, timedelta
import requests
from io import BytesIO
import traceback
import sys

app = Flask(__name__)

# 配置缓存，使用简单内存缓存（适用于小型应用）
cache_config = {"CACHE_TYPE": "SimpleCache"}
app.config.from_mapping(cache_config)
cache = Cache(app)

@app.route('/')
@cache.cached(timeout=3600)  # 缓存一小时
def get_calendar_image():
    try:
        # 获取当前日期（UTC + 8）
        today = datetime.utcnow() + timedelta(hours=8)
        year = today.year
        month = today.month
        day = today.day
        
        # 构造图片URL
        image_url = f'https://img.owspace.com/Public/uploads/Download/{year}/{month:02d}{day:02d}.jpg'
        print(f"Attempting to fetch image from: {image_url}")
        
        # 请求远程图片
        response = requests.get(image_url, timeout=10)
        if response.status_code == 200:
            return send_file(BytesIO(response.content), mimetype='image/jpeg')
        else:
            return jsonify({
                "error": "Failed to fetch image",
                "status_code": response.status_code,
                "url": image_url
            }), 500

    except Exception as e:
        error_message = traceback.format_exc()
        print("Unexpected error:", error_message)
        return jsonify({
            "error": "Internal server error",
            "exception": str(e),
            "traceback": error_message
        }), 500

# Vercel 直接处理 Flask 应用
if __name__ == '__main__':
    app.run(debug=True)

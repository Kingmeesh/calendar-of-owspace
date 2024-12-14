from flask import Flask, send_file, jsonify
from flask_compress import Compress
from datetime import datetime, timedelta
import requests
import os
from io import BytesIO

app = Flask(__name__)
Compress(app)  # 启用 GZIP 压缩

# 创建缓存目录
CACHE_DIR = "./cache"
os.makedirs(CACHE_DIR, exist_ok=True)

@app.route('/')
def get_calendar_image():
    try:
        # 获取当前日期
        today = datetime.utcnow() + timedelta(hours=8)
        year, month, day = today.year, today.month, today.day
        image_url = f'https://img.owspace.com/Public/uploads/Download/{year}/{month:02d}{day:02d}.jpg'
        cache_file = f"{CACHE_DIR}/{year}_{month:02d}_{day:02d}.jpg"

        # 检查本地缓存
        if os.path.exists(cache_file):
            return send_file(cache_file, mimetype="image/jpeg")

        # 远程获取图片
        response = requests.get(image_url, timeout=5)
        if response.status_code == 200:
            # 保存到本地缓存
            with open(cache_file, "wb") as f:
                f.write(response.content)
            return send_file(BytesIO(response.content), mimetype="image/jpeg")
        else:
            return jsonify({
                "error": "Failed to fetch image",
                "status_code": response.status_code,
                "url": image_url
            }), 500
    except Exception as e:
        return jsonify({"error": "Internal server error", "message": str(e)}), 500

if __name__ == '__main__':
    app.run(debug=True)

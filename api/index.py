from flask import Flask, send_file, jsonify
from datetime import datetime, timedelta
import requests
import os
import time
from io import BytesIO

app = Flask(__name__)

# 创建缓存目录
CACHE_DIR = "./cache"
os.makedirs(CACHE_DIR, exist_ok=True)

# 缓存过期时间（1天）
CACHE_EXPIRATION_TIME = 86400  # 86400秒 = 1天

def is_cache_expired(file_path, max_age_in_seconds=CACHE_EXPIRATION_TIME):
    """
    检查缓存文件是否过期，过期时间为 max_age_in_seconds（默认为 1 天）。
    """
    if os.path.exists(file_path):
        file_age = time.time() - os.path.getmtime(file_path)  # 获取文件修改时间
        return file_age > max_age_in_seconds  # 如果文件超过最大过期时间则认为已过期
    return True  # 文件不存在则认为过期

@app.route('/')
def get_calendar_image():
    try:
        # 获取当前日期
        today = datetime.utcnow() + timedelta(hours=8)
        year, month, day = today.year, today.month, today.day
        
        # 根据当前日期构建图片URL
        image_url = f'https://img.owspace.com/Public/uploads/Download/{year}/{month:02d}{day:02d}.jpg'
        
        # 构建本地缓存文件名
        cache_file = os.path.join(CACHE_DIR, f"{year}_{month:02d}_{day:02d}.jpg")
        
        # 如果缓存文件已存在且未过期，则直接返回缓存文件
        if os.path.exists(cache_file) and not is_cache_expired(cache_file):
            print(f"Cache hit: Serving {cache_file}")
            return send_file(cache_file, mimetype="image/jpeg")
        
        # 如果缓存文件不存在或已过期，则从远程下载并缓存
        print(f"Cache miss or expired: Fetching image from {image_url}")
        response = requests.get(image_url, timeout=5)
        
        # 检查图片是否成功获取
        if response.status_code == 200:
            # 将获取到的图片写入缓存文件
            with open(cache_file, "wb") as f:
                f.write(response.content)
            
            # 返回图片
            return send_file(BytesIO(response.content), mimetype="image/jpeg")
        else:
            # 如果无法获取图片，返回错误信息
            return jsonify({
                "error": "Failed to fetch image",
                "status_code": response.status_code,
                "url": image_url
            }), 500
    except Exception as e:
        # 处理任何异常并返回错误信息
        return jsonify({"error": "Internal server error", "message": str(e)}), 500

if __name__ == '__main__':
    app.run(debug=True)

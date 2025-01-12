from flask import Flask, send_file, jsonify
from flask_caching import Cache
from datetime import datetime, timedelta
from pytz import timezone
import requests
from io import BytesIO
import traceback
from PIL import Image  # 导入PIL库

app = Flask(__name__)
cache_config = {"CACHE_TYPE": "SimpleCache"}
app.config.from_mapping(cache_config)
cache = Cache(app)

def get_china_now():
    china_tz = timezone('Asia/Shanghai')
    return datetime.now(china_tz)

def resize_image(image_data, target_ratio=(9, 10)):
    """将图片拉伸为9:10的比例"""
    img = Image.open(BytesIO(image_data))
    width, height = img.size

    # 计算目标尺寸
    target_width = int(height * (target_ratio[0] / target_ratio[1]))
    target_height = height

    # 如果当前宽度小于目标宽度，则调整高度
    if width < target_width:
        target_height = int(width * (target_ratio[1] / target_ratio[0]))
        target_width = width

    # 拉伸图片到目标尺寸
    img_resized = img.resize((target_width, target_height), Image.Resampling.LANCZOS)

    # 将图片转换为字节流
    img_byte_arr = BytesIO()
    img_resized.save(img_byte_arr, format='JPEG')
    img_byte_arr.seek(0)

    return img_byte_arr.getvalue()

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
            # 拉伸图片比例为9:10
            resized_image = resize_image(response.content)
            cache.set(cache_key, resized_image, timeout=86400)  # 缓存图片，最多缓存一天
            cache.set(cache_date_key, f"{year}-{month:02d}-{day:02d}", timeout=86400)  # 缓存日期
            return send_file(BytesIO(resized_image), mimetype='image/jpeg')
        else:
            # 回退到前一天的图片
            fallback_date = today - timedelta(days=1)
            fallback_url = f'https://img.owspace.com/Public/uploads/Download/{fallback_date.year}/{fallback_date.month:02d}{fallback_date.day:02d}.jpg'
            print(f"Fallback to previous day: {fallback_url}")
            response = requests.get(fallback_url, timeout=10)
            if response.status_code == 200:
                # 拉伸图片比例为9:10
                resized_image = resize_image(response.content)
                cache.set(cache_key, resized_image, timeout=86400)  # 缓存回退图片
                cache.set(cache_date_key, f"{year}-{month:02d}-{day:02d}", timeout=86400)  # 更新日期为今天
                return send_file(BytesIO(resized_image), mimetype='image/jpeg')
            else:
                return jsonify({"error": "Failed to fetch image", "url": image_url}), 500
    except Exception as e:
        error_message = traceback.format_exc()
        print("Unexpected error:", error_message)
        return jsonify({"error": "Internal server error", "traceback": error_message}), 500

if __name__ == '__main__':
    app.run(debug=True)

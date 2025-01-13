from flask import Flask, send_file, jsonify
from flask_caching import Cache
from datetime import datetime
from pytz import timezone
import requests
from io import BytesIO
import traceback
from PIL import Image, ImageFilter

app = Flask(__name__)
cache_config = {"CACHE_TYPE": "SimpleCache"}
app.config.from_mapping(cache_config)
cache = Cache(app)

def get_china_now():
    china_tz = timezone('Asia/Shanghai')
    return datetime.now(china_tz)

def crop_and_resize_image(image_data):
    """裁剪图片并缩放为9:10.3的比例，同时提高清晰度"""
    img = Image.open(BytesIO(image_data))

    # 原始尺寸
    width, height = img.size

    # 裁剪区域
    left = 62
    right = width - 62
    top = 62
    bottom = height - 160

    # 裁剪图片
    img_cropped = img.crop((left, top, right, bottom))

    # 计算目标尺寸：缩放为9:10.3的比例
    target_ratio = (9, 10.2)  # 目标比例
    target_width = 9 * 100  # 目标宽度为900像素
    target_height = int(target_width * (target_ratio[1] / target_ratio[0]))  # 根据比例计算高度

    # 缩放图片
    img_resized = img_cropped.resize((target_width, target_height), Image.Resampling.LANCZOS)

    # 提高清晰度
    img_sharpened = img_resized.filter(ImageFilter.SHARPEN)  # 使用锐化滤镜

    # 将图片转换为字节流
    img_byte_arr = BytesIO()
    img_sharpened.save(img_byte_arr, format='JPEG')
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
            # 裁剪、缩放并优化图片
            processed_image = crop_and_resize_image(response.content)
            cache.set(cache_key, processed_image, timeout=86400)  # 缓存图片，最多缓存一天
            cache.set(cache_date_key, f"{year}-{month:02d}-{day:02d}", timeout=86400)  # 缓存日期
            return send_file(BytesIO(processed_image), mimetype='image/jpeg')
        else:
            # 如果今日图片获取失败，直接返回2025年1月6日的图片
            fixed_date_url = 'https://img.owspace.com/Public/uploads/Download/2025/0106.jpg'
            print(f"Fallback to fixed date: {fixed_date_url}")
            response = requests.get(fixed_date_url, timeout=10)
            if response.status_code == 200:
                # 裁剪、缩放并优化图片
                processed_image = crop_and_resize_image(response.content)
                cache.set(cache_key, processed_image, timeout=86400)  # 缓存固定日期的图片
                cache.set(cache_date_key, f"{year}-{month:02d}-{day:02d}", timeout=86400)  # 更新日期为今天
                return send_file(BytesIO(processed_image), mimetype='image/jpeg')
            else:
                return jsonify({"error": "Failed to fetch image", "url": image_url}), 500
    except Exception as e:
        error_message = traceback.format_exc()
        print("Unexpected error:", error_message)
        return jsonify({"error": "Internal server error", "traceback": error_message}), 500

if __name__ == '__main__':
    app.run(debug=True)

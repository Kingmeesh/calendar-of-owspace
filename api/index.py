from flask import Flask, send_file, render_template
from flask_caching import Cache
from datetime import datetime
from pytz import timezone
import requests
from io import BytesIO
import traceback
from PIL import Image, ImageFilter
import base64

app = Flask(__name__)
cache_config = {"CACHE_TYPE": "SimpleCache"}
app.config.from_mapping(cache_config)
cache = Cache(app)

def get_china_now():
    china_tz = timezone('Asia/Shanghai')
    return datetime.now(china_tz)

def crop_and_resize_image(image_data):
    """裁剪图片并缩放为9:10.2的比例，同时提高清晰度"""
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

    # 计算目标尺寸：缩放为9:10.2的比例
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
def index():
    try:
        today = get_china_now()
        year, month, day = today.year, today.month, today.day
        cache_key = "calendar_image"
        cache_date_key = "calendar_date"

        # 检查缓存的日期是否是今天
        cached_date = cache.get(cache_date_key)

        if cached_date == f"{year}-{month}-{day}":
            # 如果缓存日期是今天，直接返回缓存的图片
            cached_image = cache.get(cache_key)
            image_base64 = base64.b64encode(cached_image).decode('utf-8')
        else:
            # 如果缓存日期不是今天，重新处理图片并更新缓存
            image_url = "https://example.com/path/to/your/image.jpg"  # 替换为实际图片URL
            response = requests.get(image_url)
            if response.status_code != 200:
                return "Failed to fetch image", 500
            image_data = response.content
            processed_image = crop_and_resize_image(image_data)
            cache.set(cache_key, processed_image)
            cache.set(cache_date_key, f"{year}-{month}-{day}")
            image_base64 = base64.b64encode(processed_image).decode('utf-8')

        return render_template('index.html', image_base64=image_base64)
    except Exception as e:
        traceback.print_exc()
        return "An error occurred", 500

@app.route('/image')
def get_image():
    try:
        today = get_china_now()
        year, month, day = today.year, today.month, today.day
        cache_key = "calendar_image"
        cache_date_key = "calendar_date"

        # 检查缓存的日期是否是今天
        cached_date = cache.get(cache_date_key)

        if cached_date == f"{year}-{month}-{day}":
            # 如果缓存日期是今天，直接返回缓存的图片
            cached_image = cache.get(cache_key)
            return send_file(BytesIO(cached_image), mimetype='image/jpeg')
        else:
            # 如果缓存日期不是今天，重新处理图片并更新缓存
            image_url = "https://example.com/path/to/your/image.jpg"  # 替换为实际图片URL
            response = requests.get(image_url)
            if response.status_code != 200:
                return "Failed to fetch image", 500
            image_data = response.content
            processed_image = crop_and_resize_image(image_data)
            cache.set(cache_key, processed_image)
            cache.set(cache_date_key, f"{year}-{month}-{day}")
            return send_file(BytesIO(processed_image), mimetype='image/jpeg')
    except Exception as e:
        traceback.print_exc()
        return "An error occurred", 500

if __name__ == '__main__':
    app.run(debug=True)

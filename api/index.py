from flask import Flask, send_file, jsonify, render_template_string
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
def get_calendar_image():
    try:
        today = get_china_now()
        year, month, day = today.year, today.month, today.day
        cache_key = "calendar_image"
        cache_date_key = "calendar_date"

        # 检查缓存的日期是否是今天
        cached_date = cache.get(cache_date_key)
        if cached_date != f"{year}-{month}-{day}":
            # 获取图片
            image_url = f"https://example.com/calendar/{year}/{month}/{day}.jpg"  # 替换为实际的图片URL
            response = requests.get(image_url)
            if response.status_code == 200:
                image_data = crop_and_resize_image(response.content)
                cache.set(cache_key, image_data)
                cache.set(cache_date_key, f"{year}-{month}-{day}")
            else:
                return "Failed to fetch image", 500
        else:
            image_data = cache.get(cache_key)

        # 返回包含图片的HTML页面
        html_content = f"""
        <!DOCTYPE html>
        <html lang="zh-CN">
        <head>
            <meta charset="UTF-8">
            <meta name="viewport" content="width=device-width, initial-scale=1.0">
            <title>日历图片</title>
            <style>
                body, html {{
                    margin: 0;
                    padding: 0;
                    height: 100%;
                    display: flex;
                    justify-content: center;
                    align-items: center;
                    background-color: #f0f0f0;
                }}
                img {{
                    max-width: 100%;
                    max-height: 100%;
                    object-fit: contain;
                }}
            </style>
        </head>
        <body>
            <img src="data:image/jpeg;base64,{image_data}" alt="日历图片">
        </body>
        </html>
        """
        return render_template_string(html_content)

    except Exception as e:
        traceback.print_exc()
        return str(e), 500

if __name__ == '__main__':
    app.run(debug=True)

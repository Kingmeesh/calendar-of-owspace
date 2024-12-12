from flask import Flask, send_file
import datetime
import requests
from io import BytesIO

app = Flask(__name__)

@app.route('/calendar')
def get_calendar_image():
    # 获取今天的日期
    today = datetime.date.today()
    year = today.year
    month = today.month
    day = today.day
    
    # 构造图片URL
    image_url = f'https://img.owspace.com/Public/uploads/Download/{year}/{month:02d}{day:02d}.jpg'
    
    # 使用 requests 获取远程图片
    response = requests.get(image_url)
    if response.status_code == 200:
        # 将图片内容返回
        return send_file(BytesIO(response.content), mimetype='image/jpeg')
    else:
        return "Failed to fetch image", 500

# Vercel 直接使用 app 作为入口
app

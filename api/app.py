from flask import Flask, send_file, jsonify
import datetime
import requests
from io import BytesIO
import traceback

app = Flask(__name__)

@app.route('/calendar')
def get_calendar_image():
    try:
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
            # 如果获取图片失败，返回详细错误信息
            return jsonify({
                "error": "Failed to fetch image",
                "status_code": response.status_code,
                "url": image_url
            }), 500

    except Exception as e:
        # 捕获并记录详细的异常信息
        error_message = traceback.format_exc()
        print(error_message)  # 这将在 Vercel 日志中显示
        return jsonify({
            "error": str(e),
            "traceback": error_message
        }), 500

# Vercel serverless function handler
def handler(event, context):
    from flask import request
    
    try:
        with app.request_context(request.environ):
            return app.full_dispatch_request()
    except Exception as e:
        # 捕获 handler 中的任何异常
        error_message = traceback.format_exc()
        print(error_message)
        return {
            "statusCode": 500,
            "body": json.dumps({
                "error": str(e),
                "traceback": error_message
            })
        }

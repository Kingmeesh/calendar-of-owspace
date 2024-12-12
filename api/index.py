from flask import Flask, send_file, jsonify
import datetime
import requests
from io import BytesIO
import traceback
import sys

app = Flask(__name__)

@app.route('/api/calendar')
def get_calendar_image():
    try:
        # 获取今天的日期
        today = datetime.date.today()
        year = today.year
        month = today.month
        day = today.day
        
        # 构造图片URL
        image_url = f'https://img.owspace.com/Public/uploads/Download/{year}/{month:02d}{day:02d}.jpg'
        print(f"Attempting to fetch image from: {image_url}")
        
        # 使用 requests 获取远程图片
        try:
            response = requests.get(image_url, timeout=10)
            print(f"Response status code: {response.status_code}")
        except requests.RequestException as req_err:
            print(f"Request error: {req_err}")
            return jsonify({
                "error": "Request failed",
                "details": str(req_err)
            }), 500
        
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
        print("Unexpected error:", error_message)
        # 打印完整的异常堆栈信息
        traceback.print_exc(file=sys.stdout)
        return jsonify({
            "error": "Internal server error",
            "exception": str(e),
            "traceback": error_message
        }), 500

# Vercel serverless function handler
def handler(event, context):
    try:
        # 简化的 handler，直接返回 app
        return app
    except Exception as e:
        print(f"Handler error: {traceback.format_exc()}")
        return {
            "statusCode": 500,
            "body": json.dumps({
                "error": "Handler failed",
                "details": str(e)
            })
        }

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
        today = datetime.date.today()
        year = today.year
        month = today.month
        day = today.day
        
        image_url = f'https://img.owspace.com/Public/uploads/Download/{year}/{month:02d}{day:02d}.jpg'
        print(f"Attempting to fetch image from: {image_url}")
        
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
        traceback.print_exc(file=sys.stdout)
        return jsonify({
            "error": "Internal server error",
            "exception": str(e),
            "traceback": error_message
        }), 500

# Vercel 直接处理Flask应用
if __name__ == '__main__':
    app.run(debug=True)

import requests
from io import BytesIO
import cv2

# ใส่ Token ของ Bot และ Chat ID ของผู้รับข้อความ
BOT_TOKEN = ""
CHAT_ID = ""

def send_message(bot_token, chat_id, text):
    """
    ส่งข้อความไปยัง Telegram
    """
    url = f"https://api.telegram.org/bot{bot_token}/sendMessage"
    payload = {
        "chat_id": chat_id,
        "text": text
    }
    response = requests.post(url, data=payload)
    if response.status_code == 200:
        print("ส่งข้อความสำเร็จ!")
    else:
        print(f"ส่งข้อความล้มเหลว: {response.text}")

def send_photo(bot_token, chat_id, photo_bytes, caption=""):
    """
    ส่งรูปภาพจาก BytesIO ไปยัง Telegram
    """
    url = f"https://api.telegram.org/bot{bot_token}/sendPhoto"
    payload = {
        "chat_id": chat_id,
        "caption": caption
    }
    files = {
        "photo": photo_bytes
    }
    response = requests.post(url, data=payload, files=files)
    if response.status_code == 200:
        print("ส่งรูปภาพสำเร็จ!")
    else:
        print(f"ส่งรูปภาพล้มเหลว: {response.text}")
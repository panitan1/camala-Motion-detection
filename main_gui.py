import customtkinter as ctk
from tkinter import PhotoImage  , messagebox
from PIL import Image
import requests
import cv2
import numpy as np
from skimage.metrics import structural_similarity as ssim
from io import BytesIO
import configparser 
from telegram_bot import send_message, send_photo 
config = configparser.ConfigParser()
config_file = 'settings.ini'
from customtkinter import CTkImage
import json
import time
import logging  # เพิ่มการนำเข้า logging

# ตั้งค่า logging
logging.basicConfig(
    filename='app.log',
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s',
    encoding='utf-8'
)

#pyinstaller --noconfirm --onefile --windowed --icon "A:/my_output_hstn/images-Photoroom.ico" --splash "A:/my_output_hstn/images-Photoroom.png" --add-data "A:/my_output_hstn/history.json;." --add-data "A:/my_output_hstn/images-Photoroom.ico;." --add-data "A:/my_output_hstn/images-Photoroom.png;." --add-data "A:/my_output_hstn/lock_open.png;." --add-data "A:/my_output_hstn/lock1.png;." --add-data "A:/my_output_hstn/settings.ini;." --add-data "A:/my_output_hstn/telegram_bot.py;."  "A:/my_output_hstn/main_gui.py"


history_file = "history.json" 
history_window = None

def load_settings():
    if config.read(config_file):
        video_url = config.get('Settings', 'video_url', fallback='')
        bot_token = config.get('Settings', 'bot_token', fallback='')
        chat_id = config.get('Settings', 'chat_id', fallback='')
        video_url_entry.insert(0, video_url)
        bot_token_entry.insert(0, bot_token)
        chat_id_entry.insert(0, chat_id)

def save_settings():
    config['Settings'] = {
        'video_url': video_url_entry.get(),
        'bot_token': bot_token_entry.get(),
        'chat_id': chat_id_entry.get()
    }
    with open(config_file, 'w') as configfile:
        config.write(configfile)

def start_processing():
    video_url = video_url_entry.get()
    bot_token = bot_token_entry.get()
    chat_id = chat_id_entry.get()

    if not video_url:
        messagebox.showerror("Error", "กรุณากรอก URL")
        logging.error("ไม่พบการกรอก URL")
        return

    if not bot_token or not chat_id:
        messagebox.showerror("Error", "กรุณากรอก BOT_TOKEN และ CHAT_ID")
        logging.error("ไม่พบการกรอก BOT_TOKEN หรือ CHAT_ID")
        return
    print(f"Video URL : {video_url}")
    print(f"BOT Token : {bot_token}")
    print(f"Chat ID : {chat_id}")
    logging.info(f"Video URL: {video_url}, BOT Token: {bot_token}, Chat ID: {chat_id}")
    save_settings()
    save_to_history(video_url, bot_token, chat_id)
    process_video(video_url, bot_token, chat_id)

def save_to_history(video_url, bot_token, chat_id):
    history_data = []
    
    try:
        with open(history_file, "r") as f:
            history_data = json.load(f)
    except FileNotFoundError:
        pass  

    
    history_data.append({
        "video_url": video_url,
        "bot_token": bot_token,
        "chat_id": chat_id
    })

    
    if len(history_data) > 10:
        history_data = history_data[-10:]

    
    with open(history_file, "w") as f:
        json.dump(history_data, f, indent=4)
    
    if 'history_window' in globals():  
        show_history()  

def show_history():
    global history_window  # ประกาศให้ใช้ตัวเดียวกับด้านนอก

    try:
        with open(history_file, "r") as f:
            history_data = json.load(f)
    except FileNotFoundError:
        history_data = []

    # ถ้ามี history_window อยู่แล้ว ให้ปิดก่อนแล้วสร้างใหม่
    if history_window is not None and history_window.winfo_exists():
        history_window.destroy()

    history_window = ctk.CTkToplevel(app)
    history_window.title("History")
    history_window.geometry("600x400")

    frame = ctk.CTkScrollableFrame(history_window, width=580, height=300)
    frame.pack(pady=10, padx=10, fill="both", expand=True)

    if not history_data:
        label = ctk.CTkLabel(frame, text="ไม่มีประวัติที่บันทึกไว้", font=("Arial", 15))
        label.pack(pady=20)
    else:
        for entry in history_data:
            entry_text = (
                f"🎥 URL: {entry['video_url']}\n"
                f"🤖 Bot Token: {entry['bot_token']}\n"
                f"🆔 Chat ID: {entry['chat_id']}\n"
                "------------------------"
            )
            label = ctk.CTkLabel(frame, text=entry_text, font=("Arial", 12), anchor="w", justify="left")
            label.pack(anchor="w", padx=10, pady=5)
            label.bind("<Button-1>", lambda e, entry=entry: fill_form(entry))

    clear_button = ctk.CTkButton(history_window, text="Clear All", fg_color="red", command=clear_history)
    clear_button.pack(pady=10)

    history_window.update()
  
            

def fill_form(entry):
    
    video_url_entry.delete(0, ctk.END)
    bot_token_entry.delete(0, ctk.END)
    chat_id_entry.delete(0, ctk.END)
    video_url_entry.insert(0, entry['video_url'])
    bot_token_entry.insert(0, entry['bot_token'])
    chat_id_entry.insert(0, entry['chat_id'])

def clear_history():
   
    try:
        with open(history_file, "w") as f:
            json.dump([], f, indent=4)  
        messagebox.showinfo("Success", "ประวัติถูกล้างเรียบร้อยแล้ว!")
        show_history()
    except Exception as e:
        messagebox.showerror("Error", f"เกิดข้อผิดพลาดในการล้างประวัติ: {e}")

def process_video(video_url, bot_token, chat_id):
    cap = cv2.VideoCapture(video_url)

    if not cap.isOpened():
        messagebox.showerror("Error", "ไม่สามารถเปิดวิดีโอได้")
        logging.error(f"ไม่สามารถเปิดวิดีโอได้: {video_url}")    
        return

    print(f"เริ่มต้นการประมวลผลวิดีโอ: {video_url}")
    logging.info(f"เริ่มต้นการประมวลผลวิดีโอ: {video_url}")


    cap.get(cv2.CAP_PROP_FPS)
    previous_frame = None
    same_frame_count = 0
    captured_images = []
    last_saved_time = -10
    max_same_frame = 300
    capture_round = 1

    try:
        while True:
            ret, frame = cap.read()
            if not ret:
                print("จบวิดีโอหรือเกิดข้อผิดพลาดในการอ่านเฟรม")
                break
                
            current_time = cap.get(cv2.CAP_PROP_POS_MSEC) / 1000  
            formatted_time = format_time(current_time) 
            
            # out.write(frame)

            if previous_frame is not None:
                frame_diff = cv2.absdiff(frame, previous_frame)
                gray_diff = cv2.cvtColor(frame_diff, cv2.COLOR_BGR2GRAY)
                _, thresh = cv2.threshold(gray_diff, 30, 255, cv2.THRESH_BINARY)
                non_zero_count = np.count_nonzero(thresh)

                if non_zero_count == 0:
                    same_frame_count += 1 
                    
                else:
                    same_frame_count = 0

                if same_frame_count >= max_same_frame:
                    if current_time - last_saved_time >= 10:
                        captured_images.append(frame)
                        logging.info("=" * 50)
                        logging.info(f"📷 กล้อง")
                        logging.info(f"🕒 เวลา: {format_time(current_time)}")
                        logging.info(f"📄 รอบการตรวจจับ: {capture_round}")
                        logging.info("=" * 50)
                        print("=" * 50)
                        print(f"📷 กล้อง")
                        print(f"🕒 เวลา: {formatted_time}")
                        print(f"📄 รอบการตรวจจับ: {capture_round}")
                        print("=" * 50)
                        last_saved_time = current_time

                        if len(captured_images) >= 10:
                            all_images_same = all(
                                is_image_similar(captured_images[i], captured_images[i - 1])
                                for i in range(1, len(captured_images))
                            )
                            if all_images_same:
                                print(f"ภาพ 10 ภาพเหมือนกัน")
                                logging.info("ภาพ 10 ภาพเหมือนกัน")
                                send_message(bot_token, chat_id, "แจ้งเตือน: พบปัญหาภาพค้าง")
                                logging.info("ส่งข้อความแจ้งเตือนไปยัง Telegram แล้ว พบปัญหาภาพค้าง")

                                combined_image = None
                                for i in range(0, len(captured_images), 2):
                                    if i + 1 < len(captured_images):
                                        combined_pair = np.hstack([captured_images[i], captured_images[i + 1]])
                                    else:
                                        combined_pair = captured_images[i]
                                    if combined_image is None:
                                        combined_image = combined_pair
                                    else:
                                        combined_image = np.vstack([combined_image, combined_pair])

                                _, img_bytes = cv2.imencode('.png', combined_image)
                                img_bytes = BytesIO(img_bytes.tobytes())
                                send_photo(bot_token, chat_id, img_bytes, caption="ภาพที่ค้าง")
                            else:
                                print(f"ภาพ 10 ไม่เหมือนกัน = ภาพอาจจะไม่ได้ค้าง")
                                logging.info("ภาพ 10 ไม่เหมือนกัน = ภาพอาจจะไม่ได้ค้าง")
                            captured_images.clear()
                            same_frame_count = 0
                            capture_round += 1

            previous_frame = frame 
            
            cv2.imshow("Video Frame", frame) 
            if cv2.waitKey(1) & 0xFF == ord('q'):
                cap.release()
                # out.release()
                cv2.destroyAllWindows()
                break

    except Exception as e:
        messagebox.showerror("Error", f"เกิดข้อผิดพลาด: {e}")
        logging.error(f"เกิดข้อผิดพลาดใน process_video: {e}")
    finally:
        if cap.isOpened():
            cap.release()
        # out.release()    
        cv2.destroyAllWindows()

def format_time(seconds):
    hours = seconds // 3600
    minutes = (seconds % 3600) // 60
    seconds = int(seconds % 60)
    if hours > 0:
        return f"{hours} ชั่วโมง {minutes} นาที {seconds} วินาที"
    elif minutes > 0:
        return f"{minutes} นาที {seconds} วินาที"
    else:
        return f"{seconds} วินาที"

def is_image_similar(image1, image2, threshold=0.99):
    gray1 = cv2.cvtColor(image1, cv2.COLOR_BGR2GRAY)
    gray2 = cv2.cvtColor(image2, cv2.COLOR_BGR2GRAY)
    score, _ = ssim(gray1, gray2, full=True)
    return score > threshold  

def lock_fields():
    video_url_entry.configure(state="disabled", text_color="gray")
    bot_token_entry.configure(state="disabled", text_color="gray")
    chat_id_entry.configure(state="disabled", text_color="gray")

def unlock_fields():
    # ปรับสีเป็นปกติและเปิดการใช้งาน
    video_url_entry.configure(state="normal", text_color="white")
    bot_token_entry.configure(state="normal", text_color="white")
    chat_id_entry.configure(state="normal", text_color="white")

def check_credentials():
    bot_token = bot_token_entry.get()  # รับค่า BOT Token จากช่องกรอก
    chat_id = chat_id_entry.get()  # รับค่า Chat ID จากช่องกรอก

    if not bot_token or not chat_id:
        messagebox.showerror("Error", "กรุณากรอก BOT Token และ Chat ID")
        return

    url = f"https://api.telegram.org/bot{bot_token}/sendMessage"
    params = {
        "chat_id": chat_id,
        "text": "🔍 ทดสอบการเชื่อมต่อ: BOT Token และ Chat ID ถูกต้อง!"
    }

    try:
        response = requests.get(url, params=params)
        if response.status_code == 200:
            messagebox.showinfo("Success", "✅ เชื่อมต่อสำเร็จ! BOT Token และ Chat ID ถูกต้อง")
            save_settings()
        else:
            messagebox.showerror("Error", f"❌ เชื่อมต่อไม่สำเร็จ: {response.text}")
    except Exception as e:
        messagebox.showerror("Error", f"เกิดข้อผิดพลาด: {e}")


ctk.set_appearance_mode("Dark")  
ctk.set_default_color_theme("blue")  


app = ctk.CTk()
app.title("HIGH SOLUTION OF TECHNOLOGY NETWORK CO., LTD.")
app.geometry("1280 x 1024")  

p1 = PhotoImage(file = 'A:\my_output_hstn\images-Photoroom.png') 
  

app.iconphoto(False, p1) 

logo_icon = Image.open("A:\my_output_hstn\images-Photoroom.png")
ulock_icon = Image.open("A:\my_output_hstn\lock_open.png")
lock_icon = Image.open("A:\my_output_hstn\lock1.png") 
iconmain = CTkImage(light_image=logo_icon, size=(90, 90))
iconlock = CTkImage(light_image=lock_icon, size=(30, 30))
iconlock_un = CTkImage(light_image=ulock_icon, size=(30, 30))


bar_frame = ctk.CTkFrame(app, height=50, corner_radius=0)
bar_frame.pack(side="top", fill="x")


bar_icon = ctk.CTkLabel(bar_frame, text="", image=iconmain)
bar_icon.pack(side="left", padx=1)


bar_label = ctk.CTkLabel(bar_frame, text="HIGH SOLUTION OF TECHNOLOGY NETWORK CO., LTD.", font=("Arial", 15))
bar_label.pack(side="left", padx=33)


bar_histy = ctk.CTkButton(bar_frame, text="History",command=show_history, fg_color="blue", hover_color="gray", text_color="white", font=("Arial", 22))
bar_histy.pack(side="right", padx=55)


card_frame = ctk.CTkFrame(app, corner_radius=30)
card_frame.pack(side="top", fill="both", expand=True, padx=20, pady=20)  # ใช้ fill="both" เพื่อให้การ์ดยืดตามหน้าต่าง

bar_frame_b = ctk.CTkFrame(card_frame, height=50, corner_radius=30 ,fg_color=card_frame.cget("fg_color"))
bar_frame_b.pack(side="top", fill="x")

lock_button = ctk.CTkButton(bar_frame_b, text="", width=40, command=lock_fields, image=iconlock, fg_color="red")
lock_button.pack(padx=15,pady = 15,  side="right", fill="y")


unlock_button = ctk.CTkButton(bar_frame_b, text="", width=40, command=unlock_fields, image=iconlock_un, fg_color="green")
unlock_button.pack(padx=15,pady = 15,  side="right", fill="y")


video_url_label = ctk.CTkLabel(card_frame , text="Area Zome")
video_url_label.pack(pady = 10,padx=(0, 300))

video_url_entry = ctk.CTkEntry(card_frame , placeholder_text="Enter you path.",width=350 , height=44 , border_color="gray" )
video_url_entry.pack(pady=5)

bot_token_label= ctk.CTkLabel(card_frame , text="Bot Oken")
bot_token_label.pack(pady = 10 , padx=(0, 300))

bot_token_entry = ctk.CTkEntry(card_frame , placeholder_text="Enter you BOT OKEN.",width=350 , height=44 , border_color="gray")
bot_token_entry.pack(pady=5)

chat_id_label = ctk.CTkLabel(card_frame , text="Chat Id")
chat_id_label.pack(pady = 10 , padx=(0, 300))

chat_id_entry = ctk.CTkEntry(card_frame , placeholder_text="Enter you CHAT ID.",width=350 , height=44 , border_color="gray")
chat_id_entry.pack(pady=5)

frame_buttons = ctk.CTkFrame(card_frame , fg_color=card_frame.cget("fg_color"))
frame_buttons.pack(anchor="center", pady = 22)

check_button = ctk.CTkButton(frame_buttons, text="Bot Chack", fg_color="red", text_color="white", font=("Arial", 15) 
                            ,width=160 , height=44 , command = check_credentials)
check_button.pack(side="left", padx=15 )

start_button = ctk.CTkButton(frame_buttons, text="Submit", fg_color="green", text_color="white", font=("Arial", 15) ,width=160 , height=44 , command=start_processing)
start_button.pack(side="left", padx=15)

load_settings()
app.mainloop()

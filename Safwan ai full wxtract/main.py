import os
import sys
import time
import json
import threading
import psutil
import cv2
import pyttsx3
import speech_recognition as sr
import customtkinter as ctk
from PIL import Image, ImageTk

# App Setup
ctk.set_appearance_mode("Dark")
ctk.set_default_color_theme("blue")

class SafwanAIApp(ctk.CTk):
    def __init__(self):
        super().__init__()

        self.title("SAFWAN AI - Personal Assistant")
        self.geometry("900x650")

        # Load Config
        self.load_config()

        # Engine Init (TTS - Voice Reply)
        self.tts_engine = pyttsx3.init()
        self.tts_engine.setProperty('rate', 150)

        # UI Layout Setup
        self.grid_columnconfigure(1, weight=1)
        self.grid_rowconfigure(0, weight=1)

        # Sidebar
        self.sidebar = ctk.CTkFrame(self, width=200, corner_radius=0)
        self.sidebar.grid(row=0, column=0, sticky="nsew", padx=5, pady=5)
        
        self.logo_label = ctk.CTkLabel(self.sidebar, text="SAFWAN AI", font=ctk.CTkFont(size=20, weight="bold"))
        self.logo_label.pack(padx=20, pady=(20, 10))

        self.status_label = ctk.CTkLabel(self.sidebar, text="Status: Online", text_color="green")
        self.status_label.pack(padx=20, pady=5)

        self.btn_mic = ctk.CTkButton(self.sidebar, text="🎤 Voice Input", fg_color="purple", command=self.listen_voice)
        self.btn_mic.pack(padx=20, pady=10)

        self.btn_camera = ctk.CTkButton(self.sidebar, text="Toggle Security Cam", command=self.toggle_camera)
        self.btn_camera.pack(padx=20, pady=10)

        self.btn_sysinfo = ctk.CTkButton(self.sidebar, text="Check PC Stats", command=self.check_system_stats)
        self.btn_sysinfo.pack(padx=20, pady=10)

        # Main Chat Area
        self.chat_frame = ctk.CTkFrame(self, corner_radius=10)
        self.chat_frame.grid(row=0, column=1, sticky="nsew", padx=10, pady=10)
        self.chat_frame.grid_rowconfigure(0, weight=1)
        self.chat_frame.grid_columnconfigure(0, weight=1)

        self.chat_box = ctk.CTkTextbox(self.chat_frame, state="disabled")
        self.chat_box.grid(row=0, column=0, columnspan=2, sticky="nsew", padx=10, pady=10)

        self.entry_msg = ctk.CTkEntry(self.chat_frame, placeholder_text="এখানে বাংলায় বা ইংরেজিতে লিখুন...")
        self.entry_msg.grid(row=1, column=0, sticky="ew", padx=(10, 5), pady=10)
        self.entry_msg.bind("<Return>", lambda event: self.send_message())

        self.btn_send = ctk.CTkButton(self.chat_frame, text="Send", width=80, command=self.send_message)
        self.btn_send.grid(row=1, column=1, sticky="e", padx=(5, 10), pady=10)

        # Background Threads for Monitoring
        self.cam_running = False
        self.cap = None
        self.start_usb_monitoring()

        self.append_chat("SAFWAN AI", "স্বাগতম! আমি প্রস্তুত। মাইক্রোফোন বা চ্যাটের মাধ্যমে কথা বলুন।")

    def load_config(self):
        if os.path.exists("config.json"):
            with open("config.json", "r", encoding="utf-8") as f:
                self.config = json.load(f)
        else:
            self.config = {"app_name": "SAFWAN AI"}

    def append_chat(self, sender, text):
        self.chat_box.configure(state="normal")
        self.chat_box.insert("end", f"[{sender}]: {text}\n\n")
        self.chat_box.configure(state="disabled")
        self.chat_box.see("end")

    def speak(self, text):
        def _speak():
            self.tts_engine.say(text)
            self.tts_engine.runAndWait()
        threading.Thread(target=_speak, daemon=True).start()

    def send_message(self):
        user_text = self.entry_msg.get().strip()
        if not user_text:
            return
        
        self.append_chat("You", user_text)
        self.entry_msg.delete(0, "end")
        self.process_command(user_text)

    # Voice Input (Speech Recognition)
    def listen_voice(self):
        def _listen():
            r = sr.Recognizer()
            with sr.Microphone() as source:
                self.append_chat("System", "শুনছি... কথা বলুন।")
                r.adjust_for_ambient_noise(source, duration=1)
                try:
                    audio = r.listen(source, timeout=5, phrase_time_limit=10)
                    # Bengali (bn-BD) and English (en-US) support
                    text = r.recognize_google(audio, language="bn-BD")
                    self.append_chat("You (Voice)", text)
                    self.process_command(text)
                except sr.UnknownValueError:
                    self.append_chat("System", "দুঃখিত, কথা পরিষ্কার বুঝতে পারিনি। আবার চেষ্টা করুন।")
                except sr.RequestError:
                    self.append_chat("System", "ইন্টারনেট সংযোগ বা স্পিচ সার্ভিস কাজ করছে না।")
                except Exception as e:
                    self.append_chat("System", f"ভয়েস এরর: {str(e)}")

        threading.Thread(target=_listen, daemon=True).start()

    def process_command(self, text):
        text_lower = text.lower()

        # Command Rules
        if "hello" in text_lower or "হ্যালো" in text_lower or "কেমন আছো" in text_lower:
            reply = "আমি ভালো আছি! আপনাকে কীভাবে সাহায্য করব?"
        elif "status" in text_lower or "অবস্থা" in text_lower:
            reply = self.get_system_status_text()
        elif "shutdown" in text_lower or "বন্ধ কর" in text_lower:
            reply = "কম্পিউটার ৫ সেকেন্ডের মধ্যে বন্ধ হচ্ছে..."
            os.system("shutdown /s /t 5")
        elif "lock" in text_lower or "লক কর" in text_lower:
            reply = "পিসি লক করা হচ্ছে।"
            os.system("rundll32.exe user32.dll,LockWorkStation")
        else:
            reply = f"বুঝেছি: '{text}'। আমি এটি সম্পন্ন করার চেষ্টা করছি।"

        self.append_chat("SAFWAN AI", reply)
        self.speak(reply)

    def get_system_status_text(self):
        cpu = psutil.cpu_percent()
        ram = psutil.virtual_memory().percent
        return f"CPU ব্যবহার: {cpu}% | RAM ব্যবহার: {ram}%"

    def check_system_stats(self):
        stats = self.get_system_status_text()
        self.append_chat("System Guard", stats)

    # USB Monitoring
    def start_usb_monitoring(self):
        def monitor():
            initial_drives = set(psutil.disk_partitions())
            while True:
                time.sleep(3)
                current_drives = set(psutil.disk_partitions())
                new_drives = current_drives - initial_drives
                if new_drives:
                    for drive in new_drives:
                        msg = f"সতর্কতা: নতুন ডিভাইস যুক্ত হয়েছে! -> {drive.device}"
                        self.append_chat("Security Alert", msg)
                        self.speak("Security Alert! New USB drive detected.")
                    initial_drives = current_drives
        
        threading.Thread(target=monitor, daemon=True).start()

    # Camera & Face Detection
    def toggle_camera(self):
        if not self.cam_running:
            self.cam_running = True
            threading.Thread(target=self.run_camera, daemon=True).start()
            self.append_chat("Security", "ক্যামেরা নিরাপত্তা চালু করা হয়েছে।")
        else:
            self.cam_running = False
            self.append_chat("Security", "ক্যামেরা সিকিউরিটি বন্ধ করা হলো।")

    def run_camera(self):
        face_cascade = cv2.CascadeClassifier(cv2.data.haarcascades + 'haarcascade_frontalface_default.xml')
        self.cap = cv2.VideoCapture(0)

        while self.cam_running:
            ret, frame = self.cap.read()
            if not ret:
                break
            
            gray = cv2.cvtColor(frame, cv2.COLOR_BGR2GRAY)
            faces = face_cascade.detectMultiScale(gray, 1.1, 4)

            for (x, y, w, h) in faces:
                cv2.rectangle(frame, (x, y), (x+w, y+h), (255, 0, 0), 2)
                cv2.putText(frame, "Person Detected", (x, y-10), cv2.FONT_HERSHEY_SIMPLEX, 0.8, (0, 255, 0), 2)

            cv2.imshow("SAFWAN AI - Security Monitor", frame)
            if cv2.waitKey(1) & 0xFF == ord('q'):
                break

        if self.cap:
            self.cap.release()
        cv2.destroyAllWindows()
        self.cam_running = False

if __name__ == "__main__":
    app = SafwanAIApp()
    app.mainloop()

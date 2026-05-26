import os

import sys

import asyncio

import threading

import queue

import time

import requests

import customtkinter as ctk

from tkinter import messagebox, ttk

from datetime import datetime

from telethon import TelegramClient

from telethon.tl.functions.messages import RequestWebViewRequest



ctk.set_appearance_mode("dark")

ctk.set_default_color_theme("dark-blue")



API_ID = 28752231

API_HASH = 'ec1c1f2c30e2f1855c3edee7e348480b'

SESSION_DIR = "sessions"

CURRENT_VERSION = "5.4"



# ================== RAW LINK (Ẩn trong code) ==================

RAW_MAIN_URL = "https://raw.githubusercontent.com/skibidi69-tung/Farm-Telegram/main/main_gui.py"



TOOLS_RAW = {
    "ADS_TON_bot": "https://raw.githubusercontent.com/skibidi69-tung/Farm-Telegram/main/tools/ADS_TON_bot.py",
    "notbux_bot": "https://raw.githubusercontent.com/skibidi69-tung/Farm-Telegram/main/tools/notbux_bot.py",
    "EggsHatchBot": "https://raw.githubusercontent.com/skibidi69-tung/Farm-Telegram/main/tools/EggsHatchBot.py",
    "treward_ton_bot": "https://raw.githubusercontent.com/skibidi69-tung/Farm-Telegram/main/tools/treward_ton_bot.py",
    "GeneratorBot": "https://raw.githubusercontent.com/skibidi69-tung/Farm-Telegram/main/tools/GeneratorBot.py"
}


log_queue = queue.Queue()



def log_to_gui(message: str, color: str = "white"):

    log_queue.put((message, color))



class C36Darkside(ctk.CTk):

    def __init__(self):

        super().__init__()

        self.title(f"C36 - Darkside v{CURRENT_VERSION}")

        self.geometry("1150x780")

        self.configure(fg_color="#0a0a0a")



        if not os.path.exists(SESSION_DIR):

            os.makedirs(SESSION_DIR)



        self.create_main_ui()

        threading.Thread(target=self.process_log_queue, daemon=True).start()

        self.after(800, self.refresh_sessions)



        threading.Thread(target=self.check_main_update, daemon=True).start()



    # ================== AUTO UPDATE MAIN (không hiển thị link) ==================

    def check_main_update(self):

        try:

            log_to_gui("Đang kiểm tra cập nhật main tool...", "cyan")

            r = requests.get(RAW_MAIN_URL, timeout=10)

            if r.status_code == 200 and f'CURRENT_VERSION = "{CURRENT_VERSION}"' not in r.text:

                log_to_gui("Phát hiện phiên bản main mới!", "yellow")

                if messagebox.askyesno("Cập nhật", "Có phiên bản mới.\nBạn có muốn cập nhật ngay không?"):

                    self.update_main(r.text)

        except:

            log_to_gui("Không thể kiểm tra cập nhật.", "yellow")



    def update_main(self, new_code):

        try:

            with open("main_gui_new.py", "w", encoding="utf-8") as f:

                f.write(new_code)

            log_to_gui("Đã tải bản cập nhật mới.", "green")

            time.sleep(2)

            os.execl(sys.executable, sys.executable, "main_gui_new.py")

        except Exception as e:

            log_to_gui(f"Lỗi cập nhật: {e}", "red")



    def create_main_ui(self):

        header = ctk.CTkFrame(self, height=80, fg_color="#111111")

        header.pack(fill="x")

        header.pack_propagate(False)



        ctk.CTkLabel(header, text="C36", font=ctk.CTkFont(size=30, weight="bold"),

                     text_color="#00ff9d").pack(side="left", padx=30, pady=20)

        ctk.CTkLabel(header, text="Darkside", font=ctk.CTkFont(size=14),

                     text_color="#666666").pack(side="left", pady=25)



        ctk.CTkLabel(header, text="DESKTOP OPERATOR CONSOLE", 

                     font=ctk.CTkFont(size=12), text_color="#555555").pack(side="left", padx=50, pady=25)



        main_frame = ctk.CTkFrame(self, fg_color="#121212")

        main_frame.pack(fill="both", expand=True, padx=20, pady=15)



        self.tabview = ctk.CTkTabview(main_frame, fg_color="#1a1a1a", 

                                      segmented_button_fg_color="#222222",

                                      segmented_button_selected_color="#00ff9d")

        self.tabview.pack(fill="both", expand=True, padx=10, pady=10)



        self.create_sessions_tab(self.tabview.add("Sessions"))

        self.create_login_tab(self.tabview.add("Login Telegram"))

        self.create_tools_tab(self.tabview.add("Tools"))



        # Log Area

        log_frame = ctk.CTkFrame(self, height=170, fg_color="#0a0a0a")

        log_frame.pack(fill="x", padx=20, pady=(0, 20))



        log_header = ctk.CTkFrame(log_frame, fg_color="transparent")

        log_header.pack(fill="x", padx=15, pady=5)

        ctk.CTkLabel(log_header, text="LOG", font=ctk.CTkFont(size=13, weight="bold"),

                     text_color="#00ff9d").pack(side="left")

        ctk.CTkButton(log_header, text="CLEAR", width=70, height=26, fg_color="#333", 

                      command=self.clear_log).pack(side="right")



        self.log_text = ctk.CTkTextbox(log_frame, fg_color="#0a0a0a", text_color="#cccccc", 

                                       font=ctk.CTkFont(size=13), height=130)

        self.log_text.pack(fill="both", expand=True, padx=15, pady=(0,10))



    def clear_log(self):

        self.log_text.delete("1.0", "end")



    def create_sessions_tab(self, parent):

        self.tree = ttk.Treeview(parent, columns=("File", "Phone", "Status"), show="headings", height=16)

        self.tree.heading("File", text="File Session")

        self.tree.heading("Phone", text="Số điện thoại")

        self.tree.heading("Status", text="Status")

        self.tree.pack(fill="both", expand=True, padx=15, pady=15)



        btn_frame = ctk.CTkFrame(parent, fg_color="transparent")

        btn_frame.pack(pady=10)

        ctk.CTkButton(btn_frame, text="REFRESH", command=self.refresh_sessions).pack(side="left", padx=10)



    def refresh_sessions(self):

        for item in self.tree.get_children():

            self.tree.delete(item)



        for f in sorted(os.listdir(SESSION_DIR)):

            if f.endswith(".session"):

                phone = f.replace(".session", "")

                display_phone = "+" + phone if not phone.startswith("+") else phone

                status = "LIVE" if self.is_session_valid(f) else "DEAD"

                self.tree.insert("", "end", values=(f, display_phone, status))



    def is_session_valid(self, session_file):

        try:

            client = TelegramClient(os.path.join(SESSION_DIR, session_file), API_ID, API_HASH)

            client.connect()

            valid = client.is_user_authorized()

            client.disconnect()

            return valid

        except:

            return False



    def create_login_tab(self, parent):

        frame = ctk.CTkFrame(parent, fg_color="#1a1a1a")

        frame.pack(fill="both", expand=True, padx=40, pady=40)



        ctk.CTkLabel(frame, text="Login Telegram", font=ctk.CTkFont(size=22, weight="bold")).pack(pady=20)



        ctk.CTkLabel(frame, text="Số điện thoại (bao gồm +)", font=ctk.CTkFont(size=13)).pack(anchor="w", padx=20, pady=(10,5))

        self.phone_entry = ctk.CTkEntry(frame, placeholder_text="+84912345678", width=400, height=40)

        self.phone_entry.pack(pady=10, padx=20)



        self.login_btn = ctk.CTkButton(frame, text="ĐĂNG NHẬP", height=48, fg_color="#00ff9d", text_color="black",

                                       font=ctk.CTkFont(size=14, weight="bold"), command=self.start_login)

        self.login_btn.pack(pady=30)



    def start_login(self):

        phone = self.phone_entry.get().strip()

        if not phone or not phone.startswith("+"):

            messagebox.showerror("Lỗi", "Số điện thoại phải bắt đầu bằng +")

            return



        self.login_btn.configure(state="disabled")

        threading.Thread(target=lambda: asyncio.run(self.login_async(phone)), daemon=True).start()



    async def login_async(self, phone):

        sess_name = phone.replace("+", "").replace(" ", "").replace("-", "")

        try:

            client = TelegramClient(os.path.join(SESSION_DIR, sess_name), API_ID, API_HASH)

            await client.start(phone=phone)

            me = await client.get_me()

            log_to_gui(f"Đăng nhập thành công: {me.first_name} | {sess_name}.session", "green")

            self.after(0, self.refresh_sessions)

            self.after(0, lambda: messagebox.showinfo("Thành công", f"Đăng nhập OK!\nFile: {sess_name}.session"))

        except Exception as e:

            log_to_gui(f"Lỗi login: {e}", "red")

        finally:

            self.after(0, lambda: self.login_btn.configure(state="normal"))



    def create_tools_tab(self, parent):

        scroll = ctk.CTkScrollableFrame(parent, fg_color="#1a1a1a")
        scroll.pack(fill="both", expand=True, padx=20, pady=20)

        # Header
        ctk.CTkLabel(scroll, text="Tools", font=ctk.CTkFont(size=18, weight="bold")).pack(pady=(15, 5))

        # Nút Run Selected
        btn_frame = ctk.CTkFrame(scroll, fg_color="transparent")
        btn_frame.pack(pady=(5, 15))

        ctk.CTkButton(btn_frame, text="▶ RUN SELECTED", height=42, fg_color="#00ff9d",
                      text_color="black", font=ctk.CTkFont(size=14, weight="bold"),
                      command=self.run_selected).pack(side="left", padx=10)

        ctk.CTkButton(btn_frame, text="▶ RUN ALL", height=42, fg_color="#00ff9d",
                      text_color="black", font=ctk.CTkFont(size=14, weight="bold"),
                      command=self.run_all_tools).pack(side="left", padx=10)

        # Danh sách tool với checkbox - Grid layout
        container = ctk.CTkFrame(scroll, fg_color="transparent")
        container.pack(fill="both", expand=True, padx=40)

        container.grid_columnconfigure(0, weight=1, uniform="col")
        container.grid_columnconfigure(1, weight=1, uniform="col")

        self.tool_vars = {}
        tools = list(TOOLS_RAW.keys())
        for i, name in enumerate(tools):
            row, col = divmod(i, 2)
            var = ctk.BooleanVar(value=True)
            self.tool_vars[name] = var
            cb = ctk.CTkCheckBox(container, text=name, variable=var, font=ctk.CTkFont(size=13),
                                 fg_color="#00ff9d", hover_color="#00cc7a",
                                 checkbox_width=20, checkbox_height=20)
            cb.grid(row=row, column=col, sticky="w", padx=10, pady=5)

    def run_selected(self):
        selected = [name for name, var in self.tool_vars.items() if var.get()]
        if not selected:
            messagebox.showwarning("Cảnh báo", "Chưa chọn tool nào!")
            return
        log_to_gui(f"▶ Chạy {len(selected)} tool đã chọn...", "cyan")
        for name in selected:
            self.run_all(name)

    def run_all_tools(self):
        log_to_gui(f"▶ Chạy tất cả {len(TOOLS_RAW)} tool...", "cyan")
        for name in TOOLS_RAW:
            self.run_all(name)

    def run_all(self, tool_name):
        raw_url = TOOLS_RAW.get(tool_name)

        if not raw_url:

            log_to_gui(f"Tool {tool_name} chưa được cấu hình", "red")

            return



        session_files = [f for f in os.listdir(SESSION_DIR) if f.endswith('.session')]

        if not session_files:

            messagebox.showwarning("Cảnh báo", "Không có session nào!")

            return



        log_to_gui(f"Đang tải và chạy {tool_name}...", "cyan")   # Không hiển thị link

        threading.Thread(target=self.run_tool_from_raw, args=(tool_name, raw_url, session_files), daemon=True).start()



    # ================== ĐÃ ĐƯỢC FIX TRIỆT ĐỂ Ở ĐÂY ==================

    def run_tool_from_raw(self, tool_name, raw_url, session_files):

        try:

            # 1. Thêm Anti-Cache để bắt GitHub nhả code mới ngay lập tức

            buster_url = f"{raw_url}?t={int(time.time())}"

            r = requests.get(buster_url, timeout=15)

            if r.status_code != 200:

                log_to_gui(f"Không thể tải tool {tool_name}", "red")

                return



            tool_code = r.text

            log_to_gui(f"Đang thực thi {tool_name}...", "green")



            # 2. Bốc toàn bộ biến hệ thống (globals) hiện có để tool không bao giờ thiếu thư viện khi biên dịch

            local_globals = dict(globals())

            local_globals.update({

                "log_to_gui": log_to_gui,

                "SESSION_DIR": SESSION_DIR,

                "session_files": session_files

            })



            # 3. Nạp code vào môi trường thực thi đầy đủ

            exec(tool_code, local_globals)



            # 4. Trích xuất hàm chạy của tool

            run_func = local_globals.get("run")

            if run_func:

                # 5. Gọi hàm dạng Sync hoặc Async một cách thông minh tùy cấu trúc tool

                if asyncio.iscoroutinefunction(run_func):

                    asyncio.run(run_func(session_files))

                else:

                    run_func(session_files)

                    

                log_to_gui(f"Hoàn thành {tool_name}!", "green")

            else:

                log_to_gui(f"Tool {tool_name} không có hàm run() hoặc lỗi cú pháp biên dịch", "red")

        except Exception as e:

            log_to_gui(f"Lỗi khi chạy {tool_name}: {e}", "red")



    def process_log_queue(self):

        while True:

            try:

                msg, color = log_queue.get(timeout=0.1)

                self.after(0, self.append_log, msg, color)

            except:

                time.sleep(0.05)



    def append_log(self, message, color):

        if int(self.log_text.index("end-1c").split('.')[0]) > 30:

            self.log_text.delete("1.0", "2.0")

        tag = "green" if color == "green" else "red" if color == "red" else "normal"

        self.log_text.insert("end", message + "\n", tag)

        self.log_text.see("end")



    def run(self):

        self.mainloop()





if __name__ == "__main__":

    print("🚀 Khởi động C36 - Darkside...")

    app = C36Darkside()

    app.run()


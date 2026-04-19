import os
import sys
import asyncio
import threading
import importlib.util
import queue
import time
import customtkinter as ctk
from tkinter import messagebox, ttk
from datetime import datetime
from telethon import TelegramClient

ctk.set_appearance_mode("dark")
ctk.set_default_color_theme("dark-blue")

API_ID = 28752231
API_HASH = 'ec1c1f2c30e2f1855c3edee7e348480b'
SESSION_DIR = "sessions"
TOOLS_DIR = "tools"
VERSION = "5.1-DARK"

log_queue = queue.Queue()

def log_to_gui(message: str, color: str = "white"):
    log_queue.put((message, color))

class C36Darkside(ctk.CTk):
    def __init__(self):
        super().__init__()
        self.title("C36 - Darkside")
        self.geometry("1150x780")
        self.configure(fg_color="#0a0a0a")

        if not os.path.exists(SESSION_DIR):
            os.makedirs(SESSION_DIR)

        self.tools = self.load_tools()

        self.create_main_ui()
        threading.Thread(target=self.process_log_queue, daemon=True).start()
        self.after(800, self.check_all_sessions)

    def create_main_ui(self):
        # Header
        header = ctk.CTkFrame(self, height=85, fg_color="#111111")
        header.pack(fill="x")
        header.pack_propagate(False)

        title_frame = ctk.CTkFrame(header, fg_color="transparent")
        title_frame.pack(side="left", padx=30, pady=15)
        ctk.CTkLabel(title_frame, text="C36", font=ctk.CTkFont(size=32, weight="bold"),
                     text_color="#00ff9d").pack(anchor="w")
        ctk.CTkLabel(title_frame, text="Darkside", font=ctk.CTkFont(size=13),
                     text_color="#666666").pack(anchor="w")

        ctk.CTkLabel(header, text="DESKTOP OPERATOR CONSOLE", 
                     font=ctk.CTkFont(size=12), text_color="#555555").pack(side="left", padx=40, pady=25)

        right_frame = ctk.CTkFrame(header, fg_color="transparent")
        right_frame.pack(side="right", padx=30)
        ctk.CTkLabel(right_frame, text="Darkside", text_color="#888888", font=ctk.CTkFont(size=13)).pack(anchor="e")
        ctk.CTkLabel(right_frame, text=f"v{VERSION}", text_color="#444444", font=ctk.CTkFont(size=11)).pack(anchor="e")

        main_frame = ctk.CTkFrame(self, fg_color="#121212")
        main_frame.pack(fill="both", expand=True, padx=20, pady=15)

        self.tabview = ctk.CTkTabview(main_frame, fg_color="#1a1a1a", 
                                      segmented_button_fg_color="#222222",
                                      segmented_button_selected_color="#00ff9d")
        self.tabview.pack(fill="both", expand=True, padx=10, pady=10)

        tab1 = self.tabview.add("Sessions")
        self.create_sessions_tab(tab1)

        tab2 = self.tabview.add("Login Telegram")
        self.create_login_tab(tab2)

        tab3 = self.tabview.add("Tools")
        self.create_tools_tab(tab3)

        # Log Area - Sạch & Không trôi
        log_frame = ctk.CTkFrame(self, height=170, fg_color="#0a0a0a")
        log_frame.pack(fill="x", padx=20, pady=(0, 20))

        log_header = ctk.CTkFrame(log_frame, fg_color="transparent")
        log_header.pack(fill="x", padx=15, pady=5)
        ctk.CTkLabel(log_header, text="CONSOLE LOG", font=ctk.CTkFont(size=13, weight="bold"),
                     text_color="#00ff9d").pack(side="left")
        ctk.CTkButton(log_header, text="CLEAR", width=80, height=26, fg_color="#333333", 
                      command=self.clear_log).pack(side="right")

        self.log_text = ctk.CTkTextbox(log_frame, fg_color="#0a0a0a", text_color="#cccccc", 
                                       font=ctk.CTkFont(size=13), height=130)   # Sửa size=13
        self.log_text.pack(fill="both", expand=True, padx=15, pady=(0,10))

    def clear_log(self):
        self.log_text.delete("1.0", "end")

    # ====================== SESSIONS ======================
    def create_sessions_tab(self, parent):
        frame = ctk.CTkFrame(parent, fg_color="#1a1a1a")
        frame.pack(fill="both", expand=True, padx=15, pady=15)

        self.tree = ttk.Treeview(frame, columns=("File", "Phone", "Status", "Time"), show="headings", height=15)
        self.tree.heading("File", text="File Session")
        self.tree.heading("Phone", text="Số điện thoại")
        self.tree.heading("Status", text="Status")
        self.tree.heading("Time", text="Last Checked")
        self.tree.pack(fill="both", expand=True, padx=10, pady=10)

        btn_frame = ctk.CTkFrame(parent, fg_color="transparent")
        btn_frame.pack(pady=12)
        ctk.CTkButton(btn_frame, text="REFRESH & CHECK", width=180, height=38, fg_color="#00ff9d", text_color="black",
                      command=self.check_all_sessions).pack(side="left", padx=10)

    def check_all_sessions(self):
        if not self.tree: return
        log_to_gui("Đang kiểm tra tất cả session...", "cyan")

        for item in self.tree.get_children():
            self.tree.delete(item)

        for f in sorted(os.listdir(SESSION_DIR)):
            if f.endswith(".session"):
                raw_phone = f.replace(".session", "")
                display_phone = "+" + raw_phone if not raw_phone.startswith("+") else raw_phone
                status = self.check_single_session(f)
                self.tree.insert("", "end", values=(f, display_phone, status, datetime.now().strftime("%H:%M %d/%m")))

        log_to_gui("Hoàn tất kiểm tra session.", "green")

    def check_single_session(self, session_file):
        try:
            client = TelegramClient(os.path.join(SESSION_DIR, session_file), API_ID, API_HASH)
            client.connect()
            valid = client.is_user_authorized()
            client.disconnect()
            return "LIVE" if valid else "DEAD"
        except:
            return "ERROR"

    # ====================== LOGIN ======================
    def create_login_tab(self, parent):
        frame = ctk.CTkFrame(parent, fg_color="#1a1a1a")
        frame.pack(fill="both", expand=True, padx=40, pady=40)

        ctk.CTkLabel(frame, text="Login Telegram", font=ctk.CTkFont(size=22, weight="bold")).pack(pady=20)

        ctk.CTkLabel(frame, text="Số điện thoại (bao gồm +)", font=ctk.CTkFont(size=13)).pack(anchor="w", padx=20, pady=(10,5))
        self.phone_entry = ctk.CTkEntry(frame, placeholder_text="+84912345678", width=420, height=42)
        self.phone_entry.pack(pady=8, padx=20)

        self.login_btn = ctk.CTkButton(frame, text="ĐĂNG NHẬP TELEGRAM", height=52, fg_color="#00ff9d", 
                                       text_color="black", font=ctk.CTkFont(size=15, weight="bold"),
                                       command=self.start_telegram_login)
        self.login_btn.pack(pady=40)

        self.status_label = ctk.CTkLabel(frame, text="", text_color="#00ff9d", font=ctk.CTkFont(size=13))
        self.status_label.pack()

    def start_telegram_login(self):
        phone = self.phone_entry.get().strip()
        if not phone or not phone.startswith("+"):
            messagebox.showerror("Lỗi", "Vui lòng nhập số điện thoại bắt đầu bằng +")
            return

        self.login_btn.configure(state="disabled", text="ĐANG KẾT NỐI...")
        self.status_label.configure(text="Đang gửi mã OTP...", text_color="yellow")

        threading.Thread(target=lambda: asyncio.run(self.telegram_login_async(phone)), daemon=True).start()

    async def telegram_login_async(self, phone):
        sess_name = phone.replace("+", "").replace(" ", "").replace("-", "")
        session_path = os.path.join(SESSION_DIR, sess_name)

        client = None
        try:
            client = TelegramClient(session_path, API_ID, API_HASH)
            await client.connect()

            if not await client.is_user_authorized():
                log_to_gui(f"Đang gửi mã OTP đến {phone}...", "cyan")
                await client.send_code_request(phone)

                code = await self.ask_otp_from_gui(phone)
                if code is None:
                    log_to_gui("Người dùng hủy đăng nhập", "yellow")
                    return

                await client.sign_in(phone, code)

            me = await client.get_me()
            log_to_gui(f"Đăng nhập thành công → {me.first_name} | {sess_name}.session", "green")

            self.after(0, lambda: messagebox.showinfo("Thành công", 
                f"Đăng nhập thành công!\nSố: {phone}\nTên: {me.first_name}"))
            self.after(0, self.check_all_sessions)

        except Exception as e:
            log_to_gui(f"Lỗi: {e}", "red")
            self.after(0, lambda: messagebox.showerror("Lỗi", f"Đăng nhập thất bại:\n{e}"))
        finally:
            self.after(0, lambda: self.login_btn.configure(state="normal", text="ĐĂNG NHẬP TELEGRAM"))
            if client:
                try: await client.disconnect()
                except: pass

    async def ask_otp_from_gui(self, phone):
        def ask():
            dialog = ctk.CTkToplevel(self)
            dialog.title("Nhập mã OTP")
            dialog.geometry("400x220")
            dialog.configure(fg_color="#1a1a1a")
            dialog.grab_set()

            ctk.CTkLabel(dialog, text=f"Mã OTP đã gửi đến:\n{phone}", font=ctk.CTkFont(size=13)).pack(pady=20)
            entry = ctk.CTkEntry(dialog, placeholder_text="Nhập 6 số OTP", width=220, height=40)
            entry.pack(pady=10)

            result = {"code": None}

            def submit():
                result["code"] = entry.get().strip()
                dialog.destroy()

            def cancel():
                result["code"] = None
                dialog.destroy()

            btn_frame = ctk.CTkFrame(dialog, fg_color="transparent")
            btn_frame.pack(pady=20)
            ctk.CTkButton(btn_frame, text="Xác nhận", fg_color="#00ff9d", text_color="black", command=submit).pack(side="left", padx=15)
            ctk.CTkButton(btn_frame, text="Hủy", fg_color="#c42b1c", command=cancel).pack(side="left", padx=15)

            self.wait_window(dialog)
            return result["code"]

        loop = asyncio.get_event_loop()
        return await loop.run_in_executor(None, ask)

    # ====================== TOOLS TAB ======================
    def create_tools_tab(self, parent):
        frame = ctk.CTkFrame(parent, fg_color="#1a1a1a")
        frame.pack(fill="both", expand=True, padx=40, pady=40)

        ctk.CTkLabel(frame, text="RUN ALL TOOLS", font=ctk.CTkFont(size=20, weight="bold")).pack(pady=30)

        for tool_name in self.tools.keys():
            btn = ctk.CTkButton(frame, text=f"RUN ALL → {tool_name}", 
                                height=58, 
                                fg_color="#00ff9d", 
                                text_color="black", 
                                font=ctk.CTkFont(size=16, weight="bold"),
                                hover_color="#00cc7a",
                                command=lambda t=tool_name: self.run_all_accounts(t))
            btn.pack(pady=12, padx=100, fill="x")

    def run_all_accounts(self, tool_name):
        session_files = [f for f in os.listdir(SESSION_DIR) if f.endswith('.session')]
        if not session_files:
            messagebox.showwarning("Cảnh báo", "Không có session nào!")
            return

        func = self.tools.get(tool_name)
        if not func:
            log_to_gui(f"Tool {tool_name} không tồn tại!", "red")
            return

        log_to_gui(f"Đang chạy {tool_name} trên {len(session_files)} tài khoản...", "cyan")

        threading.Thread(target=self.run_tool_thread, args=(func, session_files, tool_name), daemon=True).start()

    def run_tool_thread(self, func, session_files, tool_name):
        try:
            asyncio.run(func(session_files))
            log_to_gui(f"Hoàn thành {tool_name}!", "green")
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
        # Giới hạn 30 dòng
        if int(self.log_text.index("end-1c").split('.')[0]) > 30:
            self.log_text.delete("1.0", "2.0")

        tag = "green" if color == "green" else "red" if color == "red" else "normal"
        self.log_text.insert("end", message + "\n", tag)
        self.log_text.see("end")

        self.log_text.tag_config("green", foreground="#00ff9d")
        self.log_text.tag_config("red", foreground="#ff5555")

    def load_tools(self):
        tools = {}
        if not os.path.exists(TOOLS_DIR):
            os.makedirs(TOOLS_DIR)
            return tools
        for f in os.listdir(TOOLS_DIR):
            if f.endswith(".py") and not f.startswith("__"):
                name = f[:-3].replace("_", " ").title()
                path = os.path.join(TOOLS_DIR, f)
                try:
                    spec = importlib.util.spec_from_file_location(f[:-3], path)
                    module = importlib.util.module_from_spec(spec)
                    spec.loader.exec_module(module)
                    if hasattr(module, "log_to_gui"):
                        module.log_to_gui = log_to_gui
                    for attr in ["run", "main", "start_work"]:
                        if hasattr(module, attr):
                            tools[name] = getattr(module, attr)
                            break
                except:
                    pass
        return tools

    def run(self):
        self.mainloop()


if __name__ == "__main__":
    print("🚀 Khởi động C36 - Darkside...")
    app = C36Darkside()
    app.run()
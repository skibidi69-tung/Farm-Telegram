import os
import sys
import asyncio
import threading
import queue
import time
import requests
import customtkinter as ctk
from tkinter import messagebox, ttk, simpledialog
from datetime import datetime
from telethon import TelegramClient
from telethon.tl.functions.messages import RequestWebViewRequest

ctk.set_appearance_mode("dark")
ctk.set_default_color_theme("green")

API_ID = 28752231
API_HASH = 'ec1c1f2c30e2f1855c3edee7e348480b'
SESSION_DIR = "sessions"
CURRENT_VERSION = "3.6"
RAW_MAIN_URL = "https://raw.githubusercontent.com/skibidi69-tung/Farm-Telegram/main/main_gui.py"

TOOLS_RAW = {
    "ADS_TON_bot": "https://raw.githubusercontent.com/skibidi69-tung/Farm-Telegram/main/tools/ADS_TON_bot.py",
    "notbux_bot": "https://raw.githubusercontent.com/skibidi69-tung/Farm-Telegram/main/tools/notbux_bot.py",
    "EggsHatchBot": "https://raw.githubusercontent.com/skibidi69-tung/Farm-Telegram/main/tools/EggsHatchBot.py",
    "treward_ton_bot": "https://raw.githubusercontent.com/skibidi69-tung/Farm-Telegram/main/tools/treward_ton_bot.py",
    "GeneratorBot": "https://raw.githubusercontent.com/skibidi69-tung/Farm-Telegram/main/tools/GeneratorBot.py",
    "FishVerseBot": "https://raw.githubusercontent.com/skibidi69-tung/Farm-Telegram/main/tools/FishVerseBot.py"
}

log_queue = queue.Queue()

def log_to_gui(message, color="white"):
    log_queue.put((message, color))

class App(ctk.CTk):
    accent = "#b388ff"
    accent2 = "#7c4dff"
    bg_dark = "#0a0a0f"
    bg_med = "#12121a"
    bg_light = "#1a1a26"

    def __init__(self):
        super().__init__()
        self.title(f"C36  v{CURRENT_VERSION}")
        self.geometry("820x560")
        self.configure(fg_color=self.bg_dark)
        if not os.path.exists(SESSION_DIR): os.makedirs(SESSION_DIR)
        self.build()
        threading.Thread(target=self.process_log_queue, daemon=True).start()
        self.after(800, self.refresh_sessions)

    def build(self):
        # Header
        h = ctk.CTkFrame(self, height=36, fg_color=self.bg_med)
        h.pack(fill="x")
        h.pack_propagate(0)
        ctk.CTkLabel(h, text="◈ C36", font=ctk.CTkFont(size=16, weight="bold"),
                     text_color=self.accent).pack(side="left", padx=16)
        ctk.CTkLabel(h, text="Console", font=ctk.CTkFont(size=9),
                     text_color="#555").pack(side="left", pady=10)

        # Tabs
        m = ctk.CTkFrame(self, fg_color=self.bg_dark)
        m.pack(fill="both", expand=True, padx=8, pady=6)

        self.tv = ctk.CTkTabview(m, fg_color=self.bg_med,
                                 segmented_button_fg_color="#222",
                                 segmented_button_selected_color=self.accent2,
                                 segmented_button_selected_hover_color=self.accent)
        self.tv.pack(fill="both", expand=True, padx=4, pady=4)

        self.sess_tab = self.tv.add("Sessions")
        self.tools_tab = self.tv.add("Tools")

        self.build_sessions()
        self.build_tools()

        # Log
        lf = ctk.CTkFrame(self, height=80, fg_color=self.bg_dark)
        lf.pack(fill="x", padx=8, pady=(0, 8))

        lh = ctk.CTkFrame(lf, fg_color="transparent")
        lh.pack(fill="x", padx=8, pady=1)
        ctk.CTkLabel(lh, text="LOG", font=ctk.CTkFont(size=9, weight="bold"),
                     text_color=self.accent).pack(side="left")
        ctk.CTkButton(lh, text="✕", width=22, height=16, fg_color="#333",
                      hover_color="#555", font=ctk.CTkFont(size=8),
                      command=self.clear_log).pack(side="right")

        self.log_text = ctk.CTkTextbox(lf, fg_color=self.bg_dark, text_color="#bbb",
                                       font=ctk.CTkFont(size=10), height=55)
        self.log_text.pack(fill="both", expand=True, padx=8, pady=(0, 4))

    def clear_log(self):
        self.log_text.delete("1.0", "end")

    # ── Sessions ──
    def build_sessions(self):
        lf = ctk.CTkFrame(self.sess_tab, fg_color="transparent")
        lf.pack(fill="x", padx=8, pady=(6, 2))
        ctk.CTkLabel(lf, text="Phone:", font=ctk.CTkFont(size=10),
                     text_color=self.accent).pack(side="left", padx=(0, 4))
        self.phone_entry = ctk.CTkEntry(lf, placeholder_text="+84912345678",
                                        width=120, height=24)
        self.phone_entry.pack(side="left", padx=2)
        self.login_btn = ctk.CTkButton(lf, text="LOGIN", height=24, width=50,
                                       fg_color=self.accent2, hover_color=self.accent,
                                       text_color="white", font=ctk.CTkFont(size=9, weight="bold"),
                                       command=self.start_login)
        self.login_btn.pack(side="left", padx=2)
        self.code_entry = ctk.CTkEntry(lf, placeholder_text="Code", width=80, height=24)
        self.verify_btn = ctk.CTkButton(lf, text="VERIFY", height=24, width=50,
                                        fg_color=self.accent2, hover_color=self.accent,
                                        text_color="white", font=ctk.CTkFont(size=9, weight="bold"),
                                        command=self.verify_code)
        ctk.CTkButton(lf, text="⟳", width=24, height=24,
                      fg_color="#333", hover_color="#555",
                      font=ctk.CTkFont(size=10), command=self.refresh_sessions).pack(side="left", padx=4)
        self._login_client = None

        self.tree = ttk.Treeview(self.sess_tab, columns=("File", "Phone", "Status"),
                                 show="headings", height=6)
        self.tree.heading("File", text="Session")
        self.tree.heading("Phone", text="Phone")
        self.tree.heading("Status", text="")
        self.tree.column("Status", width=30, anchor="center")
        self.tree.pack(fill="both", expand=True, padx=8, pady=4)

    def refresh_sessions(self):
        for i in self.tree.get_children():
            self.tree.delete(i)
        for f in sorted(os.listdir(SESSION_DIR)):
            if f.endswith(".session"):
                p = f.replace(".session", "")
                d = ("+" + p) if not p.startswith("+") else p
                v = "✓" if self.is_session_valid(f) else "✗"
                self.tree.insert("", "end", values=(f, d, v))

    def is_session_valid(self, session_file):
        try:
            c = TelegramClient(os.path.join(SESSION_DIR, session_file), API_ID, API_HASH)
            c.connect()
            v = c.is_user_authorized()
            c.disconnect()
            return v
        except: return False

    def start_login(self):
        phone = self.phone_entry.get().strip()
        if not phone or not phone.startswith("+"):
            messagebox.showerror("Error", "Phone must start with +")
            return
        # Ẩn code/verify cũ nếu có
        self.code_entry.pack_forget()
        self.verify_btn.pack_forget()
        self.code_entry.delete(0, "end")
        self.login_btn.configure(state="disabled", text="...")
        threading.Thread(target=lambda: asyncio.run(self._send_code(phone)), daemon=True).start()

    async def _send_code(self, phone):
        try:
            sess = phone.replace("+", "").replace(" ", "").replace("-", "")
            self._login_client = TelegramClient(os.path.join(SESSION_DIR, sess), API_ID, API_HASH)
            await self._login_client.connect()
            await self._login_client.send_code_request(phone)
            log_to_gui(f"Code sent to {phone}", "cyan")
            self.after(0, lambda: self.code_entry.pack(side="left", padx=2))
            self.after(0, lambda: self.verify_btn.pack(side="left", padx=2))
            self.after(0, lambda: self.login_btn.configure(text="SENT"))
        except Exception as e:
            log_to_gui(f"Login err: {e}", "red")
            self.after(0, lambda: self.login_btn.configure(state="normal", text="LOGIN"))

    def verify_code(self):
        code = self.code_entry.get().strip()
        phone = self.phone_entry.get().strip()
        if not code:
            messagebox.showerror("Error", "Enter code")
            return
        self.verify_btn.configure(state="disabled", text="...")
        threading.Thread(target=lambda: asyncio.run(self._verify(code, phone)), daemon=True).start()

    async def _verify(self, code, phone):
        try:
            await self._login_client.sign_in(phone=phone, code=code)
            me = await self._login_client.get_me()
            await self._login_client.disconnect()
            self._login_client = None
            s = phone.replace("+", "").replace(" ", "").replace("-", "")
            log_to_gui(f"Login OK: {me.first_name} | {s}.session", "green")
            self.after(0, self.refresh_sessions)
            self.after(0, lambda: messagebox.showinfo("OK", f"{me.first_name} logged in"))
        except Exception as e:
            msg = str(e)
            if "password" in msg.lower() or "2fa" in msg.lower():
                pwd = simpledialog.askstring("2FA", "Enter 2FA password:", parent=self)
                if pwd:
                    await self._login_client.sign_in(password=pwd)
                    me = await self._login_client.get_me()
                    await self._login_client.disconnect()
                    self._login_client = None
                    log_to_gui(f"Login OK: {me.first_name}", "green")
                    self.after(0, self.refresh_sessions)
            else:
                log_to_gui(f"Verify err: {msg}", "red")
        finally:
            self.after(0, lambda: self.verify_btn.configure(state="normal", text="VERIFY"))
            self.after(0, lambda: self.login_btn.configure(state="normal", text="LOGIN"))

    # ── Tools ──
    def build_tools(self):
        sc = ctk.CTkScrollableFrame(self.tools_tab, fg_color=self.bg_med)
        sc.pack(fill="both", expand=True, padx=8, pady=8)

        bf = ctk.CTkFrame(sc, fg_color="transparent")
        bf.pack(pady=(2, 6))

        ctk.CTkButton(bf, text="▶ RUN", width=70, height=26,
                      fg_color=self.accent2, hover_color=self.accent,
                      text_color="white", font=ctk.CTkFont(size=9, weight="bold"),
                      command=self.run_selected).pack(side="left", padx=3)

        ctk.CTkButton(bf, text="▶ ALL", width=70, height=26,
                      fg_color=self.accent2, hover_color=self.accent,
                      text_color="white", font=ctk.CTkFont(size=9, weight="bold"),
                      command=self.run_all_tools).pack(side="left", padx=3)

        ctk.CTkButton(bf, text="■ KILL", width=70, height=26,
                      fg_color="#4a152a", hover_color="#6a1a3a",
                      text_color="white", font=ctk.CTkFont(size=9, weight="bold"),
                      command=self.kill_all).pack(side="left", padx=3)

        self.tool_vars = {}
        self.tool_threads = {} # Lưu thread của từng tool đang chạy
        for name in TOOLS_RAW:
            var = ctk.BooleanVar(value=False)
            self.tool_vars[name] = var
            hf = ctk.CTkFrame(sc, fg_color="transparent")
            hf.pack(anchor="w", padx=8, pady=2, fill="x")
            cb = ctk.CTkCheckBox(hf, text=name, variable=var,
                                 font=ctk.CTkFont(size=10),
                                 fg_color=self.accent2, hover_color=self.accent,
                                 border_color="#555", checkmark_color="white",
                                 text_color="#ccc")
            cb.pack(side="left")
            # Thêm nút Kill riêng cho từng tool
            kb = ctk.CTkButton(hf, text="■", width=18, height=18,
                              fg_color="#4a152a", hover_color="#6a1a3a",
                              font=ctk.CTkFont(size=7),
                              command=lambda n=name: self.kill_tool(n))
            kb.pack(side="right", padx=4)
            self.tool_vars[name] = var

    def kill_all(self):
        log_to_gui("■ Kill all...", "red")
        os.execl(sys.executable, sys.executable, *sys.argv)

    def kill_tool(self, name):
        if name in self.tool_threads:
            thread = self.tool_threads[name]
            # We can't actually kill a thread, but we can set a flag
            # For now, we'll just remove it from tracking and let it finish its current cycle
            log_to_gui(f"⏹ Stopping {name}... (will finish current cycle)", "yellow")
            self.tool_threads.pop(name, None)
            # Optional: you could add a flag in the bot code to check for early termination
        else:
            log_to_gui(f"[{name}] Không đang chạy.", "white")

    def run_selected(self):
        sel = [n for n, v in self.tool_vars.items() if v.get()]
        if not sel:
            messagebox.showwarning("", "No tools selected")
            return
        for name in sel:
            self.run_tool(name)

    def run_all_tools(self):
        for name in TOOLS_RAW:
            self.run_tool(name)

    def run_tool(self, name):
        url = TOOLS_RAW.get(name)
        if not url: return
        sf = [f for f in os.listdir(SESSION_DIR) if f.endswith('.session')]
        if not sf:
            messagebox.showwarning("", "No sessions")
            return
        # Log khởi chạy
        self.exec_tool(name, url, sf)

    def exec_tool(self, name, url, sf):
        def tool_runner():
            try:
                # Ưu tiên tìm file local trước
                local_file = f"{name}.py"
                if os.path.exists(local_file):
                    with open(local_file, "r", encoding="utf-8") as f:
                        code = f.read()
                    log_to_gui(f"◈ Dùng file local: {local_file}", "cyan")
                else:
                    # Nếu không có file local thì tải từ GitHub
                    r = requests.get(f"{url}?t={int(time.time())}", timeout=15)
                    if r.status_code != 200: 
                        log_to_gui(f"✗ Lỗi tải tool {name}", "red")
                        return
                    code = r.text

                # Thiết lập môi trường để script chạy như một file độc lập
                lg = dict(globals())
                lg.update({
                    "__name__": "__main__", # Ép script chạy khối if __name__ == "__main__"
                    "log_to_gui": log_to_gui, 
                    "SESSION_DIR": SESSION_DIR, 
                    "session_files": sf
                })
                
                # Thực thi toàn bộ script
                exec(code, lg)
                
                log_to_gui(f"✓ {name} đã hoàn thành.", "green")
            except Exception as e:
                log_to_gui(f"✗ {name} lỗi: {e}", "red")

        thread = threading.Thread(target=tool_runner, daemon=True)
        self.tool_threads[name] = thread
        thread.start()
        log_to_gui(f"▶ {name} đang khởi chạy...", "cyan")

    def process_log_queue(self):
        while True:
            try:
                msg, color = log_queue.get(timeout=0.1)
                self.after(0, self.append_log, msg, color)
            except:
                time.sleep(0.05)

    def append_log(self, msg, color):
        if int(self.log_text.index("end-1c").split('.')[0]) > 50:
            self.log_text.delete("1.0", "2.0")
        tag = "green" if color == "green" else "red" if color == "red" else "normal"
        self.log_text.insert("end", msg + "\n", tag)
        self.log_text.see("end")

if __name__ == "__main__":
    App().mainloop()

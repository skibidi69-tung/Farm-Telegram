# tools/Pay_Plus_Bot.py
"""
PayPlus Bot - Multi Account + Bảo vệ lỗi
- Mỗi session chạy multi-thread claim
- Nếu lỗi quá 50 lần liên tục → tự dừng tool
"""

import os
import asyncio
import requests
import time
import threading
import urllib.parse
from datetime import datetime
from telethon import TelegramClient
from telethon.tl.functions.messages import RequestWebViewRequest

BASE_URL = "https://kaliboy002.duckdns.org"
THREADS_PER_ACCOUNT = 5      # Số luồng claim mỗi tài khoản
INTERVAL = 5.0               # Giây giữa mỗi đợt claim

log_to_gui = None

def log(message: str, color: str = "white"):
    ts = datetime.now().strftime("%H:%M:%S")
    if log_to_gui:
        log_to_gui(f"[{ts}] {message}", color)
    else:
        colors = {"green": "\033[92m", "red": "\033[91m", "yellow": "\033[93m", "cyan": "\033[96m", "white": "\033[0m"}
        print(f"{colors.get(color, '')}[{ts}] {message}\033[0m")


class PayPlusBot:
    def __init__(self, session_file: str):
        self.session_file = session_file
        self.name = session_file.replace('.session', '')
        self.init_data = None
        self.session = requests.Session()
        self.lock = threading.Lock()
        self.error_count = 0          # Đếm lỗi liên tục
        self.max_errors = 50          # Dừng nếu lỗi quá 50 lần
        self.is_running = True

    async def get_init_data(self):
        client = TelegramClient(os.path.join("sessions", self.session_file), 
                              28752231, 'ec1c1f2c30e2f1855c3edee7e348480b')
        await client.connect()

        try:
            if not await client.is_user_authorized():
                log(f"[{self.name}] Session không hợp lệ hoặc đã logout", "red")
                return False

            bot_entity = await client.get_input_entity('Pay_Plus_Bot')

            res = await client(RequestWebViewRequest(
                peer=bot_entity,
                bot=bot_entity,
                platform='android',
                from_bot_menu=False,
                url="https://payplus.click/"
            ))

            self.init_data = urllib.parse.unquote(
                res.url.split('tgWebAppData=')[1].split('&tgWebAppVersion')[0]
            )

            log(f"[{self.name}] Đăng nhập thành công", "green")
            return True

        except Exception as e:
            log(f"[{self.name}] Lỗi lấy initData: {e}", "red")
            return False
        finally:
            await client.disconnect()

    def claim(self, thread_id: int, round_num: int):
        if not self.init_data or not self.is_running:
            return

        try:
            payload = {"initData": self.init_data, "adType": "gigapub"}

            r = self.session.post(
                f"{BASE_URL}/api/reward",
                headers={"Content-Type": "application/json"},
                json=payload,
                timeout=10
            )

            if r.status_code == 200:
                res = r.json()
                if "balance" in res:
                    added = res.get("added", 0.20)
                    log(f"[{self.name}][R{round_num}][T{thread_id}] +${added:.2f} | Balance: ${res.get('balance', 0):.2f}", "green")
                    with self.lock:
                        self.error_count = 0   # Reset lỗi khi thành công
                else:
                    self.handle_error(round_num, thread_id, "No balance in response")
            else:
                self.handle_error(round_num, thread_id, f"HTTP {r.status_code}")

        except Exception as e:
            self.handle_error(round_num, thread_id, str(e))

    def handle_error(self, round_num, thread_id, error_msg):
        with self.lock:
            self.error_count += 1
        log(f"[{self.name}][R{round_num}][T{thread_id}] Lỗi: {error_msg} (Lỗi liên tục: {self.error_count}/{self.max_errors})", "red")

        if self.error_count >= self.max_errors:
            log(f"[{self.name}] DỪNG TOOL do lỗi quá {self.max_errors} lần liên tục!", "red")
            self.is_running = False

    async def run(self):
        if not await self.get_init_data():
            return

        log(f"[{self.name}] Bắt đầu farming | {THREADS_PER_ACCOUNT} luồng | Interval {INTERVAL}s", "cyan")

        round_num = 0
        while self.is_running:
            round_num += 1
            log(f"[{self.name}] ─── Đợt {round_num} ───────────────────────────", "magenta")

            threads = []
            for t_id in range(1, THREADS_PER_ACCOUNT + 1):
                t = threading.Thread(target=self.claim, args=(t_id, round_num), daemon=True)
                threads.append(t)
                t.start()

            for t in threads:
                t.join()

            await asyncio.sleep(INTERVAL)

        log(f"[{self.name}] Đã dừng farming", "yellow")


# ====================== ENTRY POINT ======================
async def run(session_files=None):
    """Hàm chính - Hỗ trợ multi account"""
    if session_files is None or isinstance(session_files, str):
        session_files = [f for f in os.listdir(SESSION_DIR) if f.endswith('.session')]

    if not session_files:
        log("Không tìm thấy session nào!", "red")
        return

    log(f"Bắt đầu chạy {len(session_files)} tài khoản PayPlus...", "cyan")

    tasks = [PayPlusBot(sess).run() for sess in session_files]
    await asyncio.gather(*tasks, return_exceptions=True)

    log("Hoàn thành tất cả tài khoản PayPlus!", "green")


if __name__ == "__main__":
    asyncio.run(run())

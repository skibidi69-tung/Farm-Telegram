# tools/payplus.py
"""
PayPlus Auto Reward Tool - MULTI ACCOUNT
- Hỗ trợ chạy nhiều session cùng lúc
- Multi-thread claim reward cho từng session
- Tích hợp với main_gui.py + Nuitka
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

# ====================== CONFIG ======================
BASE_URL = "https://kaliboy002.duckdns.org"
THREADS_PER_ACCOUNT = 5      # Số luồng claim mỗi tài khoản
INTERVAL = 5.0               # Giây giữa mỗi đợt claim

# Nhận log từ main_gui.py
log_to_gui = None

def log(message: str, color: str = "white"):
    ts = datetime.now().strftime("%H:%M:%S")
    prefix = f"[{ts}]"
    if log_to_gui:
        log_to_gui(f"{prefix} {message}", color)
    else:
        colors = {
            "green": "\033[92m", "red": "\033[91m", "yellow": "\033[93m",
            "cyan": "\033[96m", "magenta": "\033[95m", "white": "\033[0m"
        }
        print(f"{colors.get(color, '')}{prefix} {message}\033[0m")


class PayPlusBot:
    def __init__(self, session_file: str):
        self.session_file = session_file
        self.name = session_file.replace('.session', '')
        self.init_data = None
        self.session = requests.Session()
        self.lock = threading.Lock()
        self.stats = {"success": 0, "fail": 0, "earned": 0.0}
        self.is_running = True

    async def get_init_data(self):
        client = TelegramClient(os.path.join("sessions", self.session_file), 
                              28752231, 'ec1c1f2c30e2f1855c3edee7e348480b')
        await client.connect()

        try:
            if not await client.is_user_authorized():
                log(f"[{self.name}] Session không hợp lệ hoặc đã logout", "red")
                return False

            me = await client.get_me()
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

            log(f"[{self.name}] Đăng nhập thành công → {me.first_name or self.name}", "green")
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
            payload = {
                "initData": self.init_data,
                "adType": "gigapub"
            }

            r = requests.post(
                f"{BASE_URL}/api/reward",
                headers={"Content-Type": "application/json"},
                json=payload,
                timeout=10
            )
            res = r.json()

            if r.status_code == 200 and "balance" in res:
                added = res.get("added", 0.20)
                with self.lock:
                    self.stats["success"] += 1
                    self.stats["earned"] += added

                log(f"[{self.name}][R{round_num}][T{thread_id}] ✅ +${added:.2f} | "
                    f"Balance: ${res.get('balance', 0):.2f}", "green")

            elif r.status_code == 429:
                with self.lock:
                    self.stats["fail"] += 1
                log(f"[{self.name}][R{round_num}][T{thread_id}] ⏳ Rate limit", "yellow")
            else:
                with self.lock:
                    self.stats["fail"] += 1
                log(f"[{self.name}][R{round_num}][T{thread_id}] ❌ {r.status_code}: {res.get('error','unknown')}", "red")

        except Exception as e:
            with self.lock:
                self.stats["fail"] += 1
            log(f"[{self.name}][R{round_num}][T{thread_id}] ⛔ {e}", "red")

    async def run(self):
        if not await self.get_init_data():
            log(f"[{self.name}] Không thể khởi động", "red")
            return

        log(f"[{self.name}] Bắt đầu farming | {THREADS_PER_ACCOUNT} luồng | Interval {INTERVAL}s", "cyan")

        round_num = 0
        try:
            while self.is_running:
                round_num += 1
                log(f"[{self.name}] ─── Đợt {round_num} ───────────────────────────", "magenta")

                threads = []
                for t_id in range(1, THREADS_PER_ACCOUNT + 1):
                    t = threading.Thread(
                        target=self.claim,
                        args=(t_id, round_num),
                        daemon=True
                    )
                    threads.append(t)

                for t in threads:
                    t.start()

                for t in threads:
                    t.join()

                log(f"[{self.name}] Stats → ✅ {self.stats['success']} success | "
                    f"❌ {self.stats['fail']} fail | 💰 Earned: ${self.stats['earned']:.2f}", "cyan")

                await asyncio.sleep(INTERVAL)

        except asyncio.CancelledError:
            log(f"[{self.name}] Đã dừng farming", "yellow")
        except Exception as e:
            log(f"[{self.name}] Lỗi bất ngờ: {e}", "red")


# ====================== ENTRY POINT - Hỗ trợ Multi ======================
async def run(session_files: list):
    """Hàm chính hỗ trợ chạy nhiều session"""
    if isinstance(session_files, str):
        session_files = [session_files]  # Nếu chỉ truyền 1 session

    tasks = []
    for sess_file in session_files:
        bot = PayPlusBot(sess_file)
        tasks.append(bot.run())

    await asyncio.gather(*tasks, return_exceptions=True)


# Test riêng (chạy file này trực tiếp)
if __name__ == "__main__":
    import os
    sessions = [f for f in os.listdir("sessions") if f.endswith('.session')]
    if sessions:
        asyncio.run(run(sessions))   # Chạy tất cả session có trong thư mục
    else:
        log("Không tìm thấy session nào trong thư mục sessions/", "red")

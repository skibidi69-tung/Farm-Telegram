# tools/shibexa.py
"""
Shibexa Bot - Multi Account Version
- Chạy tất cả session trong thư mục sessions/
- Log đơn giản, sạch sẽ
- Không dùng banner neon
"""

import os
import asyncio
import requests
import time
import urllib.parse
from datetime import datetime
from telethon import TelegramClient
from telethon.tl.functions.messages import RequestWebViewRequest

WEBAPP_URL = "https://auth-gateway-helper.org/shibexa/scratch/register.html"
BASE_URL = "https://auth-gateway-helper.org/shibexa/scratch/api/"
SESSION_DIR = "sessions"   # ← Đã thêm dòng này để sửa lỗi

# Nhận log từ main_gui.py
log_to_gui = None

def log(message: str, color: str = "white"):
    ts = datetime.now().strftime("%H:%M:%S")
    if log_to_gui:
        log_to_gui(f"[{ts}] {message}", color)
    else:
        colors = {
            "green": "\033[92m",
            "red": "\033[91m",
            "yellow": "\033[93m",
            "cyan": "\033[96m",
            "white": "\033[0m"
        }
        print(f"{colors.get(color, '')}[{ts}] {message}\033[0m")


class ShibexaBot:
    def __init__(self, session_file: str):
        self.session_file = session_file
        self.name = session_file.replace('.session', '')
        self.session = requests.Session()
        self.user_id = None
        self.currency = "SHIB"

    async def get_init_data(self):
        client = TelegramClient(os.path.join(SESSION_DIR, self.session_file), 28752231, 'ec1c1f2c30e2f1855c3edee7e348480b')
        await client.connect()
        try:
            if not await client.is_user_authorized():
                log(f"[{self.name}] Session không hợp lệ hoặc đã logout", "red")
                return None

            me = await client.get_me()
            bot_entity = await client.get_input_entity('ShibexaBot')

            res = await client(RequestWebViewRequest(
                peer=bot_entity,
                bot=bot_entity,
                platform='android',
                from_bot_menu=False,
                url=WEBAPP_URL
            ))

            auth_data = urllib.parse.unquote(res.url.split('tgWebAppData=')[1].split('&tgWebAppVersion')[0])

            self.user_id = me.id
            log(f"[{self.name}] Đăng nhập thành công → {me.first_name}", "green")
            return auth_data
        finally:
            await client.disconnect()

    async def run(self):
        init_data = await self.get_init_data()
        if not init_data:
            return

        session = requests.Session()
        session.headers.update({
            'User-Agent': "Mozilla/5.0 (Linux; Android 12; K) Telegram-Android/12.1.1",
            'Content-Type': "application/json",
            'X-Requested-With': "org.telegram.messenger",
            'Origin': "https://auth-gateway-helper.org",
            'Referer': "https://auth-gateway-helper.org/shibexa/scratch/register.html"
        })

        # Đăng ký / Đồng bộ
        try:
            reg_payload = {
                "user_id": self.user_id,
                "name": self.name,
                "username": "",
                "ip": "webapp",
                "init_data": init_data,
                "ref": 0
            }
            session.post(BASE_URL + "register.php", json=reg_payload)

            dash_res = session.post(BASE_URL + "dashboard.json", json={
                "user_id": self.user_id,
                "init_data": init_data
            }).json()

            self.currency = dash_res.get('currency', 'SHIB')
            log(f"[{self.name}] Đồng bộ thành công. Currency: {self.currency}", "cyan")
        except Exception as e:
            log(f"[{self.name}] Lỗi xác thực: {e}", "red")
            return

        log(f"[{self.name}] Bắt đầu farm Shibexa...", "cyan")

        while True:
            try:
                det_res = session.post(BASE_URL + "watch-ad.json", json={
                    "user_id": self.user_id,
                    "action": "details"
                }).json()

                ads_left = det_res.get('ads_left_this_hour', 0)
                cooldown = det_res.get('cooldown_seconds_left', 0)

                if ads_left <= 0:
                    log(f"[{self.name}] Đã đạt giới hạn quảng cáo giờ này. Dừng.", "yellow")
                    break

                if cooldown > 0:
                    log(f"[{self.name}] Đang chờ cooldown {cooldown}s...", "yellow")
                    await asyncio.sleep(cooldown)

                # Xem quảng cáo
                log(f"[{self.name}] Đang xem quảng cáo Monetag...", "magenta")
                for i in range(12, 0, -1):
                    print(f"\r[{datetime.now().strftime('%H:%M:%S')}] [{self.name}] Đang xem Monetag... {i}s ", end="", flush=True)
                    await asyncio.sleep(1)
                print("\r" + " " * 60, end="\r")

                # Claim
                claim_payload = {
                    "user_id": self.user_id,
                    "ad_provider": "monetag",
                    "ad_blocked": False,
                    "shown": False
                }
                res = session.post(BASE_URL + "watch-ad.json", json=claim_payload).json()

                if res.get('status') == "success":
                    log(f"[{self.name}] ✅ +{res['earned']} {self.currency} | Số dư: {res['new_balance']}", "green")
                    cooldown_left = res.get('cooldown_seconds_left', 15)
                    await asyncio.sleep(cooldown_left)
                else:
                    log(f"[{self.name}] Claim thất bại", "red")
                    await asyncio.sleep(10)

            except Exception as e:
                log(f"[{self.name}] Lỗi kết nối server: {e}", "red")
                await asyncio.sleep(10)


# ====================== ENTRY POINT - MULTI ACCOUNT ======================
async def run(session_files=None):
    """Chạy tất cả session"""
    if session_files is None:
        session_files = [f for f in os.listdir(SESSION_DIR) if f.endswith('.session')]

    if not session_files:
        log("Không tìm thấy session nào trong thư mục sessions!", "red")
        return

    log(f"Bắt đầu chạy {len(session_files)} tài khoản Shibexa...", "cyan")

    tasks = [ShibexaBot(sess_file).run() for sess_file in session_files]
    await asyncio.gather(*tasks, return_exceptions=True)

    log("Hoàn thành tất cả tài khoản Shibexa!", "green")


if __name__ == "__main__":
    asyncio.run(run())

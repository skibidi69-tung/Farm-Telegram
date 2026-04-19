# tools/adston.py
"""
Adston (Pocket Income) - Multi Account Version
- Tự động chạy tất cả session
- Log đơn giản, sạch sẽ
"""

import os
import json
import asyncio
import requests
import re
import urllib.parse
from datetime import datetime
from telethon import TelegramClient
from telethon.tl.functions.messages import RequestWebViewRequest

# ====================== CONFIG ======================
BASE_URL = "https://pocketincome.codeissuehub.com"
BOT_USERNAME = 'ADS_TON_bot'
SESSION_DIR = "sessions"   # ← Đã thêm dòng này để sửa lỗi

# Nhận log từ main_gui.py (nếu có)
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


class AdstonBot:
    def __init__(self, session_file: str):
        self.session_file = session_file
        self.name = session_file.replace('.session', '')
        self.session = requests.Session()
        self.csrf = None
        self.balance = "0"
        self.today_ads = 0
        self.ads_limit = 0

        self.headers = {
            'User-Agent': "Mozilla/5.0 (Linux; Android 12; K) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/146.0.0.0 Mobile Safari/537.36 Telegram-Android/12.1.1",
            'Accept': "application/json, text/plain, */*",
            'X-Requested-With': "org.telegram.messenger",
            'Origin': BASE_URL,
            'Referer': f"{BASE_URL}/",
        }

    async def get_init_data(self):
        client = TelegramClient(os.path.join(SESSION_DIR, self.session_file), 28752231, 'ec1c1f2c30e2f1855c3edee7e348480b')
        await client.connect()
        try:
            if not await client.is_user_authorized():
                log(f"[{self.name}] Session không hợp lệ hoặc đã logout", "red")
                return None

            bot_entity = await client.get_input_entity(BOT_USERNAME)
            res = await client(RequestWebViewRequest(
                peer=bot_entity,
                bot=bot_entity,
                platform='android',
                from_bot_menu=False,
                url=f"{BASE_URL}/"
            ))

            tg_data = urllib.parse.unquote(res.url.split('tgWebAppData=')[1].split('&tgWebAppVersion')[0])
            user_json = json.loads(urllib.parse.parse_qs(tg_data)['user'][0])

            log(f"[{self.name}] Đăng nhập thành công", "green")
            return tg_data, user_json
        finally:
            await client.disconnect()

    async def fetch_csrf(self):
        try:
            resp = self.session.get(BASE_URL, headers=self.headers, timeout=15)
            token = None
            meta = re.search(r'name="csrf-token" content="(.*?)"', resp.text)
            if meta:
                token = meta.group(1)
            elif self.session.cookies.get("XSRF-TOKEN"):
                token = urllib.parse.unquote(self.session.cookies.get("XSRF-TOKEN"))

            if token:
                self.csrf = token
                return True
            return False
        except:
            return False

    async def run(self):
        init_data = await self.get_init_data()
        if not init_data:
            return

        _, user_info = init_data

        # Đồng bộ tài khoản
        try:
            payload = {
                "first_name": user_info.get('first_name', ''),
                "last_name": user_info.get('last_name', ''),
                "username": user_info.get('username', ''),
                "id": int(user_info['id']),
                "referral_code": None
            }
            headers = self.headers.copy()
            if self.csrf:
                headers['x-csrf-token'] = self.csrf

            resp = self.session.post(f"{BASE_URL}/user/check-or-create", json=payload, headers=headers)
            data = resp.json()

            if data.get("success"):
                user = data.get("user", {})
                self.balance = str(user.get("balance", "0"))
                self.today_ads = int(user.get("today_ads", 0))
                self.ads_limit = int(user.get("ads_limit", 2))
                log(f"[{self.name}] Balance: {self.balance} | Ads: {self.today_ads}/{self.ads_limit}", "cyan")
        except Exception as e:
            log(f"[{self.name}] Lỗi đồng bộ: {e}", "red")
            return

        # Farming loop
        while True:
            if not self.csrf and not await self.fetch_csrf():
                await asyncio.sleep(5)
                continue

            if self.today_ads >= self.ads_limit and self.ads_limit > 0:
                log(f"[{self.name}] Đã đạt giới hạn ads hôm nay → Hoàn thành!", "green")
                break

            log(f"[{self.name}] Đang xem quảng cáo {self.today_ads + 1}/{self.ads_limit}...", "magenta")

            for i in range(35, 0, -1):
                print(f"\r[{datetime.now().strftime('%H:%M:%S')}] [{self.name}] Đang xem ads... {i}s ", end="", flush=True)
                await asyncio.sleep(1)
            print("\r" + " " * 70, end="\r")

            try:
                payload = {
                    "telegram_id": int(user_info['id']),
                    "points": 50000,
                    "type": "3_ads_set"
                }
                headers = self.headers.copy()
                if self.csrf:
                    headers['x-csrf-token'] = self.csrf

                resp = self.session.post(f"{BASE_URL}/user/reward", json=payload, headers=headers)
                result = resp.json()

                if result.get("success"):
                    self.balance = str(result.get("new_balance", self.balance))
                    self.today_ads += 1
                    log(f"[{self.name}] Thành công +50k Points | Balance: {self.balance}", "green")
                else:
                    log(f"[{self.name}] Claim thất bại hoặc hết lượt", "yellow")
                    break
            except Exception as e:
                log(f"[{self.name}] Lỗi claim: {e}", "red")

            await asyncio.sleep(5)


# ====================== ENTRY POINT - MULTI ACCOUNT ======================
async def run(session_files=None):
    """Chạy tất cả session"""
    if session_files is None:
        session_files = [f for f in os.listdir(SESSION_DIR) if f.endswith('.session')]

    if not session_files:
        log("Không tìm thấy session nào trong thư mục sessions!", "red")
        return

    log(f"Bắt đầu chạy {len(session_files)} tài khoản Adston...", "cyan")

    tasks = [AdstonBot(sess_file).run() for sess_file in session_files]
    await asyncio.gather(*tasks, return_exceptions=True)

    log("Hoàn thành tất cả tài khoản Adston!", "green")


if __name__ == "__main__":
    asyncio.run(run())

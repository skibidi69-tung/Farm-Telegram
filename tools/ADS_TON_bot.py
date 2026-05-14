import time
import os
import sys
import json
import random
import asyncio
import urllib.parse
from datetime import datetime
from telethon import TelegramClient, functions
from curl_cffi import requests

# --- ANSI COLORS (Giữ nguyên từ source) ---
C = "\033[96m"; Y = "\033[93m"; W = "\033[97m"
M = "\033[95m"; R = "\033[91m"; G = "\033[92m"
X = "\033[0m"; BOLD = "\033[1m"

# --- CONFIG (API ID & HASH CỦA BẠN) ---
API_ID = 28752231
API_HASH = 'ec1c1f2c30e2f1855c3edee7e348480b'
BOT_USER = "AdsTonBot"
URL_WEBVIEW = "https://adston.org/"
SESSION_DIR = "sessions"

if not os.path.exists(SESSION_DIR): os.makedirs(SESSION_DIR)

class AdsTonPro:
    def __init__(self, token, name):
        self.session = requests.Session()
        self.token = token
        self.name = name
        self.headers = {
            'Authorization': f'Bearer {self.token}',
            'Accept': 'application/json, text/plain, */*',
            'Origin': 'https://adston.org',
            'Referer': 'https://adston.org/',
            'User-Agent': 'Mozilla/5.0 (Linux; Android 12; SM-G991B) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/121.0.0.0 Mobile Safari/537.36 Telegram-Android/10.8.2',
            'X-Requested-With': 'org.telegram.messenger'
        }

    def log(self, msg, color=W):
        ts = datetime.now().strftime('%H:%M:%S')
        print(f"[{ts}] {C}@{self.name}{X} | {color}{msg}{X}")

    def run_ads(self):
        url = "https://api.adston.org/api/ads/view"
        for i in range(15): 
            try:
                res = self.session.post(url, headers=self.headers, impersonate="chrome124")
                data = res.json()
                if res.status_code == 200 and data.get('success'):
                    self.log(f"Lượt {i+1:02} | {G}Thành công{X} | Balance: {Y}{data.get('balance')}{X}", G)
                else:
                    self.log(f"Lượt {i+1:02} | {Y}{data.get('message', 'Hết lượt')}{X}")
                    break
            except: break
            time.sleep(random.uniform(2.0, 3.5))

async def get_auth_data(sess_file):
    client = TelegramClient(os.path.join(SESSION_DIR, sess_file), API_ID, API_HASH)
    await client.connect()
    if not await client.is_user_authorized():
        await client.disconnect(); return None, None
    try:
        bot = await client.get_input_entity(BOT_USER)
        res = await client(functions.messages.RequestWebViewRequest(
            peer=bot, bot=bot, platform='android', from_bot_menu=False, url=URL_WEBVIEW
        ))
        query_id = urllib.parse.unquote(res.url.split('tgWebAppData=')[1].split('&tgWebAppVersion')[0])
        me = await client.get_me()
        await client.disconnect()
        return query_id, me.first_name
    except:
        await client.disconnect(); return None, None

async def main():
    os.system('cls' if os.name == 'nt' else 'clear')
    
    # BẮT ĐẦU VÒNG LẶP VÔ TẬN Ở ĐÂY
    while True:
        sessions = [f for f in os.listdir(SESSION_DIR) if f.endswith('.session')]
        
        if not sessions:
            print(f"{R}[!] Không có session nào...{X}")
            await asyncio.sleep(10)
            continue

        for s_file in sessions:
            token, first_name = await get_auth_data(s_file)
            if token:
                bot = AdsTonPro(token, first_name)
                bot.run_ads()
            await asyncio.sleep(2)

        # Nghỉ sau khi chạy hết tất cả tài khoản
        wait_time = 1800 # Nghỉ 30 phút
        print(f"\n{G}>>> Hoàn thành chu kỳ. Chờ 30p để chạy lại...{X}")
        for i in range(wait_time, 0, -1):
            sys.stdout.write(f"\r{Y}[!] Tiếp tục sau: {i}s...{X}")
            sys.stdout.flush()
            await asyncio.sleep(1)
        print("\n")

if __name__ == "__main__":
    try:
        asyncio.run(main())
    except KeyboardInterrupt:
        sys.exit()

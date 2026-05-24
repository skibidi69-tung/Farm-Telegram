import os
import json
import asyncio
import requests
import urllib.parse
import time
import random
from datetime import datetime
from telethon import TelegramClient
from telethon.tl.functions.messages import RequestWebViewRequest
from concurrent.futures import ThreadPoolExecutor, as_completed

BASE_URL = "https://trewards.duckdns.org"
BOT_USERNAME = 'treward_ton_bot'
WEBAPP_URL = "https://trewards.duckdns.org/"
SESSION_DIR = "sessions"   

# Giảm cooldown xuống tối thiểu để spam nhanh nhất có thể (tùy chỉnh nếu bị rate limit)
COOLDOWN_BETWEEN_ADS = 2  

API_ID = 28752231
API_HASH = 'ec1c1f2c30e2f1855c3edee7e348480b'

if 'log_to_gui' not in globals():
    def log_to_gui(message: str, color: str = "white"):
        ts = datetime.now().strftime("%H:%M:%S")
        print(f"[{ts}] {message}")

class TRewardsSpammer:
    def __init__(self, session_file: str):
        self.session_file = session_file
        self.name = session_file.replace('.session', '')
        self.session = requests.Session()
        self.init_data = None
        self.ton_balance = 0
        self.coins = 0
        self.spins = 0
        self.headers = {
            'User-Agent': "Mozilla/5.0 (Linux; Android 12; K) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/146.0.0.0 Mobile Safari/537.36 Telegram-Android/12.1.1",
            'Accept': "application/json, text/plain, */*",
            'Content-Type': "application/json",
            'X-Requested-With': "org.telegram.messenger",
            'Origin': BASE_URL,
            'Referer': f"{BASE_URL}/",
        }

    async def _async_get_init_data(self):
        client = TelegramClient(os.path.join(SESSION_DIR, self.session_file), API_ID, API_HASH)
        await client.connect()
        try:
            if not await client.is_user_authorized(): return None
            bot_entity = await client.get_input_entity(BOT_USERNAME)
            res = await client(RequestWebViewRequest(peer=bot_entity, bot=bot_entity, platform='android', from_bot_menu=False, url=WEBAPP_URL))
            parsed = urllib.parse.urlparse(res.url)
            init_data = urllib.parse.parse_qs(parsed.query).get('tgWebAppData', [None])[0]
            if not init_data:
                init_data = urllib.parse.unquote(res.url.split('tgWebAppData=')[1].split('&')[0])
            return init_data
        except Exception: return None
        finally: await client.disconnect()

    def fetch_init_data(self):
        try:
            loop = asyncio.new_event_loop()
            asyncio.set_event_loop(loop)
            self.init_data = loop.run_until_complete(self._async_get_init_data())
            loop.close()
        except Exception: self.init_data = None

    def login(self):
        if not self.init_data: return False
        try:
            resp = self.session.post(f"{BASE_URL}/api/user", json={"init_data": self.init_data, "language": "en", "referrer_id": None}, headers=self.headers, timeout=15)
            if resp.status_code == 200:
                data = resp.json()
                self.coins, self.spins, self.ton_balance = data.get("coins", 0), data.get("spins", 0), data.get("ton_balance", 0)
                log_to_gui(f"[{self.name}] 🔐 Login OK! Ví: {self.coins} Xu | {self.ton_balance} TON", "green")
                return True
            return False
        except Exception: return False

    def force_spam_ad(self, endpoint: str, ad_id: str):
        """Hàm nện thẳng vào API, không cần check giới hạn"""
        try:
            resp = self.session.post(f"{BASE_URL}{endpoint}", json={"init_data": self.init_data, "ad_id": ad_id},

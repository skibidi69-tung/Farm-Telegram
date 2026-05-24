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

# ====================== CONFIG ======================
BASE_URL = "https://trewards.duckdns.org"
BOT_USERNAME = 'treward_ton_bot'
WEBAPP_URL = "https://trewards.duckdns.org/"
SESSION_DIR = "sessions"   

MAX_COIN_ROUNDS = 10         
MAX_TON_ROUNDS = 50          
COOLDOWN_ROUND = 61          

API_ID = 28752231
API_HASH = 'ec1c1f2c30e2f1855c3edee7e348480b'

# Sử dụng hàm log_to_gui truyền từ main_gui.py sang, nếu chạy độc lập thì print ra console
if 'log_to_gui' not in globals():
    def log_to_gui(message: str, color: str = "white"):
        ts = datetime.now().strftime("%H:%M:%S")
        colors = {"green": "\033[92m", "red": "\033[91m", "yellow": "\033[93m", "cyan": "\033[96m", "magenta": "\033[95m", "white": "\033[0m"}
        print(f"{colors.get(color, '')}[{ts}] {message}\033[0m")


class TRewardsBot:
    def __init__(self, session_file: str):
        self.session_file = session_file
        self.name = session_file.replace('.session', '')
        self.session = requests.Session()
        self.init_data = None
        
        self.coins = 0
        self.spins = 0
        self.streak = 0
        self.ton_balance = 0
        self.last_ad_time = 0

        self.headers = {
            'User-Agent': "Mozilla/5.0 (Linux; Android 12; K) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/146.0.0.0 Mobile Safari/537.36 Telegram-Android/12.1.1",
            'Accept': "application/json, text/plain, */*",
            'Content-Type': "application/json",
            'X-Requested-With': "org.telegram.messenger",
            'Origin': BASE_URL,
            'Referer': f"{BASE_URL}/",
        }

    async def _async_get_init_data(self):
        """Lấy init_data thuần túy từ Telethon có await"""
        client = TelegramClient(os.path.join(SESSION_DIR, self.session_file), API_ID, API_HASH)
        await client.connect()
        try:
            if not await client.is_user_authorized():
                return None
            bot_entity = await client.get_input_entity(BOT_USERNAME)
            res = await client(RequestWebViewRequest(
                peer=bot_entity, bot=bot_entity, platform='android', from_bot_menu=False, url=WEBAPP_URL
            ))
            parsed = urllib.parse.urlparse(res.url)
            init_data = urllib.parse.parse_qs(parsed.query).get('tgWebAppData', [None])[0]
            if not init_data:
                init_data = urllib.parse.unquote(res.url.split('tgWebAppData=')[1].split('&')[0])
            return init_data
        except Exception:
            return None
        finally:
            await client.disconnect()

    def fetch_init_data(self):
        """Bọc loop riêng cô lập hoàn toàn để GUI gọi không bị báo lỗi Coroutine"""
        try:
            loop = asyncio.new_event_loop()
            asyncio.set_event_loop(loop)
            self.init_data = loop.run_until_complete(self._async_get_init_data())
            loop.close()
        except Exception:
            self.init_data = None

    def login(self):
        if not self.init_data:
            return False
        url = f"{BASE_URL}/api/user"
        try:
            resp = self.session.post(url, json={"init_data": self.init_data, "language": "en", "referrer_id": None}, headers=self.headers, timeout=15)
            if resp.status_code == 200:
                data = resp.json()
                self.coins = data.get("coins", 0)
                self.spins = data.get("spins", 0)
                self.streak = data.get("streak", 0)
                self.ton_balance = data.get("ton_balance", 0)
                log_to_gui(f"[{self.name}] 🔐 Login OK! Ví: {self.coins} Xu | {self.ton_balance} TON | {self.spins} Spin", "green")
                return True
            return False
        except Exception:
            return False

    def claim_streak(self):
        try:
            resp = self.session.post(f"{BASE_URL}/api/claim-streak", json={"init_data": self.init_data}, headers=self.headers, timeout=15)
            if resp.status_code == 200 and resp.json().get("success"):
                data = resp.json()
                self.spins += data.get("spins_earned", 0)
                log_to_gui(f"[{self.name}] 📅 Điểm danh: +{data.get('coins_earned', 0)} Xu", "green")
        except Exception:
            pass

    def claim_daily_tasks(self):
        url = f"{BASE_URL}/api/claim-daily-task"
        for task in ["checkin", "update", "share"]:
            try:
                time.sleep(random.uniform(0.3, 0.7))
                resp = self.session.post(url, json={"init_data": self.init_data, "task_type": task}, headers=self.headers, timeout=15)
                if resp.status_code == 200 and resp.json().get("success"):
                    data = resp.json()
                    self.coins = data.get("new_balance", self.coins)
                    self.spins += data.get("spins_earned", 0)
                    log_to_gui(f"[{self.name}] ✅ Task '{task}': +{data.get('coins_earned', 0)} Xu", "green")
            except Exception:
                pass

    def claim_advertiser_tasks(self):
        url = f"{BASE_URL}/api/claim-advertiser-daily"
        for task_id in [124, 123, 122, 95, 94, 93]:
            try:
                time.sleep(random.uniform(0.3, 0.7))
                resp = self.session.post(url, json={"init_data": self.init_data, "task_id": int(task_id)}, headers=self.headers, timeout=15)
                if resp.status_code == 200 and resp.json().get("success"):
                    data = resp.json()
                    self.coins = data.get("new_balance", self.coins)
                    self.spins += data.get("spins_earned", 0)
                    log_to_gui(f"[{self.name}] 💰 Adv Task {task_id}: +{data.get('coins_earned', 0)} Xu", "green")
            except Exception:
                pass

    def watch_single_ad(self, endpoint: str, ad_id: str):
        try:
            resp = self.session.post(f"{BASE_URL}{endpoint}", json={"init_data": self.init_data, "ad_id": ad_id}, headers=self.headers, timeout=12)
            if resp.status_code == 200 and resp.json().get("success"):
                data = resp.json()
                if "ton" in endpoint:
                    self.ton_balance = data.get("new_balance", self.ton_balance)
                    log_to_gui(f"[{self.name}] 💎 Ad '{ad_id}': +{data.get('ton_earned', 0)} TON | Ví: {self.ton_balance} TON", "green")
                else:
                    self.coins = data.get("new_balance", self.coins)
                    log_to_gui(f"[{self.name}] 💰 Ad '{ad_id}': +{data.get('coins_earned', 0)} Xu", "green")
        except Exception:
            pass

    def execute_ads_round(self, round_num: int):
        time_passed = time.time() - self.last_ad_time
        if time_passed < COOLDOWN_ROUND:
            time.sleep(COOLDOWN_ROUND - time_passed)

        log_to_gui(f"[{self.name}] 📺 Ads Vòng {round_num}/{MAX_TON_ROUNDS}...", "magenta")
        
        if round_num <= MAX_COIN_ROUNDS:
            self.watch_single_ad("/api/watch-ad", "ad_b1")
            self.watch_single_ad("/api/watch-ad", "ad_b2")
        
        if round_num <= MAX_TON_ROUNDS:
            self.watch_single_ad("/api/watch-ad-ton", "ad_b3")
            self.watch_single_ad("/api/watch-ad-ton", "ad_b4")
        
        self.last_ad_time = time.time()

    def auto_spin(self):
        url = f"{BASE_URL}/api/spin"
        if self.spins <= 0:
            return
        log_to_gui(f"[{self.name}] 🎰 Đang quay {self.spins} lượt Spin...", "magenta")
        while self.spins > 0:
            try:
                time.sleep(1.2)
                resp = self.session.post(url, json={"init_data": self.init_data}, headers=self.headers, timeout=15)
                if resp.status_code == 200 and resp.json().get("success"):
                    data = resp.json()
                    self.coins = data.get("new_balance", self.coins)
                    self.spins = data.get("remaining_spins", 0)
                    log_to_gui(f"[{self.name}] 🎉 Spin: +{data.get('coins_earned', 0)} Xu | Còn {self.spins}", "green")
                else:
                    break
            except Exception:
                break

    def start_farm_flow(self):
        log_to_gui(f"[{self.name}] Đang khởi tạo tài khoản...", "cyan")
        self.fetch_init_data()
        if not self.init_data:
            return

        if self.login():
            self.claim_streak()
            self.claim_daily_tasks()
            self.claim_advertiser_tasks()
            self.execute_ads_round(1)
            self.auto_spin()
            
            for r in range(2, MAX_TON_ROUNDS + 1):
                self.execute_ads_round(r)


def process_account(session_file):
    bot = TRewardsBot(session_file)
    bot.start_farm_flow()

# ====================== HÀM ENTRY POINT CHO CẢ GUI VÀ CHẠY RIÊNG ======================
def run(session_files):
    """Hàm đồng bộ (Sync) hoàn toàn giúp tương thích tuyệt đối với exec() của mainGUI"""
    log_to_gui(f"🚀 Khởi chạy xử lý {len(session_files)} tài khoản đồng bộ...", "magenta")
    with ThreadPoolExecutor(max_workers=min(len(session_files), 5)) as executor:
        futures = [executor.submit(process_account, sfile) for sfile in session_files]
        for future in as_completed(futures):
            try:
                future.result()
            except Exception:
                pass

if __name__ == "__main__":
    # Luồng xử lý khi chạy riêng lẻ bằng lệnh: python tools/trewards.py
    if os.path.exists(SESSION_DIR):
        files = [f for f in os.listdir(SESSION_DIR) if f.endswith('.session')]
        if files:
            run(files)

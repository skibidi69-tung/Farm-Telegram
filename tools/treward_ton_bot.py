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

API_ID = globals().get('API_ID', 28752231)
API_HASH = globals().get('API_HASH', 'ec1c1f2c30e2f1855c3edee7e348480b')

def log(message: str, color: str = "white"):
    ts = datetime.now().strftime("%H:%M:%S")
    colors = {
        "green": "\033[92m",
        "red": "\033[91m",
        "yellow": "\033[93m",
        "cyan": "\033[96m",
        "magenta": "\033[95m",
        "white": "\033[0m"
    }
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

    async def get_init_data(self):
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

    def login(self):
        if not self.init_data:
            return False
        url = f"{BASE_URL}/api/user"
        payload = {"init_data": self.init_data, "language": "en", "referrer_id": None}
        try:
            resp = self.session.post(url, json=payload, headers=self.headers, timeout=15)
            if resp.status_code == 200:
                data = resp.json()
                self.coins = data.get("coins", 0)
                self.spins = data.get("spins", 0)
                self.streak = data.get("streak", 0)
                self.ton_balance = data.get("ton_balance", 0)
                log(f"[{self.name}] 🔐 Login OK! Ví: {self.coins} Xu | {self.ton_balance} TON | {self.spins} Spin", "green")
                return True
            return False
        except Exception:
            return False

    def claim_streak(self):
        url = f"{BASE_URL}/api/claim-streak"
        payload = {"init_data": self.init_data}
        try:
            resp = self.session.post(url, json=payload, headers=self.headers, timeout=15)
            if resp.status_code == 200:
                data = resp.json()
                if data.get("success"):
                    earned = data.get("coins_earned", 0)
                    spins_earned = data.get("spins_earned", 0)
                    self.spins += spins_earned
                    log(f"[{self.name}] 📅 Điểm danh: +{earned} Xu | +{spins_earned} Spin", "green")
        except Exception:
            pass

    def claim_daily_tasks(self):
        url = f"{BASE_URL}/api/claim-daily-task"
        for task in ["checkin", "update", "share"]:
            try:
                time.sleep(random.uniform(0.5, 1.0))
                resp = self.session.post(url, json={"init_data": self.init_data, "task_type": task}, headers=self.headers, timeout=15)
                if resp.status_code == 200:
                    data = resp.json()
                    if data.get("success"):
                        self.coins = data.get("new_balance", self.coins)
                        self.spins += data.get("spins_earned", 0)
                        log(f"[{self.name}] ✅ Task '{task}': +{data.get('coins_earned', 0)} Xu", "green")
            except Exception:
                pass

    def claim_advertiser_tasks(self):
        url = f"{BASE_URL}/api/claim-advertiser-daily"
        for task_id in [124, 123, 122, 95, 94, 93]:
            try:
                time.sleep(random.uniform(0.5, 1.0))
                resp = self.session.post(url, json={"init_data": self.init_data, "task_id": int(task_id)}, headers=self.headers, timeout=15)
                if resp.status_code == 200:
                    data = resp.json()
                    if data.get("success"):
                        self.coins = data.get("new_balance", self.coins)
                        self.spins += data.get("spins_earned", 0)
                        log(f"[{self.name}] 💰 Adv Task {task_id}: +{data.get('coins_earned', 0)} Xu", "green")
            except Exception:
                pass

    def watch_single_ad(self, endpoint: str, ad_id: str, label: str):
        url = f"{BASE_URL}{endpoint}"
        try:
            resp = self.session.post(url, json={"init_data": self.init_data, "ad_id": ad_id}, headers=self.headers, timeout=12)
            if resp.status_code == 200:
                data = resp.json()
                if data.get("success"):
                    if "ton" in endpoint:
                        self.ton_balance = data.get("new_balance", self.ton_balance)
                        log(f"[{self.name}] 💎 Ad '{ad_id}': +{data.get('ton_earned', 0)} TON | Ví: {self.ton_balance} TON", "green")
                    else:
                        self.coins = data.get("new_balance", self.coins)
                        log(f"[{self.name}] 💰 Ad '{ad_id}': +{data.get('coins_earned', 0)} Xu | Ví: {self.coins} Xu", "green")
        except Exception:
            pass

    def execute_ads_round(self, round_num: int):
        time_passed = time.time() - self.last_ad_time
        if time_passed < COOLDOWN_ROUND:
            time.sleep(COOLDOWN_ROUND - time_passed)

        log(f"[{self.name}] 📺 Ads Vòng {round_num}/{MAX_TON_ROUNDS}...", "magenta")
        
        if round_num <= MAX_COIN_ROUNDS:
            self.watch_single_ad("/api/watch-ad", "ad_b1", "XU")
            self.watch_single_ad("/api/watch-ad", "ad_b2", "XU")
        
        if round_num <= MAX_TON_ROUNDS:
            self.watch_single_ad("/api/watch-ad-ton", "ad_b3", "TON")
            self.watch_single_ad("/api/watch-ad-ton", "ad_b4", "TON")
        
        self.last_ad_time = time.time()

    def auto_spin(self):
        url = f"{BASE_URL}/api/spin"
        if self.spins <= 0:
            return
        log(f"[{self.name}] 🎰 Đang quay {self.spins} lượt Spin...", "magenta")
        while self.spins > 0:
            try:
                time.sleep(1.5)
                resp = self.session.post(url, json={"init_data": self.init_data}, headers=self.headers, timeout=15)
                if resp.status_code == 200:
                    data = resp.json()
                    if data.get("success"):
                        self.coins = data.get("new_balance", self.coins)
                        self.spins = data.get("remaining_spins", 0)
                        log(f"[{self.name}] 🎉 Spin: +{data.get('coins_earned', 0)} Xu | Còn {self.spins}", "green")
                    else:
                        break
                else:
                    break
            except Exception:
                break

    async def run(self):
        log(f"[{self.name}] Đang khởi tạo...", "cyan")
        self.init_data = await self.get_init_data()
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
                
            log(f"[{self.name}] ✨ HOÀN THÀNH TẤT CẢ!", "cyan")


# ====================== ENTRY POINT ======================
def process_account(session_file):
    loop = asyncio.new_event_loop()
    asyncio.set_event_loop(loop)
    bot = TRewardsBot(session_file)
    loop.run_until_complete(bot.run())
    loop.close()

async def run_all():
    if not os.path.exists(SESSION_DIR):
        os.makedirs(SESSION_DIR, exist_ok=True)
    session_files = [f for f in os.listdir(SESSION_DIR) if f.endswith('.session')]
    if not session_files:
        return

    log(f"🚀 Bắt đầu chạy {len(session_files)} tài khoản...", "magenta")
    with ThreadPoolExecutor(max_workers=min(len(session_files), 10)) as executor:
        futures = [executor.submit(process_account, sfile) for sfile in session_files]
        for future in as_completed(futures):
            try:
                future.result()
            except Exception:
                pass
    log("🎉 ĐÃ HOÀN THÀNH TOÀN BỘ SYSTEM!", "green")

if __name__ == "__main__":
    asyncio.run(run_all())

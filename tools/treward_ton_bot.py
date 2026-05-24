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

# Cooldown giữa các lần gửi request ad (tránh nghẽn mạng và spam mượt hơn)
COOLDOWN_BETWEEN_ADS = 1.5  

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
                log_to_gui(f"[{self.name}] 🔐 Login OK! Ví: {self.coins} Xu | {self.ton_balance} TON | Lượt Spin: {self.spins}", "green")
                return True
            return False
        except Exception: return False

    def claim_streak(self):
        try:
            resp = self.session.post(f"{BASE_URL}/api/claim-streak", json={"init_data": self.init_data}, headers=self.headers, timeout=15)
            if resp.status_code == 200 and resp.json().get("success"):
                data = resp.json()
                self.spins = data.get("spins_earned", 0) + self.spins
                log_to_gui(f"[{self.name}] 📅 Điểm danh chuỗi thành công! Nhận thêm Spin.", "green")
        except Exception: pass

    def auto_spin(self):
        """Hàm vắt kiệt toàn bộ số lượt Spin đang có"""
        if self.spins <= 0:
            log_to_gui(f"[{self.name}] 🎰 Không có lượt Spin nào khả dụng.", "yellow")
            return
        log_to_gui(f"[{self.name}] 🎰 Đang tiến hành quay {self.spins} lượt Spin tích lũy...", "magenta")
        while self.spins > 0:
            try:
                time.sleep(1.2) # Giữ khoảng cách giữa các lượt quay tránh lỗi
                resp = self.session.post(f"{BASE_URL}/api/spin", json={"init_data": self.init_data}, headers=self.headers, timeout=15)
                if resp.status_code == 200 and resp.json().get("success"):
                    data = resp.json()
                    self.coins = data.get("new_balance", self.coins)
                    self.spins = data.get("remaining_spins", 0)
                    log_to_gui(f"[{self.name}] 🎉 Spin trúng thưởng! Số dư: {self.coins} Xu | Còn {self.spins} lượt", "green")
                else:
                    break
            except Exception:
                break

    def claim_daily_tasks(self):
        for task in ["checkin", "update", "share"]:
            try:
                time.sleep(0.3)
                resp = self.session.post(f"{BASE_URL}/api/claim-daily-task", json={"init_data": self.init_data, "task_type": task}, headers=self.headers, timeout=15)
                if resp.status_code == 200 and resp.json().get("success"):
                    data = resp.json()
                    self.coins = data.get("new_balance", self.coins)
                    self.spins = data.get("spins_earned", 0) + self.spins
                    log_to_gui(f"[{self.name}] ✅ Nhiệm vụ ngày '{task}' hoàn thành!", "green")
            except Exception: pass

    def claim_advertiser_tasks(self):
        for task_id in [124, 123, 122, 95, 94, 93]:
            try:
                time.sleep(0.3)
                resp = self.session.post(f"{BASE_URL}/api/claim-advertiser-daily", json={"init_data": self.init_data, "task_id": int(task_id)}, headers=self.headers, timeout=15)
                if resp.status_code == 200 and resp.json().get("success"):
                    data = resp.json()
                    self.coins = data.get("new_balance", self.coins)
                    self.spins = data.get("spins_earned", 0) + self.spins
                    log_to_gui(f"[{self.name}] 💰 Adv Task {task_id} hoàn thành!", "green")
            except Exception: pass

    def force_spam_ad(self, endpoint: str, ad_id: str):
        """Hàm nện thẳng vào API ad không giới hạn"""
        try:
            resp = self.session.post(f"{BASE_URL}{endpoint}", json={"init_data": self.init_data, "ad_id": ad_id}, headers=self.headers, timeout=12)
            if resp.status_code == 200:
                data = resp.json()
                if data.get("success"):
                    if "ton" in endpoint:
                        self.ton_balance = data.get("new_balance", self.ton_balance)
                        log_to_gui(f"[{self.name}] 💎 Ad '{ad_id}': +{data.get('ton_earned', 0)} TON | Tổng: {self.ton_balance} TON", "green")
                    else:
                        self.coins = data.get("new_balance", self.coins)
                        log_to_gui(f"[{self.name}] 💰 Ad '{ad_id}': +{data.get('coins_earned', 0)} Xu | Tổng: {self.coins} Xu", "green")
                    return True
                else:
                    log_to_gui(f"[{self.name}] ⚠️ Ad '{ad_id}' báo từ chối (success: false)", "yellow")
                    return False
            return False
        except Exception as e:
            log_to_gui(f"[{self.name}] ❌ Lỗi kết nối ad '{ad_id}': {e}", "red")
            return False

    def start_farm_flow(self):
        log_to_gui(f"[{self.name}] Khởi động tiến trình tài khoản...", "cyan")
        self.fetch_init_data()
        if not self.init_data:
            log_to_gui(f"[{self.name}] Lỗi: Không lấy được init_data", "red")
            return
            
        if self.login():
            # ---- BƯỚC 1: ĐIỂM DANH CHUỖI ĐỂ KIẾM THÊM SPIN ----
            log_to_gui(f"[{self.name}] 📑 Bắt đầu chạy Streak...", "magenta")
            self.claim_streak()
            
            # ---- BƯỚC 2: CÀY LUÔN NHIỆM VỤ NGÀY ĐỂ GOM HẾT SPIN THỪA ----
            log_to_gui(f"[{self.name}] 📑 Làm nhiệm vụ Daily & Advertiser Tasks...", "magenta")
            self.claim_daily_tasks()
            self.claim_advertiser_tasks()
            
            # ---- BƯỚC 3: GIẢI QUYẾT SPIN TRƯỚC KHI XEM ADS ----
            log_to_gui(f"[{self.name}] 🎰 Đang kích hoạt luồng tự động Spin...", "magenta")
            self.auto_spin()
            
            # ---- BƯỚC 4: SPAM ADS BẤT TỬ (VÒNG LẶP VÔ HẠN) ----
            log_to_gui(f"[{self.name}] 🚀 Bắt đầu Spam API Ads vô hạn (b1 -> b4)...", "magenta")
            
            loop_count = 1
            while True:
                log_to_gui(f"[{self.name}] 📺 Đang nện Ads vòng thứ {loop_count}...", "cyan")
                
                # Cổng Xu
                self.force_spam_ad("/api/watch-ad", "ad_b1")
                time.sleep(COOLDOWN_BETWEEN_ADS)
                self.force_spam_ad("/api/watch-ad", "ad_b2")
                time.sleep(COOLDOWN_BETWEEN_ADS)
                
                # Cổng TON
                self.force_spam_ad("/api/watch-ad-ton", "ad_b3")
                time.sleep(COOLDOWN_BETWEEN_ADS)
                self.force_spam_ad("/api/watch-ad-ton", "ad_b4")
                
                loop_count += 1
                time.sleep(2) # Nghỉ ngắn giữa các vòng tuần hoàn

def process_account(session_file):
    try:
        bot = TRewardsSpammer(session_file)
        bot.start_farm_flow()
    except Exception: pass

# ====================== HÀM ĐƯỢC GUI GỌI EXEC() ======================
def run(session_files):
    log_to_gui(f"🚀 Hệ thống đa luồng đang xử lý {len(session_files)} tài khoản...", "magenta")
    with ThreadPoolExecutor(max_workers=min(len(session_files), 5)) as executor:
        futures = [executor.submit(process_account, sfile) for sfile in session_files]
        for future in as_completed(futures):
            try: future.result()
            except Exception: pass

if __name__ == "__main__":
    if os.path.exists(SESSION_DIR):
        files = [f for f in os.listdir(SESSION_DIR) if f.endswith('.session')]
        if files: run(files)

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
SESSION_DIR = "sessions"   

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
            "magenta": "\033[95m",
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

    # 🎯 HÀM SWAP ĐIỂM SANG TON (ĐÃ FIX LỖI NHẬN DIỆN THÀNH CÔNG CỦA GAME)
    async def swap_gem_to_ton(self, user_id):
        """Kiểm tra số dư điểm hiện tại, nếu lớn hơn hoặc bằng 100 thì tiến hành đổi sang TON"""
        try:
            current_balance = float(self.balance) if '.' in self.balance else int(self.balance)
        except Exception:
            current_balance = 0

        if current_balance < 100:
            log(f"[{self.name}] ℹ️ Tài sản hiện tại ({current_balance} Gems) chưa đủ 100 để thực hiện đổi TON.", "yellow")
            return False

        amount_to_swap = int((current_balance // 100) * 100)
        log(f"[{self.name}] 💱 Phát hiện tài sản đủ điều kiện. Đang gửi lệnh swap {amount_to_swap} Gems sang TON...", "cyan")

        if not self.csrf:
            await self.fetch_csrf()

        headers = self.headers.copy()
        if self.csrf:
            headers['x-csrf-token'] = self.csrf

        payload_swap = {
            "user_id": int(user_id),
            "amount": amount_to_swap
        }

        try:
            resp = self.session.post(f"{BASE_URL}/swap/gem-to-ton", json=payload_swap, headers=headers, timeout=15)
            result = resp.json()
            
            # Ép kiểu chuỗi phản hồi để check tổng thể chống dev game trả text ảo
            msg = str(result.get("message", "")).lower()
            is_ok = result.get("success") or result.get("ok") or "success" in msg

            if is_ok:
                # Cập nhật số dư điểm mới từ máy chủ sau khi đổi tiền thành công
                if "new_balance" in result:
                    self.balance = str(result.get("new_balance"))
                elif "balance" in result:
                    self.balance = str(result.get("balance"))
                else:
                    self.balance = str(current_balance - amount_to_swap)

                log(f"[{self.name}] ✨ SWAP TON THÀNH CÔNG! Đã đổi {amount_to_swap} Gems. Số dư còn lại: {self.balance} Gems", "green")
                return True
            else:
                log(f"[{self.name}] ❌ Giao dịch Swap thất bại: {result.get('message', 'Từ chối giao dịch')}", "red")
                return False
        except Exception as e:
            log(f"[{self.name}] ⚠️ Lỗi kết nối API Swap: {e}", "red")
            return False

    async def run(self):
        init_data = await self.get_init_data()
        if not init_data:
            return

        _, user_info = init_data
        user_id = int(user_info['id'])

        # Tạo / Đồng bộ tài khoản ban đầu
        try:
            payload = {
                "first_name": user_info.get('first_name', ''),
                "last_name": user_info.get('last_name', ''),
                "username": user_info.get('username', ''),
                "id": user_id,
                "referral_code": None
            }
            
            await self.fetch_csrf()
            
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

        # Thực hiện đổi tiền ngay khi bắt đầu chạy nếu số dư > 100 Gems
        await self.swap_gem_to_ton(user_id)

        # ===== VÒNG LẶP VÔ TẬN Tuyệt Đối =====
        while True:
            if not self.csrf and not await self.fetch_csrf():
                log(f"[{self.name}] ⚠️ Lỗi lấy CSRF, thử lại sau 10s...", "yellow")
                await asyncio.sleep(10)
                continue

            # Kiểm tra giới hạn ads
            if self.ads_limit > 0 and self.today_ads >= self.ads_limit:
                now = datetime.now()
                tomorrow = now.replace(hour=0, minute=0, second=0, microsecond=0)
                if now.hour >= 0:
                    tomorrow = tomorrow.replace(day=now.day + 1)
                
                wait_seconds = (tomorrow - now).total_seconds() + 60
                log(f"[{self.name}] 🎯 Đã đạt giới hạn ads hôm nay ({self.today_ads}/{self.ads_limit}). Chờ reset lúc 00:00 ({int(wait_seconds)}s)...", "green")
                
                await asyncio.sleep(wait_seconds)
                
                try:
                    resp = self.session.post(f"{BASE_URL}/user/check-or-create", json=payload, headers=headers)
                    data = resp.json()
                    if data.get("success"):
                        user = data.get("user", {})
                        self.balance = str(user.get("balance", "0"))
                        self.today_ads = int(user.get("today_ads", 0))
                        self.ads_limit = int(user.get("ads_limit", 2))
                        log(f"[{self.name}] 🔄 Đã reset ngày mới! Balance: {self.balance} | Ads: {self.today_ads}/{self.ads_limit}", "cyan")
                        
                        await self.swap_gem_to_ton(user_id)
                except Exception as e:
                    log(f"[{self.name}] Lỗi đồng bộ sau ngủ: {e}", "red")
                    await asyncio.sleep(300) 
                continue

            current_ad = self.today_ads + 1
            log(f"[{self.name}] 🎬 Đang xem quảng cáo {current_ad}/{self.ads_limit if self.ads_limit > 0 else '?'}...", "magenta")

            for i in range(35, 0, -1):
                print(f"\r[{datetime.now().strftime('%H:%M:%S')}] [{self.name}] ⏳ Đang xem ads... {i}s ", end="", flush=True)
                await asyncio.sleep(1)
            print("\r" + " " * 80, end="\r")

            # Gửi yêu cầu claim reward
            try:
                payload_claim = {
                    "telegram_id": user_id,
                    "points": 50000,
                    "type": "3_ads_set"
                }
                headers = self.headers.copy()
                if self.csrf:
                    headers['x-csrf-token'] = self.csrf

                resp = self.session.post(f"{BASE_URL}/user/reward", json=payload_claim, headers=headers)
                result = resp.json()

                if result.get("success"):
                    self.balance = str(result.get("new_balance", self.balance))
                    self.today_ads += 1
                    log(f"[{self.name}] 💰 Thành công +50k Points | Balance: {self.balance}", "green")
                    
                    await self.swap_gem_to_ton(user_id)
                else:
                    msg_claim = result.get("message", "Lỗi không xác định")
                    log(f"[{self.name}] ⚠️ Claim thất bại: {msg_claim} | Thử lại sau 30s...", "yellow")
                    await asyncio.sleep(30)
                    continue

            except Exception as e:
                log(f"[{self.name}] ⚠️ Lỗi claim: {e} | Thử lại sau 5s", "red")
                await asyncio.sleep(5)
                continue

            await asyncio.sleep(5)


# ====================== ENTRY POINT - MULTI ACCOUNT ======================
async def run(session_files=None):
    """Chạy tất cả session"""
    if session_files is None:
        if not os.path.exists(SESSION_DIR):
            os.makedirs(SESSION_DIR, exist_ok=True)
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

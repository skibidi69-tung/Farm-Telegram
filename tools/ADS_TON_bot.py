import os, json, asyncio, re, urllib.parse, httpx, time
from datetime import datetime
from telethon import TelegramClient
from telethon.tl.functions.messages import RequestWebViewRequest

# ====================== CONFIG ======================
BASE_URL = "https://pocketincome.codeissuehub.com"
BOT_USERNAME = 'ADS_TON_bot'
SESSION_DIR = "sessions"
API_ID = 28752231
API_HASH = 'ec1c1f2c30e2f1855c3edee7e348480b'

def log(message: str, color: str = "white"):
    ts = datetime.now().strftime("%H:%M:%S")
    colors = {"green": "\033[92m", "red": "\033[91m", "yellow": "\033[93m", "cyan": "\033[96m", "magenta": "\033[95m", "white": "\033[0m"}
    print(f"{colors.get(color, '')}[{ts}] {message}\033[0m")

class AdstonBot:
    def __init__(self, session_file: str):
        self.session_file = session_file
        self.name = session_file.replace('.session', '')
        self.csrf = None
        self.balance = "0"
        self.today_ads = 0
        self.ads_limit = 0
        self.client = httpx.AsyncClient(timeout=15)
        self.headers = {
            'User-Agent': "Mozilla/5.0 (Linux; Android 12; K) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/146.0.0.0 Mobile Safari/537.36 Telegram-Android/12.1.1",
            'Accept': "application/json, text/plain, */*",
            'X-Requested-With': "org.telegram.messenger",
            'Origin': BASE_URL,
            'Referer': f"{BASE_URL}/",
        }

    async def get_init_data(self):
        client = TelegramClient(os.path.join(SESSION_DIR, self.session_file), API_ID, API_HASH)
        await client.connect()
        try:
            if not await client.is_user_authorized():
                log(f"[{self.name}] Session lỗi/logout", "red")
                return None
            bot_entity = await client.get_input_entity(BOT_USERNAME)
            res = await client(RequestWebViewRequest(peer=bot_entity, bot=bot_entity, platform='android', from_bot_menu=False, url=f"{BASE_URL}/"))
            tg_data = urllib.parse.unquote(res.url.split('tgWebAppData=')[1].split('&tgWebAppVersion')[0])
            user_json = json.loads(urllib.parse.parse_qs(tg_data)['user'][0])
            return tg_data, user_json
        except Exception as e:
            log(f"[{self.name}] Init Error: {e}", "red")
            return None
        finally:
            await client.disconnect()

    async def fetch_csrf(self):
        try:
            resp = await self.client.get(BASE_URL)
            meta = re.search(r'name="csrf-token" content="(.*?)"', resp.text)
            if meta:
                self.csrf = meta.group(1)
                return True
            xsrf = resp.cookies.get('XSRF-TOKEN')
            if xsrf:
                self.csrf = urllib.parse.unquote(xsrf)
                return True
            return False
        except:
            return False

    async def _call_api(self, endpoint, method='POST', payload=None):
        h = {**self.headers}
        if self.csrf:
            h['x-csrf-token'] = self.csrf
        try:
            if method == 'POST':
                resp = await self.client.post(f"{BASE_URL}{endpoint}", json=payload, headers=h)
            else:
                resp = await self.client.get(f"{BASE_URL}{endpoint}", headers=h)
            return resp.json()
        except:
            return {}

    async def run(self):
        while True:
            init = await self.get_init_data()
            if not init: break
            _, user_info = init
            uid = int(user_info['id'])
            
            await self.fetch_csrf()
            
            # Check status
            payload = {"first_name": user_info.get('first_name',''), "last_name": user_info.get('last_name',''), "username": user_info.get('username',''), "id": uid, "referral_code": None}
            data = await self._call_api("/user/check-or-create", payload=payload)
            if data.get("success"):
                u = data.get("user", {})
                self.balance, self.today_ads, self.ads_limit = str(u.get("balance", "0")), int(u.get("today_ads", 0)), int(u.get("ads_limit", 2))
                log(f"[{self.name}] Bal: {self.balance} | Ads: {self.today_ads}/{self.ads_limit}", "cyan")
            
            # Swap if needed
            curr = float(self.balance) if '.' in self.balance else int(self.balance)
            if curr >= 100:
                amt = int((curr // 100) * 100)
                log(f"[{self.name}] 💱 Swap {amt} Gems...", "cyan")
                res = await self._call_api("/swap/gem-to-ton", payload={"user_id": uid, "amount": amt})
                if res.get("success"):
                    self.balance = str(res.get("new_balance", self.balance))
                    log(f"[{self.name}] ✨ SWAP OK! Bal: {self.balance}", "green")

            # Farm Ads
            while self.today_ads < self.ads_limit:
                log(f"[{self.name}] 🎬 Xem ads {self.today_ads+1}/{self.ads_limit}...", "magenta")
                await asyncio.sleep(35)
                
                res = await self._call_api("/user/reward", payload={"telegram_id": uid, "points": 50000, "type": "3_ads_set"})
                if res.get("success"):
                    self.balance, self.today_ads = str(res.get("new_balance", self.balance)), self.today_ads + 1
                    log(f"[{self.name}] 💰 +50k | Bal: {self.balance}", "green")
                else:
                    log(f"[{self.name}] ⚠️ Claim lỗi: {res.get('message')}", "yellow")
                    await self.fetch_csrf()
                    if "limit" in str(res.get('message')).lower(): break
                    await asyncio.sleep(10)

            log(f"[{self.name}] 🎯 Xong lượt. Nghỉ 1 tiếng...", "green")
            await asyncio.sleep(3600)

async def run_all():
    sessions = [f for f in os.listdir(SESSION_DIR) if f.endswith('.session')]
    log(f"🚀 ADS_TON bắt đầu {len(sessions)} tài khoản...", "cyan")
    await asyncio.gather(*[AdstonBot(f).run() for f in sessions], return_exceptions=True)

if __name__ == "__main__":
    try:
        asyncio.run(run_all())
    except KeyboardInterrupt:
        pass

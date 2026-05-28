import os, asyncio, random, urllib.parse, httpx
from telethon import TelegramClient
from telethon.tl.functions.messages import RequestWebViewRequest
import time

API_ID = globals().get('API_ID', 28752231)
API_HASH = globals().get('API_HASH', 'ec1c1f2c30e2f1855c3edee7e348480b')
BOT_USERNAME = 'EggsHatchBot'
WEBAPP_URL = "https://eggshatch.site/"
SESSION_DIR = "sessions"
BASE_URL = "https://api.eggshatch.site"

def log(msg):
    print(f"[{time.strftime('%H:%M:%S')}] {msg}")

async def get_init_data(session_file):
    client = TelegramClient(os.path.join(SESSION_DIR, session_file), API_ID, API_HASH)
    await client.connect()
    if not await client.is_user_authorized():
        await client.disconnect()
        return None
    try:
        me = await client.get_me()
        bot_entity = await client.get_input_entity(BOT_USERNAME)
        res = await client(RequestWebViewRequest(
            peer=bot_entity, bot=bot_entity, platform='android', from_bot_menu=False, url=WEBAPP_URL
        ))
        parsed = urllib.parse.urlparse(res.url)
        init_data = urllib.parse.parse_qs(parsed.query).get('tgWebAppData', [None])[0]
        if not init_data:
            init_data = urllib.parse.unquote(res.url.split('tgWebAppData=')[1].split('&')[0])
        await client.disconnect()
        return init_data, me.first_name, me.id
    except Exception as e:
        log(f"Lỗi lấy initData: {e}")
        await client.disconnect()
        return None

class EggsHatchBot:
    def __init__(self, session_file, log_func=log):
        self.session_file = session_file
        self.log = log_func
        self.init_data = None
        self.balance = 0
        self.client = httpx.AsyncClient(timeout=15)

    async def refresh_init_data(self):
        data = await get_init_data(self.session_file)
        if not data:
            self.log("❌ No initData")
            return False
        self.init_data, name, _ = data
        self.log(f"🔄 {name}")
        return True

    def _get_headers(self):
        return {
            'accept': '*/*',
            'content-type': 'application/json',
            'origin': 'https://eggshatch.site',
            'referer': 'https://eggshatch.site/',
            'user-agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36',
            'authorization': f'Bearer {self.init_data}',
            'x-telegram-init-data': self.init_data
        }

    async def _call_api(self, endpoint, payload=None, method='POST', include_init_in_body=False):
        url = f"{BASE_URL}{endpoint}"
        headers = self._get_headers()
        if payload is None:
            payload = {}
        if include_init_in_body:
            payload['initData'] = self.init_data
        try:
            if method == 'POST':
                resp = await self.client.post(url, headers=headers, json=payload)
            else:
                resp = await self.client.get(url, headers=headers)
            return resp.status_code, resp.json() if resp.text else None
        except Exception:
            return 500, None

    async def authenticate(self):
        status, data = await self._call_api('/api/auth', payload={"initData": self.init_data}, include_init_in_body=True)
        if status == 200 and data and data.get('ok'):
            user = data.get('user', {})
            self.balance = user.get('balance', 0)
            self.log(f"✅ Bal: {self.balance} Trứng")
            return True
        self.log("❌ Auth fail")
        return False

    async def swap_eggs_to_usdt(self):
        if self.balance < 100:
            return False
        eggs_to_swap = (self.balance // 100) * 100
        self.log(f"💱 Swap {eggs_to_swap} Trứng USDT...")
        payload = {"amount": eggs_to_swap}
        status, data = await self._call_api('/api/convert/to-usdt', payload=payload, include_init_in_body=True)
        if status == 200 and data and data.get('ok'):
            usdt_received = data.get('usdt_received', 0)
            usdt_bal = data.get('usdt_balance', 0)
            self.balance = data.get('eggs_balance', 0)
            self.log(f"✨ +{usdt_received} USDT | Ví: {usdt_bal}$ | Còn: {self.balance} Trứng")
            return True
        self.log("❌ Swap fail")
        return False

    async def claim_daily(self):
        self.log("📅 Daily")
        watch_start = int(time.time() * 1000)
        await asyncio.sleep(random.randint(8, 12))
        payload = {"ad_watched": True, "clicked": True, "watch_start_ms": watch_start}
        status, data = await self._call_api('/api/eggs/claim-daily', payload=payload, include_init_in_body=True)
        if status == 200 and data and data.get('ok'):
            reward = data.get('reward', 0)
            self.balance = data.get('balance', 0)
            self.log(f"📅 +{reward} | Bal: {self.balance}")
            return True
        self.log("📅 Skip")
        return False

    async def claim_multi_ad(self, ad_type='adsgram', slot_index=0):
        watch_start = int(time.time() * 1000)
        await asyncio.sleep(random.randint(5, 8))
        payload = {"type": ad_type, "clicked": True, "watch_start_ms": watch_start, "slot_index": slot_index}
        status, data = await self._call_api('/api/tasks/claim-ad', payload=payload, include_init_in_body=True)
        if status == 200 and data and data.get('ok'):
            reward = data.get('reward_eggs', 0)
            self.balance = data.get('balance', 0)
            remaining = data.get('remaining', 0)
            self.log(f"🎬 +{reward} | Bal: {self.balance} | {ad_type} left: {remaining}")
            return True, remaining, None
        else:
            error_code = data.get('code') if data else ''
            error_msg = data.get('error', '') if data else ''
            if error_code == 'SLOT_ALREADY_CLAIMED' or 'already completed' in error_msg.lower():
                return True, None, 'skip'
            elif status == 429 or 'AD_TOO_FAST' in error_msg:
                return False, 0, 'skip'
            else:
                return False, 0, 'fail'

    async def farm_multi_ads(self, ad_type='adsgram', max_slots=20):
        skip_count = 0
        for slot in range(max_slots):
            success, remaining, status = await self.claim_multi_ad(ad_type, slot)
            if status == 'skip':
                skip_count += 1
                if skip_count >= 3:
                    break
                continue
            skip_count = 0
            if not success:
                break
            if remaining is not None and remaining <= 0:
                break
            await asyncio.sleep(random.uniform(1, 2))

    async def claim_task_ad(self, task_id):
        watch_start = int(time.time() * 1000)
        await asyncio.sleep(random.randint(5, 8))
        payload = {"task_id": task_id, "clicked": True, "watch_start_ms": watch_start}
        status, data = await self._call_api('/api/tasks/claim-adsgram-task', payload=payload, include_init_in_body=True)
        if status == 200 and data and data.get('ok'):
            reward = data.get('reward_eggs', 0)
            self.balance = data.get('balance', 0)
            remaining = data.get('tasks_adsgram_remaining', 0)
            self.log(f"📺 +{reward} | Bal: {self.balance} | left: {remaining}")
            return True, remaining
        else:
            error_msg = data.get('error', '') if data else ''
            if status == 429 or 'AD_TOO_FAST' in error_msg:
                return False, 0
            return False, 0

    async def farm_task_ads(self, max_tasks=15):
        for i in range(max_tasks):
            task_id = f"adsgram_task_{int(time.time()*1000)}"
            success, remaining = await self.claim_task_ad(task_id)
            if not success:
                break
            if remaining <= 0:
                break
            await asyncio.sleep(random.uniform(1, 2))

    async def watch_egg_ad(self, watch_start, egg_type='common'):
        payload = {"type": egg_type, "clicked": True, "watch_start_ms": watch_start}
        status, data = await self._call_api('/api/eggs/watch-ad', payload=payload, include_init_in_body=True)
        if status == 200 and data and data.get('ok'):
            return data.get('ready_to_claim', False), data
        return False, None

    async def process_any_egg(self, egg_type):
        self.log(f"🥚 Kiểm tra: {egg_type}")
        
        # 1. Thử xem ad đầu tiên để lấy thông tin Limit và Ads required
        watch_start = int(time.time() * 1000)
        ready, data = await self.watch_egg_ad(watch_start, egg_type)
        
        if not data or not data.get('ok'):
            err = data.get('error', '').lower() if data else "Unknown error"
            if "limit" in err:
                self.log(f"🏁 {egg_type} đã hết giới hạn ngày.")
            else:
                self.log(f"⏳ {egg_type} chưa sẵn sàng: {err}")
            return False

        # Kiểm tra Limit ngày nếu có
        ct = data.get('claims_today')
        md = data.get('max_daily_claims')
        if ct is not None and md is not None and ct >= md:
            self.log(f"🏁 {egg_type} đã đạt giới hạn {ct}/{md}")
            return False

        # 2. Xem các quảng cáo còn lại
        ready_to_claim = data.get('ready_to_claim', False)
        while not ready_to_claim:
            watched = data.get('ads_watched', 0)
            req = data.get('required_ads', 1)
            self.log(f"🎬 {egg_type} ad: {watched}/{req}")
            
            await asyncio.sleep(5) # Cooldown giữa các ads
            
            watch_start = int(time.time() * 1000)
            ready_to_claim, data = await self.watch_egg_ad(watch_start, egg_type)
            if not data or not data.get('ok'):
                break

        # 3. Gửi lệnh Claim
        status, data = await self._call_api('/api/eggs/claim', payload={"type": egg_type}, include_init_in_body=True)
        if status == 200 and data and data.get('ok'):
            reward = data.get('reward', 0)
            self.balance = data.get('balance', 0)
            self.log(f"✨ {egg_type} +{reward} | Bal: {self.balance}")
            return True
        
        self.log(f"❌ Claim {egg_type} thất bại.")
        return False

    async def farm_all_eggs(self):
        egg_types = ['legendary', 'common'] # Thêm loại trứng mới vào đây
        for etype in egg_types:
            await self.process_any_egg(etype)
            await asyncio.sleep(2) # Nghỉ giữa các loại trứng

    async def run(self):
        try:
            if not await self.refresh_init_data():
                return
            if not await self.authenticate():
                return
            
            # --- PHẦN 1: LÀM NHIỆM VỤ (CHỈ CHẠY 1 LẦN) ---
            await self.swap_eggs_to_usdt()
            await self.claim_daily()
            await self.farm_multi_ads('adsgram', 20)
            await self.farm_multi_ads('monetag', 13)
            await self.farm_task_ads(15)
            
            # --- PHẦN 2: CHỈ LOOP FARM EGG ---
            while True:
                await self.farm_all_eggs()
                self.log("💤 Nghỉ 1 tiếng để chờ lượt Egg tiếp theo...")
                await asyncio.sleep(3605) # Nghỉ hơn 1h một chút để chắc chắn hết cooldown
                
                # Làm mới initData mỗi vòng lặp để tránh hết hạn session
                if not await self.refresh_init_data():
                    break
        finally:
            await self.client.aclose()

async def process_account(session_file, log_callback):
    bot = EggsHatchBot(session_file, log_callback)
    await bot.run()

async def run_all(session_files, log_callback=log):
    log_callback(f"[EggsHatch] {len(session_files)} accounts")
    tasks = [process_account(sfile, log_callback) for sfile in session_files]
    await asyncio.gather(*tasks)

async def main():
    if not os.path.exists(SESSION_DIR):
        log("❌ Không tìm thấy thư mục sessions")
        return
    
    sessions = [f for f in os.listdir(SESSION_DIR) if f.endswith('.session')]
    if not sessions:
        log("❌ Không tìm thấy file session nào")
        return
            
    log(f"🚀 Bắt đầu treo 24/7 với {len(sessions)} tài khoản...")
    await run_all(sessions)

if __name__ == "__main__":
    try:
        asyncio.run(main())
    except KeyboardInterrupt:
        log("👋 Đã dừng bot.")

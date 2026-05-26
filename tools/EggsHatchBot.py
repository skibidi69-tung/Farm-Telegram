import os, time, random, asyncio, urllib.parse, json, requests
from telethon import TelegramClient
from telethon.tl.functions.messages import RequestWebViewRequest
from concurrent.futures import ThreadPoolExecutor, as_completed

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
        self.session = requests.Session()
        self.refresh_init_data()

    def refresh_init_data(self):
        loop = asyncio.new_event_loop()
        asyncio.set_event_loop(loop)
        data = loop.run_until_complete(get_init_data(self.session_file))
        loop.close()
        if not data:
            self.log("❌ No initData")
            return False
        self.init_data, name, _ = data
        self.log(f"🔄 {name}")
        return True

    def _call_api(self, endpoint, payload=None, include_init_in_body=False):
        url = f"{BASE_URL}{endpoint}"
        headers = {
            'accept': '*/*',
            'content-type': 'application/json',
            'origin': 'https://eggshatch.site',
            'referer': 'https://eggshatch.site/',
            'user-agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36',
            'x-telegram-init-data': self.init_data
        }
        if payload is None:
            payload = {}
        if include_init_in_body:
            payload['initData'] = self.init_data
        try:
            resp = self.session.post(url, headers=headers, json=payload, timeout=15)
            return resp.status_code, resp.json() if resp.text else None
        except Exception:
            return 500, None

    def authenticate(self):
        url = f"{BASE_URL}/api/auth"
        headers = {
            'accept': '*/*',
            'content-type': 'application/json',
            'origin': 'https://eggshatch.site',
            'referer': 'https://eggshatch.site/',
            'user-agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36'
        }
        payload = {"initData": self.init_data}
        try:
            resp = self.session.post(url, headers=headers, json=payload, timeout=15)
            if resp.status_code == 200:
                data = resp.json()
                if data.get('ok'):
                    user = data.get('user', {})
                    self.balance = user.get('balance', 0)
                    self.log(f"✅ Bal: {self.balance} Trứng")
                    return True
        except:
            pass
        self.log("❌ Auth fail")
        return False

    def swap_eggs_to_usdt(self):
        if self.balance < 100:
            return False
        eggs_to_swap = (self.balance // 100) * 100
        self.log(f"💱 Swap {eggs_to_swap} Trứng USDT...")
        payload = {"amount": eggs_to_swap}
        status, data = self._call_api('/api/convert/to-usdt', payload=payload, include_init_in_body=True)
        if status == 200 and data and data.get('ok'):
            usdt_received = data.get('usdt_received', 0)
            usdt_bal = data.get('usdt_balance', 0)
            self.balance = data.get('eggs_balance', 0)
            self.log(f"✨ +{usdt_received} USDT | Ví: {usdt_bal}$ | Còn: {self.balance} Trứng")
            return True
        self.log("❌ Swap fail")
        return False

    def claim_daily(self):
        self.log("📅 Daily")
        watch_start = int(time.time() * 1000)
        time.sleep(random.randint(8, 12))
        payload = {"ad_watched": True, "clicked": True, "watch_start_ms": watch_start}
        status, data = self._call_api('/api/eggs/claim-daily', payload=payload, include_init_in_body=True)
        if status == 200 and data and data.get('ok'):
            reward = data.get('reward', 0)
            self.balance = data.get('balance', 0)
            self.log(f"📅 +{reward} | Bal: {self.balance}")
            return True
        self.log("📅 Skip")
        return False

    def claim_multi_ad(self, ad_type='adsgram', slot_index=0, retry=0):
        if retry > 2:
            return False, 0, 'fail'
        watch_start = int(time.time() * 1000)
        time.sleep(random.randint(5, 8))
        payload = {"type": ad_type, "clicked": True, "watch_start_ms": watch_start, "slot_index": slot_index}
        status, data = self._call_api('/api/tasks/claim-ad', payload=payload, include_init_in_body=True)
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
                time.sleep(10)
                return self.claim_multi_ad(ad_type, slot_index, retry+1)
            else:
                return False, 0, 'fail'

    def farm_multi_ads(self, ad_type='adsgram', max_slots=20):
        skip_count = 0
        for slot in range(max_slots):
            success, remaining, status = self.claim_multi_ad(ad_type, slot)
            if status == 'skip':
                skip_count += 1
                if skip_count >= 3:  # 3 lần skip liên tiếp → hết
                    break
                continue
            skip_count = 0
            if not success:
                break
            if remaining is not None and remaining <= 0:
                break
            time.sleep(random.uniform(1, 2))

    def claim_task_ad(self, task_id, retry=0):
        if retry > 2:
            return False, 0
        watch_start = int(time.time() * 1000)
        time.sleep(random.randint(5, 8))
        payload = {"task_id": task_id, "clicked": True, "watch_start_ms": watch_start}
        status, data = self._call_api('/api/tasks/claim-adsgram-task', payload=payload, include_init_in_body=True)
        if status == 200 and data and data.get('ok'):
            reward = data.get('reward_eggs', 0)
            self.balance = data.get('balance', 0)
            remaining = data.get('tasks_adsgram_remaining', 0)
            self.log(f"📺 +{reward} | Bal: {self.balance} | left: {remaining}")
            return True, remaining
        else:
            error_msg = data.get('error', '') if data else ''
            if status == 429 or 'AD_TOO_FAST' in error_msg:
                time.sleep(5)
                return self.claim_task_ad(task_id, retry+1)
            return False, 0

    def farm_task_ads(self, max_tasks=15):
        for i in range(max_tasks):
            task_id = f"adsgram_task_{int(time.time()*1000)}"
            success, remaining = self.claim_task_ad(task_id)
            if not success:
                break
            if remaining <= 0:
                break
            time.sleep(random.uniform(1, 2))

    # ===== EGG CLAIM (COMMON, 6 LẦN/NGÀY) =====
    def watch_and_claim_egg(self):
        """1 cycle: watch ad → claim common egg. Return (success, claims_today, max_daily)"""
        watch_start = int(time.time() * 1000)

        # 1. Watch ad (dù fail vẫn claim thử)
        status, data = self._call_api('/api/eggs/watch-ad',
            payload={"type": "common", "clicked": True, "watch_start_ms": watch_start},
            include_init_in_body=True)

        if status == 200 and data and data.get('ok'):
            self.log("📺 Ad OK...")
        elif status == 429:
            self.log("⚠️ Ad 429, vẫn claim thử...")
        else:
            self.log(f"⚠️ Ad {status}, vẫn claim thử...")

        # 2. Chờ 10s giả vờ xem
        time.sleep(random.randint(8, 12))

        # 3. Claim (dù watch-ad fail hay OK)
        status, data = self._call_api('/api/eggs/claim',
            payload={"type": "common"},
            include_init_in_body=True)

        if status == 200 and data and data.get('ok'):
            reward = data.get('reward', 0)
            self.balance = data.get('balance', 0)
            ct = data.get('claims_today', 1)
            md = data.get('max_daily_claims', 6)
            self.log(f"🥚 +{reward} | Bal: {self.balance} | {ct}/{md}")
            return True, ct, md

        self.log(f"❌ Claim fail ({status})")
        return False, 0, 6

    def farm_eggs(self):
        """Farm common egg: loop tối đa 6 lần/ngày, nếu lỗi đợi 1h thử lại"""
        self.log("🥚 Farm common egg (max 6/ngày)...")
        claimed = 0

        while claimed < 6:
            success, ct, md = self.watch_and_claim_egg()
            if success:
                claimed = ct
                if ct >= md:
                    self.log(f"🏁 Hết lượt ({ct}/{md})")
                    break
                time.sleep(random.uniform(3, 6))
            else:
                self.log("⏳ Lỗi, đợi 1 tiếng thử lại...")
                time.sleep(3600)  # 1 tiếng

        self.log("✅ Egg farm done")

    def run(self):
        if not self.authenticate():
            return
        self.swap_eggs_to_usdt()
        self.claim_daily()
        self.farm_multi_ads('adsgram', 20)
        self.farm_multi_ads('monetag', 13)
        self.farm_task_ads(15)
        self.farm_eggs()  # Egg cuối

def process_account(session_file, log_callback):
    bot = EggsHatchBot(session_file, log_callback)
    if bot.init_data:
        bot.run()

async def run(session_files, log_callback=log):
    log_callback(f"[EggsHatch] {len(session_files)} accounts")
    with ThreadPoolExecutor(max_workers=len(session_files)) as executor:
        futures = [executor.submit(process_account, sfile, log_callback) for sfile in session_files]
        for future in as_completed(futures):
            try:
                future.result()
            except Exception as e:
                log_callback(f"Thread error: {e}")

def main():
    if not os.path.exists(SESSION_DIR):
        log("❌ No sessions folder")
        return
    sessions = [f for f in os.listdir(SESSION_DIR) if f.endswith('.session')]
    if not sessions:
        log("❌ No session files")
        return
    asyncio.run(run(sessions))

if __name__ == "__main__":
    main()

# tools/eggshatch_bot.py
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
            try:
                data = resp.json()
                if resp.status_code != 200:
                    self.log(f"API {resp.status_code}")
                return data
            except:
                return None
        except:
            return None

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
                    balance = user.get('balance', 0)
                    self.log(f"✅ Bal: {balance}")
                    return True
        except:
            pass
        self.log("❌ Auth fail")
        return False

    def claim_daily(self):
        watch_start = int(time.time() * 1000)
        payload = {"ad_watched": True, "clicked": True, "watch_start_ms": watch_start}
        data = self._call_api('/api/eggs/claim-daily', payload=payload, include_init_in_body=True)
        if data and data.get('ok'):
            reward = data.get('reward', 0)
            balance = data.get('balance', 0)
            self.log(f"📅 Daily +{reward} | Bal: {balance}")
            return True
        self.log("📅 Daily none")
        return False

    def claim_multi_ad(self, ad_type='adsgram', slot_index=0, retry=0):
        if retry > 2:
            return False, 0, 'fail'
        watch_start = int(time.time() * 1000)
        ad_duration = random.randint(30, 32)
        time.sleep(ad_duration + random.uniform(1, 3))
        payload = {"type": ad_type, "clicked": True, "watch_start_ms": watch_start, "slot_index": slot_index}
        data = self._call_api('/api/tasks/claim-ad', payload=payload, include_init_in_body=True)
        if data and data.get('ok'):
            reward = data.get('reward_eggs', 0)
            balance = data.get('balance', 0)
            remaining = data.get('remaining', 0)
            self.log(f"🎬 +{reward} | Bal: {balance} | {ad_type} left: {remaining}")
            return True, remaining, None
        else:
            error_code = data.get('code') if data else ''
            error_msg = data.get('error', '') if data else ''
            if error_code == 'SLOT_ALREADY_CLAIMED' or 'already completed' in error_msg.lower():
                return True, None, 'skip'
            elif 'AD_TOO_FAST' in error_msg:
                time.sleep(10)
                return self.claim_multi_ad(ad_type, slot_index, retry+1)
            else:
                self.log(f"❌ {ad_type} slot {slot_index} fail")
                return False, 0, 'fail'

    def farm_multi_ads(self, ad_type='adsgram', max_slots=10):
        for slot in range(max_slots):
            success, remaining, status = self.claim_multi_ad(ad_type, slot)
            if status == 'skip':
                continue
            if not success:
                break
            if remaining is not None and remaining <= 0:
                break
            time.sleep(random.uniform(2, 4))

    def claim_task_ad(self, task_id, retry=0):
        if retry > 2:
            return False, 0
        watch_start = int(time.time() * 1000)
        ad_duration = random.randint(30, 32)
        time.sleep(ad_duration + random.uniform(1, 3))
        payload = {"task_id": task_id, "clicked": True, "watch_start_ms": watch_start}
        data = self._call_api('/api/tasks/claim-adsgram-task', payload=payload, include_init_in_body=True)
        if data and data.get('ok'):
            reward = data.get('reward_eggs', 0)
            balance = data.get('balance', 0)
            remaining = data.get('tasks_adsgram_remaining', 0)
            self.log(f"📺 +{reward} | Bal: {balance} | Tasks left: {remaining}")
            return True, remaining
        else:
            error_msg = data.get('error', '') if data else ''
            error_code = data.get('code') if data else ''
            if 'AD_TOO_FAST' in error_msg:
                time.sleep(10)
                return self.claim_task_ad(task_id, retry+1)
            if 'daily limit' in error_msg.lower() or error_code == 'TASK_AD_DAILY_LIMIT':
                self.log("📺 Daily limit reached")
                return False, 0
            self.log("❌ Task ad fail")
            return False, 0

    def farm_task_ads(self, max_tasks=15):
        for i in range(max_tasks):
            task_id = f"adsgram_task_{int(time.time()*1000)}"
            success, remaining = self.claim_task_ad(task_id)
            if not success:
                break
            if remaining <= 0:
                break
            time.sleep(random.uniform(2, 4))

    def watch_egg_ad(self):
        watch_start = int(time.time() * 1000)
        payload = {"type": "common", "clicked": True, "watch_start_ms": watch_start}
        data = self._call_api('/api/eggs/watch-ad', payload=payload, include_init_in_body=True)
        if data and data.get('ok'):
            return data.get('ready_to_claim', False)
        return False

    def claim_egg(self):
        payload = {"type": "common"}
        data = self._call_api('/api/eggs/claim', payload=payload, include_init_in_body=True)
        if data and data.get('ok'):
            reward = data.get('reward', 0)
            balance = data.get('balance', 0)
            claims_today = data.get('claims_today', 0)
            max_daily = data.get('max_daily_claims', 6)
            self.log(f"🥚 +{reward} | Bal: {balance} | {claims_today}/{max_daily}")
            return True, claims_today, max_daily
        self.log("🥚 Claim fail")
        return False, 0, 0

    def farm_egg_cycle(self):
        self.log("🥚 Egg farm (6/day)")
        while True:
            ready = self.watch_egg_ad()
            if ready:
                success, claims_today, max_daily = self.claim_egg()
                if success:
                    if claims_today >= max_daily:
                        self.log("🏁 Daily egg limit")
                        break
                    time.sleep(3600)
                else:
                    time.sleep(60)
            else:
                time.sleep(60)

    def run(self):
        if not self.authenticate():
            return
        self.claim_daily()
        self.farm_multi_ads('adsgram', 10)
        self.farm_multi_ads('monetag', 13)
        self.farm_task_ads(15)
        self.farm_egg_cycle()

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

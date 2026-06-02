import os, asyncio, random, urllib.parse, httpx, time
from telethon import TelegramClient
from telethon.tl.functions.messages import RequestWebViewRequest

# ====================== CONFIG ======================
API_ID = globals().get('API_ID', 28752231)
API_HASH = 'ec1c1f2c30e2f1855c3edee7e348480b'
BOT_USERNAME = 'EggsHatchBot'
WEBAPP_URL = "https://eggshatch.site/"
SESSION_DIR = "sessions"
BASE_URL = "https://api.eggshatch.site"

def log(msg):
    print(f"[{time.strftime('%H:%M:%S')}] {msg}")

async def get_init_data(session_file):
    client = TelegramClient(os.path.join(SESSION_DIR, session_file), API_ID, API_HASH)
    await client.connect()
    try:
        if not await client.is_user_authorized(): return None
        me = await client.get_me()
        bot_entity = await client.get_input_entity(BOT_USERNAME)
        res = await client(RequestWebViewRequest(peer=bot_entity, bot=bot_entity, platform='android', from_bot_menu=False, url=WEBAPP_URL))
        parsed = urllib.parse.urlparse(res.url)
        init_data = urllib.parse.parse_qs(parsed.query).get('tgWebAppData', [None])[0]
        if not init_data:
            init_data = urllib.parse.unquote(res.url.split('tgWebAppData=')[1].split('&')[0])
        await client.disconnect()
        return init_data, me.first_name, me.id
    except Exception as e:
        log(f"Lỗi Telethon: {e}")
        await client.disconnect()
        return None

class EggsHatchBot:
    def __init__(self, session_file, log_func=log):
        self.session_file = session_file
        self.log = log_func
        self.init_data = None
        self.client = httpx.AsyncClient(timeout=15)

    async def refresh_init_data(self):
        data = await get_init_data(self.session_file)
        if not data: return False
        self.init_data, name, _ = data
        self.log(f"🔄 {name}")
        return True

    def _get_headers(self):
        return {
            'accept': '*/*', 'content-type': 'application/json',
            'origin': 'https://eggshatch.site', 'referer': 'https://eggshatch.site/',
            'user-agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36',
            'authorization': f'Bearer {self.init_data}', 'x-telegram-init-data': self.init_data
        }

    async def _call_api(self, endpoint, payload=None, method='POST'):
        url = f"{BASE_URL}{endpoint}"
        try:
            if method == 'POST':
                resp = await self.client.post(url, headers=self._get_headers(), json=payload or {})
            else:
                resp = await self.client.get(url, headers=self._get_headers())
            return resp.status_code, resp.json() if resp.text else None
        except: return 500, None

    async def authenticate(self):
        status, data = await self._call_api('/api/auth', payload={"initData": self.init_data})
        if status == 200 and data and data.get('ok'):
            self.log(f"✅ Bal: {data['user'].get('balance', 0)} Trứng")
            return True
        return False

    async def farm_multi_ads(self):
        self.log("🎬 Kiểm tra Adsgram (15) & Monetag (13)...")
        # Adsgram (15)
        for i in range(15):
            start_ms = int(time.time() * 1000) - 5000 # Giả lập bắt đầu sớm 5s
            await asyncio.sleep(random.randint(10, 15)) # Đợi xem ad ngắn hơn
            st, d = await self._call_api('/api/tasks/claim-ad', payload={"type": "adsgram", "clicked": True, "watch_start_ms": start_ms, "slot_index": i})
            if st == 200 and d.get('ok'):
                self.log(f"🎬 Adsgram Slot {i} OK (+{d.get('reward_eggs')} trứng)")
            else:
                err = d.get('error', 'Skip') if d else 'Error'
                if d and d.get('code') == 'SLOT_ALREADY_CLAIMED':
                    continue # Đã làm rồi, lướt qua nhanh
                self.log(f"⏩ Adsgram Slot {i}: {err}")
                continue 

        # Monetag (13)
        for i in range(13):
            start_ms = int(time.time() * 1000) - 5000
            await asyncio.sleep(random.randint(10, 15))
            st, d = await self._call_api('/api/tasks/claim-ad', payload={"type": "monetag", "clicked": True, "watch_start_ms": start_ms, "slot_index": i})
            if st == 200 and d.get('ok'):
                self.log(f"🎬 Monetag Slot {i} OK (+{d.get('reward_eggs')} trứng)")
            else:
                err = d.get('error', 'Skip') if d else 'Error'
                if d and d.get('code') == 'SLOT_ALREADY_CLAIMED':
                    continue
                self.log(f"⏩ Monetag Slot {i}: {err}")
                continue

    async def farm_adexium_tasks(self):
        self.log("💎 Kiểm tra Adexium (20)...")
        for i in range(20):
            start_ms = int(time.time() * 1000) - 5000
            await asyncio.sleep(random.randint(10, 15))
            st, d = await self._call_api('/api/tasks/claim-adexium-task', payload={"done": True, "task_id": None, "slot_index": i, "watch_start_ms": start_ms})
            if st == 200 and d.get('ok'):
                self.log(f"💎 Adexium Slot {i} OK (+{d.get('reward_eggs')} trứng)")
            else:
                err = d.get('error', 'Skip') if d else 'Error'
                if d and d.get('code') == 'SLOT_ALREADY_CLAIMED':
                    continue
                self.log(f"⏩ Adexium Slot {i}: {err}")
                continue

    async def farm_eggs_via_summary(self):
        status, data = await self._call_api('/api/eggs/summary', method='GET')
        if status != 200 or not data.get('ok'): 
            self.log("❌ Không lấy được Summary")
            return
        
        self.log(f"🥚 Tổng sản lượng: {data.get('total_hourly_production')} trứng/h")
        
        for egg in data.get('eggs', []):
            etype = egg['type']
            self.log(f"🔍 Kiểm tra {etype}:")
            
            if egg.get('daily_limit_hit'):
                self.log(f"   🏁 {etype} đã hết lượt ngày ({egg.get('claims_today')}/{egg.get('max_daily_claims')})")
                continue
            
            if not egg.get('time_ready'):
                self.log(f"   ⏳ {etype} đang sản xuất: còn {egg.get('remaining_s')}s")
                continue

            # Xem ads cho đến khi server báo sẵn sàng
            ready_to_claim = egg.get('can_claim', False)
            while not ready_to_claim:
                self.log(f"   🥚 {etype} chưa đủ ads, đang xem thêm...")
                start_ms = int(time.time() * 1000) - 10000 # Giả lập bắt đầu trước 10s
                
                # Nghỉ trước khi báo cho server (giả lập đang xem)
                await asyncio.sleep(random.randint(35, 45)) 
                
                st_ad, d_ad = await self._call_api('/api/eggs/watch-ad', payload={"type": etype, "clicked": True, "watch_start_ms": start_ms})
                
                if d_ad and d_ad.get('ok'):
                    ready_to_claim = d_ad.get('ready_to_claim', False)
                    watched = d_ad.get('ads_watched', 0)
                    total = d_ad.get('required_ads', 1)
                    self.log(f"   🎬 {etype} ads: {watched}/{total}")
                else:
                    self.log(f"   ❌ Lỗi khi xem ad cho {etype}: {d_ad.get('error') if d_ad else st_ad}")
                    # Nếu server báo xem chưa hết, nghỉ thêm rồi thử lại
                    await asyncio.sleep(10)
                    # Nếu lỗi không phải do thời gian thì mới break
                    if d_ad and "full ad" not in d_ad.get('error', ''):
                        break
            
            if not ready_to_claim:
                self.log(f"   ⏩ Bỏ qua {etype} do chưa xem đủ ads.")
                continue

            # Claim
            self.log(f"   ✨ Đang gửi lệnh Claim cho {etype}...")
            st, d = await self._call_api('/api/eggs/claim', payload={"type": etype})
            if st == 200 and d.get('ok'):
                self.log(f"   ✅ {etype} Claim thành công! +{d.get('reward')} | Bal: {d.get('balance')}")
            else:
                self.log(f"   ❌ {etype} Claim thất bại: {d.get('error') if d else st}")

    async def run(self):
        try:
            if not await self.refresh_init_data(): return
            if not await self.authenticate(): return
            
            # Claim Daily
            start_ms = int(time.time() * 1000)
            await asyncio.sleep(10)
            await self._call_api('/api/eggs/claim-daily', payload={"ad_watched": True, "clicked": True, "watch_start_ms": start_ms})
            
            await self.farm_multi_ads()
            await self.farm_adexium_tasks()
            
            while True:
                await self.farm_eggs_via_summary()
                self.log("💤 Nghỉ 1 tiếng...")
                await asyncio.sleep(3605)
                if not await self.refresh_init_data(): break
        finally: await self.client.aclose()

async def main():
    if not os.path.exists(SESSION_DIR): return log("❌ No sessions folder")
    sessions = [f for f in os.listdir(SESSION_DIR) if f.endswith('.session')]
    if not sessions: return log("❌ No sessions")
    log(f"🚀 Bắt đầu treo 24/7 với {len(sessions)} tài khoản...")
    tasks = [EggsHatchBot(s).run() for s in sessions]
    await asyncio.gather(*tasks)

if __name__ == "__main__":
    try: asyncio.run(main())
    except KeyboardInterrupt: pass

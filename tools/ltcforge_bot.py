import os, asyncio, httpx, json, urllib.parse, time, random
from datetime import datetime
from telethon import TelegramClient
from telethon.tl.functions.messages import RequestWebViewRequest

API_ID = 28752231
API_HASH = 'ec1c1f2c30e2f1855c3edee7e348480b'
BOT_USERNAME = 'ltcforge_bot'
WEBAPP_URL = 'https://tgltcminer.vercel.app/'
BASE_URL = "https://mysxcpkrphzsgtbcybkx.supabase.co"
SESSION_DIR = "sessions"
SUPABASE_KEY = "sb_publishable_av437bmlnjlhEGCs9A9NUw_YcASZO_i"

def log(msg, color="white"):
    ts = datetime.now().strftime("%H:%M:%S")
    colors = {"green": "\033[92m", "red": "\033[91m", "yellow": "\033[93m", "cyan": "\033[96m", "white": "\033[0m"}
    c = colors.get(color, "\033[0m")
    print(f"[{ts}] {c}{msg}\033[0m", flush=True)

async def get_init_data(session_file):
    client = TelegramClient(os.path.join(SESSION_DIR, session_file), API_ID, API_HASH)
    await client.connect()
    try:
        if not await client.is_user_authorized(): return None
        bot_entity = await client.get_input_entity(BOT_USERNAME)
        res = await client(RequestWebViewRequest(peer=bot_entity, bot=bot_entity, platform='android', from_bot_menu=False, url=WEBAPP_URL))
        parsed = urllib.parse.urlparse(res.url)
        init_data = urllib.parse.parse_qs(parsed.query).get('tgWebAppData', [None])[0]
        if not init_data:
            init_data = urllib.parse.unquote(res.url.split('tgWebAppData=')[1].split('&')[0])
        await client.disconnect()
        return init_data
    except:
        await client.disconnect()
        return None

class LTCForgeBot:
    def __init__(self, session_file):
        self.session_file = session_file
        self.name = session_file.replace('.session', '')
        self.init_data = None
        self.tg_id = None
        self.client = httpx.AsyncClient(timeout=30)
        self.headers = {
            'accept': '*/*', 'content-type': 'application/json',
            'apikey': SUPABASE_KEY, 'authorization': f'Bearer {SUPABASE_KEY}',
            'origin': 'https://tgltcminer.vercel.app', 'referer': 'https://tgltcminer.vercel.app/',
            'user-agent': 'Mozilla/5.0'
        }

    async def op(self, action, extra=None):
        payload = {"action": action, "telegram_id": self.tg_id, "_init_data": self.init_data, "_ts": int(time.time()*1000)}
        if extra: payload.update(extra)
        r = await self.client.post(f"{BASE_URL}/functions/v1/user-operations", headers=self.headers, json=payload)
        return r.json()

    async def pop_ad(self):
        r = await self.client.post(f"{BASE_URL}/functions/v1/pop-ad-start", headers=self.headers, json={
            "telegram_id": self.tg_id, "_init_data": self.init_data, "_ts": int(time.time()*1000)
        })
        d = r.json()
        if not d.get("ok"): return
        sid = d["session_id"]
        await asyncio.sleep(random.randint(17, 22))
        r2 = await self.client.post(f"{BASE_URL}/functions/v1/pop-ad-claim", headers=self.headers, json={
            "telegram_id": self.tg_id, "session_id": sid,
            "blur_total_ms": random.randint(7000, 13000), "elapsed_ms": random.randint(17000, 22000),
            "ad_done": True, "_init_data": self.init_data, "_ts": int(time.time()*1000)
        })
        d2 = r2.json()
        if d2.get("ok"):
            log(f"[{self.name}] 💰 Pop-ad +{d2['reward']:.8f} LTC | Left: {d2.get('remaining','?')}", "green")
        return d2

    async def daily_ad_task(self):
        r = await self.op("claim_daily_ad_task", {"task_type": "watch_3"})
        if r.get("success"):
            log(f"[{self.name}] 📋 Daily task | Count: {r.get('newCount','?')}", "green")
        return r

    async def run(self):
        self.init_data = await get_init_data(self.session_file)
        if not self.init_data: return
        for part in self.init_data.split("&"):
            if part.startswith("user="):
                user = json.loads(urllib.parse.unquote(part.split("=",1)[1]))
                self.tg_id = user["id"]
                break
        if not self.tg_id: return

        r = await self.op("register_or_login", {"username":"user","first_name":"User","last_name":"","language_code":"en","referred_by":None,"ip_address":"125.212.158.27"})
        bal = r.get("user",{}).get("balance",0)
        log(f"[{self.name}] Bal: {bal:.8f} LTC", "green")

        while True:
            log(f"[{self.name}] Running ads...", "cyan")

            while True:
                r = await self.daily_ad_task()
                if not r.get("success"): break
                await asyncio.sleep(3)

            while True:
                d = await self.pop_ad()
                if not d or not d.get("ok"): break
                if d.get("remaining", 1) <= 0: break
                await asyncio.sleep(5)

            while True:
                r = await self.op("ad_watch_reward")
                if not r.get("success"): break
                log(f"[{self.name}] Watch +{r.get('reward',0):.8f} LTC", "green")
                await self.client.post(f"{BASE_URL}/functions/v1/security-check", headers=self.headers, json={
                    "action": "log_behavior", "telegram_id": self.tg_id,
                    "event_type": "ad_watch", "event_data": {"provider": "adsgram_reward", "reward": r.get("reward",0)},
                    "_init_data": self.init_data, "_ts": int(time.time()*1000)
                })
                await asyncio.sleep(5)

            log(f"[{self.name}] All limit, sleep 1h...", "yellow")
            await asyncio.sleep(3600)

        await self.client.aclose()

async def main():
    possible = ["test/sessions", "sessions"]
    sd = next((p for p in possible if os.path.exists(p)), "sessions")
    global SESSION_DIR; SESSION_DIR = sd
    sessions = [f for f in os.listdir(sd) if f.endswith('.session')]
    log(f"LTCForge {len(sessions)} acc", "cyan")
    await asyncio.gather(*[LTCForgeBot(s).run() for s in sessions])

if __name__ == "__main__":
    try: asyncio.run(main())
    except KeyboardInterrupt: pass

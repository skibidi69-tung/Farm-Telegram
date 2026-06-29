import os, asyncio, httpx, json, urllib.parse, time, random
from datetime import datetime
from telethon import TelegramClient
from telethon.tl.functions.messages import RequestWebViewRequest

# ====================== CONFIG ======================
API_ID = 28752231
API_HASH = 'ec1c1f2c30e2f1855c3edee7e348480b'
BOT_USERNAME = 'atomicbux_bot'
WEBAPP_URL = 'https://atomicbux.online/'
BASE_URL = "https://atomicbux.online/backend/api"
SESSION_DIR = "sessions"

ALL_PROVIDERS = [
    "monetag", "adsgram", "adexium", "onclicka",
    "home_monetag", "home_adsgram", "home_adexium", "home_onclicka"
]
# ====================================================

def log(msg, color="white"):
    ts = datetime.now().strftime("%H:%M:%S")
    colors = {"green": "\033[92m", "red": "\033[91m", "yellow": "\033[93m", "cyan": "\033[96m", "white": "\033[0m"}
    c = colors.get(color, "\033[0m")
    print(f"[{ts}] {c}{msg}\033[0m")

async def get_init_data(session_file):
    client = TelegramClient(os.path.join(SESSION_DIR, session_file), API_ID, API_HASH)
    await client.connect()
    try:
        if not await client.is_user_authorized(): return None
        bot_entity = await client.get_input_entity(BOT_USERNAME)
        res = await client(RequestWebViewRequest(
            peer=bot_entity, bot=bot_entity, platform='android', from_bot_menu=False, url=WEBAPP_URL
        ))
        parsed = urllib.parse.urlparse(res.url)
        init_data = urllib.parse.parse_qs(parsed.query).get('tgWebAppData', [None])[0]
        if not init_data:
            init_data = urllib.parse.unquote(res.url.split('tgWebAppData=')[1].split('&')[0])
        await client.disconnect()
        return init_data
    except:
        await client.disconnect()
        return None

class AtomicBot:
    def __init__(self, session_file):
        self.session_file = session_file
        self.name = session_file.replace('.session', '')
        self.init_data = None
        self.client = httpx.AsyncClient(timeout=30)
        self.headers = {'accept': '*/*', 'content-type': 'application/json', 'origin': 'https://atomicbux.online', 'referer': 'https://atomicbux.online/', 'user-agent': 'Mozilla/5.0'}

    async def call(self, endpoint, payload=None):
        headers = {**self.headers, "authorization": f"Bearer {self.init_data}"}
        try:
            r = await self.client.post(f"{BASE_URL}/{endpoint}", headers=headers, json=payload or {})
            return r.json()
        except: return {}

    async def watch(self, provider):
        res = await self.call("watch-ad", {"provider": provider})
        if res.get("status") == "success":
            log(f"   +{res.get('reward')} {provider} (#{res.get('count')})", "green")
            return True
        return False

    async def run(self):
        while True:
            self.init_data = await get_init_data(self.session_file)
            if not self.init_data:
                await asyncio.sleep(600); continue

            # Daily
            await self.call("claim-daily")
            await self.call("missions", {"action": "claim_daily_ad"})

            active = ALL_PROVIDERS[:]
            while active:
                ded = []
                for p in active:
                    ok = await self.watch(p)
                    if not ok:
                        ded.append(p)
                    await asyncio.sleep(1.5)
                for p in ded:
                    if p in active: active.remove(p)

            log("🏁 All done. Waiting 60s...", "cyan")
            await asyncio.sleep(60)

async def main():
    possible = ["test/sessions", "sessions", "C:/Users/Gang/Desktop/dec/test/sessions"]
    sd = next((p for p in possible if os.path.exists(p)), "sessions")
    global SESSION_DIR; SESSION_DIR = sd

    sessions = [f for f in os.listdir(sd) if f.endswith('.session')]
    log(f"🚀 AtomicBux {len(sessions)} accounts", "cyan")
    await asyncio.gather(*[AtomicBot(s).run() for s in sessions])

if __name__ == "__main__":
    try: asyncio.run(main())
    except KeyboardInterrupt: pass

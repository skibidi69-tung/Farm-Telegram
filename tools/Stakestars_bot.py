import os, asyncio, httpx, json, urllib.parse, time, random
from datetime import datetime, timedelta
from telethon import TelegramClient
from telethon.tl.functions.messages import RequestWebViewRequest

API_ID = 28752231
API_HASH = 'ec1c1f2c30e2f1855c3edee7e348480b'
BOT_USERNAME = 'StakeStars_Bot'
WEBAPP_URL = 'https://stakestars.top/'
BASE_URL = "https://stakestars.top/api"
SESSION_DIR = "sessions"
WATCH_AD_ID = 23
HEARTBEAT_INTERVAL = 15  # Giây

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

class StakeStarsBot:
    def __init__(self, session_file):
        self.session_file = session_file
        self.name = session_file.replace('.session', '')
        self.init_data = None
        self.client = httpx.AsyncClient(timeout=30)
        self.headers = {'accept': '*/*', 'content-type': 'application/json', 'origin': 'https://stakestars.top', 'referer': 'https://stakestars.top/', 'user-agent': 'Mozilla/5.0'}

    async def get(self, endpoint):
        try:
            r = await self.client.get(f"{BASE_URL}/{endpoint}", headers={**self.headers, "authorization": self.init_data})
            return r.json()
        except: return {}

    async def post(self, endpoint):
        try:
            r = await self.client.post(f"{BASE_URL}/{endpoint}", headers={**self.headers, "authorization": self.init_data})
            return r.json()
        except: return {}

    async def heartbeat_loop(self):
        """Call user/me every 15 seconds to maintain passive income"""
        log(f"[{self.name}] ❤️ AFK heartbeat started (every {HEARTBEAT_INTERVAL}s)", "white")
        while True:
            await asyncio.sleep(HEARTBEAT_INTERVAL)
            try:
                me = await self.get("user/me")
                if me.get("id"):
                    log(f"[{self.name}] 💤 Bal: {me['balance']:.4f}", "cyan")
            except: pass

    async def run(self):
        self.init_data = await get_init_data(self.session_file)
        if not self.init_data: return

        # Start heartbeat background task
        asyncio.create_task(self.heartbeat_loop())

        while True:
            # Check tasks for ad
            tasks = await self.get("tasks")
            ad_task = next((t for t in tasks if t.get("id") == WATCH_AD_ID), None)

            if not ad_task:
                await asyncio.sleep(30); continue

            burst = ad_task.get("burstUsed", 0)
            max_burst = ad_task.get("burstMax", 5)
            available = ad_task.get("available", False)
            cooldown_h = ad_task.get("cooldownHrs", 2)

            if available and burst < max_burst:
                res = await self.post(f"tasks/{WATCH_AD_ID}/claim")
                if res.get("ok"):
                    log(f"[{self.name}] ✅ Ad +{res.get('reward')} | Bal: {res.get('balance')}", "green")
                else:
                    log(f"[{self.name}] ❌ Ad fail", "red")
                await asyncio.sleep(5)
            else:
                log(f"[{self.name}] 💤 No more ads ({burst}/{max_burst}). Waiting {cooldown_h}h...", "yellow")
                await asyncio.sleep(cooldown_h * 3600)

        await self.client.aclose()

async def main():
    possible = ["test/sessions", "sessions", "C:/Users/Gang/Desktop/dec/test/sessions"]
    sd = next((p for p in possible if os.path.exists(p)), "sessions")
    global SESSION_DIR; SESSION_DIR = sd
    sessions = [f for f in os.listdir(sd) if f.endswith('.session')]
    log(f"🚀 StakeStars {len(sessions)} acc", "cyan")
    await asyncio.gather(*[StakeStarsBot(s).run() for s in sessions])

if __name__ == "__main__":
    try: asyncio.run(main())
    except KeyboardInterrupt: pass

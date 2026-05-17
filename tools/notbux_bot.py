# tools/notbux_bot.py
import os, sys, time, random, asyncio, urllib.parse, base64, requests
from datetime import datetime
from urllib.parse import parse_qs
from telethon import TelegramClient
from telethon.tl.functions.messages import RequestWebViewRequest

# Các biến này sẽ được truyền từ main_gui.py (hoặc lấy từ biến global)
API_ID = globals().get('API_ID', 28752231)
API_HASH = globals().get('API_HASH', 'ec1c1f2c30e2f1855c3edee7e348480b')
BOT_USERNAME = 'notbux_bot'
WEBAPP_URL = "https://notbux.click/"
SESSION_DIR = "sessions"

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
        auth_data = urllib.parse.unquote(res.url.split('tgWebAppData=')[1].split('&tgWebAppVersion')[0])
        await client.disconnect()
        return auth_data, me.first_name, me.id
    except:
        await client.disconnect()
        return None

def parse_config(clean_q, first_name, tg_id):
    try:
        decoded = urllib.parse.unquote(clean_q)
        parsed = parse_qs(decoded)
        user_json = parsed.get('user', [''])[0]
        auth_date = parsed.get('auth_date', [''])[0]
        query_id = parsed.get('query_id', [''])[0]
        check_str = f"auth_date={auth_date}\nquery_id={query_id}\nuser={user_json}"
        encoded_check = base64.b64encode(check_str.encode()).decode()
        return {
            'clean_q': clean_q, 'uid': str(tg_id), 'signature': parsed.get('signature', [''])[0],
            'raw_hash': parsed.get('hash', [''])[0], 'data_check_string': encoded_check, 'name': first_name
        }
    except:
        return None

class NotBuxBot:
    def __init__(self, cfg, log_func=print):
        self.cfg = cfg
        self.auth = f"tma {cfg['clean_q']}"
        self.headers = {
            'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36',
            'Accept': '*/*',
            'Origin': 'https://notbux.click',
            'Referer': 'https://notbux.click/',
            'Authorization': self.auth
        }
        self.session = requests.Session()
        self.fail_streak = 0
        self.log = log_func

    def get_balance(self):
        try:
            resp = self.session.get('https://notbux.click/api/me', timeout=10)
            if resp.status_code == 200:
                return resp.json()['user']['balance_coins']
        except:
            pass
        return None

    def claim_daily(self):
        """Claim daily check-in using /api/earn/checkin"""
        self.log("[Daily] Đang nhận thưởng hàng ngày...")
        try:
            resp = self.session.post('https://notbux.click/api/earn/checkin', json={}, timeout=10)
            if resp.status_code == 200:
                data = resp.json()
                if data.get('ok') or data.get('success'):
                    new_balance = self.get_balance()
                    self.log(f"[Daily] Nhận thưởng thành công! Số dư mới: {new_balance}")
                    return True
                else:
                    self.log(f"[Daily] Đã nhận hôm nay rồi hoặc lỗi: {data}")
            else:
                self.log(f"[Daily] HTTP {resp.status_code} - Có thể đã claim rồi")
        except Exception as e:
            self.log(f"[Daily] Lỗi kết nối: {e}")
        return False

    def run_adsgram(self, block_id, section_name):
        self.log(f"[ADSGRAM:{section_name}] Đang lấy quảng cáo...")
        bal_before = self.get_balance()
        params = {
            'envType':'telegram','blockId':block_id,'platform':'Win32','language':'en',
            'top_domain':'notbux.click','signature':self.cfg['signature'],
            'data_check_string':self.cfg['data_check_string'],'sdk_version':'1.47.0',
            'tg_id':self.cfg['uid'],'tg_platform':'ios','tma_version':'8.0',
            'request_id':''.join(random.choices('0123456789',k=30)),'raw':self.cfg['raw_hash']
        }
        try:
            resp = self.session.get("https://api.adsgram.ai/adv", params=params, timeout=15)
            banners = resp.json().get('banners', [])
            if not banners:
                return False
            record = banners[0]['banner']['trackings'][0]['value'].split('record=')[1].split('&')[0]
            self.session.get("https://api.adsgram.ai/event", params={'record':record,'type':'Render','trackingtypeid':'13'})
            time.sleep(2)
            self.session.get("https://api.adsgram.ai/event", params={'record':record,'type':'Show','trackingtypeid':'0'})
            wait = random.randint(22,28)
            self.log(f"Xem quảng cáo ({wait}s)...")
            time.sleep(wait)
            self.session.get("https://api.adsgram.ai/event", params={'record':record,'type':'Reward','trackingtypeid':'14'})
            time.sleep(3)
            bal_after = self.get_balance()
            if bal_after and bal_before and bal_after > bal_before:
                self.log(f"Thành công! Dư: {bal_after}")
                self.fail_streak = 0
                return True
        except:
            pass
        self.fail_streak += 1
        return False

    def run_monetag(self, oaid, section):
        self.log(f"[MONETAG:{section}] Đang lấy quảng cáo...")
        self.session.cookies.clear()
        bal_before = self.get_balance()
        suffix = "tasks_ad_monetag" if section=="TASK" else "earn_ad_monetag"
        ymid = f"{self.cfg['uid']}%7C{suffix}"
        m_params = {
            'excludes':'','oaid':oaid,'ymid':ymid,'tgp':'ios','os':'windows','os_version':'10.0.0',
            'browser_version':'148.0.7778.98','sw':'1366','sh':'768','btz':'Asia/Calcutta',
            'dmn':'libtl.com','is_mobile':'false','of':'true'
        }
        m_url = f"https://e8ys.com/500/10558478?{urllib.parse.urlencode(m_params)}"
        ref = f'https://notbux.click/{section.lower()}s' if section=="TASK" else 'https://notbux.click/earn'
        headers = {**self.headers, 'Referer': ref}
        try:
            r_ad = self.session.get(m_url, headers=headers, timeout=15)
            ad_data = r_ad.json()
            ruid, ads = ad_data.get('ruid'), ad_data.get('ads', [])
            if not ads or not ruid:
                return False
            self.session.get(ads[0].get('impression_url'), headers=headers)
            self.session.get(ads[0].get('click'), headers=headers)
            wait = random.randint(35,40) if section=="TASK" else random.randint(18,22)
            self.log(f"Xem quảng cáo ({wait}s)...")
            time.sleep(wait)
            self.session.get(f"https://e8ys.com/resolve?ruid={ruid}", headers={**headers,'Referer':'https://e8ys.com/500/10558478'})
            time.sleep(3)
            bal_after = self.get_balance()
            if bal_after and bal_before and bal_after > bal_before:
                self.log(f"Thành công! Dư: {bal_after}")
                self.fail_streak = 0
                return True
        except:
            pass
        self.fail_streak += 1
        return False

    def run_all(self):
        # 1. Claim daily trước
        self.claim_daily()
        time.sleep(2)

        # 2. Chạy quảng cáo
        tasks = [
            ("ADSGRAM","27091","TASK"),
            ("ADSGRAM","27092","EARN"),
            ("MONETAG","08032ccd9bd5477bf6690d2a3bcbaa55","TASK"),
            ("MONETAG","0082440db830411bf781bf4a72e32aca","EARN")
        ]
        for provider, zone, name in tasks:
            if provider == "ADSGRAM":
                self.run_adsgram(zone, name)
            else:
                self.run_monetag(zone, name)
            if self.fail_streak >= 3:
                self.log("Dừng: 3 lỗi liên tiếp")
                break
            time.sleep(8)

# Hàm chính được gọi từ main_gui.py
async def run(session_files, log_callback=print):
    log_callback("[NotBux] Bắt đầu...")
    for sfile in session_files:
        log_callback(f"[NotBux] Đang xử lý {sfile}")
        data = await get_init_data(sfile)
        if not data:
            log_callback(f"[NotBux] Lỗi session {sfile}")
            continue
        init_data, first_name, tg_id = data
        cfg = parse_config(init_data, first_name, tg_id)
        if not cfg:
            log_callback(f"[NotBux] Parse lỗi {sfile}")
            continue
        bot = NotBuxBot(cfg, log_callback)
        bal = bot.get_balance()
        log_callback(f"[NotBux] {cfg['name']} | Dư: {bal if bal else '??'}")
        if bal is None:
            continue
        bot.run_all()
        time.sleep(5)
    log_callback("[NotBux] Hoàn tất.")

import asyncio
import random
import urllib.parse
import base64
import requests
from urllib.parse import parse_qs

def parse_gui_data(raw_data):
    if "tgWebAppData=" in raw_data:
        clean_q = raw_data.split("tgWebAppData=")[1].split("&tgWebAppVersion")[0]
    else:
        clean_q = raw_data

    decoded = urllib.parse.unquote(clean_q)
    parsed = parse_qs(decoded)
    user_json = parsed.get('user', [''])[0]
    
    try:
        import json
        user_data = json.loads(user_json)
        return {
            'clean_q': clean_q,
            'uid': str(user_data.get('id', '')),
            'signature': parsed.get('signature', [''])[0],
            'raw_hash': parsed.get('hash', [''])[0],
            'data_check_string': base64.b64encode(f"auth_date={parsed.get('auth_date', [''])[0]}\nquery_id={parsed.get('query_id', [''])[0]}\nuser={user_json}".encode()).decode(),
            'name': user_data.get('first_name', 'User')
        }
    except:
        return None

class NotBuxBot:
    def __init__(self, cfg):
        self.cfg = cfg
        self.auth = f"tma {cfg['clean_q']}"
        self.headers = {
            'User-Agent': 'Mozilla/5.0 (iPhone; CPU iPhone OS 17_7 like Mac OS X) AppleWebKit/605.1.15 (KHTML, like Gecko) Version/18.0 Mobile/15E148 Safari/604.1',
            'Accept': '*/*', 'Origin': 'https://notbux.click', 'Referer': 'https://notbux.click/'
        }
        self.session = requests.Session()
        self.fail_streak = 0

    def get_balance(self):
        try:
            resp = self.session.get('https://notbux.click/api/me', headers={**self.headers, "Authorization": self.auth}, timeout=10)
            return resp.json()['user']['balance_coins']
        except: 
            return None

    async def claim_daily_reward(self):
        try:
            resp = self.session.post('https://notbux.click/api/daily-rewards/claim', headers={**self.headers, "Authorization": self.auth}, timeout=10)
            data = resp.json()
            if resp.status_code == 200 or data.get('success'):
                print("   [Daily] -> Điểm danh thành công!")
            else:
                print(f"   [Daily] -> {data.get('message', 'Đã điểm danh trước đó.')}")
        except:
            print("   [Daily] -> Lỗi API Check-in")

    async def run_adsgram(self, block_id):
        bal_before = self.get_balance()
        params = {
            'envType': 'telegram', 'blockId': block_id, 'platform': 'Win32', 'language': 'en', 'top_domain': 'notbux.click',
            'signature': self.cfg['signature'], 'data_check_string': self.cfg['data_check_string'], 'sdk_version': '1.47.0',
            'tg_id': self.cfg['uid'], 'tg_platform': 'ios', 'tma_version': '8.0',
            'request_id': ''.join([str(random.randint(0, 9)) for _ in range(30)]), 'raw': self.cfg['raw_hash']
        }
        try:
            resp = self.session.get("https://api.adsgram.ai/adv", params=params, headers=self.headers)
            banners = resp.json().get('banners', [])
            if not banners: return False

            record = banners[0]['banner']['trackings'][0]['value'].split('record=')[1].split('&')[0]
            self.session.get("https://api.adsgram.ai/event", params={'record': record, 'type': 'Render', 'trackingtypeid': '13'})
            await asyncio.sleep(1)
            self.session.get("https://api.adsgram.ai/event", params={'record': record, 'type': 'Show', 'trackingtypeid': '0'})
            
            await asyncio.sleep(random.randint(22, 25))
            self.session.get("https://api.adsgram.ai/event", params={'record': record, 'type': 'Reward', 'trackingtypeid': '14'})
            await asyncio.sleep(2)
            
            if self.get_balance() > bal_before:
                self.fail_streak = 0
                return True
        except: 
            pass
        self.fail_streak += 1
        return False

    async def run_monetag(self, oaid, section):
        bal_before = self.get_balance()
        self.session.cookies.clear()
        m_params = {
            'excludes': '', 'oaid': oaid, 'ymid': f"{self.cfg['uid']}%7C{ 'tasks_ad_monetag' if section == 'TASK' else 'earn_ad_monetag' }", 
            'tgp': 'ios', 'os': 'windows', 'os_version': '10.0.0', 'browser_version': '148.0.7778.98', 'sw': '1366', 'sh': '768', 'btz': 'Asia/Calcutta', 'dmn': 'libtl.com', 'is_mobile': 'false', 'of': 'true'
        }
        try:
            r_ad = self.session.get(f"https://e8ys.com/500/10558478?{urllib.parse.urlencode(m_params)}", headers={**self.headers, 'Referer': f'https://notbux.click/{section.lower()}s'}, timeout=15)
            ad_data = r_ad.json()
            ruid, ads = ad_data.get('ruid'), ad_data.get('ads', [])
            if not ads or not ruid: return False

            self.session.get(ads[0].get('impression_url'), headers={**self.headers, 'Referer': f'https://notbux.click/{section.lower()}s'})
            self.session.get(ads[0].get('click'), headers={**self.headers, 'Referer': f'https://notbux.click/{section.lower()}s'})

            await asyncio.sleep(random.randint(35, 38) if section == "TASK" else random.randint(18, 21))
            self.session.get(f"https://e8ys.com/resolve?ruid={ruid}", headers={**self.headers, 'Referer': 'https://e8ys.com/500/10558478'})
            await asyncio.sleep(2)
            
            if self.get_balance() > bal_before:
                self.fail_streak = 0
                return True
        except: 
            pass
        self.fail_streak += 1
        return False

# --- HÀM ASYNC RUN THEO CHUẨN ĐA LUỒNG CỦA MAIN_GUI ---
async def run(web_app_data):
    if isinstance(web_app_data, list):
        if len(web_app_data) == 0: return
        web_app_data = web_app_data[0]

    cfg = parse_gui_data(web_app_data)
    if not cfg: return

    bot = NotBuxBot(cfg)
    balance_start = bot.get_balance()
    if balance_start is None:
        print(f"[*] Tài khoản: {cfg['name']} | Lỗi kết nối API")
        return

    print(f"[*] Tài khoản: {cfg['name']} | Số dư ban đầu: {balance_start}")
    
    # 1. Điểm danh hàng ngày
    await bot.claim_daily_reward()
    await asyncio.sleep(1)

    tasks = [
        ("ADSGRAM", "27091", "TASK"),
        ("ADSGRAM", "27092", "EARN"),
        ("MONETAG", "08032ccd9bd5477bf6690d2a3bcbaa55", "TASK"),
        ("MONETAG", "0082440db830411bf781bf4a72e32aca", "EARN")
    ]

    # 2. Xem quảng cáo (chạy ngầm hoàn toàn không print log thừa)
    for provider, zone, name in tasks:
        if provider == "ADSGRAM":
            await bot.run_adsgram(zone)
        else:
            await bot.run_monetag(zone, name)
            
        if bot.fail_streak >= 3:
            break
        await asyncio.sleep(2)

    # 3. Kết thúc in số dư tổng kết
    balance_end = bot.get_balance()
    print(f"   -> Hoàn thành | Số dư hiện tại: {balance_end if balance_end is not None else 'Lỗi kết nối'}")

import time
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

    def claim_daily_reward(self):
        try:
            resp = self.session.post('https://notbux.click/api/daily-rewards/claim', headers={**self.headers, "Authorization": self.auth}, timeout=10)
            data = resp.json()
            if resp.status_code == 200 or data.get('success'):
                print("   [Daily] -> Điểm danh thành công!")
            else:
                print(f"   [Daily] -> {data.get('message', 'Đã điểm danh trước đó.')}")
        except:
            print("   [Daily] -> Lỗi API Check-in")

    def run_adsgram(self, block_id):
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
            time.sleep(1)
            self.session.get("https://api.adsgram.ai/event", params={'record': record, 'type': 'Show', 'trackingtypeid': '0'})
            
            time.sleep(random.randint(22, 25))
            self.session.get("https://api.adsgram.ai/event", params={'record': record, 'type': 'Reward', 'trackingtypeid': '14'})
            time.sleep(2)
            
            if self.get_balance() > bal_before:
                self.fail_streak = 0
                return True
        except: 
            pass
        self.fail_streak += 1
        return False

    def run_monetag(self, oaid, section):
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

            time.sleep(random.randint(35, 38) if section == "TASK" else random.randint(18, 21))
            self.session.get(f"https://e8ys.com/resolve?ruid={ruid}", headers={**self.headers, 'Referer': 'https://e8ys.com/500/10558478'})
            time.sleep(2)
            
            if self.get_balance() > bal_before:
                self.fail_streak = 0
                return True
        except: 
            pass
        self.fail_streak += 1
        return False

# --- HÀM RUN() ĐỂ MAIN_GUI.PY CỦA REPO GỌI ĐƠN LẺ TỪNG ACCOUNT ---
def run(web_app_data):
    """
    Hàm chuẩn format adston/repo GUI. 
    Mỗi khi Thread của GUI chạy đến tài khoản nào, nó sẽ gọi hàm này và truyền web_app_data vào.
    """
    cfg = parse_gui_data(web_app_data)
    if not cfg:
        print("[X] Dữ liệu WebAppData không hợp lệ!")
        return

    bot = NotBuxBot(cfg)
    balance_start = bot.get_balance()
    if balance_start is None:
        print(f"[*] Tài khoản: {cfg['name']} | Không thể kết nối API Notbux")
        return

    print(f"[*] Tài khoản: {cfg['name']} | Số dư ban đầu: {balance_start}")
    
    # 1. Tự động xử lý điểm danh hàng ngày
    bot.claim_daily_reward()
    time.sleep(1)

    # Danh sách cấu hình mạng Ads quảng cáo cần cày
    tasks = [
        ("ADSGRAM", "27091", "TASK"),
        ("ADSGRAM", "27092", "EARN"),
        ("MONETAG", "08032ccd9bd5477bf6690d2a3bcbaa55", "TASK"),
        ("MONETAG", "0082440db830411bf781bf4a72e32aca", "EARN")
    ]

    # 2. Chạy chuỗi Ads ngầm hoàn toàn
    for provider, zone, name in tasks:
        if provider == "ADSGRAM":
            bot.run_adsgram(zone)
        else:
            bot.run_monetag(zone, name)
            
        if bot.fail_streak >= 3:
            break
        time.sleep(3) # Nghỉ ngắn giữa các mạng Ads

    # 3. Kết thúc in ra số dư tổng kết của tài khoản đó
    balance_end = bot.get_balance()
    print(f"   -> Hoàn thành nhiệm vụ | Số dư hiện tại: {balance_end if balance_end is not None else 'Lỗi kết nối'}")

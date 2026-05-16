import os
import sys
import time
import random
import asyncio
import urllib.parse
import base64
import requests
from datetime import datetime
from urllib.parse import parse_qs
from telethon import TelegramClient
from telethon.tl.functions.messages import RequestWebViewRequest

# --- ANSI COLORS (Đầy đủ tránh hoàn toàn lỗi NameError) ---
G = "\033[38;5;82m"    # Xanh lá
C = "\033[38;5;51m"    # Xanh dương sáng
Y = "\033[38;5;226m"   # Vàng
R = "\033[38;5;196m"   # Đỏ
W = "\033[38;5;255m"   # Trắng
RESET = "\033[0m"

# --- CẤU HÌNH HỆ THỐNG CHUNG ---
API_ID = 28752231 
API_HASH = 'ec1c1f2c30e2f1855c3edee7e348480b'
SESSION_DIR = "sessions"

if not os.path.exists(SESSION_DIR):
    os.makedirs(SESSION_DIR)

# --- THÀNH PHẦN 3: NOTBUX BOT LOGIC ---
BOT_USERNAME_NOTBUX = 'notbux_bot'
WEBAPP_URL_NOTBUX = "https://notbux.click/"

async def get_telegram_init_data_notbux(session_file):
    client = TelegramClient(os.path.join(SESSION_DIR, session_file), API_ID, API_HASH)
    await client.connect()
    if not await client.is_user_authorized():
        await client.disconnect()
        return None
    try:
        me = await client.get_me()
        bot_entity = await client.get_input_entity(BOT_USERNAME_NOTBUX)
        res = await client(RequestWebViewRequest(
            peer=bot_entity, bot=bot_entity, platform='android', from_bot_menu=False, url=WEBAPP_URL_NOTBUX
        ))
        auth_data = urllib.parse.unquote(res.url.split('tgWebAppData=')[1].split('&tgWebAppVersion')[0])
        await client.disconnect()
        return auth_data, me.first_name, me.id
    except:
        await client.disconnect()
        return None

def parse_auth_to_config_notbux(clean_q, first_name, tg_id):
    try:
        decoded = urllib.parse.unquote(clean_q)
        parsed = parse_qs(decoded)
        user_json = parsed.get('user', [''])[0]
        auth_date = parsed.get('auth_date', [''])[0]
        query_id = parsed.get('query_id', [''])[0]
        
        check_str = f"auth_date={auth_date}\nquery_id={query_id}\nuser={user_json}"
        encoded_check = base64.b64encode(check_str.encode()).decode()

        return {
            'clean_q': clean_q,
            'uid': str(tg_id),
            'signature': parsed.get('signature', [''])[0],
            'raw_hash': parsed.get('hash', [''])[0],
            'data_check_string': encoded_check,
            'name': first_name
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

    def log(self, tag, msg, color=W):
        now = datetime.now().strftime("%H:%M:%S")
        print(f"[{now}] {color}[{tag}]{RESET} {msg}")

    def get_balance(self):
        h = {**self.headers, "Authorization": self.auth}
        try:
            resp = self.session.get('https://notbux.click/api/me', headers=h, timeout=10)
            return resp.json()['user']['balance_coins']
        except: 
            return None

    def run_adsgram(self, block_id, section_name):
        self.log(f"ADSGRAM:{section_name}", "Đang lấy quảng cáo...", C)
        bal_before = self.get_balance()
        
        params = {
            'envType': 'telegram', 'blockId': block_id, 'platform': 'Win32',
            'language': 'en', 'top_domain': 'notbux.click', 'signature': self.cfg['signature'],
            'data_check_string': self.cfg['data_check_string'], 'sdk_version': '1.47.0',
            'tg_id': self.cfg['uid'], 'tg_platform': 'ios', 'tma_version': '8.0',
            'request_id': ''.join([str(random.randint(0, 9)) for _ in range(30)]), 'raw': self.cfg['raw_hash']
        }

        try:
            resp = self.session.get("https://api.adsgram.ai/adv", params=params, headers=self.headers)
            banners = resp.json().get('banners', [])
            if not banners:
                self.log("EMPTY", "Không tìm thấy quảng cáo.", Y)
                return False

            record = banners[0]['banner']['trackings'][0]['value'].split('record=')[1].split('&')[0]
            self.session.get("https://api.adsgram.ai/event", params={'record': record, 'type': 'Render', 'trackingtypeid': '13'})
            time.sleep(2)
            self.session.get("https://api.adsgram.ai/event", params={'record': record, 'type': 'Show', 'trackingtypeid': '0'})

            wait = random.randint(22, 28)
            self.log("WATCH", f"Đang xem quảng cáo ({wait}s)...", Y)
            time.sleep(wait)

            self.session.get("https://api.adsgram.ai/event", params={'record': record, 'type': 'Reward', 'trackingtypeid': '14'})
            time.sleep(3)
            
            bal_after = self.get_balance()
            if bal_after and bal_before and bal_after > bal_before:
                self.log("SUCCESS", f"Cộng tiền thành công! Số dư: {G}{bal_after}{RESET}", G)
                self.fail_streak = 0
                return True
        except: 
            pass
        self.fail_streak += 1
        return False

    def run_monetag(self, oaid, section):
        self.log(f"MONETAG:{section}", "Đang lấy quảng cáo...", C)
        self.session.cookies.clear()
        bal_before = self.get_balance()

        suffix = "tasks_ad_monetag" if section == "TASK" else "earn_ad_monetag"
        ymid = f"{self.cfg['uid']}%7C{suffix}"
        
        m_params = {
            'excludes': '', 'oaid': oaid, 'ymid': ymid, 'tgp': 'ios', 'os': 'windows',
            'os_version': '10.0.0', 'browser_version': '148.0.7778.98', 'sw': '1366',
            'sh': '768', 'btz': 'Asia/Calcutta', 'dmn': 'libtl.com', 'is_mobile': 'false', 'of': 'true'
        }
        
        m_url = f"https://e8ys.com/500/10558478?{urllib.parse.urlencode(m_params)}"
        ref = f'https://notbux.click/{section.lower()}s' if section == "TASK" else 'https://notbux.click/earn'
        curr_headers = {**self.headers, 'Referer': ref}

        try:
            r_ad = self.session.get(m_url, headers=curr_headers, timeout=15)
            ad_data = r_ad.json()
            ruid, ads = ad_data.get('ruid'), ad_data.get('ads', [])

            if not ads or not ruid: 
                return False

            self.session.get(ads[0].get('impression_url'), headers=curr_headers)
            self.session.get(ads[0].get('click'), headers=curr_headers)

            wait = random.randint(35, 40) if section == "TASK" else random.randint(18, 22)
            self.log("WATCH", f"Đang xem quảng cáo ({wait}s)...", Y)
            time.sleep(wait)

            self.session.get(f"https://e8ys.com/resolve?ruid={ruid}", headers={**curr_headers, 'Referer': 'https://e8ys.com/500/10558478'})
            time.sleep(3)
            
            bal_after = self.get_balance()
            if bal_after and bal_before and bal_after > bal_before:
                self.log("SUCCESS", f"Cộng tiền thành công! Số dư: {G}{bal_after}{RESET}", G)
                self.fail_streak = 0
                return True
        except: 
            pass
        self.fail_streak += 1
        return False

async def run_notbux_bot_logic():
    os.system('clear' if os.name == 'posix' else 'cls')
    print(f"{G}=== NOTBUX AUTO AD-BOT (INTEGRATED & LOOP) ==={RESET}")

    tasks = [
        ("ADSGRAM", "27091", "TASK"),
        ("ADSGRAM", "27092", "EARN"),
        ("MONETAG", "08032ccd9bd5477bf6690d2a3bcbaa55", "TASK"),
        ("MONETAG", "0082440db830411bf781bf4a72e32aca", "EARN")
    ]

    # VÒNG LẶP VÔ TẬN KHÔNG BAO GIỜ DỪNG
    while True:
        session_files = [f for f in os.listdir(SESSION_DIR) if f.endswith('.session')]
        
        if not session_files:
            print(f"{Y}[!] Thư mục 'sessions' trống. Đang chờ quét lại...{RESET}")
            await asyncio.sleep(10)
            continue

        print(f"{G}[+] Bắt đầu chu kỳ mới với {len(session_files)} tài khoản.{RESET}")
        
        for idx, s_file in enumerate(session_files, start=1):
            print(f"\n{G}------------------------------------------------------------{RESET}")
            print(f"{G}[ Tài khoản {idx}/{len(session_files)} ] File: {W}{s_file}{RESET}")
            print(f"{G}------------------------------------------------------------{RESET}")
            
            data = await get_telegram_init_data_notbux(s_file)
            if not data:
                print(f"{R}[X] Lỗi session hoặc bị log out khỏi phiên: {s_file}{RESET}")
                continue

            init_data, first_name, tg_id = data
            cfg = parse_auth_to_config_notbux(init_data, first_name, tg_id)
            if not cfg:
                print(f"{R}[X] Lỗi mã hóa token Telegram.{RESET}")
                continue

            bot = NotBuxBot(cfg)
            balance = bot.get_balance()
            print(f"[+] Tên: {W}{cfg['name']}{RESET} | Số dư: {G}{balance if balance is not None else 'Lỗi API'}{RESET}\n")
            
            if balance is None:
                continue

            for provider, zone, name in tasks:
                print(f">> Chạy mạng: {Y}{provider} ({name}){RESET}")
                if provider == "ADSGRAM":
                    bot.run_adsgram(zone, name)
                else:
                    bot.run_monetag(zone, name)

                if bot.fail_streak >= 3:
                    print(f"{R}[!] Gặp 3 lỗi liên tiếp (Hết quảng cáo/Đạt giới hạn). Chuyển tài khoản.{RESET}")
                    break

                time.sleep(8)

        # Kết thúc một lượt quét danh sách, chờ 5 phút rồi lặp lại vĩnh viễn
        wait_seconds = 300
        print(f"\n{G}>>> HOÀN THÀNH TẤT CẢ ACC.{Y} Đang nghỉ {wait_seconds} giây trước khi lặp lại chu kỳ mới...{RESET}")
        for i in range(wait_seconds, 0, -1):
            sys.stdout.write(f"\r{Y}[!] Vòng lặp tiếp tục sau: {i}s...{RESET}")
            sys.stdout.flush()
            await asyncio.sleep(1)
        print("\n")


# --- GIAO DIỆN TRUNG TÂM (MAIN GUI CONTROLLER) ---
def display_menu():
    os.system('clear' if os.name == 'posix' else 'cls')
    print(f"{C}===================================================={RESET}")
    print(f"{C}          FARM TELEGRAM CENTRAL CONTROLLER          {RESET}")
    print(f"{C}===================================================={RESET}")
    print(f"{G}1.{W} Chạy tool Egg Tapper Pro{RESET}")
    print(f"{G}2.{W} Chạy tool ShardsEarn Bot{RESET}")
    print(f"{G}3.{W} Chạy tool NotBux Auto Ad-Bot (Vòng lặp vô tận){RESET}")
    print(f"{R}0.{W} Thoát hệ thống{RESET}")
    print(f"{C}----------------------------------------------------{RESET}")

async def main():
    while True:
        display_menu()
        choice = input(f"{Y}[?] Nhập lựa chọn của bạn (0-3): {RESET}").strip()
        
        if choice == "1":
            print(f"\n{G}[*] Đang khởi động Egg Tapper Pro...{RESET}")
            time.sleep(1)
            # Khởi chạy hàm logic của Egg Tapper tại đây nếu bạn gộp chung
            break
        elif choice == "2":
            print(f"\n{G}[*] Đang khởi động ShardsEarn Bot...{RESET}")
            time.sleep(1)
            # Khởi chạy hàm logic của ShardsEarn tại đây nếu bạn gộp chung
            break
        elif choice == "3":
            print(f"\n{G}[*] Đang khởi động NotBux Bot với vòng lặp vô tận...{RESET}")
            time.sleep(1)
            await run_notbux_bot_logic()
            break
        elif choice == "0":
            print(f"\n{R}[!] Đang thoát hệ thống.{RESET}")
            sys.exit()
        else:
            print(f"\n{R}[X] Lựa chọn không hợp lệ! Vui lòng thử lại.{RESET}")
            time.sleep(1.5)

if __name__ == "__main__":
    try:
        asyncio.run(main())
    except KeyboardInterrupt:
        print(f"\n{R}[!] Đã đóng trình điều khiển trung tâm.{RESET}")
        sys.exit()

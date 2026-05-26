# tools/crypto_claim_bot.py
# Hỗ trợ: LitecoinGeneratorBot, DigibyteGeneratorBot, DogecoinGeneratorBot
# Cùng 1 tool, chỉ khác API URL và bot username

import os
import time
import random
import asyncio
import urllib.parse
import json
import re
import math
import requests
from datetime import datetime
from telethon import TelegramClient
from telethon.tl.functions.messages import RequestWebViewRequest
from concurrent.futures import ThreadPoolExecutor, as_completed

# ====================== CONFIG ======================
API_ID = globals().get('API_ID', 28752231)
API_HASH = globals().get('API_HASH', 'ec1c1f2c30e2f1855c3edee7e348480b')
SESSION_DIR = "sessions"

# Config coins
COINS_CONFIG = {
    "ltc": {
        "name": "Litecoin",
        "bot_username": "LitecoinGeneratorBot",
        "webapp_url": "https://claimltc.net/",
        "api_url": "https://claimltc.net/api",
        "enabled": True
    },
    "dgb": {
        "name": "Digibyte",
        "bot_username": "DigibyteGeneratorBot",
        "webapp_url": "https://claimdgb.net/",
        "api_url": "https://claimdgb.net/api",
        "enabled": True
    },
    "doge": {
        "name": "Dogecoin",
        "bot_username": "DogecoinGeneratorBot",
        "webapp_url": "https://claimdoge.net/",
        "api_url": "https://claimdoge.net/api",
        "enabled": True
    }
}

def log_msg(message: str, color: str = "white"):
    ts = datetime.now().strftime("%H:%M:%S")
    colors = {
        "green": "\033[92m",
        "red": "\033[91m",
        "yellow": "\033[93m",
        "cyan": "\033[96m",
        "magenta": "\033[95m",
        "white": "\033[0m"
    }
    print(f"{colors.get(color, '')}[{ts}] {message}\033[0m")

# ====================== GET INIT DATA ======================
async def get_init_data(session_file, bot_username, webapp_url):
    """Lấy initData từ Telegram qua Telethon"""
    full_path = os.path.join(SESSION_DIR, session_file)
    client = TelegramClient(full_path, API_ID, API_HASH)
    await client.connect()
    
    if not await client.is_user_authorized():
        await client.disconnect()
        return None
    
    try:
        me = await client.get_me()
        bot_entity = await client.get_input_entity(bot_username)
        res = await client(RequestWebViewRequest(
            peer=bot_entity,
            bot=bot_entity,
            platform='android',
            from_bot_menu=False,
            url=webapp_url
        ))
        
        parsed = urllib.parse.urlparse(res.url)
        init_data = urllib.parse.parse_qs(parsed.query).get('tgWebAppData', [None])[0]
        if not init_data:
            init_data = urllib.parse.unquote(res.url.split('tgWebAppData=')[1].split('&')[0])
        
        await client.disconnect()
        return init_data, me.first_name, me.id
    except Exception as e:
        await client.disconnect()
        return None

# ====================== CRYPTO CLAIM BOT CLASS ======================
class CryptoClaimBot:
    def __init__(self, session_file, coin_key, coin_config, log_func=log_msg):
        self.session_file = session_file
        self.coin_key = coin_key
        self.coin_name = coin_config['name']
        self.bot_username = coin_config['bot_username']
        self.webapp_url = coin_config['webapp_url']
        self.api_url = coin_config['api_url']
        
        self.name = f"{session_file.replace('.session', '')}_{coin_key.upper()}"
        self.log = log_func
        self.init_data = None
        self.session = requests.Session()
        
        self.headers = {
            "accept": "*/*",
            "content-type": "application/json",
            "origin": self.api_url,
            "referer": f"{self.api_url}/",
            "user-agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36",
            "x-requested-with": "TelegramWebApp"
        }
    
    def fetch_init_data(self):
        """Lấy initData từ Telegram"""
        try:
            loop = asyncio.new_event_loop()
            asyncio.set_event_loop(loop)
            result = loop.run_until_complete(get_init_data(
                self.session_file,
                self.bot_username,
                self.webapp_url
            ))
            loop.close()
            
            if not result:
                self.log(f"[{self.name}] ❌ Không lấy được initData", "red")
                return False
            
            self.init_data, name, tg_id = result
            self.log(f"[{self.name}] ✅ Lấy initData: {name}", "green")
            return True
        except Exception as e:
            self.log(f"[{self.name}] ❌ Lỗi fetch initData: {e}", "red")
            return False
    
    def call_api(self, action, extra=None):
        """Call API chung cho tất cả coins"""
        ts = int(time.time() * 1000)
        payload = {
            "action": action,
            "initData": self.init_data,
            "timestamp": ts,
            "requestId": f"{ts}-{random.randint(1000,9999)}",
            "client_attestation": {
                "session_id": "368635a667d33334465b0a019fbfa041",
                "telegram": {"available": True, "platform": "android", "version": "8.0", "color_scheme": "light", "user_present": True},
                "navigator": {"webdriver": False, "platform": "Win32", "vendor": "Google Inc."},
                "screen": {"width": 1366, "height": 768},
                "timezone": "Asia/Calcutta"
            }
        }
        if extra:
            payload.update(extra)
        
        try:
            r = requests.post(self.api_url, headers=self.headers, json=payload, timeout=20)
            return r.json()
        except:
            return None
    
    def claim_daily_bonus(self):
        """Claim daily bonus (x2)"""
        self.log(f"[{self.name}] 💰 Bonus...", "cyan")
        
        try:
            p_init = self.call_api("action_proof_init", {
                "targetAction": "claim_daily_bonus",
                "doubled": True,
                "captcha": "",
                "captcha_provider": "internal"
            })
            if not p_init or "challenge_id" not in p_init:
                self.log(f"[{self.name}] ❌ Bonus Init Fail", "red")
                return False
            
            time.sleep(p_init.get("min_wait_seconds", 2) + random.uniform(1, 2))
            
            p_comp = self.call_api("action_proof_complete", {
                "targetAction": "claim_daily_bonus",
                "challengeId": p_init.get("challenge_id"),
                "doubled": True,
                "captcha": "",
                "captcha_provider": "internal"
            })
            if not p_comp or "proof_token" not in p_comp:
                self.log(f"[{self.name}] ❌ Bonus Proof Fail", "red")
                return False
            
            claim = self.call_api("claim_daily_bonus", {
                "action_proof": p_comp.get("proof_token"),
                "doubled": True
            })
            
            if claim and claim.get("status") == "success":
                reward = claim.get("reward", 0)
                bal = claim.get("new_balance", "?")
                self.log(f"[{self.name}] ✅ Bonus +{reward} (Bal: {bal})", "green")
                return True
            
            self.log(f"[{self.name}] ❌ Bonus Claim Fail", "red")
            return False
            
        except Exception as e:
            self.log(f"[{self.name}] ❌ Bonus Err: {str(e)}", "red")
            return False
    
    def claim_faucet(self):
        """Claim faucet (x2)"""
        self.log(f"[{self.name}] 🚰 Faucet...", "cyan")
        
        try:
            p_init = self.call_api("action_proof_init", {
                "targetAction": "claim_faucet",
                "doubled": True,
                "captcha": "",
                "captcha_provider": "internal"
            })
            
            if not p_init or "challenge_id" not in p_init:
                msg = p_init.get("message", "Fail") if p_init else "No response"
                self.log(f"[{self.name}] ⏳ Faucet: {msg}", "yellow")
                return False
            
            time.sleep(p_init.get("min_wait_seconds", 2) + random.uniform(1, 2))
            
            p_comp = self.call_api("action_proof_complete", {
                "targetAction": "claim_faucet",
                "challengeId": p_init.get("challenge_id"),
                "doubled": True,
                "captcha": "",
                "captcha_provider": "internal"
            })
            
            if not p_comp or "proof_token" not in p_comp:
                self.log(f"[{self.name}] ❌ Faucet Proof Fail", "red")
                return False
            
            claim = self.call_api("claim_faucet", {
                "action_proof": p_comp.get("proof_token"),
                "doubled": True
            })
            
            if claim and claim.get("status") == "success":
                reward = claim.get("reward", 0)
                bal = claim.get("new_balance", "?")
                self.log(f"[{self.name}] ✅ Faucet +{reward} (Bal: {bal})", "green")
                return True
            
            self.log(f"[{self.name}] ❌ Faucet Claim Fail", "red")
            return False
            
        except Exception as e:
            self.log(f"[{self.name}] ❌ Faucet Err: {str(e)}", "red")
            return False

    def farm_daily_ads(self, max_ads=7):
        """Farm daily ads (7 videos)"""
        self.log(f"[{self.name}] 🎬 Ads ({max_ads})...", "cyan")
        ok = 0
        
        try:
            for i in range(1, max_ads + 1):
                p_init = self.call_api("action_proof_init", {
                    "targetAction": "claim_rewarded_video_task",
                    "captcha": "",
                    "captcha_provider": "internal"
                })
                
                if not p_init or "challenge_id" not in p_init:
                    break
                
                time.sleep(p_init.get("min_wait_seconds", 2) + random.uniform(1, 2))
                
                p_comp = self.call_api("action_proof_complete", {
                    "targetAction": "claim_rewarded_video_task",
                    "challengeId": p_init.get("challenge_id"),
                    "captcha": "",
                    "captcha_provider": "internal"
                })
                
                if not p_comp or "proof_token" not in p_comp:
                    break
                
                claim = self.call_api("claim_rewarded_video_task", {
                    "action_proof": p_comp.get("proof_token")
                })
                
                if claim and claim.get("status") == "success":
                    ok += 1
                    reward = claim.get("reward", 0)
                    self.log(f"[{self.name}] ✅ Ad {i} +{reward}", "green")
                else:
                    break
                
                if i < max_ads:
                    time.sleep(random.randint(30, 60))
            
            self.log(f"[{self.name}] 📺 Ads done: {ok}/{max_ads}", "green")
            return ok > 0
            
        except Exception as e:
            self.log(f"[{self.name}] ❌ Ads Err: {str(e)}", "red")
            return False
            return False
    
    def generate_trajectory(self, target_x):
        traj = []
        cur_x, cur_t = 0, int(time.time()*1000)-2000+random.randint(150,300)
        steps = random.randint(12,18)
        for i in range(steps):
            prog = (i+1)/steps
            cur_x = target_x * (math.sin((prog*math.pi)/2)) + random.uniform(-1.5,1.5)
            cur_t += random.randint(80,160)
            traj.append({"x": round(max(0,cur_x),2), "t": cur_t})
        cur_t += random.randint(50,100)
        traj.append({"x": target_x, "t": cur_t})
        return traj

    def solve_captcha(self):
        c_init = self.call_api("captcha_init", {"context":"mines"})
        if not c_init or "session" not in c_init: return None
        sess = c_init['session']['sessionId']
        time.sleep(random.uniform(3,4.5))
        svg = c_init['session']['step1']['puzzleSvg']
        target = float(re.search(r"translate\(([\d.]+),", svg).group(1))
        slide = self.call_api("captcha_verify_slide", {"sessionId":sess, "x":target, "trajectory":self.generate_trajectory(target)})
        if not slide or not slide.get("success"): return None
        time.sleep(random.uniform(2.5,4))
        grid = c_init['session']['step2']['grid']
        targets = c_init['session']['step2']['targets']
        icon_map = {item['icon']:item['id'] for item in grid}
        selected = [icon_map[t] for t in targets]
        pattern = self.call_api("captcha_verify_pattern", {"sessionId":sess, "selectedIds":selected})
        token = pattern.get("token") if pattern else None
        if not token: return None
        p_init = self.call_api("action_proof_init", {"targetAction":"mines_cashout","captcha":token,"captcha_provider":"internal"})
        if not p_init: return None
        time.sleep(p_init.get("min_wait_seconds",2)+1.5)
        p_comp = self.call_api("action_proof_complete", {"targetAction":"mines_cashout","challengeId":p_init['challenge_id'],"captcha":token,"captcha_provider":"internal"})
        if not p_comp: return None
        return {"token":token, "proof":p_comp.get("proof_token")}

    def play_mines_round(self):
        u = self.call_api("get_user_data", {})
        s = self.call_api("mines_get_stats", {})
        if not u or not s: return False
        stats = s.get("stats",{})
        lives = int(stats.get("game_lives",0))
        if lives <= 0 and not stats.get("has_active_game"):
            wait = stats.get("seconds_until_next_life",0)
            if wait>0: time.sleep(min(wait+5,60))
            return False
        if not stats.get("has_active_game"):
            start = self.call_api("mines_start_game", {"difficulty":"expert"})
            if not start or start.get("status")!="success": return False
            stats = self.call_api("mines_get_stats", {}).get("stats",{})
        try:
            grid = json.loads(stats['active_grid_state'])
            bombs = grid.get('bombs',[])
            revealed = grid.get('revealed',[])
            safe = [i for i in range(25) if i not in bombs and i not in revealed]
        except: return False
        if safe:
            for tile in safe:
                time.sleep(random.uniform(0.8,1.4))
                res = self.call_api("mines_open_tile", {"tile_index":tile})
                if not res or res.get("status")!="success": break
        cap = self.solve_captcha()
        if cap:
            cash = self.call_api("mines_cashout", {"captcha":cap['token'], "captcha_provider":"internal", "action_proof":cap['proof']})
            if cash and cash.get("status")=="success":
                self.log(f"[{self.name}] ⛏️ Mines won! +{cash.get('result',{}).get('reward',0)}", "green")
                return True
        self.log(f"[{self.name}] ⛏️ Mines failed", "yellow")
        return False

    def farm_mines(self, rounds=6):
        for _ in range(rounds):
            if not self.play_mines_round(): break
            time.sleep(5)
    
    def claim_share_daily(self):
        """Claim share reward daily (5 networks)"""
        networks = ["facebook", "linkedin", "twitter", "whatsapp", "telegram"]
        self.log(f"[{self.name}] 📤 Claim share ({len(networks)} networks)...", "cyan")
        ok = 0
        
        for net in networks:
            p_init = self.call_api("action_proof_init", {
                "targetAction": "claim_share_reward", "network": net,
                "captcha": "", "captcha_provider": "internal"
            })
            if not p_init or "challenge_id" not in p_init:
                continue
            
            time.sleep(p_init.get("min_wait_seconds", 1) + random.uniform(0.5, 1))
            
            p_comp = self.call_api("action_proof_complete", {
                "targetAction": "claim_share_reward", "network": net,
                "challengeId": p_init['challenge_id'],
                "captcha": "", "captcha_provider": "internal"
            })
            if not p_comp or "proof_token" not in p_comp:
                continue
            
            claim = self.call_api("claim_share_reward", {
                "network": net, "action_proof": p_comp['proof_token']
            })
            
            if claim and claim.get("status") == "success":
                ok += 1
                reward = claim.get("claimed_amount", 0)
                self.log(f"[{self.name}] ✅ Share {net} +{reward}", "green")
            time.sleep(1)
        
        if ok > 0:
            self.log(f"[{self.name}] 📤 Share done: {ok}/{len(networks)}", "green")
    
    def run(self):
        """Luồng chính (chạy 24/7, mine mỗi tiếng)"""
        if not self.fetch_init_data():
            return
        
        self.log(f"[{self.name}] 🚀 Bắt đầu farming {self.coin_name}...", "cyan")
        
        # === PHASE 1: Daily tasks (chạy 1 lần) ===
        if not self.claim_daily_bonus():
            self.log(f"[{self.name}] ⚠️ Skip bonus (lỗi/đã claim)", "yellow")
        time.sleep(2)
        
        if not self.claim_faucet():
            self.log(f"[{self.name}] ⚠️ Skip faucet (lỗi/đã claim)", "yellow")
        time.sleep(2)
        
        self.claim_share_daily()
        time.sleep(2)
        
        if not self.farm_daily_ads(7):
            self.log(f"[{self.name}] ⚠️ Skip ads (hết lượt)", "yellow")
        time.sleep(3)
        
        # === PHASE 2: Mine loop (60 phút/lần) ===
        self.log(f"[{self.name}] ⛏️ Bắt đầu mine loop (mỗi 60 phút)...", "cyan")
        
        while True:
            self.farm_mines(rounds=6)
            self.log(f"[{self.name}] ⏳ Đợi 60 phút trước lần mine tiếp theo...", "yellow")
            time.sleep(3600)  # 60 phút

# ====================== PROCESS ACCOUNT ======================
def process_account(session_file, coin_key, coin_config, log_callback):
    """Xử lý từng tài khoản cho một coin"""
    try:
        bot = CryptoClaimBot(session_file, coin_key, coin_config, log_callback)
        bot.run()
    except Exception as e:
        log_callback(f"❌ Lỗi xử lý {session_file}_{coin_key}: {e}")

# ====================== ENTRY POINT ======================
async def run(session_files, log_callback=log_msg):
    """Entry point từ main_gui.py"""
    log_callback("[CryptoClaim] Bắt đầu farming tất cả coins...")
    
    # Tạo danh sách task cho tất cả session x tất cả coin
    all_tasks = []
    for session_file in session_files:
        for coin_key, coin_config in COINS_CONFIG.items():
            if coin_config['enabled']:
                all_tasks.append((session_file, coin_key, coin_config))
    
    log_callback(f"[CryptoClaim] Tổng cộng {len(all_tasks)} task ({len(session_files)} session x {len([c for c in COINS_CONFIG if COINS_CONFIG[c]['enabled']])} coins)")
    
    with ThreadPoolExecutor(max_workers=min(len(all_tasks), 10)) as executor:
        futures = [executor.submit(process_account, *task, log_callback) for task in all_tasks]
        for future in as_completed(futures):
            try:
                future.result()
            except Exception as e:
                log_callback(f"[CryptoClaim] Thread error: {e}")
    
    log_callback("[CryptoClaim] Hoàn tất!")

def main():
    """Standalone mode"""
    if not os.path.exists(SESSION_DIR):
        log_msg("❌ Sessions folder not found")
        return
    
    sessions = [f for f in os.listdir(SESSION_DIR) if f.endswith('.session')]
    if not sessions:
        log_msg("❌ No session files")
        return
    
    log_msg(f"[CryptoClaim] Chạy {len(sessions)} tài khoản x {len([c for c in COINS_CONFIG if COINS_CONFIG[c]['enabled']])} coins...", "cyan")
    asyncio.run(run(sessions))

if __name__ == "__main__":
    main()

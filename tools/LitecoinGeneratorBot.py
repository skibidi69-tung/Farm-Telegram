# tools/litecoin_bot.py
import os, time, random, asyncio, urllib.parse, json, re, math, requests
from telethon import TelegramClient
from telethon.tl.functions.messages import RequestWebViewRequest

API_ID = globals().get('API_ID', 28752231)
API_HASH = globals().get('API_HASH', 'ec1c1f2c30e2f1855c3edee7e348480b')
BOT_USERNAME = 'LitecoinGeneratorBot'
WEBAPP_URL = "https://claimltc.net/"
SESSION_DIR = "sessions"
API_URL = "https://claimltc.net/api"

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
    except:
        await client.disconnect()
        return None

def call_api(action, init_data, extra=None):
    ts = int(time.time()*1000)
    payload = {
        "action": action,
        "initData": init_data,
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
        r = requests.post(API_URL, headers={
            "accept": "*/*",
            "content-type": "application/json",
            "origin": "https://claimltc.net",
            "referer": "https://claimltc.net/",
            "user-agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36",
            "x-requested-with": "TelegramWebApp"
        }, json=payload, timeout=20)
        return r.json()
    except:
        return None

# ---------- CLAIM DAILY BONUS X2 ----------
def claim_daily_bonus(init_data, log):
    log("  Claiming daily bonus (x2)...")
    p_init = call_api("action_proof_init", init_data, {
        "targetAction": "claim_daily_bonus",
        "doubled": True,
        "captcha": "",
        "captcha_provider": "internal"
    })
    if not p_init or "challenge_id" not in p_init:
        log("  ❌ Daily bonus proof init failed")
        return False
    challenge_id = p_init['challenge_id']
    min_wait = p_init.get("min_wait_seconds", 2)
    time.sleep(min_wait + random.uniform(1, 2))

    p_comp = call_api("action_proof_complete", init_data, {
        "targetAction": "claim_daily_bonus",
        "challengeId": challenge_id,
        "doubled": True,
        "captcha": "",
        "captcha_provider": "internal"
    })
    if not p_comp or "proof_token" not in p_comp:
        log("  ❌ Daily bonus proof complete failed")
        return False
    proof_token = p_comp['proof_token']

    claim = call_api("claim_daily_bonus", init_data, {
        "action_proof": proof_token,
        "doubled": True
    })
    if claim and claim.get("status") == "success":
        reward = claim.get("reward", 0)
        new_balance = claim.get("new_balance", "?")
        log(f"  ✅ Daily bonus claimed! +{reward} LTC | New balance: {new_balance}")
        return True
    else:
        log(f"  ❌ Daily bonus claim failed: {claim}")
        return False

# ---------- CLAIM FAUCET X2 (cooldown 8h) ----------
def claim_faucet(init_data, log):
    log("  Claiming faucet (x2) - may have 8h cooldown...")
    p_init = call_api("action_proof_init", init_data, {
        "targetAction": "claim_faucet",
        "doubled": True,
        "captcha": "",
        "captcha_provider": "internal"
    })
    if not p_init:
        log("  ❌ Faucet proof init failed (no response)")
        return False
    if "challenge_id" not in p_init:
        # Có thể do cooldown hoặc lỗi
        error_msg = p_init.get("message", p_init.get("error", "Unknown error"))
        if "cooldown" in str(error_msg).lower() or "wait" in str(error_msg).lower():
            log(f"  ⏳ Faucet on cooldown (8h): {error_msg}")
        else:
            log(f"  ❌ Faucet proof init failed: {error_msg}")
        return False
    challenge_id = p_init['challenge_id']
    min_wait = p_init.get("min_wait_seconds", 2)
    time.sleep(min_wait + random.uniform(1, 2))

    p_comp = call_api("action_proof_complete", init_data, {
        "targetAction": "claim_faucet",
        "challengeId": challenge_id,
        "doubled": True,
        "captcha": "",
        "captcha_provider": "internal"
    })
    if not p_comp or "proof_token" not in p_comp:
        log("  ❌ Faucet proof complete failed")
        return False
    proof_token = p_comp['proof_token']

    claim = call_api("claim_faucet", init_data, {
        "action_proof": proof_token,
        "doubled": True
    })
    if claim and claim.get("status") == "success":
        reward = claim.get("reward", 0)
        new_balance = claim.get("new_balance", "?")
        log(f"  ✅ Faucet claimed! +{reward} LTC | New balance: {new_balance}")
        return True
    else:
        log(f"  ❌ Faucet claim failed: {claim}")
        return False

# ---------- DAILY ADS (7 videos) ----------
def farm_daily_ads(init_data, log, max_ads=7):
    ok = 0
    for i in range(1, max_ads+1):
        p_init = call_api("action_proof_init", init_data, {"targetAction":"claim_rewarded_video_task","captcha":"","captcha_provider":"internal"})
        if not p_init or "challenge_id" not in p_init: break
        time.sleep(p_init.get("min_wait_seconds",2)+random.uniform(1,2))
        p_comp = call_api("action_proof_complete", init_data, {"targetAction":"claim_rewarded_video_task","challengeId":p_init['challenge_id'],"captcha":"","captcha_provider":"internal"})
        if not p_comp or "proof_token" not in p_comp: break
        claim = call_api("claim_rewarded_video_task", init_data, {"action_proof":p_comp['proof_token']})
        if claim and claim.get("status")=="success":
            ok += 1
            log(f"    Daily ad {i}/{max_ads} +{claim.get('reward',0)}")
        else: break
        if i < max_ads: time.sleep(random.randint(30,60))
    log(f"  Daily ads done: {ok}/{max_ads}")

# ---------- MINES GAME ----------
def generate_trajectory(target_x):
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

def solve_captcha(init_data):
    c_init = call_api("captcha_init", init_data, {"context":"mines"})
    if not c_init or "session" not in c_init: return None
    sess = c_init['session']['sessionId']
    time.sleep(random.uniform(3,4.5))
    svg = c_init['session']['step1']['puzzleSvg']
    target = float(re.search(r"translate\(([\d.]+),", svg).group(1))
    slide = call_api("captcha_verify_slide", init_data, {"sessionId":sess, "x":target, "trajectory":generate_trajectory(target)})
    if not slide or not slide.get("success"): return None
    time.sleep(random.uniform(2.5,4))
    grid = c_init['session']['step2']['grid']
    targets = c_init['session']['step2']['targets']
    icon_map = {item['icon']:item['id'] for item in grid}
    selected = [icon_map[t] for t in targets]
    pattern = call_api("captcha_verify_pattern", init_data, {"sessionId":sess, "selectedIds":selected})
    token = pattern.get("token") if pattern else None
    if not token: return None
    p_init = call_api("action_proof_init", init_data, {"targetAction":"mines_cashout","captcha":token,"captcha_provider":"internal"})
    if not p_init: return None
    time.sleep(p_init.get("min_wait_seconds",2)+1.5)
    p_comp = call_api("action_proof_complete", init_data, {"targetAction":"mines_cashout","challengeId":p_init['challenge_id'],"captcha":token,"captcha_provider":"internal"})
    if not p_comp: return None
    return {"token":token, "proof":p_comp.get("proof_token")}

def play_mines_round(init_data, log):
    u = call_api("get_user_data", init_data)
    s = call_api("mines_get_stats", init_data)
    if not u or not s: return False
    stats = s.get("stats",{})
    lives = int(stats.get("game_lives",0))
    if lives <= 0 and not stats.get("has_active_game"):
        wait = stats.get("seconds_until_next_life",0)
        if wait>0: time.sleep(min(wait+5,60))
        return False
    if not stats.get("has_active_game"):
        start = call_api("mines_start_game", init_data, {"difficulty":"expert"})
        if not start or start.get("status")!="success": return False
        stats = call_api("mines_get_stats", init_data).get("stats",{})
    try:
        grid = json.loads(stats['active_grid_state'])
        bombs = grid.get('bombs',[])
        revealed = grid.get('revealed',[])
        safe = [i for i in range(25) if i not in bombs and i not in revealed]
    except: return False
    if safe:
        for tile in safe:
            time.sleep(random.uniform(0.8,1.4))
            res = call_api("mines_open_tile", init_data, {"tile_index":tile})
            if not res or res.get("status")!="success": break
    cap = solve_captcha(init_data)
    if cap:
        cash = call_api("mines_cashout", init_data, {"captcha":cap['token'], "captcha_provider":"internal", "action_proof":cap['proof']})
        if cash and cash.get("status")=="success":
            log(f"  Mines won! New balance: {cash['result']['new_balance']}")
            return True
    log("  Mines failed")
    return False

def mines_loop(init_data, log, rounds=3):
    for _ in range(rounds):
        if not play_mines_round(init_data, log): break
        time.sleep(5)

# ---------- MAIN ----------
async def run(session_files, log_callback=print):
    log_callback("[LTC] Start")
    for sfile in session_files:
        log_callback(f"[LTC] {sfile}")
        data = await get_init_data(sfile)
        if not data:
            log_callback("  No initData")
            continue
        init_data, name, _ = data
        user = call_api("get_user_data", init_data)
        if not user or "username" not in user:
            log_callback("  Invalid initData")
            continue
        bal = user.get("balance","0")
        log_callback(f"  {user['username']} | Bal: {bal}")
        claim_daily_bonus(init_data, log_callback)   # 24h cooldown
        claim_faucet(init_data, log_callback)        # 8h cooldown
        farm_daily_ads(init_data, log_callback)
        mines_loop(init_data, log_callback)
        time.sleep(5)
    log_callback("[LTC] Done")

def main():
    if not os.path.exists(SESSION_DIR):
        print("Missing sessions folder")
        return
    sessions = [f for f in os.listdir(SESSION_DIR) if f.endswith('.session')]
    if not sessions:
        print("No session files")
        return
    asyncio.run(run(sessions))

if __name__ == "__main__":
    main()

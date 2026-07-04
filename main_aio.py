import os, sys, threading, requests, asyncio, json, time, queue
from datetime import datetime
from telethon import TelegramClient
from telethon.tl.functions.messages import RequestWebViewRequest
from telethon.errors import SessionPasswordNeededError

API_ID = 28752231
API_HASH = 'ec1c1f2c30e2f1855c3edee7e348480b'
SESSION_DIR = "sessions"
TOOLS_RAW = {
    "EggsHatch": "https://raw.githubusercontent.com/skibidi69-tung/Farm-Telegram/main/tools/EggsHatchBot.py",
    "GeneratorBot": "https://raw.githubusercontent.com/skibidi69-tung/Farm-Telegram/main/tools/GeneratorBot.py",
    "atomicbux_bot": "https://raw.githubusercontent.com/skibidi69-tung/Farm-Telegram/refs/heads/main/tools/Atomicbux_bot.py",
    "StakeStars_Bot": "https://raw.githubusercontent.com/skibidi69-tung/Farm-Telegram/refs/heads/main/tools/Stakestars_bot.py",
    "ltcforge_bot": "https://raw.githubusercontent.com/skibidi69-tung/Farm-Telegram/refs/heads/main/tools/ltcforge_bot.py"
}
COLORS = {"green": "\033[92m", "red": "\033[91m", "yellow": "\033[93m", "cyan": "\033[96m", "magenta": "\033[95m", "white": "\033[0m"}

def log(msg, color="white"):
    ts = datetime.now().strftime("%H:%M:%S")
    print(f"{COLORS.get(color,'')}[{ts}] {msg}\033[0m")

def clear():
    os.system('cls' if os.name == 'nt' else 'clear')

def list_sessions():
    if not os.path.exists(SESSION_DIR): os.makedirs(SESSION_DIR)
    return [f for f in os.listdir(SESSION_DIR) if f.endswith('.session')]

def check_sessions():
    """Auto-check all sessions, remove expired/invalid ones"""
    log("🔄 Checking sessions...", "cyan")
    if not os.path.exists(SESSION_DIR): os.makedirs(SESSION_DIR)
    
    files = [f for f in os.listdir(SESSION_DIR) if f.endswith('.session')]
    removed = 0
    kept = 0
    
    for f in files:
        path = os.path.join(SESSION_DIR, f)
        try:
            client = TelegramClient(path, API_ID, API_HASH)
            client.connect()
            if client.is_user_authorized():
                me = client.get_me()
                log(f"   ✓ {f} ({me.first_name})", "green")
                kept += 1
            else:
                log(f"   ✗ {f} expired, removing...", "red")
                client.disconnect()
                os.remove(path)
                removed += 1
                continue
            client.disconnect()
        except Exception as e:
            log(f"   ✗ {f} error: {e}, removing...", "red")
            try:
                os.remove(path)
                removed += 1
            except: pass
    
    log(f"✅ Done: {kept} valid, {removed} removed", "green")
    return removed

def run_tool(name):
    url = TOOLS_RAW.get(name)
    if not url: return
    t = threading.Thread(target=exec_tool, args=(name, url), daemon=True)
    t.start()

def exec_tool(name, url):
    log(f"▶ {name}", "cyan")
    try:
        local = f"{name}.py"
        code = ""
        if os.path.exists(local):
            with open(local, "r", encoding="utf-8") as f: code = f.read()
            log(f"   File local: {local}", "green")
        else:
            r = requests.get(url+"?t="+str(int(time.time())), timeout=15)
            if r.status_code == 200: code = r.text
        if not code: return
        sf = [f for f in os.listdir(SESSION_DIR) if f.endswith('.session')]
        lg = {"__name__": "__main__", "log_to_gui": lambda m,c=None: log(m, "white"), "SESSION_DIR": SESSION_DIR, "session_files": sf}
        exec(code, lg)
        fn = lg.get("run")
        if fn:
            if asyncio.iscoroutinefunction(fn): asyncio.run(fn(sf))
            else: fn(sf)
        log(f"✓ {name} hoàn tất.", "green")
    except Exception as e:
        log(f"✗ {name} lỗi: {e}", "red")

def login_telegram():
    phone = input("📱 Phone (+...): ").strip().replace(" ", "")
    if not phone.startswith("+"): phone = "+" + phone
    sess = phone.replace("+", "")
    client = TelegramClient(os.path.join(SESSION_DIR, sess), API_ID, API_HASH)
    try:
        client.connect()
        if not client.is_user_authorized():
            client.send_code_request(phone)
            code = input("📨 OTP Code: ").strip()
            try:
                client.sign_in(phone=phone, code=code)
            except SessionPasswordNeededError:
                pwd = input("🔐 2FA Password: ")
                client.sign_in(password=pwd)
            me = client.get_me()
            log(f"✅ Login OK: {me.first_name}", "green")
        else:
            log(f"✅ {sess} already logged in.", "yellow")
        client.disconnect()
    except Exception as e:
        log(f"❌ Error: {e}", "red")

def menu():
    sessions = [f for f in os.listdir(SESSION_DIR) if f.endswith('.session')] if os.path.exists(SESSION_DIR) else []
    print()
    print(f"\033[95m═══════════════════════════════════\033[0m")
    print(f"\033[95m  C36 FARM - Termux/PC Edition\033[0m")
    print(f"\033[95m═══════════════════════════════════\033[0m")
    print(f"\033[94m[{len(sessions)}] Sessions\033[0m")
    print()
    print(f" \033[33m 1\033[0m. Login Telegram")
    print(f" \033[33m 2\033[0m. Run All Tools (ALL Sessions)")
    print(f" \033[33m 3\033[0m. List Sessions")
    print(f" \033[33m 4\033[0m. Clean Invalid Sessions")
    print(f" \033[33m 0\033[0m. Run Single Tool")
    print(f" \033[33m Q\033[0m. Quit")
    print()

def run_all():
    log("🚀 Running ALL tools on ALL sessions...", "cyan")
    for name in TOOLS_RAW:
        t = threading.Thread(target=exec_tool, args=(name, TOOLS_RAW[name]), daemon=True)
        t.start()
        time.sleep(1)

def run_single():
    names = list(TOOLS_RAW.keys())
    print("\n\033[95mSelect Tool:\033[0m")
    for i, name in enumerate(names):
        print(f" {i+1}. {name}")
    print(f" 0. Back")
    try:
        choice = int(input("> ").strip())
        if 1 <= choice <= len(names):
            run_tool(names[choice-1])
        elif choice == 0:
            return
    except: pass

def main():
    if not os.path.exists(SESSION_DIR): os.makedirs(SESSION_DIR)
    clear()
    log("🚀 C36 FARM initialized", "magenta")
    check_sessions()
    
    while True:
        clear()
        menu()
        cmd = input("> ").strip().lower()
        if cmd == 'q': break
        elif cmd == '1': login_telegram()
        elif cmd == '2': run_all()
        elif cmd == '3':
            clear()
            sf = [f for f in os.listdir(SESSION_DIR) if f.endswith('.session')]
            print(f"\033[94mSessions ({len(sf)}):\033[0m")
            for f in sf: 
                try:
                    client = TelegramClient(os.path.join(SESSION_DIR, f), API_ID, API_HASH)
                    client.connect()
                    status = "✓" if client.is_user_authorized() else "✗"
                    client.disconnect()
                except: status = "✗"
                print(f"   {status} {f}")
            input("\nPress Enter...")
        elif cmd == '4':
            check_sessions()
            input("Press Enter...")
        elif cmd == '0': run_single()
        else:
            input("Invalid command. Press Enter...")

if __name__ == "__main__":
    try:
        main()
    except KeyboardInterrupt:
        print("\n👋 Bye!")

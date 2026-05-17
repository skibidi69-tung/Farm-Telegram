import asyncio
from notbux_bot import run
import os

async def test():
    session_dir = "sessions"
    if not os.path.exists(session_dir):
        print(f"❌ Thư mục {session_dir} không tồn tại!")
        return
    sessions = [f for f in os.listdir(session_dir) if f.endswith('.session')]
    print(f"📁 Tìm thấy {len(sessions)} session: {sessions}")
    if not sessions:
        print("❌ Không có session nào. Hãy đăng nhập trước.")
        return
    await run(sessions, log_callback=print)

asyncio.run(test())

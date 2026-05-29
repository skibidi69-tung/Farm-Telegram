import webview, os, threading, requests, asyncio, time, json, queue, random
from datetime import datetime

API_ID = 28752231
API_HASH = 'ec1c1f2c30e2f1855c3edee7e348480b'
SESSION_DIR = "sessions"
TOOLS_RAW = {
    "ADS_TON_bot": "https://raw.githubusercontent.com/skibidi69-tung/Farm-Telegram/main/tools/ADS_TON_bot.py",
    "notbux_bot": "https://raw.githubusercontent.com/skibidi69-tung/Farm-Telegram/main/tools/notbux_bot.py",
    "EggsHatchBot": "https://raw.githubusercontent.com/skibidi69-tung/Farm-Telegram/main/tools/EggsHatchBot.py",
    "GeneratorBot": "https://raw.githubusercontent.com/skibidi69-tung/Farm-Telegram/main/tools/GeneratorBot.py",
    "FishVerseBot": "https://raw.githubusercontent.com/skibidi69-tung/Farm-Telegram/main/tools/FishVerseBot.py"
}
logq = queue.Queue()
def log(m): logq.put(f"[{datetime.now().strftime('%H:%M:%S')}] {m}")

HTML = """<!DOCTYPE html><html><head>
<meta charset="utf-8">
<style>
*{margin:0;padding:0;box-sizing:border-box;font-family:sans-serif;}
body{background:#0a0a0f;color:#ccc;padding:16px;height:100vh;overflow:hidden;}
#cv{position:fixed;top:0;left:0;width:100%;height:100%;pointer-events:none;z-index:0;}
.c{position:relative;z-index:1;height:100vh;display:flex;flex-direction:column;}
h1{color:#b388ff;font-size:16px;margin-bottom:8px;}
.r{display:flex;gap:10px;flex:1;min-height:0;}
.cl{flex:0 0 180px;display:flex;flex-direction:column;}
.cr{flex:1;display:flex;flex-direction:column;}
.bx{background:rgba(18,18,26,0.8);border-radius:8px;border:1px solid #222;padding:8px;flex:1;overflow-y:auto;margin-top:4px;}
.l{font-size:10px;color:#888;}
.it{padding:4px 6px;font-size:10px;border-bottom:1px solid rgba(255,255,255,0.04);display:flex;justify-content:space-between;}
.ti{padding:3px 6px;font-size:10px;cursor:pointer;border-radius:3px;}
.ti:hover{background:rgba(179,136,255,0.1);}
.ti .cb{display:inline-block;width:10px;height:10px;border:1.5px solid #555;border-radius:2px;margin-right:6px;text-align:center;line-height:10px;font-size:7px;color:#b388ff;}
.ti .cb.on{border-color:#b388ff;background:rgba(179,136,255,0.2);}
.btn{background:#7c4dff;color:white;border:none;border-radius:4px;padding:4px 10px;cursor:pointer;font-size:9px;}
.bt{background:#333;}
.bk{background:#5a1a3a;}
.lg{background:rgba(18,18,26,0.8);border-radius:8px;border:1px solid #222;padding:6px;font-size:9px;color:#666;overflow-y:auto;margin-top:4px;flex:0 0 70px;}
input{background:#12121a;border:1px solid #333;border-radius:4px;color:white;padding:5px;font-size:10px;width:100%;margin-bottom:4px;}
</style>
</head><body>
<canvas id="cv"></canvas>
<div class="c">
<h1>&#9670; C36</h1>
<div class="r">
<div class="cl">
<div class="l">Sessions <button class="btn" onclick="ls()">&#8635;</button> <button class="btn bt" onclick="sL()">+</button></div>
<div class="bx" id="sl"><div style="color:#555;font-size:9px;">Loading...</div></div>
</div>
<div class="cr">
<div class="l">Tools
<button class="btn" onclick="rSel()">&#9654; RUN</button>
<button class="btn" onclick="rAll()">&#9654; ALL</button>
<button class="btn bk" onclick="kAll()">&#9632; KILL</button>
</div>
<div class="bx" id="tl"><div style="color:#555;font-size:9px;">Loading...</div></div>
</div>
</div>
<div class="l" style="margin-top:2px;">Log</div>
<div class="lg" id="lb"></div>
<div id="lm" style="display:none;position:fixed;top:0;left:0;width:100%;height:100%;background:rgba(0,0,0,0.6);z-index:10;align-items:center;justify-content:center;">
<div style="background:#1a1a26;border-radius:10px;padding:20px;width:280px;border:1px solid #333;">
<h3 id="mt" style="color:#b388ff;font-size:13px;margin-bottom:8px;">Login</h3>
<input id="pi" placeholder="+84912345678">
<div id="cr" style="display:none;"><input id="ci" placeholder="Code" style="letter-spacing:3px;"></div>
<div id="msg" style="font-size:9px;color:#888;margin-bottom:6px;"></div>
<div style="display:flex;gap:4px;justify-content:flex-end;">
<button class="btn bt" onclick="cLm()">Cancel</button>
<button class="btn" id="lb2" onclick="dL()">Send Code</button>
</div></div></div>
<script>
(function(){
var c=document.getElementById('cv');
if(!c)return;
var cx=c.getContext('2d'),W,H,p=[],i,j;
function rz(){W=c.width=innerWidth;H=c.height=innerHeight;}
rz();window.onresize=rz;
for(i=0;i<100;i++)p.push({x:Math.random()*W,y:Math.random()*H,r:Math.random()*3+1,dx:(Math.random()-0.5)*0.5,dy:(Math.random()-0.5)*0.5,a:Math.random()*0.4+0.1});
var mx=W/2,my=H/2,tx=W/2,ty=H/2;
document.onmousemove=function(e){tx=e.clientX;ty=e.clientY;};
function dr(){
  mx+=(tx-mx)*0.08;my+=(ty-my)*0.08;
  cx.clearRect(0,0,W,H);
  var g=cx.createRadialGradient(mx,my,0,mx,my,250);
  g.addColorStop(0,'rgba(179,136,255,0.12)');g.addColorStop(0.5,'rgba(124,77,255,0.05)');g.addColorStop(1,'rgba(0,0,0,0)');
  cx.fillStyle=g;cx.fillRect(0,0,W,H);
  for(i=0;i<p.length;i++){
    p[i].x+=p[i].dx;p[i].y+=p[i].dy;
    if(p[i].x<0)p[i].x=W;if(p[i].x>W)p[i].x=0;
    if(p[i].y<0)p[i].y=H;if(p[i].y>H)p[i].y=0;
    var d=Math.hypot(p[i].x-mx,p[i].y-my);
    var a=p[i].a*(d<250?1+d/500:1-d/500);
    cx.beginPath();cx.arc(p[i].x,p[i].y,p[i].r,0,Math.PI*2);
    cx.fillStyle='rgba(179,136,255,'+Math.max(0.05,a)+')';cx.fill();
  }
  for(i=0;i<p.length;i++){
    var di=Math.hypot(p[i].x-mx,p[i].y-my);
    if(di>180)continue;
    for(j=i+1;j<p.length;j++){
      var d2=Math.hypot(p[i].x-p[j].x,p[i].y-p[j].y);
      if(d2<100){cx.beginPath();cx.moveTo(p[i].x,p[i].y);cx.lineTo(p[j].x,p[j].y);
        cx.strokeStyle='rgba(179,136,255,'+0.15*(1-d2/100)+')';cx.lineWidth=0.4;cx.stroke();}
    }
  }
  requestAnimationFrame(dr);
}
dr();
})();
var st=1;
function sL(){st=1;document.getElementById('mt').textContent='Login';document.getElementById('pi').value='';document.getElementById('cr').style.display='none';document.getElementById('lb2').textContent='Send Code';document.getElementById('msg').textContent='';document.getElementById('lm').style.display='flex';}
function cLm(){document.getElementById('lm').style.display='none';}
function dL(){
  var p=document.getElementById('pi').value.trim();
  if(st==1){
    if(!p.startsWith('+')){document.getElementById('msg').textContent='+ required';return;}
    document.getElementById('msg').textContent='Sending...';
    pywebview.api.login_step1(p).then(function(r){document.getElementById('msg').textContent=r.msg;if(r.ok){document.getElementById('cr').style.display='block';document.getElementById('lb2').textContent='Verify';st=2;}});
  }else{
    var c=document.getElementById('ci').value.trim();
    if(!c){document.getElementById('msg').textContent='Enter code';return;}
    document.getElementById('msg').textContent='Verifying...';
    pywebview.api.login_step2(p,c).then(function(r){document.getElementById('msg').textContent=r.msg;if(r.ok){setTimeout(function(){cLm();ls();},1000);}});
  }
}
function ls(){
  pywebview.api.get_sessions().then(function(s){var h='';for(var i=0;i<s.length;i++){h+='<div class=it><span>'+s[i].phone+'</span><b>'+s[i].status+'</b></div>';}document.getElementById('sl').innerHTML=h||'None';});
}
var sel={};
function lt(){
  pywebview.api.get_tools().then(function(t){var h='';for(var i=0;i<t.length;i++){h+='<div class=ti onclick="tg('+i+')"><span class=cb id=cb'+i+'></span>'+t[i].name+'</div>';}document.getElementById('tl').innerHTML=h;});
}
function tg(i){
  var e=document.getElementById('cb'+i);
  if(sel[i]){
    delete sel[i];
    e.className='cb';
    e.innerHTML='';
  }else{
    sel[i]=1;
    e.className='cb on';
    e.innerHTML='✓';
  }
}
function rSel(){
  var ids=Object.keys(sel);
  if(!ids.length)return;
  for(var k in sel){pywebview.api.run_tool(k);}
}
function rAll(){
  pywebview.api.get_tools().then(function(t){for(var i=0;i<t.length;i++){pywebview.api.run_tool(i);}});
}
function kAll(){pywebview.api.stop_all();}
setInterval(function(){
  pywebview.api.get_logs().then(function(l){
    if(l.length){document.getElementById('lb').innerHTML=l.slice(-100).map(function(x){return '<div style=padding:1px 0;>'+x+'</div>';}).join('');document.getElementById('lb').scrollTop=document.getElementById('lb').scrollHeight;}
  });
}, 800);
setTimeout(function(){ls();lt();setInterval(ls,5000);}, 400);
</script></body></html>"""

class Api:
    def __init__(self):
        self._client = None
        self.running = {}
        self.log_hist = []

    def get_sessions(self):
        if not os.path.exists(SESSION_DIR): os.makedirs(SESSION_DIR)
        r = []
        for f in sorted(os.listdir(SESSION_DIR)):
            if f.endswith(".session"):
                p = f.replace(".session", ""); d = ("+"+p) if not p.startswith("+") else p
                r.append({"phone": d, "status": "✓"})
        return r

    def get_tools(self):
        return [{"name": k} for k in TOOLS_RAW]

    def run_tool(self, idx):
        idx = int(idx)
        names = list(TOOLS_RAW.keys())
        if idx >= len(names): return False
        name = names[idx]
        log(f"▶ {name} khởi chạy...")
        t = threading.Thread(target=self._exec, args=(name, TOOLS_RAW[name]), daemon=True)
        self.running[name] = t; t.start()
        return True

    def _exec(self, name, url):
        try:
            # Ưu tiên file local
            local_file = f"{name}.py"
            code = ""
            if os.path.exists(local_file):
                with open(local_file, "r", encoding="utf-8") as f: code = f.read()
                log(f"◈ Local: {local_file}")
            else:
                r = requests.get(url+"?t="+str(int(time.time())), timeout=10)
                if r.status_code == 200: code = r.text
            
            if not code: return
            sf = [f for f in os.listdir(SESSION_DIR) if f.endswith('.session')]
            
            # Setup môi trường độc lập
            lg = dict(globals())
            lg.update({
                "__name__": "__main__", # Quan trọng đẻ chạy script entry point
                "log_to_gui": lambda m,c=None: log(m),
                "SESSION_DIR": SESSION_DIR,
                "session_files": sf
            })
            
            exec(code, lg)
            
            # Nếu script có hàm run thì gọi thủ công
            fn = lg.get("run")
            if fn:
                if asyncio.iscoroutinefunction(fn): asyncio.run(fn(sf))
                else: fn(sf)
                
            log(f"✓ {name} đã hoàn thành.")
        except Exception as e: log(f"Lỗi: {name} - {e}")
        finally: self.running.pop(name, None)

    def stop_all(self):
        os._exit(0)

    def get_logs(self):
        lines = []
        while not logq.empty(): lines.append(logq.get())
        if lines: self.log_hist.extend(lines)
        return self.log_hist[-100:]

    def login_step1(self, phone):
        try:
            from telethon import TelegramClient
            sess = phone.replace("+","").replace(" ","")
            self._client = TelegramClient(os.path.join(SESSION_DIR, sess), API_ID, API_HASH)
            loop = asyncio.new_event_loop(); asyncio.set_event_loop(loop)
            loop.run_until_complete(self._client.connect())
            loop.run_until_complete(self._client.send_code_request(phone))
            return {"ok": True, "msg": "Code sent"}
        except Exception as e: return {"ok": False, "msg": str(e)}

    def login_step2(self, phone, code):
        try:
            loop = asyncio.new_event_loop(); asyncio.set_event_loop(loop)
            loop.run_until_complete(self._client.sign_in(phone=phone, code=code))
            me = loop.run_until_complete(self._client.get_me())
            self._client.disconnect(); return {"ok": True, "msg": f"OK: {me.first_name}"}
        except Exception as e: return {"ok": False, "msg": str(e)}

if __name__ == "__main__":
    webview.create_window("C36", html=HTML, js_api=Api(), width=800, height=520)
    webview.start()

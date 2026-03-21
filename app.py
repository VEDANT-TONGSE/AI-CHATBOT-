import streamlit as st
import anthropic, time, re, json, os, urllib.request, urllib.error
from datetime import datetime, date

# ═══════════════════════════════════════════════════════
# PAGE CONFIG
# ═══════════════════════════════════════════════════════
st.set_page_config(
    page_title="NexusAI",
    page_icon="⬡",
    layout="wide",
    initial_sidebar_state="expanded",
)

# ═══════════════════════════════════════════════════════
# PROVIDER REGISTRY
# ═══════════════════════════════════════════════════════
ENV_MAP = {
    "anthropic":"ANTHROPIC_API_KEY","openai":"OPENAI_API_KEY",
    "gemini":"GOOGLE_API_KEY","groq":"GROQ_API_KEY",
    "mistral":"MISTRAL_API_KEY","cohere":"COHERE_API_KEY",
    "together":"TOGETHER_API_KEY","ollama":"",
}
PROVIDERS = {
    "anthropic":{"name":"Anthropic","icon":"⬡","color":"#E34234","no_key":False,
        "key_hint":"sk-ant-api03-…","docs":"https://console.anthropic.com",
        "models":{"claude-sonnet-4-20250514":"Claude Sonnet 4","claude-opus-4-20250514":"Claude Opus 4","claude-haiku-4-5":"Claude Haiku 4.5"}},
    "openai":{"name":"OpenAI","icon":"◈","color":"#10A37F","no_key":False,
        "key_hint":"sk-…","docs":"https://platform.openai.com/api-keys","base_url":"https://api.openai.com/v1",
        "models":{"gpt-4o":"GPT-4o","gpt-4o-mini":"GPT-4o Mini","gpt-3.5-turbo":"GPT-3.5 Turbo"}},
    "gemini":{"name":"Google Gemini","icon":"◇","color":"#4285F4","no_key":False,
        "key_hint":"AIza…","docs":"https://aistudio.google.com/app/apikey",
        "models":{"gemini-2.0-flash-exp":"Gemini 2.0 Flash","gemini-1.5-pro":"Gemini 1.5 Pro","gemini-1.5-flash":"Gemini 1.5 Flash"}},
    "groq":{"name":"Groq","icon":"⚡","color":"#F55036","no_key":False,
        "key_hint":"gsk_…","docs":"https://console.groq.com/keys","base_url":"https://api.groq.com/openai/v1",
        "models":{"llama-3.3-70b-versatile":"Llama 3.3 70B","llama-3.1-8b-instant":"Llama 3.1 8B","mixtral-8x7b-32768":"Mixtral 8x7B"}},
    "mistral":{"name":"Mistral AI","icon":"▲","color":"#FA5204","no_key":False,
        "key_hint":"…","docs":"https://console.mistral.ai/api-keys/","base_url":"https://api.mistral.ai/v1",
        "models":{"mistral-large-latest":"Mistral Large","mistral-small-latest":"Mistral Small","codestral-latest":"Codestral"}},
    "ollama":{"name":"Ollama (Local)","icon":"◉","color":"#333","no_key":True,
        "key_hint":"No key needed","docs":"https://ollama.com","base_url":"http://localhost:11434",
        "models":{"llama3.2":"Llama 3.2","mistral":"Mistral","gemma2":"Gemma 2","deepseek-r1":"DeepSeek R1"}},
}

# ═══════════════════════════════════════════════════════
# SYSTEM PROMPTS
# ═══════════════════════════════════════════════════════
SYSTEM_PROMPTS = {
    "default":"""You are NexusAI, a world-class AI assistant. Communicate like a brilliant, warm human expert.
Rules:
- NEVER open with "Certainly!", "Of course!", "Sure!", "Great question!"
- Use contractions naturally: it's, you're, don't, I'd
- Vary sentence length dynamically
- Show genuine curiosity: "What's fascinating here is…", "Here's the nuance though…"
- Use markdown: **bold** key concepts, `code` inline, structured headers for complex answers
- Number steps 1. 2. 3. and bullet points with -
- End with an actionable insight or a follow-up question that adds value
- Be precise, confident, warm""",
    "technical":"""You are a senior engineer with 20 years experience.
- Always lead with the working solution, then explain
- Use proper code blocks with language tags for ALL code
- Explain WHY, not just WHAT
- Proactively mention edge cases and gotchas
- Use benchmarks, complexity analysis when relevant""",
    "creative":"""You are a visionary creative director and writer.
- Open with a surprising metaphor or unexpected perspective
- Use vivid, sensory language
- Take creative risks — propose the road less traveled
- Build narrative tension, then release it""",
    "concise":"""You are a direct, efficient assistant.
- One clear answer per message
- No preamble, no fluff, no summary
- Bullets only for genuinely list-like things""",
    "academic":"""You are a PhD-level research assistant.
- Cite reasoning clearly
- Distinguish between established facts and emerging research
- Use technical terminology precisely
- Provide multiple perspectives on contested topics""",
}

TONES = {
    "default":   ("◈","Balanced"),
    "technical": ("⚙","Technical"),
    "creative":  ("✦","Creative"),
    "concise":   ("→","Concise"),
    "academic":  ("◎","Academic"),
}

QUICK_ACTIONS = [
    ("⬡","Write Article",  "Write a compelling, well-structured 600-word article about the most transformative AI development of 2026."),
    ("⚙","Debug Code",     "I need help debugging my code. Please act as a senior engineer and walk me through systematic debugging."),
    ("◈","Research Deep",  "Give me a comprehensive, nuanced analysis of the current state of quantum computing and its practical applications."),
    ("✦","Brainstorm",     "Generate 15 innovative, specific business ideas for 2026 that leverage AI in non-obvious ways."),
    ("→","Summarize",      "Summarize the key points of our conversation so far as a structured briefing document."),
    ("◎","Teach Me",       "Explain neural networks from scratch — use analogies, then build up to technical details."),
]

EXPLORE_LIBRARY = [
    ("⬡","Python Mastery",     "Teach me advanced Python: decorators, context managers, async/await, and metaclasses with examples."),
    ("◈","System Design",      "Walk me through designing a scalable chat application like WhatsApp from scratch."),
    ("⚙","SQL Optimization",   "Teach me SQL query optimization: indexes, query plans, and common performance pitfalls."),
    ("✦","Email Persuasion",    "Write a persuasive cold outreach email for a B2B SaaS product. Make it genuinely useful."),
    ("→","Data Structures",     "Explain every major data structure with time complexity, use cases, and Python examples."),
    ("◎","Machine Learning",    "Give me a practical ML roadmap — from linear regression to transformers, with resources."),
    ("⬡","API Design",          "Explain REST API best practices: versioning, authentication, error handling, documentation."),
    ("◈","Git Advanced",        "Teach me advanced Git: rebasing, cherry-pick, bisect, reflog, and stash."),
    ("⚙","Docker & K8s",        "Explain Docker and Kubernetes clearly — containers, images, pods, services, deployments."),
    ("✦","Startup Strategy",    "Give me a lean startup framework: customer discovery, MVP, product-market fit, scaling."),
    ("→","Finance Basics",      "Explain compound interest, index funds, and the basics of long-term investing simply."),
    ("◎","Neuroscience",        "Explain how memory formation works in the brain — from neurons to long-term memory."),
]

# ═══════════════════════════════════════════════════════
# MARKDOWN RENDERER
# ═══════════════════════════════════════════════════════
def render_md(text):
    lines = text.split("\n")
    out, code_buf = [], []
    in_code = in_ul = False
    code_lang = ""

    def flush_ul():
        nonlocal in_ul
        if in_ul: out.append("</ul>"); in_ul = False

    def esc(s): return s.replace("&","&amp;").replace("<","&lt;").replace(">","&gt;")

    def inline(s):
        t = esc(s)
        t = re.sub(r"\*\*\*(.+?)\*\*\*", r"<strong><em>\1</em></strong>", t)
        t = re.sub(r"\*\*(.+?)\*\*",     r"<strong>\1</strong>", t)
        t = re.sub(r"__(.+?)__",         r"<strong>\1</strong>", t)
        t = re.sub(r"\*([^*\n]+?)\*",    r"<em>\1</em>", t)
        t = re.sub(r"`([^`\n]+?)`",      r'<code class="ic">\1</code>', t)
        t = re.sub(r"\[(.+?)\]\((.+?)\)",r'<a href="\2" target="_blank">\1</a>', t)
        return t

    for line in lines:
        if line.startswith("```"):
            if not in_code:
                flush_ul(); code_lang=line[3:].strip() or "text"; in_code=True; code_buf=[]
            else:
                ll  = f'<span class="cl">{esc(code_lang)}</span>' if code_lang else ""
                bod = esc("\n".join(code_buf))
                out.append(f'<div class="cw"><div class="ch">{ll}<button class="cc-btn" onclick="cpCode(this)">Copy</button></div><pre><code>{bod}</code></pre></div>')
                in_code=False; code_buf=[]; code_lang=""
            continue
        if in_code: code_buf.append(line); continue
        if line.strip() in ("---","***","___"): flush_ul(); out.append('<hr class="mhr">'); continue
        matched = False
        for pat,cls in [(r"^# (.+)$","mh1"),(r"^## (.+)$","mh2"),(r"^### (.+)$","mh3")]:
            m = re.match(pat, line)
            if m: flush_ul(); out.append(f'<div class="{cls}">{inline(m.group(1))}</div>'); matched=True; break
        if matched: continue
        bq = re.match(r"^> (.+)$", line)
        if bq: flush_ul(); out.append(f'<blockquote class="mbq">{inline(bq.group(1))}</blockquote>'); continue
        nl = re.match(r"^(\d+)\.\s+(.+)$", line)
        if nl: flush_ul(); out.append(f'<div class="nli"><span class="nln">{nl.group(1)}.</span><span>{inline(nl.group(2))}</span></div>'); continue
        bl = re.match(r"^[\*\-]\s+(.+)$", line)
        if bl:
            if not in_ul: out.append('<ul class="mul">'); in_ul=True
            out.append(f"<li>{inline(bl.group(1))}</li>"); continue
        flush_ul()
        if not line.strip(): out.append('<div class="mg"></div>'); continue
        out.append(f'<p class="mp">{inline(line)}</p>')
    flush_ul()
    return "\n".join(out)

# ═══════════════════════════════════════════════════════
# HTTP + API CALLS
# ═══════════════════════════════════════════════════════
try:
    import requests as _req; _HAS_REQ = True
except ImportError:
    _HAS_REQ = False

_UA = "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/122.0.0.0 Safari/537.36"

def http_post(url, hdrs, payload, timeout=90):
    merged = {"User-Agent":_UA,"Accept":"application/json","Accept-Language":"en-US,en;q=0.9"}
    merged.update(hdrs)
    body = json.dumps(payload).encode("utf-8")
    if _HAS_REQ:
        for i in range(2):
            try:
                r = _req.post(url, data=body, headers=merged, timeout=timeout)
                if r.status_code==429 and i==0: time.sleep(2); continue
                if not r.ok: raise RuntimeError(f"HTTP {r.status_code}: {r.text[:300]}")
                return r.json()
            except _req.exceptions.RequestException as e:
                if i==0: time.sleep(1); continue
                raise RuntimeError(f"Request failed: {e}")
    else:
        req = urllib.request.Request(url, data=body, headers=merged, method="POST")
        for i in range(2):
            try:
                with urllib.request.urlopen(req, timeout=timeout) as resp:
                    return json.loads(resp.read().decode("utf-8"))
            except urllib.error.HTTPError as e:
                err = e.read().decode("utf-8",errors="replace")
                if e.code==429 and i==0: time.sleep(2); req=urllib.request.Request(url,data=body,headers=merged,method="POST"); continue
                raise RuntimeError(f"HTTP {e.code}: {err[:300]}")
            except Exception as ex:
                raise RuntimeError(f"Connection error: {ex}")

def resolve_key(pid):
    saved  = st.session_state.get(f"sk_{pid}","").strip()
    widget = st.session_state.get(f"kw_{pid}","").strip()
    env    = os.environ.get(ENV_MAP.get(pid,""),"").strip()
    key    = saved or widget or env
    if key and not saved: st.session_state[f"sk_{pid}"] = key
    return key

def call_anthropic(hist, sys_p, model, key, max_tok, temp, stream):
    client = anthropic.Anthropic(api_key=key)
    t0 = time.time()
    if stream:
        reply = ""
        with client.messages.stream(model=model,max_tokens=max_tok,temperature=temp,system=sys_p,messages=hist) as s:
            for chunk in s.text_stream: reply += chunk
        fin = s.get_final_message()
        return reply, fin.usage.input_tokens, fin.usage.output_tokens, round(time.time()-t0,2)
    else:
        r = client.messages.create(model=model,max_tokens=max_tok,temperature=temp,system=sys_p,messages=hist)
        return r.content[0].text, r.usage.input_tokens, r.usage.output_tokens, round(time.time()-t0,2)

def call_openai_compat(hist, sys_p, model, key, base_url, max_tok, temp):
    t0=time.time(); msgs=[{"role":"system","content":sys_p}]+hist
    hdrs={"Content-Type":"application/json"}
    if key: hdrs["Authorization"]=f"Bearer {key}"
    d=http_post(f"{base_url}/chat/completions",hdrs,{"model":model,"messages":msgs,"max_tokens":max_tok,"temperature":temp})
    reply=d["choices"][0]["message"]["content"]; u=d.get("usage",{})
    return reply,u.get("prompt_tokens",0),u.get("completion_tokens",0),round(time.time()-t0,2)

def call_gemini(hist, sys_p, model, key, max_tok, temp):
    t0=time.time(); gm=[]
    if sys_p: gm+=[{"role":"user","parts":[{"text":f"[System]: {sys_p}"}]},{"role":"model","parts":[{"text":"Understood."}]}]
    for m in hist: gm.append({"role":"user" if m["role"]=="user" else "model","parts":[{"text":m["content"]}]})
    url=f"https://generativelanguage.googleapis.com/v1beta/models/{model}:generateContent?key={key}"
    d=http_post(url,{"Content-Type":"application/json"},{"contents":gm,"generationConfig":{"maxOutputTokens":max_tok,"temperature":temp}})
    reply=d["candidates"][0]["content"]["parts"][0]["text"]; u=d.get("usageMetadata",{})
    return reply,u.get("promptTokenCount",0),u.get("candidatesTokenCount",0),round(time.time()-t0,2)

def call_ai(messages, prompt):
    pid=st.session_state.active_provider; prov=PROVIDERS[pid]
    no_key=prov.get("no_key",False); api_key=resolve_key(pid)
    if not api_key and not no_key:
        raise ValueError(f"NO_KEY|{prov['name']}|{prov['docs']}")
    model=st.session_state.model_key
    mlist=list(prov["models"].keys())
    if model not in mlist: model=mlist[0]; st.session_state.model_key=model
    sys_p=SYSTEM_PROMPTS.get(st.session_state.tone,SYSTEM_PROMPTS["default"])
    if st.session_state.get("code_mode"): sys_p+="\n\nCode mode active: Always use proper code blocks with syntax highlighting and detailed comments."
    max_tok=st.session_state.max_tokens; temp=st.session_state.temperature
    stream=st.session_state.stream_mode
    hist=list(messages)+[{"role":"user","content":prompt}]
    if pid=="anthropic": return call_anthropic(hist,sys_p,model,api_key,max_tok,temp,stream)
    elif pid=="gemini":  return call_gemini(hist,sys_p,model,api_key,max_tok,temp)
    else:
        base=prov.get("base_url","https://api.openai.com/v1")
        if pid=="ollama": base=st.session_state.get("ollama_url","http://localhost:11434")+"/v1"
        return call_openai_compat(hist,sys_p,model,api_key,base,max_tok,temp)

def send_message(prompt):
    if not prompt.strip(): return
    t=datetime.now().strftime("%H:%M")
    if not st.session_state.messages:
        w=prompt.split(); st.session_state.conv_name=" ".join(w[:6])+("…" if len(w)>6 else "")
    st.session_state.messages.append({"role":"user","content":prompt,"time":t})
    ph=st.session_state.get("prompt_history",[])
    if prompt not in ph: st.session_state.prompt_history=([prompt]+ph)[:30]
    history=[{"role":m["role"],"content":m["content"]} for m in st.session_state.messages[:-1]]
    try:
        reply,in_tok,out_tok,elapsed=call_ai(history,prompt)
        st.session_state.resp_times.append(elapsed)
        st.session_state.total_tokens+=in_tok+out_tok
        st.session_state.total_words+=len(reply.split())
        st.session_state.chats_today+=1
        bd=st.session_state.bar_data+[st.session_state.chats_today]
        st.session_state.bar_data=bd[-14:]
        st.session_state.messages.append({
            "role":"assistant","content":reply,
            "time":datetime.now().strftime("%H:%M"),"tokens":out_tok,
            "feedback":None,"model":st.session_state.model_key,
            "provider":st.session_state.active_provider,"elapsed":elapsed,
        })
        st.session_state.notifications.insert(0,{
            "icon":"✓","text":f"Reply in {elapsed}s · {out_tok} tokens","time":"now","read":False
        })
        st.session_state.notifications=st.session_state.notifications[:10]
    except ValueError as ve:
        if st.session_state.messages and st.session_state.messages[-1]["role"]=="user":
            st.session_state.messages.pop()
        parts=str(ve).split("|")
        if parts[0]=="NO_KEY":
            pname=parts[1] if len(parts)>1 else "API"; docs=parts[2] if len(parts)>2 else ""
            lnk=f' <a href="{docs}" target="_blank" style="color:#F97316;text-decoration:underline;">Get key →</a>' if docs else ""
            st.session_state.toast=("warn",f"No {pname} key.{lnk}")
        else: st.session_state.toast=("err",f"Error: {ve}")
    except Exception as e:
        if st.session_state.messages and st.session_state.messages[-1]["role"]=="user":
            st.session_state.messages.pop()
        msg=str(e)
        if any(x in msg.lower() for x in ["401","auth","api_key","invalid"]): st.session_state.toast=("err","Invalid API key — check sidebar")
        elif "429" in msg or "rate" in msg.lower(): st.session_state.toast=("warn","Rate limited — wait 30s")
        elif "connection" in msg.lower() or "timeout" in msg.lower(): st.session_state.toast=("err","Connection error — check network")
        else: st.session_state.toast=("err",f"{msg[:160]}")

# ═══════════════════════════════════════════════════════
# SESSION STATE
# ═══════════════════════════════════════════════════════
def init():
    d={
        "messages":[],"total_tokens":0,"total_words":0,"chats_today":0,
        "convs":[{"name":"Getting Started","icon":"⬡","msgs":[],"time":""},
                 {"name":"Code Review",     "icon":"⚙","msgs":[],"time":""}],
        "conv_name":"New Session",
        "active_provider":"anthropic","model_key":"claude-sonnet-4-20250514",
        "temperature":0.72,"max_tokens":2048,"stream_mode":True,"tone":"default",
        "resp_times":[],"bar_data":[8,14,11,19,16,24,20,28,22,30,25,32,28,34],
        "sk_anthropic":os.environ.get("ANTHROPIC_API_KEY",""),
        "sk_openai":os.environ.get("OPENAI_API_KEY",""),
        "sk_gemini":os.environ.get("GOOGLE_API_KEY",""),
        "sk_groq":os.environ.get("GROQ_API_KEY",""),
        "sk_mistral":os.environ.get("MISTRAL_API_KEY",""),
        "sk_ollama":"","ollama_url":"http://localhost:11434",
        "pending_prompt":None,"retry_idx":None,"active_view":"chat",
        "saved_msgs":[],"toast":None,"notif_open":False,
        "notifications":[
            {"icon":"⬡","text":"Welcome to NexusAI — 2026 Edition","time":"now","read":False},
            {"icon":"⚡","text":"8 AI providers available. Add your API key to begin.","time":"now","read":False},
        ],
        "file_content":None,"file_name":None,
        "code_mode":False,"prompt_history":[],"search_query":"",
        "pinned_msgs":[],"msg_ratings":{},
    }
    for k,v in d.items():
        if k not in st.session_state: st.session_state[k]=v

init()

def ts(): return datetime.now().strftime("%H:%M")
def fmt(n): return f"{n:,}" if n>=1000 else str(n)

def save_conv():
    if st.session_state.messages:
        nm=st.session_state.conv_name
        if not any(c["name"]==nm for c in st.session_state.convs):
            st.session_state.convs.append({"name":nm,"icon":"◈","msgs":[m.copy() for m in st.session_state.messages],"time":ts()})

def load_conv(idx):
    if 0<=idx<len(st.session_state.convs):
        c=st.session_state.convs[idx]
        st.session_state.messages=[m.copy() for m in c.get("msgs",[])]
        st.session_state.conv_name=c["name"]

def export_md():
    lines=[f"# NexusAI Session Export\n*{datetime.now().strftime('%Y-%m-%d %H:%M')}*\n\n---\n"]
    for m in st.session_state.messages:
        who="**You**" if m["role"]=="user" else f"**⬡ NexusAI** _{m.get('model','')}_"
        lines.append(f"{who}  `{m.get('time','')}`\n\n{m['content']}\n\n---\n")
    return "\n".join(lines)

# ═══════════════════════════════════════════════════════
# PENDING ACTION PROCESSOR
# ═══════════════════════════════════════════════════════
if st.session_state.pending_prompt:
    pp=st.session_state.pending_prompt; st.session_state.pending_prompt=None
    with st.spinner("⬡ Thinking…"): send_message(pp)
    st.rerun()

if st.session_state.retry_idx is not None:
    idx=st.session_state.retry_idx; st.session_state.retry_idx=None
    if idx<len(st.session_state.messages):
        tgt=st.session_state.messages[idx]
        if tgt["role"]=="user":
            st.session_state.messages=st.session_state.messages[:idx]
            with st.spinner("⬡ Retrying…"): send_message(tgt["content"])
            st.rerun()

_pid=st.session_state.active_provider; _prov=PROVIDERS[_pid]
_key_ok=bool(resolve_key(_pid)) or _prov.get("no_key",False)

# ═══════════════════════════════════════════════════════
# CSS
# ═══════════════════════════════════════════════════════
st.markdown("""
<style>
@import url('https://fonts.googleapis.com/css2?family=Inter:ital,wght@0,300;0,400;0,500;0,600;0,700;1,400&family=JetBrains+Mono:wght@400;500&family=Manrope:wght@400;500;600;700;800&display=swap');

*,*::before,*::after{box-sizing:border-box;margin:0;padding:0;}

:root{
  /* Core palette */
  --bg:         #0C0E14;
  --bg2:        #111420;
  --bg3:        #161A26;
  --card:       #1A1E2C;
  --card2:      #1E2334;
  --hover:      #232840;
  --border:     rgba(255,255,255,0.06);
  --border2:    rgba(255,255,255,0.12);
  /* Accent */
  --accent:     #6C63FF;
  --accent2:    #8B5CF6;
  --accent3:    #A78BFA;
  --cyan:       #22D3EE;
  --emerald:    #10B981;
  --amber:      #F59E0B;
  --rose:       #F43F5E;
  --orange:     #F97316;
  /* Text */
  --t1:         #F0F2FF;
  --t2:         #A8B2D8;
  --t3:         #606882;
  --t4:         #404660;
  /* Glow */
  --glow:       0 0 40px rgba(108,99,255,0.15);
  --glow2:      0 0 20px rgba(108,99,255,0.25);
  /* Radii */
  --r1:6px;--r2:10px;--r3:14px;--r4:20px;--r5:28px;
  /* Fonts */
  --fd:'Manrope',sans-serif;
  --fb:'Inter',sans-serif;
  --fm:'JetBrains Mono',monospace;
}

/* ─── APP BASE ─── */
html,body,.stApp{background:var(--bg)!important;font-family:var(--fb);color:var(--t1);}
.stApp::before{content:'';position:fixed;inset:0;z-index:0;pointer-events:none;
  background:
    radial-gradient(ellipse 60% 40% at 15% 0%,   rgba(108,99,255,.07) 0%,transparent 60%),
    radial-gradient(ellipse 50% 35% at 85% 100%,  rgba(139,92,246,.06) 0%,transparent 60%),
    radial-gradient(ellipse 40% 50% at 50% 50%,   rgba(34,211,238,.03) 0%,transparent 65%);}

/* ─── HIDE CHROME ─── */
#MainMenu,footer,header,.stDeployButton,[data-testid="stToolbar"],
[data-testid="stDecoration"],[data-testid="stStatusWidget"]{display:none!important;}
[data-testid="stAppViewContainer"]>div:first-child{padding-top:0!important;}
[data-testid="stMainBlockContainer"]{padding:0!important;max-width:none!important;}
section.main>.block-container{padding:0!important;max-width:none!important;}

/* ─── KILL ALL STREAMLIT WHITE BOXES ─── */
.stApp [data-testid="stVerticalBlock"],
.stApp [data-testid="stHorizontalBlock"],
.stApp [data-testid="stColumn"],
.stApp [data-testid="element-container"],
.stApp .stMarkdown{background:transparent!important;border:none!important;box-shadow:none!important;}

/* ─── SIDEBAR ─── */
[data-testid="stSidebar"]{
  background:var(--bg2)!important;border-right:1px solid var(--border2)!important;
  width:268px!important;}
[data-testid="stSidebar"]>div:first-child{
  padding:0!important;height:100vh;overflow-y:auto;
  scrollbar-width:thin;scrollbar-color:var(--border2) transparent;}

.sb{padding:20px 16px 28px;}
.sb-logo{display:flex;align-items:center;gap:11px;padding:0 2px 20px;
  border-bottom:1px solid var(--border);margin-bottom:16px;}
.sb-mark{width:36px;height:36px;border-radius:10px;
  background:linear-gradient(135deg,var(--accent),var(--accent2));
  display:flex;align-items:center;justify-content:center;font-size:16px;
  box-shadow:0 0 20px rgba(108,99,255,.35);animation:lp 4s ease-in-out infinite;}
@keyframes lp{0%,100%{box-shadow:0 0 20px rgba(108,99,255,.35);}
               50%{box-shadow:0 0 35px rgba(108,99,255,.55),0 0 60px rgba(139,92,246,.2);}}
.sb-name{font-family:var(--fd);font-size:18px;font-weight:800;letter-spacing:-.4px;
  background:linear-gradient(135deg,var(--accent3),var(--cyan));
  -webkit-background-clip:text;-webkit-text-fill-color:transparent;}
.sb-ver{font-size:10px;color:var(--t3);letter-spacing:2px;text-transform:uppercase;margin-top:1px;}

.sbl{font-size:10px;font-weight:700;letter-spacing:2px;color:var(--t3);
  text-transform:uppercase;padding:0 2px;margin-bottom:7px;font-family:var(--fd);}

.sb-ci{display:flex;align-items:center;gap:9px;padding:8px 10px;border-radius:var(--r2);
  cursor:pointer;color:var(--t2);font-size:13px;margin-bottom:2px;transition:all .18s;}
.sb-ci:hover{background:var(--hover);color:var(--t1);}
.sb-ci.act{background:rgba(108,99,255,.15);color:var(--accent3);border:1px solid rgba(108,99,255,.2);}
.sb-ci .cit{flex:1;white-space:nowrap;overflow:hidden;text-overflow:ellipsis;}
.sb-ci .cim{font-size:9.5px;color:var(--t3);flex-shrink:0;font-family:var(--fm);}
.sb-div{height:1px;background:var(--border);margin:12px 0;}
.sb-nav{display:flex;align-items:center;gap:10px;padding:9px 10px;border-radius:var(--r2);
  cursor:pointer;color:var(--t2);font-size:13.5px;margin-bottom:1px;font-weight:500;transition:all .18s;}
.sb-nav:hover{background:var(--hover);color:var(--t1);}
.sb-nav.nact{background:rgba(108,99,255,.12);color:var(--accent3);}
.sb-nav .ni{font-size:15px;width:18px;text-align:center;}

/* Key status */
.key-ok{font-size:10.5px;color:var(--emerald);padding:3px 2px 8px;}
.key-ok code{color:var(--emerald);font-size:10px;font-family:var(--fm);
  background:rgba(16,185,129,.12);padding:1px 5px;border-radius:3px;}
.key-no{font-size:10.5px;color:var(--amber);padding:3px 2px 8px;}
.key-no a{color:var(--amber);text-decoration:underline;}

/* ─── TOP BAR ─── */
.topbar{display:flex;align-items:center;justify-content:space-between;
  padding:12px 24px;background:var(--bg2);border-bottom:1px solid var(--border2);
  position:sticky;top:0;z-index:200;backdrop-filter:blur(20px);}
.tb-l{display:flex;align-items:center;gap:14px;}
.tb-logo{font-family:var(--fd);font-size:18px;font-weight:800;letter-spacing:-.4px;
  background:linear-gradient(135deg,var(--accent3),var(--cyan));
  -webkit-background-clip:text;-webkit-text-fill-color:transparent;}
.tb-slash{color:var(--t4);margin:0 2px;}
.tb-conv{font-family:var(--fb);font-size:14px;color:var(--t2);font-weight:500;max-width:200px;
  white-space:nowrap;overflow:hidden;text-overflow:ellipsis;}
.tb-badge{padding:3px 10px;border-radius:20px;font-size:11px;font-weight:700;font-family:var(--fd);
  background:linear-gradient(135deg,var(--accent),var(--accent2));color:white;letter-spacing:.3px;}
.tb-r{display:flex;align-items:center;gap:8px;}
.tb-btn{width:32px;height:32px;border-radius:var(--r2);background:var(--card);
  border:1px solid var(--border2);display:flex;align-items:center;justify-content:center;
  cursor:pointer;font-size:14px;position:relative;transition:all .18s;color:var(--t2);}
.tb-btn:hover{background:var(--hover);border-color:rgba(108,99,255,.3);color:var(--t1);}
.tb-btn.active{background:rgba(108,99,255,.15);border-color:rgba(108,99,255,.35);color:var(--accent3);}
.nd{position:absolute;top:5px;right:5px;width:7px;height:7px;border-radius:50%;
  background:var(--rose);border:2px solid var(--bg2);}
.tb-av{width:32px;height:32px;border-radius:var(--r2);
  background:linear-gradient(135deg,var(--accent),var(--accent2));
  display:flex;align-items:center;justify-content:center;color:white;font-size:13px;
  font-weight:700;font-family:var(--fd);cursor:pointer;box-shadow:var(--glow2);}

/* Provider badge */
.prov-chip{display:inline-flex;align-items:center;gap:6px;padding:4px 10px;
  border-radius:16px;background:rgba(108,99,255,.10);
  border:1px solid rgba(108,99,255,.20);font-size:11px;color:var(--accent3);font-family:var(--fd);font-weight:600;}
.live-dot{width:6px;height:6px;border-radius:50%;background:var(--emerald);
  box-shadow:0 0 6px var(--emerald);display:inline-block;
  animation:ld 2.2s ease-in-out infinite;}
@keyframes ld{0%,100%{opacity:1;}50%{opacity:.3;}}

/* Notif panel */
.npanel{position:fixed;top:54px;right:16px;width:300px;z-index:999;
  background:var(--card);border-radius:var(--r3);border:1px solid var(--border2);
  box-shadow:0 12px 40px rgba(0,0,0,.5);overflow:hidden;}
.nph{padding:12px 16px;border-bottom:1px solid var(--border);
  font-family:var(--fd);font-size:13px;font-weight:700;color:var(--t1);}
.npi{padding:11px 15px;border-bottom:1px solid var(--border);
  display:flex;gap:9px;cursor:pointer;transition:background .15s;}
.npi:hover{background:var(--hover);}
.npi.unr{background:rgba(108,99,255,.06);}
.npi-ico{font-size:14px;flex-shrink:0;color:var(--accent3);}
.npi-txt{font-size:12.5px;color:var(--t2);line-height:1.4;}
.npi-t{font-size:10px;color:var(--t3);margin-top:2px;font-family:var(--fm);}

/* ─── CENTER PANEL ─── */
.cpanel{display:flex;flex-direction:column;background:var(--bg3);border-radius:var(--r4);
  border:1px solid var(--border2);overflow:hidden;height:calc(100vh - 102px);
  box-shadow:0 4px 30px rgba(0,0,0,.3);}

/* Welcome zone */
.wzone{padding:20px 24px 14px;border-bottom:1px solid var(--border);}
.wrow{display:flex;align-items:center;justify-content:space-between;margin-bottom:4px;}
.wtitle{font-family:var(--fd);font-size:19px;font-weight:800;color:var(--t1);letter-spacing:-.4px;}
.wstatus{display:flex;align-items:center;gap:8px;}
.wsub{font-size:13px;color:var(--t3);margin-bottom:12px;}
.model-chip{display:inline-flex;align-items:center;gap:5px;padding:3px 10px;border-radius:12px;
  background:rgba(108,99,255,.10);border:1px solid rgba(108,99,255,.20);
  font-size:10px;color:var(--accent3);font-family:var(--fm);font-weight:600;}
.qlabel{font-size:10.5px;font-weight:700;letter-spacing:1.5px;color:var(--t4);
  text-transform:uppercase;font-family:var(--fd);margin-bottom:7px;}
.qchips{display:flex;flex-wrap:wrap;gap:6px;}
.qchip{display:inline-flex;align-items:center;gap:6px;padding:6px 13px;border-radius:20px;
  font-size:12px;font-weight:600;cursor:pointer;transition:all .2s;
  background:var(--card);border:1px solid var(--border2);color:var(--t2);font-family:var(--fd);}
.qchip:hover{background:rgba(108,99,255,.15);border-color:rgba(108,99,255,.35);
  color:var(--accent3);transform:translateY(-1px);box-shadow:0 4px 12px rgba(108,99,255,.15);}

/* Conversation header */
.conv-hdr{display:flex;align-items:center;justify-content:space-between;
  padding:10px 24px 0;}
.conv-title{font-size:13px;font-weight:600;color:var(--t2);font-family:var(--fd);}
.conv-meta{font-size:10.5px;color:var(--t4);font-family:var(--fm);}
.conv-acts{display:flex;gap:5px;}
.cact{padding:3px 9px;border-radius:6px;font-size:10.5px;background:var(--card);
  border:1px solid var(--border);color:var(--t3);cursor:pointer;transition:all .15s;}
.cact:hover{background:var(--hover);color:var(--t1);border-color:var(--border2);}

/* ─── CHAT AREA ─── */
.chatarea{flex:1;overflow-y:auto;padding:16px 24px;display:flex;flex-direction:column;gap:14px;
  scrollbar-width:thin;scrollbar-color:var(--border2) transparent;}
.chatarea::-webkit-scrollbar{width:4px;}
.chatarea::-webkit-scrollbar-thumb{background:var(--border2);border-radius:2px;}

/* Empty state */
.empty{flex:1;display:flex;align-items:center;justify-content:center;
  padding:40px;text-align:center;}
.empty-icon{font-size:40px;margin-bottom:14px;}
.empty-t{font-family:var(--fd);font-size:15px;font-weight:700;color:var(--t2);margin-bottom:6px;}
.empty-s{font-size:13px;color:var(--t3);max-width:240px;line-height:1.55;}

/* Key missing banner */
.kbanner{padding:12px 16px;background:rgba(249,115,22,.06);border:1px solid rgba(249,115,22,.20);
  border-radius:var(--r3);margin-bottom:12px;}
.kbanner-t{font-size:13px;font-weight:700;color:var(--orange);margin-bottom:4px;font-family:var(--fd);}
.kbanner-b{font-size:12px;color:rgba(249,115,22,.75);line-height:1.5;}
.kbanner-b a{color:var(--orange);text-decoration:underline;}

/* User message */
.umsg{display:flex;justify-content:flex-end;animation:msgIn .25s ease-out;}
@keyframes msgIn{from{opacity:0;transform:translateY(8px);}to{opacity:1;transform:none;}}
.ubub{max-width:74%;padding:12px 16px;
  background:linear-gradient(135deg,var(--accent),var(--accent2));
  color:white;border-radius:16px 16px 4px 16px;font-size:14px;line-height:1.65;
  box-shadow:0 4px 16px rgba(108,99,255,.3);}
.umts{font-size:10px;color:var(--t4);margin-top:4px;text-align:right;font-family:var(--fm);}

/* AI message */
.aimsg{display:flex;align-items:flex-start;gap:11px;animation:msgIn .25s ease-out;}
.aiav{width:32px;height:32px;border-radius:50%;flex-shrink:0;
  background:linear-gradient(135deg,var(--accent),var(--accent2));
  display:flex;align-items:center;justify-content:center;color:white;
  font-size:13px;font-weight:700;margin-top:2px;
  box-shadow:0 0 14px rgba(108,99,255,.3);font-family:var(--fd);}
.aibody{flex:1;min-width:0;}
.ainame{font-size:10.5px;font-weight:700;color:var(--accent3);margin-bottom:4px;
  font-family:var(--fd);text-transform:uppercase;letter-spacing:.5px;
  display:flex;align-items:center;gap:7px;}
.tokbadge{font-size:9px;color:var(--t3);background:var(--card);
  border:1px solid var(--border);padding:1px 6px;border-radius:8px;font-family:var(--fm);}
.pbadge{font-size:9px;color:var(--t4);background:rgba(108,99,255,.06);
  border:1px solid rgba(108,99,255,.12);padding:1px 6px;border-radius:8px;font-family:var(--fm);}
.aibub{padding:13px 16px;background:var(--card);border:1px solid var(--border2);
  border-radius:4px 16px 16px 16px;font-size:14px;line-height:1.75;color:var(--t1);}
.aimts{font-size:10px;color:var(--t4);margin-top:4px;font-family:var(--fm);}
.actrow{display:flex;gap:4px;margin-top:6px;opacity:0;transition:opacity .18s;}
.aibody:hover .actrow,.umsg:hover .actrow{opacity:1;}
.acbt{padding:2px 9px;border-radius:5px;font-size:10.5px;background:var(--card);
  border:1px solid var(--border);color:var(--t3);cursor:pointer;transition:all .15s;}
.acbt:hover{background:var(--hover);color:var(--t1);border-color:var(--border2);}
.acbt.gd{background:rgba(16,185,129,.10);color:var(--emerald);border-color:rgba(16,185,129,.25);}
.acbt.bd{background:rgba(244,63,94,.08);color:var(--rose);border-color:rgba(244,63,94,.2);}

/* ─── MARKDOWN ─── */
.aibub .mp{font-size:14px;line-height:1.75;color:var(--t1);margin:0;}
.aibub .mg{height:9px;}
.aibub .mh1{font-family:var(--fd);font-size:17px;font-weight:800;color:var(--t1);
  margin:14px 0 7px;padding-bottom:6px;border-bottom:1px solid var(--border);}
.aibub .mh2{font-family:var(--fd);font-size:15px;font-weight:700;color:var(--accent3);margin:12px 0 5px;}
.aibub .mh3{font-family:var(--fd);font-size:13.5px;font-weight:600;color:var(--t2);margin:10px 0 4px;}
.aibub strong{color:var(--accent3);font-weight:700;}
.aibub em{color:var(--t2);font-style:italic;}
.aibub a{color:var(--cyan);text-underline-offset:3px;}
.aibub .ic{font-family:var(--fm);font-size:12px;background:rgba(108,99,255,.12);
  padding:2px 6px;border-radius:4px;color:var(--accent3);border:1px solid rgba(108,99,255,.2);}
.aibub .mbq{border-left:3px solid var(--accent);padding:8px 13px;
  color:var(--t2);margin:9px 0;font-style:italic;
  background:rgba(108,99,255,.05);border-radius:0 var(--r1) var(--r1) 0;}
.aibub .mhr{border:none;border-top:1px solid var(--border);margin:10px 0;}
.aibub .mul{padding-left:0;margin:7px 0;list-style:none;}
.aibub .mul li{padding:2px 0 2px 18px;position:relative;color:var(--t1);font-size:14px;line-height:1.7;}
.aibub .mul li::before{content:"•";position:absolute;left:3px;color:var(--accent);font-weight:700;}
.aibub .nli{display:flex;gap:8px;align-items:baseline;padding:2px 0;font-size:14px;line-height:1.7;}
.aibub .nln{color:var(--accent);font-weight:700;flex-shrink:0;font-size:12px;min-width:16px;}
.aibub .cw{margin:9px 0;border-radius:var(--r2);overflow:hidden;border:1px solid var(--border2);}
.aibub .ch{display:flex;align-items:center;justify-content:space-between;
  padding:6px 13px;background:rgba(0,0,0,.3);border-bottom:1px solid var(--border);}
.aibub .cl{font-size:10px;font-family:var(--fm);color:var(--accent3);font-weight:500;}
.aibub .cc-btn{font-size:10px;font-family:var(--fm);color:var(--t3);cursor:pointer;
  padding:2px 8px;border-radius:4px;background:var(--hover);border:1px solid var(--border);transition:all .15s;}
.aibub .cc-btn:hover{background:rgba(108,99,255,.15);color:var(--accent3);}
.aibub pre{background:#0A0C14!important;border:none!important;border-radius:0!important;
  padding:14px 16px!important;margin:0!important;font-family:var(--fm)!important;
  font-size:12px!important;line-height:1.65!important;overflow-x:auto!important;}
.aibub pre code{background:transparent!important;padding:0!important;
  color:#B8C0D8!important;border:none!important;font-family:var(--fm)!important;}

/* ─── INPUT ZONE ─── */
.izone{padding:12px 20px 14px;border-top:1px solid var(--border2);background:var(--bg3);}
.tok-bar-wrap{display:flex;align-items:center;gap:10px;padding:0 4px 8px;}
.tok-bar-track{flex:1;height:2px;background:var(--border);border-radius:1px;overflow:hidden;}
.tok-bar-fill{height:100%;border-radius:1px;transition:width .5s ease;}
.tok-label{font-size:9.5px;color:var(--t4);font-family:var(--fm);white-space:nowrap;}
.ishell{display:flex;align-items:flex-end;gap:8px;padding:10px 14px 10px 18px;
  background:var(--card2);border:1.5px solid var(--border2);border-radius:var(--r4);
  transition:all .2s;}
.ishell:focus-within{border-color:rgba(108,99,255,.4);
  box-shadow:0 0 0 3px rgba(108,99,255,.08),0 4px 20px rgba(0,0,0,.2);}
.ifoot{display:flex;align-items:center;justify-content:space-between;margin-top:8px;padding:0 4px;}
.ihints{display:flex;align-items:center;gap:6px;flex-wrap:wrap;}
.ihint{padding:3px 9px;border-radius:10px;font-size:10.5px;
  background:var(--card);border:1px solid var(--border);color:var(--t4);font-family:var(--fd);}
.ihint.on{background:rgba(108,99,255,.12);border-color:rgba(108,99,255,.25);color:var(--accent3);}
.ichar{font-size:10px;color:var(--t4);font-family:var(--fm);}
.att-bar{display:flex;align-items:center;gap:8px;padding:6px 12px;
  background:rgba(108,99,255,.08);border-radius:var(--r2);
  border:1px solid rgba(108,99,255,.18);font-size:12px;color:var(--accent3);margin-bottom:8px;}

/* ─── RIGHT PANEL ─── */
.rpanel{display:flex;flex-direction:column;gap:12px;overflow-y:auto;
  height:calc(100vh - 102px);
  scrollbar-width:thin;scrollbar-color:var(--border2) transparent;padding-right:2px;}
.rpanel::-webkit-scrollbar{width:3px;}
.rpanel::-webkit-scrollbar-thumb{background:var(--border2);border-radius:2px;}
.rc{background:var(--card);border-radius:var(--r3);border:1px solid var(--border2);padding:14px 16px;}
.rct{font-family:var(--fd);font-size:12.5px;font-weight:700;color:var(--t2);
  margin-bottom:10px;letter-spacing:-.1px;text-transform:uppercase;font-size:10px;letter-spacing:1.5px;color:var(--t3);}
.stat-n{font-family:var(--fd);font-size:28px;font-weight:800;color:var(--t1);line-height:1;}
.stat-l{font-size:11.5px;color:var(--t3);margin-top:2px;}
.chart-wrap{display:flex;align-items:flex-end;gap:2px;height:36px;}
.cbar{flex:1;border-radius:2px 2px 0 0;min-width:6px;
  background:linear-gradient(to top,var(--accent),var(--accent2));opacity:.7;transition:all .3s;}
.cbar:hover{opacity:1;}
.statrr{display:flex;align-items:flex-end;justify-content:space-between;}
.model-rr{display:flex;align-items:center;justify-content:space-between;}
.mn{font-family:var(--fd);font-size:14px;font-weight:800;color:var(--t1);word-break:break-word;}
.ms{font-size:11px;color:var(--t3);margin-top:2px;}
.mbadges{display:flex;gap:4px;margin-top:6px;flex-wrap:wrap;}
.mbadge{font-size:9px;padding:2px 7px;border-radius:7px;font-family:var(--fm);}
.mico{width:38px;height:38px;border-radius:50%;
  background:linear-gradient(135deg,rgba(108,99,255,.15),rgba(139,92,246,.10));
  border:2px solid rgba(108,99,255,.25);display:flex;align-items:center;justify-content:center;
  font-size:16px;animation:glow3 3s ease-in-out infinite;}
@keyframes glow3{0%,100%{box-shadow:0 0 8px rgba(108,99,255,.25);}
                 50%{box-shadow:0 0 16px rgba(108,99,255,.45);}}
.qa-g{display:grid;grid-template-columns:repeat(2,1fr);gap:6px;}
.qa-item{display:flex;flex-direction:column;align-items:center;gap:4px;
  padding:10px 8px;border-radius:var(--r2);background:var(--card2);
  border:1px solid var(--border);cursor:pointer;text-align:center;transition:all .2s;}
.qa-item:hover{background:rgba(108,99,255,.10);border-color:rgba(108,99,255,.25);transform:translateY(-2px);}
.qa-ico{font-size:16px;margin-bottom:1px;}
.qa-lbl{font-size:10px;font-weight:600;color:var(--t2);line-height:1.25;}
.tgrid{display:grid;grid-template-columns:repeat(3,1fr);gap:6px;}
.tc{border-radius:var(--r2);overflow:hidden;cursor:pointer;transition:all .22s;}
.tc:hover{transform:translateY(-3px);box-shadow:0 6px 20px rgba(0,0,0,.3);}
.tcimg{height:48px;display:flex;align-items:center;justify-content:center;font-size:18px;}
.tclbl{padding:5px 6px;font-size:9.5px;font-weight:700;color:var(--t2);text-align:center;
  background:var(--card2);border:1px solid var(--border);border-top:none;
  border-radius:0 0 var(--r2) var(--r2);line-height:1.3;}
.sgrid{display:grid;grid-template-columns:repeat(3,1fr);gap:5px;}
.stile{background:var(--card2);border-radius:var(--r1);padding:8px 10px;border:1px solid var(--border);}
.stl{font-size:8.5px;color:var(--t3);text-transform:uppercase;letter-spacing:1px;
  margin-bottom:2px;font-family:var(--fd);}
.stv{font-size:15px;font-weight:800;color:var(--accent3);font-family:var(--fd);}
.tone-g{display:grid;grid-template-columns:1fr 1fr;gap:4px;}
.tone-opt{padding:7px 8px;border-radius:var(--r2);font-size:11px;font-weight:600;
  color:var(--t3);background:var(--card2);border:1.5px solid var(--border);
  transition:all .18s;text-align:center;cursor:pointer;}
.tone-opt:hover{background:rgba(108,99,255,.10);border-color:rgba(108,99,255,.25);color:var(--accent3);}
.tone-opt.tact{background:rgba(108,99,255,.12);border-color:var(--accent);color:var(--accent3);font-weight:700;}

/* ─── VIEW CARDS ─── */
.vcard{background:var(--card2);border-radius:var(--r3);padding:10px 13px;
  border:1px solid var(--border);margin-bottom:6px;cursor:pointer;transition:all .18s;}
.vcard:hover{background:var(--hover);border-color:var(--border2);}
.vcard-t{font-family:var(--fd);font-size:13px;font-weight:700;color:var(--t1);margin-bottom:2px;}
.vcard-s{font-size:11.5px;color:var(--t3);}
.view-hdr{font-family:var(--fd);font-size:17px;font-weight:800;color:var(--t1);margin-bottom:14px;}

/* ─── TOAST ─── */
.toast{position:fixed;bottom:20px;right:20px;z-index:9999;padding:11px 18px;
  border-radius:var(--r3);font-size:13px;font-family:var(--fb);font-weight:500;
  max-width:360px;animation:tin .3s ease-out;}
.t-err{background:rgba(244,63,94,.12);border:1px solid rgba(244,63,94,.3);color:var(--rose);}
.t-ok{background:rgba(16,185,129,.10);border:1px solid rgba(16,185,129,.25);color:var(--emerald);}
.t-warn{background:rgba(249,115,22,.10);border:1px solid rgba(249,115,22,.25);color:var(--orange);}
.t-inf{background:rgba(108,99,255,.10);border:1px solid rgba(108,99,255,.25);color:var(--accent3);}
@keyframes tin{from{opacity:0;transform:translateY(8px);}to{opacity:1;transform:none;}}

/* ─── STREAMLIT OVERRIDES ─── */
.stTextArea textarea{
  background:var(--card2)!important;border:none!important;color:var(--t1)!important;
  font-family:var(--fb)!important;font-size:14px!important;resize:none!important;
  outline:none!important;box-shadow:none!important;padding:4px 0!important;line-height:1.6!important;}
.stTextArea textarea::placeholder{color:var(--t4)!important;}
.stTextArea>div,[data-baseweb="textarea"]{
  background:transparent!important;border:none!important;box-shadow:none!important;}
[data-baseweb="textarea"]>div{background:transparent!important;border:none!important;}

/* All buttons → ghost dark */
.stButton>button{background:var(--card)!important;color:var(--t2)!important;
  border:1px solid var(--border2)!important;border-radius:var(--r2)!important;
  font-family:var(--fb)!important;font-size:12px!important;padding:6px 12px!important;
  height:auto!important;box-shadow:none!important;transition:all .18s!important;font-weight:500!important;}
.stButton>button:hover{background:var(--hover)!important;color:var(--t1)!important;
  border-color:rgba(108,99,255,.3)!important;transform:none!important;}

/* Send button — last column */
section[data-testid="column"]:last-child .stButton>button{
  background:linear-gradient(135deg,var(--accent),var(--accent2))!important;
  color:white!important;border:none!important;border-radius:var(--r2)!important;
  font-family:var(--fd)!important;font-weight:700!important;font-size:13px!important;
  padding:10px 18px!important;box-shadow:0 4px 16px rgba(108,99,255,.3)!important;}
section[data-testid="column"]:last-child .stButton>button:hover{
  transform:translateY(-1px)!important;box-shadow:0 6px 22px rgba(108,99,255,.45)!important;}

/* Sidebar buttons */
[data-testid="stSidebar"] .stButton>button{
  background:rgba(255,255,255,.06)!important;color:var(--t2)!important;
  border:1px solid var(--border2)!important;border-radius:var(--r2)!important;}
[data-testid="stSidebar"] .stButton>button:hover{
  background:rgba(108,99,255,.12)!important;color:var(--t1)!important;border-color:rgba(108,99,255,.3)!important;}

[data-baseweb="select"]>div{background:rgba(255,255,255,.05)!important;
  border-color:var(--border2)!important;border-radius:var(--r2)!important;color:var(--t2)!important;}
[data-testid="stExpander"]{background:rgba(255,255,255,.03)!important;
  border:1px solid var(--border)!important;border-radius:var(--r3)!important;}
[data-testid="stExpander"] summary{color:var(--t2)!important;font-size:12.5px!important;}
[data-testid="stDownloadButton"] button{background:rgba(108,99,255,.10)!important;
  color:var(--accent3)!important;border:1px solid rgba(108,99,255,.2)!important;box-shadow:none!important;}
[data-testid="stSidebar"] label{color:var(--t3)!important;font-size:11px!important;}
[data-testid="stTextInput"]>div>div>input{background:rgba(255,255,255,.05)!important;
  border-color:var(--border2)!important;border-radius:var(--r2)!important;
  color:var(--t2)!important;font-size:12.5px!important;}
[data-testid="stFileUploader"]{background:rgba(108,99,255,.04)!important;
  border:1px dashed rgba(108,99,255,.2)!important;border-radius:var(--r3)!important;}
[data-testid="stFileUploader"] label{color:var(--t3)!important;}
hr{border:none!important;border-top:1px solid var(--border)!important;margin:10px 0!important;}
.stAlert{background:var(--card)!important;border:1px solid var(--border2)!important;
  border-radius:var(--r3)!important;color:var(--t2)!important;}
::-webkit-scrollbar{width:4px;height:4px;}
::-webkit-scrollbar-track{background:transparent;}
::-webkit-scrollbar-thumb{background:var(--border2);border-radius:2px;}
[data-testid="column"]{padding:0!important;}
</style>
""", unsafe_allow_html=True)

st.markdown("""
<script>
function cpCode(btn){
  const pre=btn.closest('.cw').querySelector('code');
  navigator.clipboard.writeText(pre.innerText).then(()=>{
    const o=btn.textContent;btn.textContent='✓ Copied';
    setTimeout(()=>btn.textContent=o,2000);
  });
}
function scrollChat(){
  document.querySelectorAll('.chatarea').forEach(a=>{a.scrollTop=a.scrollHeight;});
}
const _mo=new MutationObserver(scrollChat);
document.addEventListener('DOMContentLoaded',()=>{
  const r=document.getElementById('root');
  if(r)_mo.observe(r,{childList:true,subtree:true});
  scrollChat();
});
setTimeout(scrollChat,600);
</script>
""", unsafe_allow_html=True)

# ═══════════════════════════════════════════════════════
# SIDEBAR
# ═══════════════════════════════════════════════════════
with st.sidebar:
    st.markdown("""
    <div class="sb"><div class="sb-logo">
      <div class="sb-mark">⬡</div>
      <div><div class="sb-name">NexusAI</div><div class="sb-ver">2026 Edition</div></div>
    </div></div>""", unsafe_allow_html=True)

    # Provider
    st.markdown('<div class="sbl" style="margin:0 2px 6px;">AI Provider</div>', unsafe_allow_html=True)
    plist = list(PROVIDERS.keys())
    cur_p = st.session_state.active_provider
    if cur_p not in plist: cur_p = "anthropic"
    sel_p = st.selectbox("pv", plist,
        format_func=lambda k: f"{PROVIDERS[k]['icon']}  {PROVIDERS[k]['name']}",
        index=plist.index(cur_p), label_visibility="collapsed", key="psel")
    if sel_p != st.session_state.active_provider:
        st.session_state.active_provider = sel_p
        st.session_state.model_key = list(PROVIDERS[sel_p]["models"].keys())[0]
        st.rerun()
    cur_prov = PROVIDERS[sel_p]

    # Model
    st.markdown('<div class="sbl" style="margin:10px 2px 6px;">Model</div>', unsafe_allow_html=True)
    mlist = list(cur_prov["models"].keys())
    cmk = st.session_state.model_key
    if cmk not in mlist: cmk = mlist[0]; st.session_state.model_key = cmk
    sel_m = st.selectbox("md", mlist, format_func=lambda k: cur_prov["models"][k],
        index=mlist.index(cmk), label_visibility="collapsed", key="msel")
    st.session_state.model_key = sel_m

    # API Key
    no_key = cur_prov.get("no_key", False)
    st.markdown(f'<div class="sbl" style="margin:10px 2px 6px;">{"No Key Needed" if no_key else "API Key"}</div>',
                unsafe_allow_html=True)
    if not no_key:
        stored = st.session_state.get(f"sk_{sel_p}", "")
        ki = st.text_input(f"kw_{sel_p}", value=stored, type="password",
            placeholder=cur_prov["key_hint"], label_visibility="collapsed", key=f"kw_{sel_p}")
        kc1,kc2 = st.columns([3,1])
        with kc1:
            if st.button("Save Key", use_container_width=True, key=f"sk_btn_{sel_p}"):
                k = ki.strip()
                if k: st.session_state[f"sk_{sel_p}"]=k; st.session_state.toast=("ok",f"✓ {cur_prov['name']} key saved"); st.rerun()
                else: st.session_state.toast=("err","Key cannot be empty"); st.rerun()
        with kc2:
            if st.button("✕", use_container_width=True, key=f"ck_{sel_p}"):
                st.session_state[f"sk_{sel_p}"]=""
                if f"kw_{sel_p}" in st.session_state: del st.session_state[f"kw_{sel_p}"]
                st.rerun()
        eff = resolve_key(sel_p)
        env_s = bool(os.environ.get(ENV_MAP.get(sel_p,""),""))
        if eff:
            m = eff[:6]+"•"*max(4,len(eff)-10)+eff[-4:] if len(eff)>10 else "••••••"
            src = " (env)" if env_s and not stored else ""
            st.markdown(f'<div class="key-ok">✓ Connected{src}: <code>{m}</code></div>', unsafe_allow_html=True)
        else:
            d2 = cur_prov["docs"]; dom = d2.split("//")[1].split("/")[0] if "//" in d2 else d2
            st.markdown(f'<div class="key-no">⚠ Get key → <a href="{d2}" target="_blank">{dom}</a></div>', unsafe_allow_html=True)
    else:
        ou = st.text_input("Ollama URL", value=st.session_state.get("ollama_url","http://localhost:11434"),
            label_visibility="visible", key="olu")
        st.session_state.ollama_url = ou
        st.markdown('<div class="key-ok">◉ Local — no key needed</div>', unsafe_allow_html=True)

    st.markdown('<div class="sb-div"></div>', unsafe_allow_html=True)

    if st.button("⬡  New Session", use_container_width=True, key="nc"):
        save_conv(); st.session_state.messages=[]; st.session_state.conv_name="New Session"
        st.session_state.active_view="chat"; st.rerun()

    st.markdown('<div class="sbl" style="margin:3px 2px 7px;">Recent Sessions</div>', unsafe_allow_html=True)
    for i,conv in enumerate(st.session_state.convs[-7:]):
        ri = max(0,len(st.session_state.convs)-7)+i
        act = "act" if conv["name"]==st.session_state.conv_name else ""
        nm = (conv["name"][:24]+"…") if len(conv["name"])>24 else conv["name"]
        cnt = len(conv.get("msgs",[])); ico = conv.get("icon","◈")
        st.markdown(f"""<div class="sb-ci {act}">
          <span>{ico}</span><span class="cit">{nm}</span>
          <span class="cim">{cnt}m</span></div>""", unsafe_allow_html=True)
        if st.button("▶", key=f"lc_{i}", help=nm):
            load_conv(ri); st.session_state.active_view="chat"; st.rerun()

    st.markdown('<div class="sb-div"></div>', unsafe_allow_html=True)

    for ico,lbl,vw in [("◎","Explore","explore"),("◌","History","history"),
                        ("◈","Saved","saved"),("⚙","Settings","settings")]:
        act = "nact" if st.session_state.active_view==vw else ""
        st.markdown(f'<div class="sb-nav {act}"><span class="ni">{ico}</span><span>{lbl}</span></div>',
                    unsafe_allow_html=True)
        if st.button(lbl, key=f"nav_{vw}", help=lbl):
            st.session_state.active_view=vw; st.rerun()

    st.markdown('<div class="sb-div"></div>', unsafe_allow_html=True)

    with st.expander("⚙ Advanced"):
        st.session_state.temperature = st.slider("Temperature",0.0,1.0,st.session_state.temperature,0.05)
        st.session_state.max_tokens = st.select_slider("Max Tokens",
            options=[256,512,1024,2048,4096,8192],value=st.session_state.max_tokens)
        st.session_state.stream_mode = st.checkbox("Streaming",st.session_state.stream_mode)
        st.session_state.code_mode   = st.checkbox("Code Mode ⚙",st.session_state.code_mode)

    st.markdown('<div class="sbl" style="margin:10px 2px 5px;">Attach File</div>', unsafe_allow_html=True)
    upl = st.file_uploader("f", type=["txt","py","md","csv","json","html","js","ts","xml"],
        label_visibility="collapsed", key="upl")
    if upl:
        st.session_state.file_content=upl.read().decode("utf-8",errors="replace")
        st.session_state.file_name=upl.name; st.success(f"✓ {upl.name}")
    if st.session_state.file_content:
        if st.button("✕ Remove", key="rmf"):
            st.session_state.file_content=None; st.session_state.file_name=None; st.rerun()

    if st.session_state.messages:
        st.markdown("")
        cc1,cc2=st.columns(2)
        with cc1:
            st.download_button("↓ Export",data=export_md(),
                file_name=f"nexus_{datetime.now().strftime('%Y%m%d_%H%M')}.md",
                mime="text/markdown",use_container_width=True)
        with cc2:
            if st.button("⊘ Clear",use_container_width=True,key="clr"):
                save_conv(); st.session_state.messages=[];
                st.session_state.conv_name="New Session"; st.rerun()

    st.markdown("""<div style="text-align:center;margin-top:20px;font-size:9.5px;
      color:var(--t4);font-family:var(--fd);letter-spacing:1.5px;">
      NEXUSAI · 2026 · PRO</div>""", unsafe_allow_html=True)

# ═══════════════════════════════════════════════════════
# TOP BAR
# ═══════════════════════════════════════════════════════
unread = sum(1 for n in st.session_state.notifications if not n["read"])
nd = '<span class="nd"></span>' if unread else ""
code_act = "active" if st.session_state.code_mode else ""
st.markdown(f"""
<div class="topbar">
  <div class="tb-l">
    <span class="tb-logo">NexusAI</span>
    <span class="tb-slash">/</span>
    <span class="tb-conv">{st.session_state.conv_name}</span>
    <span class="tb-badge">PRO</span>
  </div>
  <div class="tb-r">
    <div class="prov-chip">
      <span class="live-dot"></span>
      {_prov["icon"]} {_prov["name"]}
    </div>
    <div class="tb-btn {code_act}" title="Code Mode">⚙</div>
    <div class="tb-btn" title="Notifications">⬡{nd}</div>
    <div class="tb-av">U</div>
  </div>
</div>""", unsafe_allow_html=True)

tbc = st.columns([8,1,1])
with tbc[1]:
    if st.button("⬡ Notif", key="nt", help="Notifications"):
        st.session_state.notif_open = not st.session_state.notif_open
        for n in st.session_state.notifications: n["read"]=True
        st.rerun()
with tbc[2]:
    if st.button("⚙ Code", key="tcode", help="Toggle Code Mode"):
        st.session_state.code_mode = not st.session_state.code_mode
        st.session_state.toast=("inf",f"Code Mode {'ON' if st.session_state.code_mode else 'OFF'}")
        st.rerun()

if st.session_state.notif_open:
    ni = "".join(['<div class="npi '+('unr' if not n['read'] else '')+'">'+
                  '<span class="npi-ico">'+n["icon"]+'</span>'+
                  '<div><div class="npi-txt">'+n["text"]+'</div>'+
                  '<div class="npi-t">'+n["time"]+'</div></div></div>'
                  for n in st.session_state.notifications[:6]])
    st.markdown(f'<div class="npanel"><div class="nph">Notifications ({unread} unread)</div>{ni}</div>',
                unsafe_allow_html=True)

# ═══════════════════════════════════════════════════════
# MAIN LAYOUT
# ═══════════════════════════════════════════════════════
cc, cr = st.columns([3, 1.04])

# ────────────────────────────────────
# CENTER
# ────────────────────────────────────
with cc:
    # Quick action chips
    qa_cols = st.columns(len(QUICK_ACTIONS))
    for i,(ico,lbl,prompt) in enumerate(QUICK_ACTIONS):
        with qa_cols[i]:
            if st.button(f"{ico} {lbl}", key=f"qa_{i}", use_container_width=True):
                st.session_state.pending_prompt=prompt
                st.session_state.active_view="chat"; st.rerun()

    st.markdown('<div class="cpanel">', unsafe_allow_html=True)

    # Conversation header
    if st.session_state.messages:
        mc = len(st.session_state.messages)
        ac = sum(1 for m in st.session_state.messages if m["role"]=="assistant")
        wc = st.session_state.total_words
        st.markdown(f"""
        <div class="conv-hdr">
          <div>
            <div class="conv-title">◈ {st.session_state.conv_name}</div>
            <div class="conv-meta">{mc} messages · {ac} AI replies · {fmt(wc)} words generated · {PROVIDERS[_pid]["icon"]} {PROVIDERS[_pid]["name"]}</div>
          </div>
          <div class="conv-acts">
            <span class="cact">⬡ Search</span>
            <span class="cact">↓ Export</span>
            <span class="cact">◎ Share</span>
          </div>
        </div>""", unsafe_allow_html=True)

    # Welcome zone
    cur_m_disp = cur_prov["models"].get(st.session_state.model_key,"").split("—")[0].strip() or st.session_state.model_key
    key_status = "◎ Ready" if _key_ok else "⚠ No Key"
    ks_col = "var(--emerald)" if _key_ok else "var(--amber)"
    last_rt = f"{st.session_state.resp_times[-1]:.1f}s" if st.session_state.resp_times else "—"
    st.markdown(f"""
    <div class="wzone">
      <div class="wrow">
        <div class="wtitle">Good to see you.</div>
        <div class="wstatus">
          <span class="model-chip">⬡ {cur_m_disp}</span>
          <span style="font-size:11px;color:{ks_col};font-family:var(--fm);">{key_status}</span>
          <span style="font-size:11px;color:var(--t4);font-family:var(--fm);">Last: {last_rt}</span>
        </div>
      </div>
      <div class="wsub">What would you like to explore today?</div>
    </div>""", unsafe_allow_html=True)

    # Smart chips (when empty)
    if len(st.session_state.messages) < 2:
        smarts = ["Write something","Debug my code","Explain clearly","Brainstorm ideas","Summarize this","Research topic","Build a plan","Teach me"]
        chips_html = "".join([f'<span class="qchip">{s}</span>' for s in smarts])
        st.markdown(f"""
        <div style="padding:10px 24px 12px;border-bottom:1px solid var(--border);">
          <div class="qlabel">Quick starts</div>
          <div class="qchips">{chips_html}</div>
        </div>""", unsafe_allow_html=True)

    # Chat area
    st.markdown('<div class="chatarea">', unsafe_allow_html=True)

    # ── SETTINGS VIEW ──
    if st.session_state.active_view == "settings":
        st.markdown('<div class="view-hdr">⚙ Settings</div>', unsafe_allow_html=True)
        s1,s2 = st.columns(2)
        with s1:
            st.markdown("**Response Tone**")
            for k,(ico,nm) in TONES.items():
                act = "tact" if st.session_state.tone==k else ""
                st.markdown(f'<div class="tone-opt {act}" style="margin-bottom:4px;">{ico} {nm}</div>', unsafe_allow_html=True)
                if st.button(f"→ {nm}", key=f"st_{k}", use_container_width=True):
                    st.session_state.tone=k; st.session_state.toast=("inf",f"Tone → {nm}"); st.rerun()
        with s2:
            st.markdown("**Interface**")
            st.session_state.stream_mode = st.checkbox("Streaming responses", st.session_state.stream_mode, key="ss")
            st.session_state.code_mode   = st.checkbox("Code mode", st.session_state.code_mode, key="sc")
            st.markdown("**Parameters**")
            st.session_state.temperature = st.slider("Temperature",0.0,1.0,st.session_state.temperature,0.05,key="stmp")
            st.session_state.max_tokens  = st.select_slider("Max Tokens",
                options=[256,512,1024,2048,4096,8192],value=st.session_state.max_tokens,key="smtk")

    # ── HISTORY VIEW ──
    elif st.session_state.active_view == "history":
        st.markdown('<div class="view-hdr">◌ Session History</div>', unsafe_allow_html=True)
        if not st.session_state.convs:
            st.markdown('<div style="text-align:center;padding:30px;color:var(--t3);">No sessions yet.</div>', unsafe_allow_html=True)
        else:
            hs = st.text_input("Search", placeholder="⬡ Filter sessions…", key="hsr", label_visibility="collapsed")
            filtered = [(i,c) for i,c in enumerate(reversed(st.session_state.convs))
                        if not hs or hs.lower() in c["name"].lower()]
            ri_map = {j: len(st.session_state.convs)-1-j for j in range(len(st.session_state.convs))}
            if not filtered:
                st.markdown(f'<div style="text-align:center;padding:20px;color:var(--t3);">No results for "{hs}"</div>', unsafe_allow_html=True)
            for j,(fi,conv) in enumerate(filtered):
                ri = ri_map[fi]
                nm = conv["name"]; cnt = len(conv.get("msgs",[])); t = conv.get("time","")
                st.markdown(f'<div class="vcard"><div class="vcard-t">{conv.get("icon","◈")} {nm}</div><div class="vcard-s">{cnt} messages · {t}</div></div>', unsafe_allow_html=True)
                hc1,hc2 = st.columns([4,1])
                with hc1:
                    if st.button("Load session", key=f"hl_{j}", use_container_width=True):
                        load_conv(ri); st.session_state.active_view="chat"; st.rerun()
                with hc2:
                    if st.button("✕", key=f"hd_{j}", use_container_width=True):
                        st.session_state.convs.pop(ri); st.rerun()

    # ── SAVED VIEW ──
    elif st.session_state.active_view == "saved":
        st.markdown('<div class="view-hdr">◈ Pinned Messages</div>', unsafe_allow_html=True)
        if not st.session_state.saved_msgs:
            st.markdown('<div style="text-align:center;padding:30px;color:var(--t3);">No pinned messages yet.<br>Click ◈ on any AI reply to pin it.</div>', unsafe_allow_html=True)
        else:
            for i,sm in enumerate(st.session_state.saved_msgs):
                rendered = render_md(sm["content"])
                st.markdown(f'<div class="vcard"><div class="vcard-t">◈ Pinned · {sm.get("time","")}</div><div class="aibub" style="margin-top:8px;">{rendered}</div></div>', unsafe_allow_html=True)
                if st.button("✕ Remove", key=f"rs_{i}"):
                    st.session_state.saved_msgs.pop(i); st.rerun()

    # ── EXPLORE VIEW ──
    elif st.session_state.active_view == "explore":
        st.markdown('<div class="view-hdr">◎ Explore</div>', unsafe_allow_html=True)
        if st.session_state.prompt_history:
            st.markdown('<div style="font-family:var(--fd);font-size:13px;font-weight:700;color:var(--t2);margin-bottom:8px;">↩ Recent Prompts</div>', unsafe_allow_html=True)
            for rpi,rp in enumerate(st.session_state.prompt_history[:5]):
                rp_s = rp[:68]+"…" if len(rp)>68 else rp
                rc1,rc2 = st.columns([5,1])
                with rc1: st.markdown(f'<div class="vcard" style="padding:8px 12px;margin-bottom:4px;"><div class="vcard-s" style="color:var(--t1);">{rp_s}</div></div>', unsafe_allow_html=True)
                with rc2:
                    if st.button("Use", key=f"rp_{rpi}", use_container_width=True):
                        st.session_state.pending_prompt=rp; st.session_state.active_view="chat"; st.rerun()
            st.markdown('<hr>', unsafe_allow_html=True)
        st.markdown('<div style="font-family:var(--fd);font-size:13px;font-weight:700;color:var(--t2);margin-bottom:9px;">⬡ Prompt Library</div>', unsafe_allow_html=True)
        ec = st.columns(3)
        for i,(eico,enm,ep) in enumerate(EXPLORE_LIBRARY):
            with ec[i%3]:
                st.markdown(f'<div class="vcard"><div class="vcard-t">{eico} {enm}</div><div class="vcard-s">{ep[:50]}…</div></div>', unsafe_allow_html=True)
                if st.button("→", key=f"ex_{i}", use_container_width=True):
                    st.session_state.pending_prompt=ep; st.session_state.active_view="chat"; st.rerun()

    # ── MAIN CHAT ──
    else:
        if not st.session_state.messages:
            if not _key_ok:
                pn=_prov["name"]; ph=_prov["key_hint"]; pd=_prov["docs"]
                dom = pd.split("//")[1].split("/")[0] if "//" in pd else pd
                st.markdown(f"""<div class="kbanner">
                  <div class="kbanner-t">⚠ API Key Required</div>
                  <div class="kbanner-b">Enter your <strong>{pn}</strong> key in the sidebar.
                    Format: <code style="font-family:var(--fm);font-size:10px;background:rgba(249,115,22,.1);padding:1px 5px;border-radius:3px;">{ph}</code><br>
                    <a href="{pd}" target="_blank">Get your free key at {dom} →</a>
                  </div></div>""", unsafe_allow_html=True)
            st.markdown("""<div class="empty"><div>
              <div class="empty-icon">⬡</div>
              <div class="empty-t">Start a new session</div>
              <div class="empty-s">Type a message below, click a quick action above, or explore the prompt library.</div>
            </div></div>""", unsafe_allow_html=True)
        else:
            for idx,msg in enumerate(st.session_state.messages):
                is_u=msg["role"]=="user"; raw=msg["content"]; t_s=msg.get("time","")
                if is_u:
                    safe=raw.replace("&","&amp;").replace("<","&lt;").replace(">","&gt;").replace("\n","<br>")
                    st.markdown(f"""<div class="umsg"><div>
                      <div class="ubub">{safe}</div>
                      <div class="umts">{t_s}</div>
                    </div></div>""", unsafe_allow_html=True)
                    ua1,ua2,_ = st.columns([1,1,9])
                    with ua1:
                        if st.button("↩",key=f"ry_{idx}",help="Retry"):
                            st.session_state.retry_idx=idx; st.rerun()
                    with ua2:
                        if st.button("⬡",key=f"cu_{idx}",help="Copy"):
                            st.session_state.toast=("inf","Copied to clipboard"); st.rerun()
                else:
                    rendered=render_md(raw)
                    tok=msg.get("tokens",""); fb=msg.get("feedback")
                    elapsed=msg.get("elapsed","")
                    wc=len(raw.split()); rt="<1m" if wc<200 else f"{wc//200}m read"
                    prov_n=PROVIDERS.get(msg.get("provider",_pid),{}).get("name","")
                    mdl_n=PROVIDERS.get(msg.get("provider",_pid),{}).get("models",{}).get(msg.get("model",""),"").split("—")[0].strip()
                    th=f'<span class="tokbadge">{tok} tok</span>' if tok else ""
                    ph_=f'<span class="pbadge">{prov_n}</span>' if prov_n else ""
                    st.markdown(f"""<div class="aimsg">
                      <div class="aiav">⬡</div>
                      <div class="aibody">
                        <div class="ainame">NexusAI {th} {ph_}</div>
                        <div class="aibub">{rendered}</div>
                        <div class="aimts">{t_s} · {wc} words · {rt}{f" · {elapsed}s" if elapsed else ""}</div>
                      </div>
                    </div>""", unsafe_allow_html=True)
                    ab1,ab2,ab3,ab4,ab5,_ = st.columns([1,1,1,1,1,6])
                    with ab1:
                        if st.button("⬡",key=f"ca_{idx}",help="Copy"):
                            st.session_state.toast=("inf","Copied"); st.rerun()
                    with ab2:
                        if st.button("↺",key=f"rg_{idx}",help="Regenerate"):
                            if idx>0 and st.session_state.messages[idx-1]["role"]=="user":
                                pp=st.session_state.messages[idx-1]["content"]
                                st.session_state.messages=st.session_state.messages[:idx-1]
                                st.session_state.pending_prompt=pp; st.rerun()
                    with ab3:
                        if st.button("◈",key=f"pn_{idx}",help="Pin"):
                            st.session_state.saved_msgs.append({"content":raw,"time":t_s})
                            st.session_state.toast=("ok","◈ Pinned"); st.rerun()
                    with ab4:
                        gcls = "gd" if fb=="good" else ""
                        if st.button("▲",key=f"gd_{idx}",help="Good"):
                            st.session_state.messages[idx]["feedback"]="good"
                            st.session_state.toast=("ok","Thanks!"); st.rerun()
                    with ab5:
                        bcls = "bd" if fb=="bad" else ""
                        if st.button("▽",key=f"bd_{idx}",help="Poor"):
                            st.session_state.messages[idx]["feedback"]="bad"
                            st.session_state.toast=("inf","Got it — noted"); st.rerun()

    st.markdown('</div>', unsafe_allow_html=True)  # chatarea

    # ── INPUT ──
    tok_u = st.session_state.total_tokens
    tok_b = st.session_state.max_tokens * max(1, len([m for m in st.session_state.messages if m["role"]=="assistant"])+1)
    tok_p = min(100, int(tok_u/max(tok_b,1)*100))
    tok_col = "#F43F5E" if tok_p>80 else "#F59E0B" if tok_p>50 else "#6C63FF"
    tok_bg  = f"linear-gradient(90deg,#F43F5E,#F97316)" if tok_p>80 else "linear-gradient(90deg,var(--accent),var(--accent2))"

    if st.session_state.messages:
        st.markdown(f"""<div style="padding:6px 24px 0;background:var(--bg3);">
          <div class="tok-bar-wrap">
            <div class="tok-bar-track"><div class="tok-bar-fill" style="width:{tok_p}%;background:{tok_bg};"></div></div>
            <span class="tok-label" style="color:{tok_col};">{fmt(tok_u)} tok · {tok_p}%</span>
          </div>
        </div>""", unsafe_allow_html=True)

    if st.session_state.file_content:
        st.markdown(f'<div style="padding:0 24px 0;background:var(--bg3);"><div class="att-bar">⬡ <strong>{st.session_state.file_name}</strong> — {len(st.session_state.file_content):,} chars attached</div></div>', unsafe_allow_html=True)

    st.markdown('<div class="izone"><div class="ishell">', unsafe_allow_html=True)
    ic,bc = st.columns([11,1.8])
    with ic:
        tone_n = TONES[st.session_state.tone][1]
        user_input = st.text_area("msg",
            placeholder=f"Message NexusAI  ·  {tone_n} mode  ·  Shift+Enter for new line",
            height=72, key="ui", label_visibility="collapsed")
    with bc:
        send = st.button("Send →", key="sb", use_container_width=True)

    char=len(user_input) if user_input else 0
    char_col="#F43F5E" if char>3800 else "#F59E0B" if char>3000 else "var(--t4)"
    char_w=600 if char>3000 else 400
    code_cls="on" if st.session_state.code_mode else ""
    tone_ico=TONES[st.session_state.tone][0]
    tone_lbl=TONES[st.session_state.tone][1]
    pname=PROVIDERS[st.session_state.active_provider]["name"]
    att_s=(f'<span class="ihint on">⬡ {st.session_state.file_name}</span>') if st.session_state.file_content else ""
    st.markdown(f"""</div>
    <div class="ifoot">
      <div class="ihints">
        <span class="ihint">{tone_ico} {tone_lbl}</span>
        <span class="ihint {code_cls}">⚙ Code</span>
        <span class="ihint">◈ {pname}</span>
        <span class="ihint" style="color:var(--t4);">Shift+↵ newline</span>
        {att_s}
      </div>
      <span class="ichar" style="color:{char_col};font-weight:{char_w};">{char}/4000</span>
    </div></div></div>""", unsafe_allow_html=True)  # izone + cpanel

# ────────────────────────────────────
# RIGHT PANEL
# ────────────────────────────────────
with cr:
    chats_t = st.session_state.chats_today + sum(1 for m in st.session_state.messages if m["role"]=="user")
    bd=st.session_state.bar_data; mx=max(bd) or 1
    bars="".join([f'<div class="cbar" style="height:{int(h/mx*100)}%;"></div>' for h in bd])
    ai_cnt=sum(1 for m in st.session_state.messages if m["role"]=="assistant")
    avg_rt=f"{sum(st.session_state.resp_times)/len(st.session_state.resp_times):.1f}s" if st.session_state.resp_times else "—"
    tps_v="—"
    ai_ms=[m for m in st.session_state.messages if m["role"]=="assistant"]
    if ai_ms and st.session_state.resp_times:
        lt=ai_ms[-1].get("tokens",0); lr=st.session_state.resp_times[-1]
        if lt>0 and lr>0: tps_v=f"{int(lt/lr)}"
    cur_mn=cur_prov["models"].get(st.session_state.model_key,"").split("—")[0].strip() or st.session_state.model_key
    stream_s="🌊 Stream" if st.session_state.stream_mode else "📦 Batch"
    key_s2="✓ Key OK" if _key_ok else "⚠ No Key"
    kc2="#10B981" if _key_ok else "#F59E0B"

    # Usage
    st.markdown(f"""<div class="rc"><div class="rct">Usage</div>
      <div class="statrr">
        <div><div class="stat-n">{chats_t}</div><div class="stat-l">Messages Today</div></div>
        <div class="chart-wrap">{bars}</div>
      </div></div>""", unsafe_allow_html=True)

    # Model
    st.markdown(f"""<div class="rc"><div class="rct">Active Model</div>
      <div class="model-rr">
        <div>
          <div class="mn">{cur_mn}</div>
          <div class="ms">{_prov["icon"]} {_prov["name"]}</div>
          <div class="mbadges">
            <span class="mbadge" style="background:rgba(108,99,255,.10);color:var(--accent3);">{stream_s}</span>
            <span class="mbadge" style="background:rgba(0,0,0,.2);color:{kc2};">{key_s2}</span>
            <span class="mbadge" style="background:rgba(0,0,0,.2);color:var(--t3);">🌡 {st.session_state.temperature}</span>
          </div>
        </div>
        <div class="mico">⬡</div>
      </div></div>""", unsafe_allow_html=True)

    # Quick Actions
    st.markdown('<div class="rc"><div class="rct">Quick Actions</div><div class="qa-g">', unsafe_allow_html=True)
    qac = st.columns(2)
    qa_panel = [
        ("⬡","Summarize","Summarize our conversation as a structured briefing with key takeaways."),
        ("◈","Explain","Explain the last response in simpler terms with an analogy."),
        ("⚙","Code It","Convert the last response into working code with comments."),
        ("✦","Expand","Expand on the most interesting idea from the last response."),
    ]
    for i,(ico,lbl,pr) in enumerate(qa_panel):
        with qac[i%2]:
            st.markdown(f"""<div class="qa-item">
              <div class="qa-ico">{ico}</div>
              <div class="qa-lbl">{lbl}</div>
            </div>""", unsafe_allow_html=True)
            if st.button("→", key=f"qap_{i}", use_container_width=True, help=lbl):
                st.session_state.pending_prompt=pr; st.session_state.active_view="chat"; st.rerun()
    st.markdown('</div></div>', unsafe_allow_html=True)

    # Topics
    topics = [
        ("◎","tt","Science","What's the most mind-bending scientific discovery of 2026?"),
        ("⬡","th","Finance","Explain how to build long-term wealth from scratch in 2026."),
        ("⚙","tv","Build","Give me a step-by-step guide to build a SaaS product solo."),
    ]
    bg_map={"tt":"linear-gradient(135deg,#1E3A5F,#2563EB)","th":"linear-gradient(135deg,#78350F,#D97706)","tv":"linear-gradient(135deg,#164E63,#0891B2)"}
    st.markdown('<div class="rc"><div class="rct">Explore Topics</div><div class="tgrid">', unsafe_allow_html=True)
    tpc=st.columns(3)
    for i,(ico,cls,lbl,pr) in enumerate(topics):
        with tpc[i]:
            st.markdown(f"""<div class="tc">
              <div class="tcimg" style="background:{bg_map[cls]};">{ico}</div>
              <div class="tclbl">{lbl}</div>
            </div>""", unsafe_allow_html=True)
            if st.button("→", key=f"tp_{i}", use_container_width=True, help=lbl):
                st.session_state.pending_prompt=pr; st.session_state.active_view="chat"; st.rerun()
    st.markdown('</div></div>', unsafe_allow_html=True)

    # Stats
    st.markdown(f"""<div class="rc"><div class="rct">Session Stats</div>
      <div class="sgrid">
        <div class="stile"><div class="stl">Tokens</div><div class="stv">{fmt(st.session_state.total_tokens)}</div></div>
        <div class="stile"><div class="stl">Replies</div><div class="stv">{ai_cnt}</div></div>
        <div class="stile"><div class="stl">Words</div><div class="stv">{fmt(st.session_state.total_words)}</div></div>
        <div class="stile"><div class="stl">Avg Time</div><div class="stv">{avg_rt}</div></div>
        <div class="stile"><div class="stl">Tok/s</div><div class="stv">{tps_v}</div></div>
        <div class="stile"><div class="stl">Sessions</div><div class="stv">{len(st.session_state.convs)}</div></div>
      </div></div>""", unsafe_allow_html=True)

    # Tone
    st.markdown('<div class="rc"><div class="rct">Response Tone</div><div class="tone-g">', unsafe_allow_html=True)
    tnc=st.columns(2)
    for i,(k,(tico,tnm)) in enumerate(TONES.items()):
        with tnc[i%2]:
            act="tact" if st.session_state.tone==k else ""
            st.markdown(f'<div class="tone-opt {act}">{tico} {tnm}</div>', unsafe_allow_html=True)
            if st.button(tnm, key=f"tr_{k}", use_container_width=True):
                st.session_state.tone=k; st.session_state.toast=("inf",f"{tico} Tone → {tnm}"); st.rerun()
    st.markdown('</div></div>', unsafe_allow_html=True)

# ═══════════════════════════════════════════════════════
# SEND HANDLER
# ═══════════════════════════════════════════════════════
if send and user_input and user_input.strip():
    prompt = user_input.strip()
    if st.session_state.file_content:
        prompt += f"\n\n---\n**File: {st.session_state.file_name}**\n```\n{st.session_state.file_content[:8000]}\n```"
        st.session_state.file_content=None; st.session_state.file_name=None
    st.session_state.active_view="chat"
    with st.spinner("⬡ NexusAI is thinking…"):
        send_message(prompt)
    st.rerun()

# ═══════════════════════════════════════════════════════
# TOAST
# ═══════════════════════════════════════════════════════
if st.session_state.toast:
    kind,msg_t=st.session_state.toast
    cls={"err":"t-err","ok":"t-ok","warn":"t-warn","inf":"t-inf"}.get(kind,"t-inf")
    st.markdown(f'<div class="toast {cls}">{msg_t}</div>', unsafe_allow_html=True)
    st.session_state.toast=None

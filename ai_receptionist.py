import csv
import json
import os
from datetime import datetime
from fastapi import FastAPI, Request
from fastapi.responses import HTMLResponse, PlainTextResponse
from google import genai
from google.genai import types

if os.path.exists(".env"):
    with open(".env", encoding="utf-8") as f:
        for line in f:
            if line.strip().startswith("GEMINI_API_KEY="):
                os.environ["GEMINI_API_KEY"] = line.strip().split("=", 1)[1].strip('"').strip("'")

CATALOG_CSV = "mts_catalog.csv"
LEADS_CSV = "leads_tracker.csv"
CLIENT_BOOKINGS_CSV = "client_bookings.csv"
VERIFY_TOKEN = "mts_free_webhook_2026"
FALLBACK_MODELS = ["gemini-3.5-flash-lite", "gemini-3.8-flash"]

app = FastAPI(title="Dual-Mode AI Receptionist with Memory")
SESSIONS = {}  # {session_id: {"history": [...], "logged": False}}


def load_mts_knowledge():
    if not os.path.exists(CATALOG_CSV):
        return "OT Tables, LED OT Lights, Anesthesia Machines, Patient Monitors, Ultrasound, CBC Analyzers (~40% below new import prices, Rawalpindi/Islamabad stock)."
    lines = []
    with open(CATALOG_CSV, mode="r", encoding="utf-8") as f:
        for r in csv.DictReader(f):
            est = int(float(r["new_market_price_pkr"]) * 0.60)
            lines.append(f"{r['item_code']}: {r['item_name']} ({r['department']}) - Est. PKR {est:,}")
    return "\n".join(lines[:35])


def save_mts_lead(hosp, doc, phone, interest):
    file_exists = os.path.exists(LEADS_CSV)
    with open(LEADS_CSV, mode="a", newline="", encoding="utf-8") as f:
        writer = csv.writer(f)
        if not file_exists:
            writer.writerow(["hospital_name", "doctor_name", "phone", "interest", "last_contact_date", "status"])
        writer.writerow([hosp, doc or "Inquiry", phone, interest or "GENERAL:1", datetime.now().strftime("%Y-%m-%d"), "AI Lead Captured"])


def save_client_booking(business_type, name, phone, service_requested, preferred_time):
    file_exists = os.path.exists(CLIENT_BOOKINGS_CSV)
    with open(CLIENT_BOOKINGS_CSV, mode="a", newline="", encoding="utf-8") as f:
        writer = csv.writer(f)
        if not file_exists:
            writer.writerow(["timestamp", "business_type", "client_name", "phone", "service", "preferred_time"])
        writer.writerow([datetime.now().strftime("%Y-%m-%d %H:%M"), business_type, name, phone, service_requested, preferred_time])


def ask_ai_receptionist(user_msg: str, mode: str = "mts", session_id: str = "default") -> dict:
    api_key = os.getenv("GEMINI_API_KEY", "").strip()
    if not api_key or api_key == "PASTE_YOUR_ACTUAL_KEY_HERE":
        return {"reply": "⚠️ API Key missing! Add GEMINI_API_KEY=your_key inside your .env file and refresh.", "lead_captured": False}

    session = SESSIONS.setdefault(session_id, {"history": [], "logged": False})
    session["history"].append(f"User: {user_msg}")
    recent_context = "\n".join(session["history"][-10:])

    try:
        client = genai.Client(api_key=api_key)
        if mode == "mts":
            system_prompt = f"""You are Mudasir's 24/7 AI Receptionist for MTS Medical Systems (Rawalpindi/Islamabad).
We supply certified refurbished hospital & clinic machinery (~40% below brand-new import prices) with local warranty & parts backup.
Catalog:\n{load_mts_knowledge()}\n
Goal: Remember details the user already shared earlier in the conversation (like their name, clinic, or phone). Answer equipment questions politely and concisely (in English or Roman Urdu). Collect Hospital/Clinic Name, Contact Name, Phone/WhatsApp, and Equipment Needed.
Return ONLY valid JSON with keys:
"reply" (string), "lead_captured" (boolean, true ONLY when phone AND hospital/clinic name are known from the conversation), "hospital_name" (string), "doctor_name" (string), "phone" (string), "interest" (string, e.g. "OT-02:1")."""
        else:
            system_prompt = """You are a 24/7 AI Front-Desk Receptionist for a modern Medical/Dental Clinic & Fitness Studio in Islamabad/Rawalpindi.
Services: Dental Checkup & Scaling (PKR 3,000), Specialist Consultation (PKR 2,500), Personal Training & Gym Membership (PKR 10,000/mo). Hours: Mon-Sat 10 AM - 9 PM.
Goal: Remember details the user shared earlier in the conversation. Answer warmly (in English or Roman Urdu) and book an appointment by collecting Name, Phone, Service, and Preferred Day/Time.
Return ONLY valid JSON with keys:
"reply" (string), "lead_captured" (boolean, true ONLY when name AND phone are known from the conversation), "client_name" (string), "phone" (string), "service" (string), "preferred_time" (string)."""

        resp = None
        last_err = None
        for model_name in FALLBACK_MODELS:
            try:
                resp = client.models.generate_content(
                    model=model_name,
                    contents=f"Conversation so far:\n{recent_context}",
                    config=types.GenerateContentConfig(
                        system_instruction=system_prompt,
                        response_mime_type="application/json",
                    ),
                )
                break
            except Exception as m_err:
                last_err = m_err

        if resp is None:
            raise last_err

        data = json.loads(resp.text)
        session["history"].append(f"Assistant: {data.get('reply', '')}")

        newly_logged = False
        if data.get("lead_captured") and not session["logged"]:
            if mode == "mts":
                save_mts_lead(
                    data.get("hospital_name", "Unknown Clinic"),
                    data.get("doctor_name", ""),
                    data.get("phone", ""),
                    data.get("interest", "GENERAL:1"),
                )
            else:
                save_client_booking(
                    "Clinic/Gym Demo",
                    data.get("client_name", "Guest"),
                    data.get("phone", ""),
                    data.get("service", "Consultation"),
                    data.get("preferred_time", "Flexible"),
                )
            session["logged"] = True
            newly_logged = True

        data["lead_captured"] = newly_logged
        return data
    except Exception as e:
        return {"reply": f"⚠️ Backend Error: {str(e)}", "lead_captured": False}


@app.get("/", response_class=HTMLResponse)
def web_widget():
    return """<!DOCTYPE html><html><head><title>24/7 AI Receptionist</title>
<style>body{font-family:Arial;background:#0b2545;color:#fff;display:flex;justify-content:center;padding:30px}
.box{width:460px;background:#fff;color:#111;border-radius:12px;padding:20px;box-shadow:0 8px 24px rgba(0,0,0,.3)}
#chat{height:320px;overflow-y:auto;border:1px solid #ddd;padding:10px;border-radius:8px;margin:10px 0;background:#f8fafc}
.msg{margin:8px 0;padding:8px 12px;border-radius:8px}.u{background:#dbeafe;text-align:right}.a{background:#e2e8f0}
input,select,button{padding:10px;border-radius:6px;border:1px solid #ccc}button{background:#0b2545;color:#fff;cursor:pointer}</style></head>
<body><div class="box"><div style="display:flex;justify-content:space-between;align-items:center">
<h3 style="margin:0">🤖 24/7 AI Receptionist</h3><button onclick="resetChat()" style="padding:5px 10px;font-size:12px;background:#475569">New Chat</button></div>
<select id="mode" onchange="resetChat()" style="width:100%;margin-top:8px"><option value="mts">Mode 1: MTS Medical Systems (Auto-Logs to Warehouse)</option><option value="client">Mode 2: Clinic / Dentist / Gym Freelance Demo</option></select>
<div id="chat"><div class="msg a">Assalam-o-Alaikum! How can I help you today?</div></div>
<div style="display:flex;gap:6px"><input id="inp" style="flex:1" placeholder="Type inquiry..." onkeydown="if(event.key==='Enter')send()">
<button onclick="send()">Send</button></div></div>
<script>let sid='sess_'+Math.random().toString(36).slice(2);
function resetChat(){sid='sess_'+Math.random().toString(36).slice(2);document.getElementById('chat').innerHTML="<div class='msg a'>Assalam-o-Alaikum! How can I help you today?</div>";}
async function send(){let i=document.getElementById('inp'),c=document.getElementById('chat'),m=document.getElementById('mode').value;
if(!i.value.trim())return;let t=i.value;i.value='';c.innerHTML+=`<div class='msg u'>${t}</div>`;
try{let r=await fetch('/chat',{method:'POST',headers:{'Content-Type':'application/json'},body:JSON.stringify({message:t,mode:m,session_id:sid})});
let d=await r.json();let tag=d.lead_captured?"<br><small style='color:green'>✅ Lead auto-logged to CSV!</small>":"";
c.innerHTML+=`<div class='msg a'>${d.reply}${tag}</div>`;}catch(err){c.innerHTML+=`<div class='msg a'>⚠️ Network Error: ${err}</div>`;}
c.scrollTop=c.scrollHeight;}</script></body></html>"""


@app.post("/chat")
async def chat_endpoint(req: Request):
    body = await req.json()
    return ask_ai_receptionist(body.get("message", ""), body.get("mode", "mts"), body.get("session_id", "default"))


@app.get("/webhook")
def verify_whatsapp(request: Request):
    params = request.query_params
    if params.get("hub.verify_token") == VERIFY_TOKEN:
        return PlainTextResponse(params.get("hub.challenge", ""))
    return PlainTextResponse("Invalid token", status_code=403)


@app.post("/webhook")
async def whatsapp_webhook(request: Request):
    data = await request.json()
    try:
        msg = data["entry"][0]["changes"][0]["value"]["messages"][0]
        text = msg["text"]["body"]
        sender = msg["from"]
        ai_res = ask_ai_receptionist(f"Sender phone: {sender}. Message: {text}", mode="mts", session_id=f"wa_{sender}")
        print(f"[WHATSAPP AI REPLY to {sender}]: {ai_res['reply']}")
    except Exception:
        pass
    return {"status": "ok"}

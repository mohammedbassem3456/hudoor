from fastapi import FastAPI, HTTPException
from fastapi.staticfiles import StaticFiles
from fastapi.responses import HTMLResponse, JSONResponse
from app.database import supabase
from app.models import EventCreate, GuestCreate, RSVPUpdate, GateKeeperCreate
import qrcode
import uuid
import os
from io import BytesIO
import base64
from datetime import datetime

app = FastAPI(title="Hudoor - حضور")

BASE_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))

if os.path.exists(os.path.join(BASE_DIR, "app", "static")):
    app.mount("/static", StaticFiles(directory=os.path.join(BASE_DIR, "app", "static")), name="static")

def read_html(filename):
    with open(os.path.join(BASE_DIR, "app", "templates", filename), encoding="utf-8") as f:
        return HTMLResponse(content=f.read())

# ═══════════════════════════════
# الصفحات
# ═══════════════════════════════

@app.get("/")
async def home():
    return read_html("index.html")

@app.get("/packages")
async def packages():
    return read_html("packages.html")

@app.get("/create-event")
async def create_event_page():
    return read_html("create_event.html")

@app.get("/dashboard")
async def dashboard():
    return read_html("dashboard.html")

@app.get("/event-details")
async def event_details():
    return read_html("event_details.html")

@app.get("/rsvp-page")
async def rsvp_page():
    return read_html("rsvp.html")

@app.get("/scanner")
async def scanner():
    return read_html("scanner.html")

# ═══════════════════════════════
# API المناسبات
# ═══════════════════════════════

@app.post("/events")
async def create_event(event: EventCreate):
    data = supabase.table("events").insert(event.dict()).execute()
    return {"success": True, "event": data.data[0]}

@app.get("/events-list")
async def get_events_list():
    data = supabase.table("events").select("*").execute()
    return {"events": data.data}

@app.get("/events/{event_id}")
async def get_event(event_id: str):
    data = supabase.table("events").select("*").eq("id", event_id).execute()
    if not data.data:
        raise HTTPException(status_code=404, detail="المناسبة غير موجودة")
    return data.data[0]

# ═══════════════════════════════
# API المدعوين
# ═══════════════════════════════

@app.post("/guests")
async def add_guest(guest: GuestCreate):
    data = supabase.table("guests").insert(guest.dict()).execute()
    return {"success": True, "guest": data.data[0]}

@app.get("/events/{event_id}/guests")
async def get_guests(event_id: str):
    data = supabase.table("guests").select("*").eq("event_id", event_id).execute()
    return {"guests": data.data}

@app.get("/guest/{guest_id}")
async def get_guest(guest_id: str):
    guest = supabase.table("guests").select("*").eq("id", guest_id).execute()
    if not guest.data:
        raise HTTPException(status_code=404, detail="المدعو غير موجود")
    event = supabase.table("events").select("*").eq("id", guest.data[0]["event_id"]).execute()
    return {"guest": guest.data[0], "event": event.data[0]}

@app.get("/guest-pass/{guest_id}")
async def get_guest_pass(guest_id: str):
    data = supabase.table("entry_passes").select("*").eq("guest_id", guest_id).execute()
    if not data.data:
        return {"qr_code": None}
    return {"qr_code": data.data[0]["qr_code"], "token": data.data[0]["token"]}

# ═══════════════════════════════
# RSVP
# ═══════════════════════════════

@app.post("/rsvp")
async def rsvp(update: RSVPUpdate):
    if update.status not in ["accepted", "declined"]:
        raise HTTPException(status_code=400, detail="الحالة غير صحيحة")

    supabase.table("guests").update({"status": update.status}).eq("id", update.guest_id).execute()

    if update.status == "accepted":
        guest = supabase.table("guests").select("*").eq("id", update.guest_id).execute()
        guest_data = guest.data[0]
        token = str(uuid.uuid4())
        qr = qrcode.make(token)
        buffer = BytesIO()
        qr.save(buffer, format="PNG")
        qr_base64 = base64.b64encode(buffer.getvalue()).decode()
        supabase.table("entry_passes").insert({
            "guest_id": update.guest_id,
            "event_id": guest_data["event_id"],
            "token": token,
            "qr_code": qr_base64
        }).execute()
        return {"success": True, "status": "accepted", "token": token, "qr_code": qr_base64}

    return {"success": True, "status": "declined"}

# ═══════════════════════════════
# التحقق من الباركود
# ═══════════════════════════════

@app.get("/verify/{token}")
async def verify_token(token: str):
    data = supabase.table("entry_passes").select("*, guests(name, phone)").eq("token", token).execute()
    if not data.data:
        return {"valid": False, "message": "باركود غير صحيح"}
    pass_data = data.data[0]
    if pass_data["used"]:
        return {"valid": False, "message": "تم استخدام هذا الباركود مسبقاً", "used_at": pass_data["used_at"]}
    supabase.table("entry_passes").update({
        "used": True,
        "used_at": datetime.now().isoformat()
    }).eq("token", token).execute()
    return {"valid": True, "message": "مرحباً!", "guest": pass_data["guests"]}

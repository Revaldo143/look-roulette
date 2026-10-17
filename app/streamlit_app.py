"""Look Roulette frontend — Spin. Swipe. Slay.

Selfie upload -> SPIN (slot-machine animation) -> rendered look ->
LIKE / DISLIKE -> taste profile learns -> Shop This Look (mock cart).

Run: streamlit run app/streamlit_app.py
Demo: append ?demo=1 for an instant illustrated demo portrait.
"""
import io
import os
import random
import time

# This VM's NO_PROXY carries bracketed IPv6 literals that crash httpx's proxy
# parsing at client construction; drop just the bracketed entries once here so
# backend calls to 127.0.0.1 keep working.
for _k in ("no_proxy", "NO_PROXY"):
    _v = os.environ.get(_k)
    if _v and "[" in _v:
        os.environ[_k] = ",".join(p for p in _v.split(",") if "[" not in p)

import httpx
import streamlit as st
from PIL import Image, ImageDraw

BACKEND = os.environ.get("LOOKROULETTE_BACKEND", "http://127.0.0.1:8000")

st.set_page_config(page_title="Look Roulette", page_icon="🎰", layout="wide")

st.markdown(
    "<link href='https://fonts.googleapis.com/css2?family=Playfair+Display:wght@600;700;800&family=Montserrat:wght@400;500;600;700;800&display=swap' rel='stylesheet'>",
    unsafe_allow_html=True,
)

NOIR_CSS = """
<style>
#MainMenu { visibility: hidden; }
footer { visibility: hidden; }
header[data-testid="stHeader"] { background: rgba(0,0,0,0); }

.stApp {
    background:
        radial-gradient(ellipse 90% 45% at 50% -8%, rgba(212,175,55,0.12), rgba(212,175,55,0) 70%),
        radial-gradient(circle at 50% 0%, #1d1036 0%, #0a0a12 62%) !important;
    font-family: 'Montserrat', system-ui, -apple-system, sans-serif;
}
h1, h2, h3 { font-family: 'Playfair Display', Georgia, 'Times New Roman', serif !important; color: #f8f2e4 !important; }
.stMarkdown p, .stMarkdown li, p, li { color: #ddd2b8 !important; }
.stCaption { color: #9a8f74 !important; }
.hint { color: #b9ac8d !important; }

.kicker { text-transform: uppercase; letter-spacing: .38em; font-size: 11.5px; color: #d4af37; font-weight: 700; }
.hero-title { font-family: 'Playfair Display', Georgia, serif; font-size: 56px; font-weight: 800; color: #faf5e9; line-height: 1.05; margin: 6px 0 4px; }
.hero-sub { color: #c8bc9c; font-size: 17px; margin-bottom: 2px; }
.gold-rule { height: 2px; border: 0; background: linear-gradient(90deg, transparent, #d4af37 30%, #d4af37 70%, transparent); margin: 16px 0 10px; opacity: .8; }

.notice { border: 1px solid rgba(212,175,55,.45); background: rgba(212,175,55,.07); border-radius: 12px; padding: 10px 16px; color: #ead9a4; font-size: 14px; }

.step-card { background: rgba(255,255,255,.03); border: 1px solid rgba(212,175,55,.22); border-radius: 14px; padding: 12px 14px; min-height: 118px; }
.step-num { font-family: 'Playfair Display', Georgia, serif; color: #d4af37; font-size: 24px; font-weight: 700; }
.step-label { color: #f2ead6; font-weight: 700; font-size: 14px; margin-top: 2px; }
.step-desc { color: #a79b7c; font-size: 12.5px; margin-top: 2px; }

.look-card { background: rgba(255,255,255,.035); border: 1px solid rgba(212,175,55,.30); border-radius: 18px; padding: 22px; box-shadow: 0 10px 44px rgba(0,0,0,.5); }
.lookname { font-family: 'Playfair Display', Georgia, serif; font-size: 36px; font-weight: 700; color: #ffd76a; margin: 0 0 4px; }
.badge { display: inline-block; padding: 5px 15px; border-radius: 999px; background: rgba(212,175,55,.13); border: 1px solid rgba(212,175,55,.55); color: #ffd76a; font-weight: 600; font-size: 13px; margin: 3px 6px 3px 0; }

.spin-btn button { background: linear-gradient(180deg, #ffe08a, #f0b429) !important; color: #3a2400 !important; font-size: 24px !important; font-weight: 800 !important; letter-spacing: .12em !important; border-radius: 16px !important; padding: 16px 20px !important; border: 1px solid #fff3cf !important; box-shadow: 0 0 28px rgba(240,180,41,.5), inset 0 1px 0 rgba(255,255,255,.6) !important; width: 100%; text-transform: uppercase; }
.spin-btn button:hover { filter: brightness(1.06); }
.swipe-like button { background: linear-gradient(180deg, #2dd4a0, #16a34a) !important; color: #062b1c !important; font-size: 17px !important; font-weight: 800 !important; letter-spacing: .06em !important; border-radius: 12px !important; width: 100%; border: 1px solid #a7f3d0 !important; padding: 12px !important; }
.swipe-nope button { background: rgba(255,255,255,.06) !important; color: #e8c9c9 !important; font-size: 17px !important; font-weight: 800 !important; letter-spacing: .06em !important; border-radius: 12px !important; width: 100%; border: 1px solid rgba(255,255,255,.22) !important; padding: 12px !important; }
.stButton > button { transition: filter .15s ease; }

[data-testid="stSidebar"] { background: #0c0c14 !important; border-right: 1px solid rgba(212,175,55,.18); }
[data-testid="stExpander"] { border: 1px solid rgba(212,175,55,.25); border-radius: 12px; background: rgba(255,255,255,.02); }
[data-testid="stProgressBar"] > div > div { background: linear-gradient(90deg, #d4af37, #ffe08a) !important; }

.footer-note { text-align: center; color: #8d8163; font-size: 12.5px; letter-spacing: .04em; }
.footer-note b { color: #c9b98a; }
</style>
"""
st.markdown(NOIR_CSS, unsafe_allow_html=True)


def demo_portrait() -> bytes:
    """Deterministic illustrated demo portrait (clearly synthetic)."""
    rng = random.Random("lookroulette-demo")
    W, H = 512, 640
    img = Image.new("RGB", (W, H))
    px = img.load()
    for y in range(H):
        t = y / H
        px_line = (int(24 + 30 * t), int(10 + 14 * t), int(38 + 40 * t))
        for x in range(W):
            px[x, y] = px_line
    d = ImageDraw.Draw(img, "RGBA")
    d.arc([60, 40, W - 60, 300], start=180, end=360, fill=(245, 197, 24, 200), width=6)
    d.ellipse([100, 150, 412, 490], fill=(214, 164, 128))          # face (>60% width for Skin AI)
    d.arc([84, 100, 428, 440], start=180, end=360, fill=(58, 32, 20), width=34)  # hair
    d.arc([180, 270, 240, 305], start=200, end=340, fill=(40, 22, 16), width=4)   # eyes
    d.arc([272, 270, 332, 305], start=200, end=340, fill=(40, 22, 16), width=4)
    d.ellipse([216, 390, 296, 416], fill=(170, 80, 80))            # lips hint
    for _ in range(24):                                           # sparkles
        x, y = rng.randint(0, W - 1), rng.randint(0, H - 1)
        d.ellipse([x, y, x + 3, y + 3], fill=(245, 197, 24, 160))
    buf = io.BytesIO()
    img.save(buf, format="PNG")
    return buf.getvalue()


def backend_get(path):
    return httpx.get(BACKEND + path, timeout=15).json()


def swatches(palette):
    hexes = [palette["lip"]["hex"], palette["blush_hex"]] + palette["shadows"]
    boxes = "".join(
        "<div title='%s' style='display:inline-block;width:46px;height:46px;"
        "border-radius:12px;background:%s;margin:5px;border:2px solid #ffffff33'></div>" % (h, h)
        for h in hexes
    )
    st.markdown(boxes, unsafe_allow_html=True)
    st.caption(" ".join(hexes))


def slot_animation():
    ph = st.empty()
    for sym in ["🍒", "💄", "🎰", "✨", "💋", "🍒", "🎰", "💄"]:
        ph.markdown(
            "<div style='text-align:center;font-size:72px'>%s"
            "<div style='font-size:20px;color:#ffd76a'>spinning…</div></div>" % sym,
            unsafe_allow_html=True,
        )
        time.sleep(0.16)
    ph.empty()


# ---------------------------------------------------------------- header
st.markdown("<div class='kicker'>YouCam API · Skin AI &amp; eCommerce VTO Hackathon</div>", unsafe_allow_html=True)
st.markdown("<div class='hero-title'>🎰 Look Roulette</div>", unsafe_allow_html=True)
st.markdown("<div class='hero-sub'><i>Spin. Swipe. Slay.</i> — your face, the slot machine.</div>", unsafe_allow_html=True)
st.markdown("<hr class='gold-rule'/>", unsafe_allow_html=True)

_steps = [("01", "Upload", "Drop in your selfie"),
          ("02", "Spin", "AI renders the look"),
          ("03", "Swipe", "Teach it your taste"),
          ("04", "Shop", "Check out the look")]
_scols = st.columns(4)
for _c, (_n, _l, _d) in zip(_scols, _steps):
    _c.markdown(
        "<div class='step-card'><div class='step-num'>%s</div>"
        "<div class='step-label'>%s</div><div class='step-desc'>%s</div></div>" % (_n, _l, _d),
        unsafe_allow_html=True,
    )

try:
    health = backend_get("/health")
    simulated = health.get("simulated", True)
except Exception:
    st.error("Backend not reachable. Start it first: `uvicorn app.main:app --port 8000` (from ~/workspace/lookroulette)")
    st.stop()

if simulated:
    st.markdown("<div class='notice'>🎲 <b>Simulated preview mode</b> — renders are illustrative. Connect the YouCam API credential for live YouCam AI renders.</div>", unsafe_allow_html=True)

demo = st.query_params.get("demo", "") == "1"
if "selfie" not in st.session_state:
    st.session_state.selfie = demo_portrait() if demo else None
if "look" not in st.session_state:
    st.session_state.look = None
if "cart" not in st.session_state:
    st.session_state.cart = {"cart": [], "total": 0.0}

# ---------------------------------------------------------------- sidebar cart
with st.sidebar:
    st.markdown("## 🛒 Your Cart")
    cart = st.session_state.cart
    if not cart["cart"]:
        st.markdown("<span class='hint'>Empty — spin a look you love, then shop it.</span>", unsafe_allow_html=True)
    for item in cart["cart"]:
        st.write("💄 %s — $%.2f" % (item["look_name"], item["price"]))
    if cart["cart"]:
        st.write("**Total: $%.2f** (mock)" % cart["total"])
        if st.button("Checkout (mock)"):
            st.success("🎉 Mock checkout complete — no real payment, no real order.")
    st.divider()
    st.caption("Skin Analysis Report values shown are illustrative in simulated mode. No medical claims.")

# ---------------------------------------------------------------- main flow
uploaded = st.file_uploader("📸 Drop your selfie to play", type=["png", "jpg", "jpeg"])
if uploaded is not None:
    st.session_state.selfie = uploaded.read()
    st.session_state.look = None

if st.session_state.selfie is None:
    st.markdown("<span class='hint'>Upload a selfie — or open with <b>?demo=1</b> for an instant illustrated demo.</span>", unsafe_allow_html=True)
    st.stop()

col_spin, col_face = st.columns([1, 1])
with col_face:
    st.image(st.session_state.selfie, caption="Your selfie" + (" (illustrated demo portrait)" if demo else ""), width=320)

with col_spin:
    st.markdown("### Feeling lucky?")
    st.markdown("<div class='spin-btn'>", unsafe_allow_html=True)
    do_spin = st.button("🎰 SPIN", key="spin")
    st.markdown("</div>", unsafe_allow_html=True)
    if do_spin:
        slot_animation()
        try:
            r = httpx.post(
                BACKEND + "/spin",
                files={"file": ("selfie.png", st.session_state.selfie, "image/png")},
                timeout=180,
            )
            r.raise_for_status()
            st.session_state.look = r.json()
        except Exception as e:
            st.error("Spin failed: %s" % str(e)[:160])

look = st.session_state.look
if look:
    if look.get("jackpot"):
        st.success("🎰 **JACKPOT!** Rare curated look landed on your spin!")
    st.divider()
    st.markdown("<div class='look-card'>", unsafe_allow_html=True)
    c1, c2 = st.columns([1, 1])
    with c1:
        st.image(look["image"], caption="Rendered look" + (" (simulated)" if look.get("simulated") else ""), use_container_width=True)
    with c2:
        st.markdown("<div class='lookname'>%s</div>" % look["look_name"], unsafe_allow_html=True)
        st.markdown("<span class='badge'>%s undertone</span> <span class='badge'>%s · %s</span>"
                    % (look["undertone"], look["family"], look["texture"]), unsafe_allow_html=True)
        st.write("")
        st.markdown("**Palette**")
        swatches(look["palette"])
        with st.expander("Skin Analysis Report"):
            rep = look.get("skin_report", {})
            st.write("Undertone:", rep.get("undertone"), "| Skin type:", rep.get("skin_type"))
            for k, v in (rep.get("scores") or {}).items():
                st.write("- %s: %s" % (k, v))
            if look.get("simulated"):
                st.caption("Illustrative values — simulated mode.")
        st.write("")
        b1, b2 = st.columns(2)
        with b1:
            st.markdown("<div class='swipe-like'>", unsafe_allow_html=True)
            liked = st.button("👍 LOVE IT", key="like")
            st.markdown("</div>", unsafe_allow_html=True)
        with b2:
            st.markdown("<div class='swipe-nope'>", unsafe_allow_html=True)
            noped = st.button("👎 NEXT", key="nope")
            st.markdown("</div>", unsafe_allow_html=True)
        if liked or noped:
            try:
                s = httpx.post(BACKEND + "/swipe",
                               json={"look_id": look["look_id"], "liked": bool(liked)}, timeout=15).json()
                pct = s.get("style_iq")
                if pct is not None:
                    st.progress(pct / 100, text="🧠 Style IQ %d%% — the machine is learning your taste" % pct)
                else:
                    st.caption("Vote counted — keep spinning to train your Style IQ.")
                if liked:
                    st.balloons()
            except Exception as e:
                st.error("Swipe failed: %s" % str(e)[:120])
        st.write("")
        if st.button("🛒 Shop This Look", key="shop"):
            try:
                st.session_state.cart = httpx.post(BACKEND + "/cart",
                                                   json={"look_id": look["look_id"]}, timeout=15).json()
                st.success("Added to cart (mock).")
            except Exception as e:
                st.error("Cart failed: %s" % str(e)[:120])
    st.markdown("</div>", unsafe_allow_html=True)

with st.expander("🕘 Your spin history"):
    try:
        for l in backend_get("/looks")["looks"]:
            mark = "👍" if l["liked"] == 1 else ("👎" if l["liked"] == 0 else "🎰")
            st.write("%s **%s** — %s · %s%s" % (mark, l["look_name"], l["family"], l["texture"],
                                               " · JACKPOT" if l["jackpot"] else ""))
    except Exception:
        st.caption("No history yet.")

st.markdown("<hr class='gold-rule'/>", unsafe_allow_html=True)
st.markdown("<div class='footer-note'>Built with <b>YouCam Skin AI</b> · <b>Makeup VTO</b> · <b>Look VTO</b> &nbsp;—&nbsp; FastAPI · Streamlit · SQLite</div>", unsafe_allow_html=True)

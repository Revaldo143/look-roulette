"""Look Roulette frontend — Spin. Swipe. Slay.

Selfie upload -> SPIN (slot-machine animation) -> rendered look ->
LIKE / DISLIKE -> taste profile learns -> Shop This Look (mock cart).

Styled exactly after the Look Roulette Web Card preview model:
Bricolage Grotesque, Public Sans, IBM Plex Mono typography,
violet & gold casino aesthetic, 3-column dashboard,
interactive before/after stage slider, skin analysis report,
reels, swatches, cart, history, and under-the-hood breakdown.
"""
import base64
import io
import os
import random
import time

# Handle NO_PROXY bracketed IPv6 literals if present
for _k in ("no_proxy", "NO_PROXY"):
    _v = os.environ.get(_k)
    if _v and "[" in _v:
        os.environ[_k] = ",".join(p for p in _v.split(",") if "[" not in p)

import httpx
import streamlit as st
import streamlit.components.v1 as components
from PIL import Image, ImageDraw, ImageFont

BACKEND = os.environ.get("LOOKROULETTE_BACKEND", "http://127.0.0.1:8000")

st.set_page_config(
    page_title="Look Roulette — Spin. Swipe. Slay.",
    page_icon="🎰",
    layout="wide",
    initial_sidebar_state="collapsed",
)

WEB_CARD_CSS = """
<link rel="preconnect" href="https://fonts.googleapis.com" />
<link rel="preconnect" href="https://fonts.gstatic.com" crossorigin />
<link href="https://fonts.googleapis.com/css2?family=Bricolage+Grotesque:opsz,wght@12..96,500;12..96,700;12..96,800&family=Public+Sans:wght@400;500;600;700&family=IBM+Plex+Mono:wght@500;600&display=swap" rel="stylesheet" />

<style>
:root {
  --bg: #12081f;
  --bg-deep: #0d0616;
  --panel: #221238;
  --panel-2: #2a1245;
  --ink: #f5e9ff;
  --ink-soft: #c9b8e8;
  --ink-faint: #9a83c4;
  --gold: #ffd76a;
  --gold-bright: #f5a623;
  --gold-pale: #3a2a05;
  --plum: #e89aab;
  --plum-btn: #7a2340;
  --line: #3d2566;
  --green: #4ade80;
  --green-bg: #12351f;
  --shadow: 0 18px 44px rgba(0,0,0,.5);
  --stage-bg: radial-gradient(120% 90% at 50% 0%, #3a1a63 0%, #241040 55%, #170b2c 100%);
}

#MainMenu { visibility: hidden; }
footer { visibility: hidden; }
header[data-testid="stHeader"] { background: transparent !important; }
.block-container {
  padding-top: 1.4rem !important;
  padding-bottom: 2.5rem !important;
  max-width: 1260px !important;
}

.stApp {
  background: var(--bg) !important;
  color: var(--ink) !important;
  font-family: "Public Sans", system-ui, -apple-system, sans-serif !important;
  font-size: 15px;
  line-height: 1.55;
}

h1, h2, h3, h4 {
  font-family: "Bricolage Grotesque", system-ui, sans-serif !important;
  color: var(--ink) !important;
  letter-spacing: -0.01em;
}

p, span, label, div {
  color: var(--ink);
}

/* Header */
.app-header {
  display: flex;
  flex-wrap: wrap;
  align-items: flex-end;
  gap: 14px 26px;
  margin-bottom: 6px;
}
.app-header h1 {
  font-family: "Bricolage Grotesque", sans-serif;
  font-weight: 800;
  font-size: clamp(34px, 5.2vw, 52px);
  line-height: 1;
  margin: 0;
}
.app-header h1 .gold { color: var(--gold); }
.app-header .tagline {
  font-size: clamp(15px, 2.1vw, 19px);
  color: var(--ink-soft);
  font-weight: 600;
  margin: 6px 0 0;
}
.mode-chip {
  margin-left: auto;
  align-self: flex-start;
  font-family: "IBM Plex Mono", monospace;
  font-size: 12px;
  font-weight: 600;
  border: 1.5px solid var(--gold);
  color: var(--gold);
  background: rgba(255, 215, 106, 0.08);
  padding: 6px 14px;
  border-radius: 999px;
  white-space: nowrap;
}
.mode-chip b { color: #fff; }
.lede {
  max-width: 82ch;
  color: var(--ink-soft);
  font-size: 14.5px;
  margin: 12px 0 24px;
  line-height: 1.5;
}
.lede b { color: var(--gold); }

/* Card */
.card {
  background: var(--panel);
  border: 1px solid var(--line);
  border-radius: 18px;
  box-shadow: var(--shadow);
  padding: 20px;
  margin-bottom: 20px;
}
.card h2 {
  font-family: "Bricolage Grotesque", sans-serif;
  font-size: 19px;
  font-weight: 700;
  margin: 0 0 12px;
  letter-spacing: .01em;
  color: var(--ink) !important;
}
.card h2 .sub {
  display: block;
  font-family: "Public Sans", sans-serif;
  font-size: 12.5px;
  font-weight: 500;
  color: var(--ink-faint);
  margin-top: 2px;
}

/* P1-1 FIX (cards): sections that contain interactive widgets CANNOT be
   wrapped by a <section> opened in one st.markdown and closed in another
   (separate DOM elements again). Those sections now use Streamlit-native
   st.container(border=True), and this rule paints every bordered container
   with the card look. Sections that are a single markdown string keep
   using .card directly (skin report, Under the Hood, footer). */
div[data-testid="stVerticalBlockBorderWrapper"] {
  background: var(--panel) !important;
  border: 1px solid var(--line) !important;
  border-radius: 18px !important;
  box-shadow: var(--shadow) !important;
  padding: 20px !important;
  margin-bottom: 20px !important;
}

/* P2-17 NOTE (fonts, explicit): Bricolage Grotesque / Public Sans /
   IBM Plex Mono load from Google Fonts when online and fall back to
   system fonts offline — by design, not by accident. Bundling the font
   files locally was NOT done (it needs font downloads + licence checks);
   layout is unchanged either way, only typography softens offline. */

/* Badges */
.skin-grid { display: flex; flex-wrap: wrap; gap: 8px; margin-bottom: 14px; }
.badge {
  display: inline-block;
  padding: 4px 13px;
  border-radius: 999px;
  font-size: 12.5px;
  font-weight: 700;
  background: var(--gold-pale);
  color: var(--gold);
  border: 1px solid var(--gold);
}
.badge.plain {
  background: var(--panel-2);
  color: var(--ink-soft);
  border-color: var(--line);
}

/* Scores & Bars */
.score { margin: 9px 0; }
.score .row { display: flex; justify-content: space-between; font-size: 13.5px; color: var(--ink); }
.score .row span:last-child { font-family: "IBM Plex Mono", monospace; font-weight: 600; color: var(--gold); }
.bar { height: 8px; border-radius: 99px; background: var(--bg-deep); overflow: hidden; margin-top: 4px; }
.bar i {
  display: block;
  height: 100%;
  border-radius: 99px;
  background: linear-gradient(90deg, #7a2340, #f5a623);
}
.fineprint { font-size: 12px; color: var(--ink-faint); margin: 12px 0 0; }

/* Reels */
.reels { display: grid; grid-template-columns: repeat(3, 1fr); gap: 10px; margin-bottom: 16px; }
.reel {
  background: var(--stage-bg);
  border: 2px solid var(--gold);
  border-radius: 14px;
  height: 88px;
  display: flex;
  align-items: center;
  justify-content: center;
  font-size: 40px;
  color: #ffd76a;
  font-family: "Bricolage Grotesque", sans-serif;
  font-weight: 800;
  overflow: hidden;
  box-shadow: inset 0 2px 8px rgba(0,0,0,0.6);
}
.reel.win {
  box-shadow: 0 0 0 3px var(--gold-bright), 0 0 26px rgba(245,166,35,.55);
}

/* Jackpot Alert */
.jackpot {
  margin: 0 0 14px;
  padding: 10px 14px;
  border-radius: 12px;
  text-align: center;
  background: var(--green-bg);
  color: var(--green);
  font-weight: 800;
  font-size: 15px;
  border: 1px solid var(--green);
}

/* Result */
.lookname {
  font-family: "Bricolage Grotesque", sans-serif;
  font-size: 28px;
  font-weight: 800;
  color: var(--gold);
  line-height: 1.1;
  margin: 6px 0 10px;
}

/* Swatches */
.swatches { display: flex; gap: 8px; flex-wrap: wrap; margin: 12px 0 8px; }
.sw { width: 52px; text-align: center; }
.sw .chip { height: 44px; border-radius: 12px; border: 2px solid rgba(255,255,255,.2); box-shadow: 0 3px 8px rgba(0,0,0,0.4); }
.sw .lbl { font-size: 10.5px; color: var(--ink-faint); margin-top: 4px; font-weight: 600; text-transform: uppercase; letter-spacing: .04em; }
.sw .hex { font-family: "IBM Plex Mono", monospace; font-size: 10.5px; color: var(--ink-soft); }
.swatch-note { font-size: 12.5px; color: var(--ink-faint); margin: 6px 0 12px; line-height: 1.4; }

/* Buttons.
   P1-1 FIX: Streamlit renders every st.markdown / st.button as a SEPARATE
   DOM element, so a <div class="spin-btn"> opened in one markdown element
   can NEVER wrap the button rendered in the next element — the old
   ".spin-btn button" selectors matched nothing. The working mechanism:
   the marker div's stMarkdown block is immediately followed by the button's
   wrapper div, so the selector targets the NEXT SIBLING element's button
   via :has(). (Needs a visual check: Streamlit's DOM is client-rendered.) */
div[data-testid="stMarkdown"]:has(.spin-btn) + div button {
  width: 100% !important;
  background: linear-gradient(180deg, #ffd76a, #f5a623) !important;
  color: #3a1c00 !important;
  font-family: "Bricolage Grotesque", sans-serif !important;
  font-size: 24px !important;
  font-weight: 800 !important;
  letter-spacing: .05em !important;
  border-radius: 16px !important;
  padding: 14px 20px !important;
  border: 2.5px solid #fff2c9 !important;
  box-shadow: 0 0 24px rgba(245,166,35,.45), 0 8px 18px rgba(0,0,0,.25) !important;
  text-transform: uppercase !important;
  transition: transform .12s ease, filter .12s ease !important;
}
div[data-testid="stMarkdown"]:has(.spin-btn) + div button:hover {
  transform: translateY(-2px) !important;
  filter: brightness(1.08) !important;
}

div[data-testid="stMarkdown"]:has(.btn-love) + div button {
  width: 100% !important;
  background: #22c55e !important;
  color: #06280f !important;
  font-family: "Public Sans", sans-serif !important;
  font-size: 16px !important;
  font-weight: 700 !important;
  border-radius: 12px !important;
  border: 1px solid #86efac !important;
  padding: 12px 10px !important;
  transition: transform .12s ease !important;
}
div[data-testid="stMarkdown"]:has(.btn-love) + div button:hover {
  transform: translateY(-1px) !important;
  filter: brightness(1.08) !important;
}

div[data-testid="stMarkdown"]:has(.btn-next) + div button {
  width: 100% !important;
  background: var(--panel-2) !important;
  color: var(--ink) !important;
  font-family: "Public Sans", sans-serif !important;
  font-size: 16px !important;
  font-weight: 700 !important;
  border-radius: 12px !important;
  border: 1.5px solid var(--line) !important;
  padding: 12px 10px !important;
  transition: transform .12s ease !important;
}
div[data-testid="stMarkdown"]:has(.btn-next) + div button:hover {
  transform: translateY(-1px) !important;
  filter: brightness(1.08) !important;
}

div[data-testid="stMarkdown"]:has(.btn-shop) + div button {
  width: 100% !important;
  background: #7a2340 !important;
  color: #ffffff !important;
  font-family: "Public Sans", sans-serif !important;
  font-size: 16px !important;
  font-weight: 700 !important;
  border-radius: 12px !important;
  border: 1px solid #e89aab !important;
  padding: 12px 10px !important;
  margin-top: 8px !important;
  transition: transform .12s ease !important;
}
div[data-testid="stMarkdown"]:has(.btn-shop) + div button:hover {
  transform: translateY(-1px) !important;
  filter: brightness(1.08) !important;
}

div[data-testid="stMarkdown"]:has(.btn-download) + div button {
  width: 100% !important;
  background: rgba(255, 215, 106, 0.12) !important;
  color: var(--gold) !important;
  border: 1.5px solid var(--gold) !important;
  border-radius: 12px !important;
  font-family: "Public Sans", sans-serif !important;
  font-size: 14.5px !important;
  font-weight: 700 !important;
  padding: 10px !important;
  margin-top: 6px !important;
}

div[data-testid="stMarkdown"]:has(.btn-checkout) + div button {
  width: 100% !important;
  background: #7a2340 !important;
  color: #ffffff !important;
  border-radius: 12px !important;
  font-family: "Public Sans", sans-serif !important;
  font-size: 15px !important;
  font-weight: 700 !important;
  padding: 10px !important;
  margin-top: 10px !important;
}

/* Style IQ inside Machine */
.iq-box {
  margin-top: 14px;
  background: rgba(0,0,0,0.2);
  border-radius: 12px;
  padding: 10px 14px;
  border: 1px solid var(--line);
}
.iq-box .row {
  display: flex;
  justify-content: space-between;
  font-size: 13.5px;
  font-weight: 600;
  gap: 10px;
}
.iq-box .row span:last-child {
  font-family: "IBM Plex Mono", monospace;
  color: var(--green);
}
.iq-box .bar i {
  background: linear-gradient(90deg, #22c55e, #a3e635);
}
.feedback-msg {
  font-size: 13px;
  color: var(--gold);
  margin-top: 8px;
  min-height: 1.2em;
  line-height: 1.4;
}

/* Cart & History */
.cart-item {
  display: flex;
  justify-content: space-between;
  gap: 10px;
  padding: 8px 0;
  border-bottom: 1px dashed var(--line);
  font-size: 14.5px;
}
.cart-total {
  font-weight: 800;
  font-size: 16px;
  margin-top: 12px;
  color: var(--gold);
}
.empty-note {
  color: var(--ink-faint);
  font-size: 14px;
}
.checkout-msg {
  margin-top: 12px;
  padding: 10px 12px;
  border-radius: 10px;
  background: var(--green-bg);
  color: var(--green);
  font-weight: 600;
  font-size: 13.5px;
  border: 1px solid var(--green);
}

.hist {
  list-style: none;
  margin: 0;
  padding: 0;
  font-size: 14px;
}
.hist li {
  padding: 8px 0;
  border-bottom: 1px dashed var(--line);
  display: flex;
  gap: 10px;
  align-items: baseline;
}
.hist li:last-child { border-bottom: none; }
.hist .mark { width: 22px; flex: none; text-align: center; }
.hist .meta { color: var(--ink-faint); font-size: 12.5px; display: block; }
.hist .live { color: var(--green); font-weight: 700; }

/* Lower: Steps, Table, Stack */
.steps { list-style: none; counter-reset: step; margin: 0; padding: 0; }
.steps li {
  padding: 10px 0 10px 44px;
  position: relative;
  border-bottom: 1px dashed var(--line);
  font-size: 14px;
  color: var(--ink-soft);
}
.steps li:last-child { border-bottom: none; }
.steps li b { color: var(--gold); }
.steps li::before {
  counter-increment: step;
  content: counter(step);
  position: absolute;
  left: 0;
  top: 9px;
  width: 28px;
  height: 28px;
  border-radius: 50%;
  background: var(--gold-pale);
  color: var(--gold);
  border: 1.5px solid var(--gold);
  font-family: "Bricolage Grotesque", sans-serif;
  font-weight: 800;
  font-size: 14px;
  display: flex;
  align-items: center;
  justify-content: center;
}

table.units { width: 100%; border-collapse: collapse; font-size: 13.5px; margin-top: 10px; }
table.units th, table.units td { text-align: left; padding: 7px 6px; border-bottom: 1px solid var(--line); }
table.units th { font-size: 11.5px; text-transform: uppercase; letter-spacing: .06em; color: var(--ink-faint); }
table.units td.num, table.units th.num { text-align: right; font-family: "IBM Plex Mono", monospace; color: var(--gold); }

.stack { display: flex; flex-wrap: wrap; gap: 7px; margin-top: 14px; }
.stack span {
  font-family: "IBM Plex Mono", monospace;
  font-size: 12px;
  padding: 4px 10px;
  border-radius: 999px;
  background: var(--panel-2);
  border: 1px solid var(--line);
  color: var(--ink-soft);
}

/* File uploader styling */
[data-testid="stFileUploader"] {
  background: var(--panel-2) !important;
  border: 1.5px dashed var(--line) !important;
  border-radius: 14px !important;
  padding: 8px !important;
}
[data-testid="stFileUploader"]:hover {
  border-color: var(--gold) !important;
}

.app-footer {
  margin-top: 36px;
  padding-top: 18px;
  border-top: 1px solid var(--line);
  color: var(--ink-faint);
  font-size: 13px;
  display: flex;
  flex-wrap: wrap;
  gap: 8px 24px;
}
.app-footer b { color: var(--gold); }
</style>
"""

st.markdown(WEB_CARD_CSS, unsafe_allow_html=True)


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


def backend_get(path, timeout=15, headers=None):
    return httpx.get(BACKEND + path, timeout=timeout, headers=headers).json()


def cart_headers():
    # P1-5: every cart call carries the client session id so the backend
    # cart is per-session, not one global list.
    return {"X-Session-Id": st.session_state.session_id}


def slider_html(before_b64: str, after_b64: str, look_name: str = "Berry Bonanza", is_real: bool = True) -> str:
    """Web Card Stage: Draggable before/after comparison slider matching preview.html."""
    tag_text = "AFTER — REAL YOUCAM RENDER" if is_real else "AFTER — SIMULATED"
    caption_text = (
        f"<b>{look_name}</b> — rendered by YouCam Makeup VTO. Drag handle to compare."
        if is_real
        else f"<b>{look_name}</b> — simulated preview grade. Live app renders with YouCam VTO."
    )
    return f"""
    <!DOCTYPE html>
    <html>
    <head>
    <meta charset="utf-8">
    <link href="https://fonts.googleapis.com/css2?family=IBM+Plex+Mono:wght@600&family=Public+Sans:wght@500;700&display=swap" rel="stylesheet">
    <style>
      * {{ box-sizing: border-box; margin: 0; padding: 0; }}
      body {{ background: transparent; font-family: 'Public Sans', system-ui, sans-serif; overflow: hidden; color: #f5e9ff; }}
      .stage {{
        background: radial-gradient(120% 90% at 50% 0%, #3a1a63 0%, #241040 55%, #170b2c 100%);
        border-radius: 18px;
        padding: 16px;
        border: 1px solid #3d2566;
        box-shadow: 0 18px 44px rgba(0,0,0,.5);
      }}
      .ba {{
        position: relative;
        border-radius: 12px;
        overflow: hidden;
        aspect-ratio: 512/640;
        background: #1c0d33;
        touch-action: none;
        user-select: none;
        -webkit-user-select: none;
        cursor: ew-resize;
      }}
      .ba img {{
        position: absolute;
        inset: 0;
        width: 100%;
        height: 100%;
        object-fit: cover;
        display: block;
        pointer-events: none;
      }}
      .ba .after-wrap {{
        position: absolute;
        inset: 0;
        overflow: hidden;
        clip-path: inset(0 0 0 50%);
      }}
      .ba .divider {{
        position: absolute;
        top: 0;
        bottom: 0;
        left: 50%;
        width: 3px;
        background: #ffd76a;
        transform: translateX(-50%);
        pointer-events: none;
        box-shadow: 0 0 12px rgba(0,0,0,.45);
      }}
      .ba .handle {{
        position: absolute;
        top: 50%;
        left: 50%;
        transform: translate(-50%,-50%);
        width: 40px;
        height: 40px;
        border-radius: 50%;
        background: #ffd76a;
        color: #3a1c00;
        display: flex;
        align-items: center;
        justify-content: center;
        font-size: 15px;
        font-weight: 800;
        pointer-events: none;
        box-shadow: 0 4px 14px rgba(0,0,0,.4);
        border: 2.5px solid #fff2c9;
      }}
      .ba .tag {{
        position: absolute;
        top: 10px;
        font-family: "IBM Plex Mono", monospace;
        font-size: 10.5px;
        font-weight: 600;
        letter-spacing: .08em;
        padding: 4px 8px;
        border-radius: 6px;
        background: rgba(10,4,22,.75);
        color: #f5e9ff;
        z-index: 3;
      }}
      .tag.before {{ left: 10px; }}
      .tag.after {{ right: 10px; color: #ffd76a; }}
      .stage-cap {{
        color: #c9b8e8;
        font-size: 13px;
        margin: 10px 2px 0;
        line-height: 1.4;
      }}
      .stage-cap b {{ color: #ffd76a; }}
      .drag-hint {{
        color: #9a83c4;
        font-size: 12px;
        margin: 3px 2px 0;
      }}
    </style>
    </head>
    <body>
    <div class="stage">
      <div class="ba" id="ba" tabindex="0" role="slider" aria-label="Before and after comparison slider"
           aria-valuemin="0" aria-valuemax="100" aria-valuenow="50">
        <img src="data:image/png;base64,{before_b64}" alt="Before makeup" />
        <div class="after-wrap" id="afterWrap">
          <img src="data:image/png;base64,{after_b64}" alt="After makeup" id="afterImg" />
        </div>
        <span class="tag before">BEFORE</span>
        <span class="tag after">{tag_text}</span>
        <div class="divider" id="divider"></div>
        <div class="handle" id="handle">&harr;</div>
      </div>
      <p class="stage-cap">{caption_text}</p>
      <p class="drag-hint">Drag gold handle (or arrow keys) to compare before / after.</p>
    </div>
    <script>
      (function(){{
        var ba = document.getElementById("ba");
        var afterWrap = document.getElementById("afterWrap");
        var divider = document.getElementById("divider");
        var handle = document.getElementById("handle");
        var dragging = false;

        function setSplit(pct){{
          pct = Math.max(0, Math.min(100, pct));
          afterWrap.style.clipPath = "inset(0 0 0 " + pct + "%)";
          divider.style.left = pct + "%";
          handle.style.left = pct + "%";
          ba.setAttribute("aria-valuenow", Math.round(pct));
        }}

        function splitFromEvent(e){{
          var r = ba.getBoundingClientRect();
          var x = e.clientX - r.left;
          setSplit((x / r.width) * 100);
        }}

        ba.addEventListener("pointerdown", function(e){{
          dragging = true;
          ba.setPointerCapture(e.pointerId);
          splitFromEvent(e);
        }});
        ba.addEventListener("pointermove", function(e){{
          if(dragging) splitFromEvent(e);
        }});
        ba.addEventListener("pointerup", function(){{ dragging = false; }});
        ba.addEventListener("pointercancel", function(){{ dragging = false; }});
        ba.addEventListener("keydown", function(e){{
          var now = parseFloat(ba.getAttribute("aria-valuenow")) || 50;
          if(e.key === "ArrowLeft"){{ setSplit(now - 5); e.preventDefault(); }}
          if(e.key === "ArrowRight"){{ setSplit(now + 5); e.preventDefault(); }}
        }});
      }})();
    </script>
    </body>
    </html>
    """


def stage_single_html(image_b64: str, is_demo: bool = False, simulated: bool = True) -> str:
    """Web Card Stage: Single photo display before the first spin."""
    desc = "Illustrated demo portrait." if is_demo else "Your uploaded selfie."
    # P2-3: the caption must not promise a YouCam analysis in simulated mode.
    spin_cap = (
        "Press the golden SPIN button for a simulated preview look."
        if simulated
        else "Press the golden SPIN button to let YouCam Skin AI analyze your undertone and spin your look."
    )
    return f"""
    <!DOCTYPE html>
    <html>
    <head>
    <meta charset="utf-8">
    <link href="https://fonts.googleapis.com/css2?family=IBM+Plex+Mono:wght@600&family=Public+Sans:wght@500;700&display=swap" rel="stylesheet">
    <style>
      * {{ box-sizing: border-box; margin: 0; padding: 0; }}
      body {{ background: transparent; font-family: 'Public Sans', system-ui, sans-serif; overflow: hidden; color: #f5e9ff; }}
      .stage {{
        background: radial-gradient(120% 90% at 50% 0%, #3a1a63 0%, #241040 55%, #170b2c 100%);
        border-radius: 18px;
        padding: 16px;
        border: 1px solid #3d2566;
        box-shadow: 0 18px 44px rgba(0,0,0,.5);
      }}
      .ba {{
        position: relative;
        border-radius: 12px;
        overflow: hidden;
        aspect-ratio: 512/640;
        background: #1c0d33;
      }}
      .ba img {{
        width: 100%;
        height: 100%;
        object-fit: cover;
        display: block;
      }}
      .ba .tag {{
        position: absolute;
        top: 10px;
        left: 10px;
        font-family: "IBM Plex Mono", monospace;
        font-size: 10.5px;
        font-weight: 600;
        letter-spacing: .08em;
        padding: 4px 8px;
        border-radius: 6px;
        background: rgba(10,4,22,.75);
        color: #ffd76a;
        border: 1px solid rgba(255,215,106,0.3);
      }}
      .stage-cap {{
        color: #c9b8e8;
        font-size: 13px;
        margin: 10px 2px 0;
        line-height: 1.4;
      }}
      .stage-cap b {{ color: #ffd76a; }}
    </style>
    </head>
    <body>
    <div class="stage">
      <div class="ba">
        <img src="data:image/png;base64,{image_b64}" alt="Selfie portrait" />
        <span class="tag">READY TO SPIN</span>
      </div>
      <p class="stage-cap"><b>{desc}</b> {spin_cap}</p>
    </div>
    </body>
    </html>
    """


def swatches_html(palette: dict) -> str:
    """Ported directly from preview.html: swatch chips with labels & hex codes."""
    lip = palette.get("lip")
    lip_hex = lip.get("hex") if isinstance(lip, dict) else (lip or "#B5542D")
    blush_hex = palette.get("blush_hex") or palette.get("blush") or "#D98A68"
    shadows = palette.get("shadows") or ["#8A5A3B", "#C98B5E", "#5E3A24"]

    items = [("Lip", lip_hex), ("Blush", blush_hex)]
    for i, s in enumerate(shadows):
        items.append((f"Shadow {i+1}" if len(shadows) > 1 else "Shadow", s))

    # SWATCH FIX: chips are built as single-line strings with no leading
    # whitespace and no blank lines. The old triple-quoted chips left a
    # whitespace-only line between items; Markdown ends the HTML block at
    # that blank line and renders the following 8-space-indented lines as
    # an indented code block — so Blush/Shadow chips showed as literal
    # HTML source text instead of coloured chips.
    chips = "".join(
        f'<div class="sw"><div class="chip" style="background:{h};" title="{lbl}: {h}"></div><div class="lbl">{lbl}</div><div class="hex">{h}</div></div>'
        for lbl, h in items
    )
    return f'<div class="swatches">{chips}</div>'


def _score_val(scores: dict, *keys) -> int | None:
    """P2-6: return a clamped int score, or None when the value is missing,
    None, or non-numeric — never int(None), never a fabricated default."""
    for key in keys:
        val = scores.get(key)
        if val is None:
            continue
        try:
            return max(10, min(100, int(val)))
        except (TypeError, ValueError):
            continue
    return None


def skin_report_html(skin_report: dict, undertone: str = "NEUTRAL", simulated: bool = True) -> str:
    """Card: Skin Analysis Report with animated gradient progress bars.

    P1-3 FIX: no hardcoded 78/64/82 fallbacks anywhere. A bar renders ONLY
    when a real score value exists; the caller renders this card only after
    a spin with real score data. Badges and fineprint state the mode
    truthfully: simulated = 0 units, preview engine.
    """
    scores = skin_report.get("scores") or {}
    bars = [
        ("Radiance", _score_val(scores, "radiance", "Radiance")),
        ("Evenness", _score_val(scores, "evenness", "spots", "Evenness")),
        ("Smoothness", _score_val(scores, "smoothness", "texture", "Smoothness")),
    ]
    bars = [(label, val) for label, val in bars if val is not None]

    mode_note = "from YouCam SD Skin Analysis" if not simulated else "YouCam SD Skin Analysis · simulated"
    engine_badge = "Engine: YouCam Skin AI" if not simulated else "Engine: simulated preview"
    cost_badge = "Cost: 9 units" if not simulated else "Cost: 0 units (simulated)"
    fineprint = (
        "The undertone is analyzed by YouCam Skin AI. Scores show skin health metrics."
        if not simulated
        else "Simulated preview — scores are illustrative, not a measurement."
    )
    bars_html = "".join(
        f'<div class="score"><div class="row"><span>{label}</span><span>{val}%</span></div>'
        f'<div class="bar"><i style="width:{val}%;"></i></div></div>'
        for label, val in bars
    )
    if not bars_html:
        bars_html = "<p class='empty-note'>No skin scores returned for this spin.</p>"
    return f"""
    <section class="card" aria-label="Skin analysis report">
      <h2>Skin Analysis Report <span class="sub">{mode_note}</span></h2>
      <div class="skin-grid">
        <span class="badge">Undertone: {undertone.upper()}</span>
        <span class="badge plain">{engine_badge}</span>
        <span class="badge plain">{cost_badge}</span>
      </div>
      {bars_html}
      <p class="fineprint">{fineprint}</p>
    </section>
    """


def style_dna_html(taste_rows, style_iq) -> str:
    """Learned taste profile breakdown matching the web card style."""
    fam = {}
    for t in taste_rows:
        f = fam.setdefault(t["family"], [0, 0])
        f[0] += t["likes"]
        f[1] += t["dislikes"]
    if not fam:
        return "<p class='empty-note'>No swipes yet — spin a look and vote 👍 LOVE IT or 👎 NEXT to train your Style DNA.</p>"

    rows = sorted(fam.items(), key=lambda kv: kv[1][0] - kv[1][1], reverse=True)
    # SWATCH FIX (same defect as swatches_html): row parts are single-line
    # strings with no leading whitespace and no blank lines, so Markdown
    # cannot split them into an HTML block plus an indented code block.
    parts = ["<div style='display:flex;flex-direction:column;gap:12px;'>"]
    for name, (lk, dk) in rows:
        tot = lk + dk
        pct = round(100 * lk / tot) if tot else 0
        parts.append(
            f'<div><div class="score" style="margin:0;"><div class="row"><span style="font-weight:700;text-transform:capitalize;">{name}</span><span style="font-size:12px;color:var(--ink-soft);">{lk} 👍 · {dk} 👎 ({pct}%)</span></div><div class="bar"><i style="width:{pct}%;"></i></div></div></div>'
        )
    parts.append("</div>")
    iq_part = (
        f'<div class="iq-box" style="margin-top:14px;"><div class="row"><span>Style IQ — overall taste harmony</span><span>{style_iq}%</span></div><div class="bar"><i style="width:{style_iq}%;"></i></div></div>'
        if style_iq is not None
        else ""
    )
    return "".join(parts) + iq_part


def _get_font(size: int, bold: bool = False, serif: bool = False):
    """Safe font loader for Windows & Linux."""
    names = []
    if serif:
        names = ["georgia.ttf", "times.ttf", "arial.ttf", "DejaVuSerif-Bold.ttf"]
    elif bold:
        names = ["arialbd.ttf", "segoeuib.ttf", "calibrib.ttf", "DejaVuSans-Bold.ttf"]
    else:
        names = ["arial.ttf", "segoeui.ttf", "calibri.ttf", "DejaVuSans.ttf"]

    for name in names:
        try:
            return ImageFont.truetype(name, size)
        except Exception:
            continue
    try:
        return ImageFont.load_default(size=size)
    except Exception:
        return ImageFont.load_default()


def _cover(img: Image.Image, box) -> Image.Image:
    bw, bh = box
    w, h = img.size
    s = max(bw / w, bh / h)
    img = img.resize((int(w * s + 0.5), int(h * s + 0.5)), Image.LANCZOS)
    x, y = (img.width - bw) // 2, (img.height - bh) // 2
    return img.crop((x, y, x + bw, y + bh))


def look_card_png(before_bytes: bytes, after_uri: str, look: dict) -> bytes:
    """Shareable 1080x1350 Look Card in the luxury purple & gold aesthetic."""
    W, H = 1080, 1350
    card = Image.new("RGB", (W, H))
    px = card.load()
    top, bot = (34, 18, 56), (18, 8, 31)
    for y in range(H):
        t = y / H
        c = tuple(int(top[i] + (bot[i] - top[i]) * t) for i in range(3))
        for x in range(W):
            px[x, y] = c

    glow = Image.new("RGBA", (W, H), (0, 0, 0, 0))
    gd = ImageDraw.Draw(glow)
    for r in range(400, 0, -10):
        gd.ellipse(
            [W // 2 - r * 2, -r * 2, W // 2 + r * 2, r * 2],
            fill=(255, 215, 106, int(18 * (1 - r / 400))),
        )
    card = Image.alpha_composite(card.convert("RGBA"), glow).convert("RGB")
    d = ImageDraw.Draw(card, "RGBA")

    serif_b = _get_font(52, bold=True, serif=True)
    sans_b = _get_font(22, bold=True)
    sans = _get_font(20)
    sans_s = _get_font(16)
    GOLD, CREAM, MUT = (255, 215, 106), (245, 233, 255), (201, 184, 232)

    def center(y_pos, text, font, fill):
        bb = d.textbbox((0, 0), text, font=font)
        d.text(((W - (bb[2] - bb[0])) // 2, y_pos), text, font=font, fill=fill)

    y = 44
    center(y, "LOOK ROULETTE  ·  SPIN. SWIPE. SLAY.", sans_b, GOLD)
    y += 50
    before = _cover(Image.open(io.BytesIO(before_bytes)).convert("RGB"), (492, 560))
    raw = after_uri.split(",", 1)[1] if "," in after_uri else after_uri
    after = _cover(Image.open(io.BytesIO(base64.b64decode(raw))).convert("RGB"), (492, 560))
    card.paste(before, (28, y))
    card.paste(after, (560, y))
    d.rectangle([28, y, 520, y + 560], outline=GOLD, width=3)
    d.rectangle([560, y, 1052, y + 560], outline=GOLD, width=3)

    for lx, tx in ((48, "BEFORE"), (580, "AFTER")):
        d.rounded_rectangle([lx, y + 14, lx + 140, y + 50], radius=18, fill=(10, 4, 22, 190))
        d.text((lx + 20, y + 18), tx, font=sans_b, fill=GOLD)

    y += 592
    center(y, look.get("look_name", "Look Roulette"), serif_b, GOLD)
    y += 74
    center(
        y,
        f"{look.get('undertone', '').upper()} undertone  ·  {look.get('family', '')} family  ·  {look.get('texture', '')}",
        sans,
        MUT,
    )
    y += 48
    # P1-6: jackpot cards show the template image, not a palette render —
    # drawing palette swatches on them would mislabel the look. Skip the
    # swatch row for jackpots and say so in the render line instead.
    if not look.get("jackpot"):
        pal = look.get("palette", {})
        lip = pal.get("lip", {})
        lip_hex = lip.get("hex") if isinstance(lip, dict) else (lip or "#B5542D")
        blush_hex = pal.get("blush_hex") or pal.get("blush") or "#D98A68"
        shadows = pal.get("shadows") or ["#8A5A3B", "#C98B5E", "#5E3A24"]
        hexes = [lip_hex, blush_hex] + shadows

        sw, gap = 114, 16
        x0 = (W - (len(hexes) * sw + (len(hexes) - 1) * gap)) // 2
        for i, hx in enumerate(hexes):
            x = x0 + i * (sw + gap)
            try:
                fill_c = tuple(int(hx[j : j + 2], 16) for j in (1, 3, 5))
            except Exception:
                fill_c = (180, 100, 80)
            d.rounded_rectangle([x, y, x + sw, y + sw], radius=16, fill=fill_c, outline=(255, 255, 255, 70), width=2)
            bb = d.textbbox((0, 0), hx, font=sans_s)
            d.text((x + (sw - (bb[2] - bb[0])) // 2, y + sw + 8), hx, font=sans_s, fill=MUT)

        y += sw + 46
    else:
        y += 20
    for x in range(90, W - 90):
        a = int(180 * (1 - abs(x - W / 2) / (W / 2)))
        d.line([(x, y), (x, y + 2)], fill=GOLD + (a,))
    y += 24
    render_line = (
        "Curated YouCam Look VTO template"
        if look.get("jackpot")
        else "Rendered with YouCam Makeup VTO"
    )
    center(y, render_line, sans, MUT)
    y += 32
    if look.get("simulated"):
        center(y, "Simulated preview — illustrative render", sans_s, (154, 131, 196))

    buf = io.BytesIO()
    card.save(buf, format="PNG")
    return buf.getvalue()


# ---------------------------------------------------------------- session state setup
demo_flag = st.query_params.get("demo", "") == "1"

if "selfie" not in st.session_state:
    st.session_state.selfie = demo_portrait() if demo_flag else None
if "is_demo" not in st.session_state:
    st.session_state.is_demo = demo_flag
if "look" not in st.session_state:
    st.session_state.look = None
if "cart" not in st.session_state:
    st.session_state.cart = {"cart": [], "total": 0.0}
if "checkout_done" not in st.session_state:
    st.session_state.checkout_done = False
if "feedback" not in st.session_state:
    st.session_state.feedback = ""
if "reels" not in st.session_state:
    st.session_state.reels = ["♦", "★", "7"]
if "uploaded_file_id" not in st.session_state:
    # P0-1: fingerprint of the last processed upload (see uploader guard).
    st.session_state.uploaded_file_id = None
if "spin_error" not in st.session_state:
    # P1-2: spin errors survive reruns via session state, never bare st.error.
    st.session_state.spin_error = ""
if "session_id" not in st.session_state:
    # P1-5: per-browser cart session id, sent as X-Session-Id on cart calls.
    import uuid as _uuid

    st.session_state.session_id = _uuid.uuid4().hex
if "look_card_cache" not in st.session_state:
    # P2-2: (look_id, png bytes) — the card is built once, not every rerun.
    st.session_state.look_card_cache = (None, None)
if "voted_look_id" not in st.session_state:
    # P1-8: the look already voted on this session (buttons disable for it).
    st.session_state.voted_look_id = None
if "health_cache" not in st.session_state:
    # P2-1: (simulated flag, timestamp) — health is cached, not re-fetched
    # on every rerun (old code blocked up to 15 s per rerun when down).
    st.session_state.health_cache = (True, 0.0)

# ---------------------------------------------------------------- backend health check (cached, P2-1)
_health_cached, _health_ts = st.session_state.health_cache
if time.time() - _health_ts > 60:
    try:
        health = backend_get("/health", timeout=3)
        simulated = health.get("simulated", True)
    except Exception:
        simulated = True
    st.session_state.health_cache = (simulated, time.time())
else:
    simulated = _health_cached

# ---------------------------------------------------------------- app header
# P2-16: when a look is on screen, the chip follows THAT look's mode flag
# (not a possibly-stale health check), so chip and per-look label agree.
_header_look = st.session_state.look
_chip_simulated = _header_look.get("simulated", simulated) if _header_look else simulated
mode_chip_text = "SIMULATED PREVIEW · <b>0 YouCam units</b>" if _chip_simulated else "LIVE BACKEND · <b>YouCam AI Active</b>"

# P2-3: the lede must not promise YouCam analysis while in simulated mode.
lede_body = (
    "In the full live app you upload a selfie, <b>YouCam Skin AI</b> reads your undertone, the machine spins a "
    "harmonious palette, and <b>YouCam Makeup VTO</b> renders it on your face — then your swipes teach it your taste. "
    "Hit <b>SPIN</b> to begin!"
    if not _chip_simulated
    else "In this simulated preview you upload a selfie, the machine spins a "
    "harmonious palette, and a preview render shows it on your face — then your swipes teach it your taste. "
    "Hit <b>SPIN</b> to begin! No YouCam units are used in simulated mode."
)

st.markdown(
    f"""
    <div class="app-header">
      <div>
        <h1>Look <span class="gold">Roulette</span></h1>
        <p class="tagline">Spin. Swipe. Slay. — your face is the slot machine.</p>
      </div>
      <div class="mode-chip">{mode_chip_text}</div>
    </div>
    <p class="lede">
      {lede_body}
    </p>
    """,
    unsafe_allow_html=True,
)

# ---------------------------------------------------------------- 3-column web card layout
col_stage, col_machine, col_side = st.columns([1.1, 1.25, 0.95], gap="medium")

# ================================================================
# COLUMN 1: THE STAGE (Before / After Slider + Selfie Upload)
# ================================================================
with col_stage:
    if st.session_state.selfie is not None:
        selfie_b64 = base64.b64encode(st.session_state.selfie).decode()
        if st.session_state.look is not None:
            raw_img = st.session_state.look["image"]
            after_b64 = raw_img.split(",", 1)[1] if "," in raw_img else raw_img
            components.html(
                slider_html(
                    selfie_b64,
                    after_b64,
                    look_name=st.session_state.look.get("look_name", "Berry Bonanza"),
                    is_real=not st.session_state.look.get("simulated", simulated),
                ),
                # P2-5: 590 px clipped the caption on wide windows (image
                # height scales with column width). 760 px is the safest
                # fixed height without a live resize hook — flagged in
                # FIXES.md as "needs visual check".
                height=760,
            )
        else:
            components.html(
                stage_single_html(
                    selfie_b64,
                    is_demo=st.session_state.is_demo,
                    simulated=simulated,
                ),
                height=760,
            )
    else:
        # Prompt to load photo
        st.markdown(
            """
            <div class="card" style="text-align:center;padding:48px 24px;border:2px dashed var(--line);">
              <div style="font-size:48px;margin-bottom:12px;">📸</div>
              <h2 style="font-size:20px;margin-bottom:8px;">Drop your selfie to play</h2>
              <p style="color:var(--ink-soft);font-size:14px;margin-bottom:16px;">
                Upload a clear front-facing portrait to let YouCam Skin AI analyze your tone.
              </p>
            </div>
            """,
            unsafe_allow_html=True,
        )

    # Selfie uploader widget
    uploaded = st.file_uploader(
        "Upload Selfie",
        type=["png", "jpg", "jpeg"],
        label_visibility="collapsed",
        key="uploader",
    )
    # P0-1 FIX: the old code called st.rerun() unconditionally whenever the
    # uploader held a value — and the widget KEEPS its value across reruns,
    # so the app looped forever and SPIN (below this branch) never fired.
    # Guard: act only when the uploaded file's fingerprint differs from the
    # one already stored (name + sha256 of bytes via getvalue(), which does
    # not consume the buffer). Repeat runs skip the branch entirely, so the
    # page settles and SPIN stays reachable after an upload.
    if uploaded is not None:
        import hashlib as _hashlib

        file_id = (uploaded.name, _hashlib.sha256(uploaded.getvalue()).hexdigest())
        if st.session_state.uploaded_file_id != file_id:
            st.session_state.uploaded_file_id = file_id
            st.session_state.selfie = uploaded.getvalue()
            st.session_state.is_demo = False
            st.session_state.look = None
            st.session_state.feedback = ""
            st.session_state.spin_error = ""
            st.rerun()

    c_demo, c_clear = st.columns([1, 1])
    with c_demo:
        if st.button("🎭 Use Demo Face", key="use_demo", help="Load illustrated portrait (?demo=1)"):
            st.session_state.selfie = demo_portrait()
            st.session_state.is_demo = True
            st.session_state.look = None
            st.session_state.feedback = ""
            st.rerun()
    with c_clear:
        if st.session_state.selfie is not None:
            if st.button("🔄 Reset Face", key="clear_face"):
                st.session_state.selfie = None
                st.session_state.look = None
                st.session_state.feedback = ""
                st.rerun()


# ================================================================
# COLUMN 2: THE MACHINE (Skin Report + Slot Machine + Look Card)
# ================================================================
with col_machine:
    # 1. Skin Analysis Report Card
    # P1-3: the card renders ONLY after a spin that returned real score
    # data. Before that, a plain placeholder with no numbers at all.
    current_look = st.session_state.look
    undertone_val = current_look.get("undertone", "NEUTRAL") if current_look else "NEUTRAL"
    skin_report_data = current_look.get("skin_report", {}) if current_look else {}
    if current_look and (skin_report_data.get("scores") or {}):
        st.markdown(
            skin_report_html(
                skin_report_data,
                undertone=undertone_val,
                simulated=current_look.get("simulated", simulated),
            ),
            unsafe_allow_html=True,
        )
    else:
        st.markdown(
            "<p class='empty-note'>Skin Analysis Report appears after your first spin.</p>",
            unsafe_allow_html=True,
        )

    # 2. The Roulette Machine Card (P1-1: native bordered container)
    with st.container(border=True):

        if current_look and current_look.get("jackpot"):
            st.markdown(
                '<div class="jackpot">🎰 JACKPOT! A rare curated look landed on your spin!</div>',
                unsafe_allow_html=True,
            )

        # Reels display
        r0, r1, r2 = st.session_state.reels
        win_class = " win" if (current_look and current_look.get("jackpot")) else ""
        reels_placeholder = st.empty()
        reels_placeholder.markdown(
            f"""
            <div class="reels" aria-hidden="true">
              <div class="reel{win_class}">{r0}</div>
              <div class="reel{win_class}">{r1}</div>
              <div class="reel{win_class}">{r2}</div>
            </div>
            """,
            unsafe_allow_html=True,
        )

        # Big Golden SPIN Button
        st.markdown("<div class='spin-btn'>", unsafe_allow_html=True)
        spin_btn_label = "SPIN AGAIN" if current_look else "SPIN"
        do_spin = st.button(spin_btn_label, key="spin_btn")
        st.markdown("</div>", unsafe_allow_html=True)

        if do_spin:
            if st.session_state.selfie is None:
                st.session_state.selfie = demo_portrait()
                st.session_state.is_demo = True

            # Slot machine spinning animation
            SYMBOLS = ["♦", "★", "7", "♥", "♣", "●", "✦", "🍒", "💄"]
            for _ in range(7):
                s0 = random.choice(SYMBOLS)
                s1 = random.choice(SYMBOLS)
                s2 = random.choice(SYMBOLS)
                reels_placeholder.markdown(
                    f"""
                    <div class="reels" aria-hidden="true">
                      <div class="reel">{s0}</div>
                      <div class="reel">{s1}</div>
                      <div class="reel">{s2}</div>
                    </div>
                    """,
                    unsafe_allow_html=True,
                )
                time.sleep(0.12)

            try:
                r = httpx.post(
                    BACKEND + "/spin",
                    files={"file": ("selfie.png", st.session_state.selfie, "image/png")},
                    # P1-7: 180 s was SMALLER than the backend worst case
                    # (skin poll 180 s + render poll 180 s + uploads), so
                    # the UI could report failure while the backend still
                    # saved the spin. 600 s covers it with margin.
                    timeout=600,
                )
                r.raise_for_status()
                res_look = r.json()
                st.session_state.look = res_look
                st.session_state.feedback = ""
                st.session_state.spin_error = ""
                st.session_state.voted_look_id = None
                if res_look.get("jackpot"):
                    st.session_state.reels = ["7", "7", "7"]
                else:
                    st.session_state.reels = ["♦", "★", "7"]
            except Exception as e:
                # P1-2: the error goes into session state (survives rerun)
                # instead of a bare st.error() that the rerun discards.
                st.session_state.spin_error = f"Spin failed: {str(e)[:160]}"
            st.rerun()

        # P1-2: show any stored spin error (it survives reruns).
        if st.session_state.spin_error:
            st.error(st.session_state.spin_error)

        # P1-12: a live-intended spin that fell back to mock shows a VISIBLE
        # warning — never a silent downgrade.
        if current_look and current_look.get("fallback_warning"):
            st.warning(current_look["fallback_warning"])

        # Look Result Section (when spun)
        if current_look:
            is_real_look = not current_look.get("simulated", simulated)
            real_label = "REAL YouCam render" if is_real_look else "Simulated render (preview)"
            look_name = current_look.get("look_name", "Ember Spin")
            look_fam = current_look.get("family", "terracotta")
            look_tex = current_look.get("texture", "satin")
            intensity = current_look.get("palette", {}).get("intensity", 85)

            st.markdown(
                f"""
                <div class="lookname">{look_name}</div>
                <div class="skin-grid" style="margin-bottom:6px;">
                  <span class="badge">{look_fam} family</span>
                  <span class="badge plain">{look_tex} · intensity {intensity}</span>
                  <span class="badge plain">{real_label}</span>
                </div>
                """,
                unsafe_allow_html=True,
            )

            # Swatches — P1-6: jackpot spins show a TEMPLATE image, so the
            # palette swatches and any "exact palette" claim are wrong for
            # them. Jackpots get a template note instead of swatches.
            if current_look.get("jackpot"):
                st.markdown(
                    '<p class="swatch-note">Curated template look — the image comes from a '
                    "YouCam Look VTO template, so palette swatches do not apply here.</p>",
                    unsafe_allow_html=True,
                )
            else:
                st.markdown(swatches_html(current_look.get("palette", {})), unsafe_allow_html=True)
                swatch_note = (
                    "The exact palette rendered with YouCam Makeup VTO onto your selfie."
                    if is_real_look
                    else f"Generated by color-harmony engine for {undertone_val} undertone."
                )
                st.markdown(f'<p class="swatch-note">{swatch_note}</p>', unsafe_allow_html=True)

            # Swipe Action Buttons: LOVE IT / NEXT
            # P1-8: once this look is voted on, the buttons disable so a
            # repeat click cannot double-count (the backend also guards).
            already_voted = st.session_state.voted_look_id == current_look.get("look_id")
            b1, b2 = st.columns(2)
            with b1:
                st.markdown("<div class='btn-love'>", unsafe_allow_html=True)
                liked = st.button("👍 LOVE IT", key="love_btn", disabled=already_voted)
                st.markdown("</div>", unsafe_allow_html=True)
            with b2:
                st.markdown("<div class='btn-next'>", unsafe_allow_html=True)
                nexted = st.button("👎 NEXT", key="next_btn", disabled=already_voted)
                st.markdown("</div>", unsafe_allow_html=True)

            if liked or nexted:
                is_like = bool(liked)
                try:
                    s = httpx.post(
                        BACKEND + "/swipe",
                        json={"look_id": current_look["look_id"], "liked": is_like},
                        timeout=15,
                    ).json()
                    # P2-13: the old dead `pct = s.get("style_iq", 80)` line
                    # is gone (it was computed and never used).
                    if s.get("changed"):
                        st.session_state.feedback = (
                            f"Noted! {look_fam.capitalize()} looks now carry boosted weight — machine leans your way."
                            if is_like
                            else f"Noted. {look_fam.capitalize()} / {look_tex} drops in frequency — you'll see it less."
                        )
                        st.session_state.voted_look_id = current_look.get("look_id")
                        if is_like:
                            st.balloons()
                    else:
                        st.session_state.feedback = "Already voted on this look — vote unchanged."
                except Exception as e:
                    # P1-9: the error branch must NEVER say "recorded".
                    st.session_state.feedback = f"Swipe failed — not recorded: {str(e)[:80]}"
                st.rerun()

            # Shop Button
            st.markdown("<div class='btn-shop'>", unsafe_allow_html=True)
            if st.button("🛒 Shop This Look", key="shop_btn"):
                try:
                    cart_res = httpx.post(
                        BACKEND + "/cart",
                        json={"look_id": current_look["look_id"]},
                        headers=cart_headers(),
                        timeout=15,
                    ).json()
                    st.session_state.cart = cart_res
                    st.session_state.checkout_done = False
                    # P1-5: the backend dedups identical items — say so
                    # instead of claiming a duplicate was added.
                    if cart_res.get("already_in_cart"):
                        st.session_state.feedback = f"{look_name} is already in your cart."
                    else:
                        st.session_state.feedback = f"{look_name} added to cart (mock)."
                except Exception as e:
                    st.session_state.feedback = f"Cart failed: {str(e)[:80]}"
                st.rerun()
            st.markdown("</div>", unsafe_allow_html=True)

            # Style IQ & Feedback
            try:
                t_data = backend_get("/taste")
                iq_val = t_data.get("style_iq")
            except Exception:
                iq_val = None

            if iq_val is not None:
                st.markdown(
                    f"""
                    <div class="iq-box">
                      <div class="row">
                        <span>Style IQ — the machine is learning your taste</span>
                        <span>{iq_val}%</span>
                      </div>
                      <div class="bar"><i style="width:{iq_val}%;"></i></div>
                    </div>
                    """,
                    unsafe_allow_html=True,
                )

            if st.session_state.feedback:
                st.markdown(f'<p class="feedback-msg">✨ {st.session_state.feedback}</p>', unsafe_allow_html=True)

            # Download Look Card
            # P2-2: build the PNG once per look and cache it — the old code
            # rebuilt it (per-pixel 1080x1350 loop) on EVERY rerun.
            try:
                _cached_id, _cached_png = st.session_state.look_card_cache
                if _cached_id != current_look.get("look_id") or _cached_png is None:
                    _cached_png = look_card_png(
                        st.session_state.selfie,
                        current_look["image"],
                        current_look,
                    )
                    st.session_state.look_card_cache = (current_look.get("look_id"), _cached_png)
                card_bytes = _cached_png
                st.markdown("<div class='btn-download'>", unsafe_allow_html=True)
                st.download_button(
                    "📥 Download Shareable Look Card",
                    data=card_bytes,
                    file_name=f"look-roulette-{current_look['look_id']}.png",
                    mime="image/png",
                    key="dl_btn",
                )
                st.markdown("</div>", unsafe_allow_html=True)
            except Exception as e:
                st.caption(f"Look card unavailable: {str(e)[:80]}")



# ================================================================
# COLUMN 3: SIDE PANEL (Your Cart + Spin History)
# ================================================================
with col_side:
    # (P1-1: native bordered container — see CSS rule)
    with st.container(border=True):
        st.markdown("""<h2>Your Cart <span class="sub">mock checkout — no real payment, no real order</span></h2>""", unsafe_allow_html=True)

        # P1-5: sync with the backend cart every load (per-session id), so a
        # reload shows the real cart instead of an empty local one.
        try:
            st.session_state.cart = backend_get("/cart", headers=cart_headers())
        except Exception:
            pass  # backend down: keep the last known local cart state
        cart_state = st.session_state.cart
        cart_items = cart_state.get("cart", [])
        cart_total = cart_state.get("total", 0.0)

        if not cart_items:
            st.markdown("<p class='empty-note'>Empty — spin a look you love, then shop it.</p>", unsafe_allow_html=True)
        else:
            for item in cart_items:
                st.markdown(
                    f"""
                    <div class="cart-item">
                      <span>💄 {item.get('look_name', 'Look')}</span>
                      <span style="font-family:'IBM Plex Mono',monospace;font-weight:600;">${float(item.get('price', 19.99)):.2f}</span>
                    </div>
                    """,
                    unsafe_allow_html=True,
                )
            st.markdown(f"<div class='cart-total'>Total: ${cart_total:.2f} (mock)</div>", unsafe_allow_html=True)
            st.markdown("<div class='btn-checkout'>", unsafe_allow_html=True)
            if st.button("Checkout (mock)", key="co_btn"):
                # P1-5 + P2-12: clear the BACKEND cart too (old code only
                # cleared local state, so items resurrected on next Shop),
                # and clear the stale "added to cart" feedback message.
                try:
                    httpx.post(BACKEND + "/cart/clear", headers=cart_headers(), timeout=15).raise_for_status()
                    st.session_state.cart = {"cart": [], "total": 0.0}
                    st.session_state.feedback = ""
                    st.session_state.checkout_done = True
                except Exception as e:
                    st.session_state.feedback = f"Checkout failed: {str(e)[:80]}"
                st.rerun()
            st.markdown("</div>", unsafe_allow_html=True)

        if st.session_state.checkout_done:
            st.markdown(
                '<div class="checkout-msg">🎉 Mock checkout complete — no real payment, no real order.</div>',
                unsafe_allow_html=True,
            )


    # (P1-1: native bordered container — see CSS rule)
    with st.container(border=True):
        st.markdown("""<h2>Spin History <span class="sub">latest spins (all sessions on this backend)</span></h2>""", unsafe_allow_html=True)
        try:
            past_looks = backend_get("/looks").get("looks", [])
            if past_looks:
                st.markdown("<ul class='hist'>", unsafe_allow_html=True)
                # P1-4: /looks returns id DESC (newest first), so the 8
                # NEWEST are past_looks[:8] in order — the old
                # reversed(past_looks[-8:]) showed the 8 OLDEST, oldest-first.
                # P2-4: unswiped looks get a neutral mark; jackpots keep
                # their JACKPOT tag (jackpot_text below) instead of the mark.
                for l in past_looks[:8]:
                    mark = "👍" if l.get("liked") == 1 else ("👎" if l.get("liked") == 0 else "○")
                    live_text = "<span class='live'> · LIVE YouCam</span>" if not l.get("mock", True) else " · simulated"
                    jackpot_text = " · <b style='color:#ffd76a;'>JACKPOT</b>" if l.get("jackpot") else ""
                    st.markdown(
                        f"""
                        <li>
                          <span class="mark">{mark}</span>
                          <span>
                            <b>{l.get('look_name', 'Look')}</b>
                            <span class="meta">{l.get('family', '')} · {l.get('texture', '')}{live_text}{jackpot_text}</span>
                          </span>
                        </li>
                        """,
                        unsafe_allow_html=True,
                    )
                st.markdown("</ul>", unsafe_allow_html=True)
            else:
                st.markdown("<p class='empty-note'>No spins yet — press SPIN to begin.</p>", unsafe_allow_html=True)
        except Exception:
            st.markdown("<p class='empty-note'>Log starts after your first spin.</p>", unsafe_allow_html=True)



# ================================================================
# LOWER SECTION: Under the Hood + Style DNA
# ================================================================
col_dna, col_hood = st.columns([1, 1], gap="medium")

with col_dna:
    with st.container(border=True):
        st.markdown("""<h2>🧬 Style DNA <span class="sub">what the machine has learned from your swipes</span></h2>""", unsafe_allow_html=True)
        try:
            t_data = backend_get("/taste")
            st.markdown(style_dna_html(t_data.get("taste", []), t_data.get("style_iq")), unsafe_allow_html=True)
        except Exception:
            st.markdown("<p class='empty-note'>Style DNA starts recording once you vote 👍 or 👎 on looks.</p>", unsafe_allow_html=True)

with col_hood:
    st.markdown(
        """
        <section class="card">
          <h2>Under the Hood <span class="sub">how Look Roulette works</span></h2>
          <ol class="steps">
            <li><b>Analyze.</b> The selfie goes to YouCam SD Skin Analysis — undertone plus a per-concern Skin Analysis Report.</li>
            <li><b>Spin.</b> A color-harmony palette engine picks a lip, blush and shadow set that suits the undertone — weighted by everything you've swiped so far.</li>
            <li><b>Render.</b> YouCam Makeup VTO paints the exact hex shades and texture onto the selfie.</li>
            <li><b>Learn.</b> Every LOVE IT / NEXT retrains the taste profile in SQLite, so your favourite families spin up more often. Style IQ tracks the match.</li>
            <li><b>Shop.</b> Love a look? One tap builds the cart.</li>
          </ol>
          <table class="units" aria-label="YouCam API unit costs">
            <thead><tr><th>API call</th><th class="num">Units</th></tr></thead>
            <tbody>
              <tr><td>SD Skin Analysis</td><td class="num">9 / spin</td></tr>
              <tr><td>Makeup VTO render</td><td class="num">1 / spin</td></tr>
              <tr><td>Failed task</td><td class="num">refunded</td></tr>
              <tr><td><b>One full live spin (non-jackpot)</b></td><td class="num"><b>10</b></td></tr>
              <tr><td>Jackpot live spin (Look VTO template)</td><td class="num">9 + Look VTO (price to verify)</td></tr>
              <tr><td>Account balance (approx., at last check)</td><td class="num">≈433</td></tr>
            </tbody>
          </table>
          <div class="stack">
            <span>FastAPI</span><span>Streamlit</span><span>SQLite</span><span>YouCam Skin AI</span><span>YouCam Makeup VTO</span><span>Color-harmony engine</span>
          </div>
        </section>
        """,
        unsafe_allow_html=True,
    )

# ---------------------------------------------------------------- footer
# P2-3: in simulated mode the footer must not claim YouCam-powered renders.
footer_renders = (
    "Renders powered by <b>YouCam Skin AI &amp; Makeup VTO</b>."
    if not _chip_simulated
    else "Simulated preview — no live YouCam renders in this mode."
)
st.markdown(
    f"""
    <div class="app-footer">
      <span>Look Roulette — built for the <b>YouCam API Skin AI &amp; eCommerce VTO Hackathon</b> (Perfect Corp).</span>
      <span>{footer_renders}</span>
    </div>
    """,
    unsafe_allow_html=True,
)

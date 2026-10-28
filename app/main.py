"""Look Roulette backend: FastAPI + SQLite + YouCam provider."""
import base64
import hashlib
import io
import random
import uuid
from contextlib import asynccontextmanager

from fastapi import FastAPI, File, Header, HTTPException, UploadFile
from PIL import Image
from pydantic import BaseModel

from . import db
from .palette import generate_palette
from .youcam import MockYouCamProvider, get_provider, palette_to_effects

# P2-7: reject oversized uploads before they are read into memory.
MAX_UPLOAD_BYTES = 10 * 1024 * 1024


@asynccontextmanager
async def lifespan(_app):
    # P2-15: DB creation happens at server startup, NOT at import time, so
    # importing this module (tests, inspection) creates no state on disk.
    db.init_db()
    yield


app = FastAPI(title="Look Roulette", lifespan=lifespan)

# P1-5: carts are scoped per client session (header X-Session-Id), never a
# single module-global list shared across all browsers.
_carts: dict = {}


def _session_id(x_session_id: str | None) -> tuple:
    """Return (session_id, is_new). Headerless clients get a fresh id that
    the response returns, so the frontend can send it on later calls."""
    if x_session_id:
        return x_session_id, False
    return uuid.uuid4().hex, True


def _cart_total(cart: list) -> float:
    return round(sum(i["price"] for i in cart), 2)


class SwipeIn(BaseModel):
    look_id: int
    liked: bool


class CartIn(BaseModel):
    look_id: int


def _mock_price(look_id: int) -> float:
    # Deterministic mock price per look.
    return round(18 + (look_id * 7) % 30 + 0.99, 2)


@app.get("/health")
def health():
    return {"status": "ok", "simulated": get_provider().is_mock}


@app.post("/spin")
async def spin(file: UploadFile = File(...)):
    # P2-7: read at most cap+1 bytes so an oversized upload is rejected
    # before a multi-hundred-MB body is buffered.
    raw = await file.read(MAX_UPLOAD_BYTES + 1)
    if not raw:
        raise HTTPException(status_code=400, detail="empty upload")
    if len(raw) > MAX_UPLOAD_BYTES:
        raise HTTPException(status_code=413, detail="upload exceeds 10 MB limit")
    try:
        Image.open(io.BytesIO(raw)).verify()
    except Exception:
        raise HTTPException(status_code=400, detail="upload is not a valid image")

    provider = get_provider()
    # P1-12: any fallback to the mock is reported to the UI, never silent.
    skin_fell_back = False
    render_fell_back = False
    try:
        skin = await provider.analyze_skin(raw)
    except Exception:
        # Live API failed: fall back to simulated so the demo never dies.
        provider = MockYouCamProvider()
        skin = await provider.analyze_skin(raw)
        skin_fell_back = True
    undertone = skin.get("undertone", "neutral") or "neutral"

    # Deterministic per (image, spin number): stable demo across reruns.
    seed = hashlib.sha256(raw).hexdigest() + ":" + str(db.spin_count())
    rng = random.Random(seed)

    palette = generate_palette(undertone, db.get_taste_weights(), rng)

    # Occasional "jackpot": a curated Look VTO template (live mode only).
    # P1-11: the Look VTO unit price is NOT claimed here — the backend
    # comment previously said "2 units/call" while the UI table said a flat
    # 10/spin. The true price must be verified against the console; the UI
    # table now states the jackpot cost as "9 + Look VTO (price to verify)".
    jackpot = False
    template_name = None
    try:
        if not provider.is_mock and rng.random() < 0.125:
            templates = await provider.list_look_templates()
            if templates:
                template_id = templates[0].get("template_id") or templates[0].get("id")
                # P1-6: keep the template's own name so the UI shows it
                # instead of the generated palette name for jackpot spins.
                template_name = templates[0].get("name") or templates[0].get("title")
                if template_id:
                    rendered = await provider.render_look(raw, str(template_id), seed=seed)
                    jackpot = True
        if not jackpot:
            rendered = await provider.render_makeup(raw, palette_to_effects(palette), seed=seed)
    except Exception:
        # Live render failed mid-spin: fall back to simulated for this spin.
        provider = MockYouCamProvider()
        rendered = await provider.render_makeup(raw, palette_to_effects(palette), seed=seed)
        jackpot = False
        template_name = None
        render_fell_back = True

    # P1-12: build the visible warning from exactly what fell back.
    fallback_warning = None
    if skin_fell_back and render_fell_back:
        fallback_warning = "Live YouCam was unreachable — this look is fully simulated (0 live units used)."
    elif render_fell_back:
        fallback_warning = (
            "Live skin analysis ran, but the render fell back to a simulated preview — "
            "the image is NOT a live YouCam render."
        )
    elif skin_fell_back:
        fallback_warning = "Live skin analysis failed, so this look is simulated (preview engine)."

    look_id = db.save_spin(palette, jackpot=jackpot, mock=provider.is_mock)
    img_b64 = base64.b64encode(rendered).decode("ascii")

    return {
        "look_id": look_id,
        # P1-6: jackpot spins carry the template name, not the palette name.
        "look_name": template_name if (jackpot and template_name) else palette["look_name"],
        "template_name": template_name,
        "family": palette["family"],
        "texture": palette["texture"],
        "undertone": undertone,
        "palette": {
            "lip": palette["lip"],
            "blush_hex": palette["blush_hex"],
            "shadows": palette["shadows"],
            "intensity": palette["intensity"],
        },
        "image": "data:image/png;base64," + img_b64,
        "jackpot": jackpot,
        "simulated": provider.is_mock,
        "fallback_warning": fallback_warning,
        "skin_report": {
            "undertone": undertone,
            "skin_type": skin.get("skin_type"),
            "scores": skin.get("scores", {}),
        },
    }


@app.post("/swipe")
def swipe(body: SwipeIn):
    # P1-8: set_swipe returns (found, changed); a repeat vote on the same
    # look is a no-op, and LOVE -> NEXT moves the vote instead of adding both.
    found, changed = db.set_swipe(body.look_id, body.liked)
    if not found:
        raise HTTPException(status_code=404, detail="look not found")
    likes, dislikes, pct = db.style_iq()
    return {"ok": True, "changed": changed, "likes": likes, "dislikes": dislikes, "style_iq": pct}


@app.get("/looks")
def looks():
    return {"looks": db.list_spins(20)}


@app.get("/taste")
def taste():
    """Learned taste profile: per family+texture likes/dislikes + Style IQ."""
    likes, dislikes, pct = db.style_iq()
    rows = [
        {"family": fam, "texture": tex, "likes": lk, "dislikes": dk}
        for (fam, tex), (lk, dk) in db.get_taste_weights().items()
    ]
    return {"taste": rows, "likes": likes, "dislikes": dislikes, "style_iq": pct}


@app.get("/cart")
def get_cart(x_session_id: str | None = Header(default=None)):
    # P1-5: the frontend syncs with this endpoint on every load, so a page
    # reload shows the real backend cart instead of an empty local one.
    session_id, is_new = _session_id(x_session_id)
    cart = _carts.setdefault(session_id, [])
    return {"cart": cart, "total": _cart_total(cart), "mock": True, "session_id": session_id}


@app.post("/cart")
def add_to_cart(body: CartIn, x_session_id: str | None = Header(default=None)):
    session_id, _ = _session_id(x_session_id)
    cart = _carts.setdefault(session_id, [])
    spin = db.get_spin(body.look_id)
    if not spin:
        raise HTTPException(status_code=404, detail="look not found")
    # P1-5: identical items are deduplicated, not added as duplicate lines.
    for existing in cart:
        if existing["look_id"] == spin["id"]:
            return {"cart": cart, "total": _cart_total(cart), "mock": True,
                    "session_id": session_id, "already_in_cart": True}
    item = {
        "look_id": spin["id"],
        "look_name": spin["look_name"],
        "price": _mock_price(spin["id"]),
        "mock": True,
    }
    cart.append(item)
    return {"cart": cart, "total": _cart_total(cart), "mock": True,
            "session_id": session_id, "already_in_cart": False}


@app.post("/cart/clear")
def clear_cart(x_session_id: str | None = Header(default=None)):
    # P1-5: mock checkout clears the BACKEND cart too, so the next Shop
    # click cannot resurrect already-"checked-out" items.
    session_id, _ = _session_id(x_session_id)
    _carts[session_id] = []
    return {"cart": [], "total": 0.0, "mock": True, "session_id": session_id}

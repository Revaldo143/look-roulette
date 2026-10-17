"""Look Roulette backend: FastAPI + SQLite + YouCam provider."""
import base64
import hashlib
import io
import random

from fastapi import FastAPI, File, HTTPException, UploadFile
from PIL import Image
from pydantic import BaseModel

from . import db
from .palette import generate_palette
from .youcam import MockYouCamProvider, get_provider, palette_to_effects

app = FastAPI(title="Look Roulette")
db.init_db()

_cart: list = []


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
    raw = await file.read()
    if not raw:
        raise HTTPException(status_code=400, detail="empty upload")
    try:
        Image.open(io.BytesIO(raw)).verify()
    except Exception:
        raise HTTPException(status_code=400, detail="upload is not a valid image")

    provider = get_provider()
    try:
        skin = await provider.analyze_skin(raw)
    except Exception:
        # Live API failed: fall back to simulated so the demo never dies.
        provider = MockYouCamProvider()
        skin = await provider.analyze_skin(raw)
    undertone = skin.get("undertone", "neutral") or "neutral"

    # Deterministic per (image, spin number): stable demo across reruns.
    seed = hashlib.sha256(raw).hexdigest() + ":" + str(db.spin_count())
    rng = random.Random(seed)

    palette = generate_palette(undertone, db.get_taste_weights(), rng)

    # Occasional "jackpot": a curated Look VTO template (live mode only, 2 units/call).
    jackpot = False
    try:
        if not provider.is_mock and rng.random() < 0.125:
            templates = await provider.list_look_templates()
            if templates:
                template_id = templates[0].get("template_id") or templates[0].get("id")
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

    look_id = db.save_spin(palette, jackpot=jackpot, mock=provider.is_mock)
    img_b64 = base64.b64encode(rendered).decode("ascii")

    return {
        "look_id": look_id,
        "look_name": palette["look_name"],
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
        "skin_report": {
            "undertone": undertone,
            "skin_type": skin.get("skin_type"),
            "scores": skin.get("scores", {}),
        },
    }


@app.post("/swipe")
def swipe(body: SwipeIn):
    if not db.set_swipe(body.look_id, body.liked):
        raise HTTPException(status_code=404, detail="look not found")
    likes, dislikes, pct = db.style_iq()
    return {"ok": True, "likes": likes, "dislikes": dislikes, "style_iq": pct}


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


@app.post("/cart")
def add_to_cart(body: CartIn):
    spin = db.get_spin(body.look_id)
    if not spin:
        raise HTTPException(status_code=404, detail="look not found")
    item = {
        "look_id": spin["id"],
        "look_name": spin["look_name"],
        "price": _mock_price(spin["id"]),
        "mock": True,
    }
    _cart.append(item)
    total = round(sum(i["price"] for i in _cart), 2)
    return {"cart": _cart, "total": total, "mock": True}

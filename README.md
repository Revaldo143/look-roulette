# 🎰 Look Roulette — Spin. Swipe. Slay.

A slot-machine makeup discovery app for the **YouCam API Skin AI & eCommerce VTO Hackathon** (Perfect Corp, Devpost).

**The loop:** upload a selfie → skin tone is analyzed → a palette generator picks hue families
harmonious with *your* undertone → **SPIN** renders the look on your face via Makeup VTO →
swipe like/dislike → a taste profile in SQLite makes every spin visibly smarter →
**Shop This Look** (mock cart).

## Quickstart

```bash
cd ~/workspace/lookroulette
python3 -m venv .venv
.venv/bin/pip install -r requirements.txt

# Terminal 1 — backend
.venv/bin/uvicorn app.main:app --port 8000

# Terminal 2 — frontend
.venv/bin/streamlit run app/streamlit_app.py
```

Open the Streamlit URL, upload a selfie, hit **🎰 SPIN**.
For an instant demo without a photo: append `?demo=1` (uses an illustrated demo portrait).

## Real vs simulated (mock) — read this

- **Without the YouCam credential**, the app runs in **SIMULATED mode**: a deterministic,
  seeded mock provider returns plausible skin-tone data and palette-tinted renders.
  Same selfie → same results, so the demo is stable across reruns. The UI labels
  this clearly ("Simulated preview mode").
- **With the YouCam credential connected** (Secure Vault, `custom.youcam`), the app uses
  the real YouCam API: `Authorization: Bearer` (short-lived vault surrogate — the real
  key never appears in code, env, or logs) against `https://yce-api-01.makeupar.com`,
  async task endpoints (`/s2s/v2.0/task/skin-analysis`, `/s2s/v2.0/task/makeup-vto`,
  `/s2s/v2.0/task/look-vto`) with status polling. Occasional "jackpot" spins use a
  curated Look VTO template (2 API units/call — used sparingly, ~1 in 8 spins).
- **The key holder needs to do nothing code-wise**: the credential is saved once
  through Muse's secure connect flow and the app picks it up automatically.

## API

| Method | Path | What |
|---|---|---|
| GET | `/health` | status + `simulated` flag |
| POST | `/spin` | multipart selfie → `{look_id, look_name, palette, image (data URI), jackpot, simulated, skin_report}` |
| POST | `/swipe` | `{look_id, liked}` → updates taste profile, returns Style IQ |
| GET | `/looks` | spin history |
| POST | `/cart` | mock add-to-cart → `{cart, total}` |

## Project layout

```
lookroulette/
├── app/
│   ├── main.py          # FastAPI: /spin /swipe /looks /cart /health
│   ├── db.py            # SQLite: spins + taste tables
│   ├── palette.py       # pure-Python undertone → hue-family generator (deterministic)
│   ├── youcam.py        # provider protocol; SIMULATED mock + live YouCam client + factory
│   └── streamlit_app.py # casino-glam frontend: upload → SPIN → swipe → mock cart
├── data/                # SQLite db (gitignored in real repo)
├── requirements.txt
└── README.md
```

## Devpost submission notes

- **Judging criteria it targets:** Technological Implementation (measured skin tone *generates*
  the palettes the VTO renders — beyond a single API call), Design (3-second spin-and-reveal
  hook, casino-glam UI), Potential Impact (shade anxiety / decision paralysis in beauty
  shopping, taste-learning = the brief's "self-learning styling assistant"), Quality of Idea
  (joy-first game loop vs earnest utilities).
- **Demo script (100 seconds):** 0–10s hook ("your face is a slot machine"), 10–40s upload +
  SPIN + reveal, 40–70s swipe twice showing Style IQ climbing, 70–90s Shop This Look mock
  cart, 90–100s "Spin. Swipe. Slay." close.
- **Claim hygiene:** no absolute claims anywhere (no "0% mismatch", no "guarantee");
  skin values are shown as a "Skin Analysis Report"; no medical claims.

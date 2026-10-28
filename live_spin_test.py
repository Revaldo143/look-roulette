"""One-shot live /spin test for Look Roulette. Saves before/after PNGs.

NOTE: running this against a live backend spends a real ~10-unit spin by
design ("live_spin_test" is its name) — never run it casually.
"""
import json, base64, io, time, random, uuid, urllib.request, os, sys
from PIL import Image, ImageDraw

# P2-9: the old script hardcoded /home/hatch/workspace/lookroulette/shots/,
# which does not exist on the user's laptop (crash on open()). The output
# dir is now script-relative, overridable via LOOKROULETTE_SHOTS, and
# created if missing.
OUT_DIR = os.environ.get(
    "LOOKROULETTE_SHOTS",
    os.path.join(os.path.dirname(os.path.abspath(__file__)), "shots"),
)
os.makedirs(OUT_DIR, exist_ok=True)

def demo_portrait() -> bytes:
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
    d.ellipse([100, 150, 412, 490], fill=(214, 164, 128))
    d.arc([84, 100, 428, 440], start=180, end=360, fill=(58, 32, 20), width=34)
    d.arc([180, 270, 240, 305], start=200, end=340, fill=(40, 22, 16), width=4)
    d.arc([272, 270, 332, 305], start=200, end=340, fill=(40, 22, 16), width=4)
    d.ellipse([216, 390, 296, 416], fill=(170, 80, 80))
    for _ in range(24):
        x, y = rng.randint(0, W - 1), rng.randint(0, H - 1)
        d.ellipse([x, y, x + 3, y + 3], fill=(245, 197, 24, 160))
    buf = io.BytesIO()
    img.save(buf, format="PNG")
    return buf.getvalue()

portrait = demo_portrait()
print("portrait bytes:", len(portrait), flush=True)

boundary = uuid.uuid4().hex
body = (
    f"--{boundary}\r\nContent-Disposition: form-data; name=\"file\"; filename=\"demo.png\"\r\n"
    "Content-Type: image/png\r\n\r\n"
).encode() + portrait + f"\r\n--{boundary}--\r\n".encode()
req = urllib.request.Request("http://127.0.0.1:8000/spin", data=body, method="POST")
req.add_header("Content-Type", f"multipart/form-data; boundary={boundary}")
t0 = time.time()
try:
    with urllib.request.urlopen(req, timeout=600) as r:
        result = json.loads(r.read().decode())
except Exception as e:
    # P2-9: a failed spin no longer leaves a misleading "before" file
    # behind, and no KeyError is raised on an error payload.
    print("spin request failed:", e, flush=True)
    sys.exit(1)
print(f"spin done in {time.time()-t0:.0f}s", flush=True)
print("look:", result.get("look_name"), "| family:", result.get("family"),
      "| texture:", result.get("texture"), "| undertone:", result.get("undertone"),
      "| jackpot:", result.get("jackpot"), "| simulated:", result.get("simulated"), flush=True)
print("palette:", json.dumps(result.get("palette"))[:200], flush=True)
if not result.get("image"):
    # Error payload (e.g. {"detail": ...}) instead of an image: report it
    # and exit non-zero rather than raising KeyError.
    print("spin returned no image:", json.dumps(result)[:300], flush=True)
    sys.exit(1)
# P2-9: both files are written only AFTER a successful spin.
open(os.path.join(OUT_DIR, "spin_before.png"), "wb").write(portrait)
img_b64 = result["image"].split(",", 1)[1]
open(os.path.join(OUT_DIR, "spin_after.png"), "wb").write(base64.b64decode(img_b64))
print("saved:", os.path.join(OUT_DIR, "spin_before.png"), "and",
      os.path.join(OUT_DIR, "spin_after.png"), flush=True)

"""YouCam API provider layer: protocol + deterministic mock + live client.

Architecture: the UI/backend never talks to YouCam directly; everything goes
through a provider. ``get_provider()`` returns the live client only when the
Secure Vault holds the YouCam credential (``custom.youcam``), otherwise a
clearly-labeled SIMULATED mock.

The API key lives in the vault and is NEVER in env vars, files, or logs. Each
request carries a short-lived ``hsurr:`` surrogate in the Authorization header;
the runtime swaps in the real credential only on approved requests to the
registered API host.
"""
import asyncio
import hashlib
import importlib.util
import io
import os
import random
import sys
import urllib.request

from PIL import Image, ImageEnhance

sys.path.insert(0, "/opt/muse/skills/custom-connector-setup/bin")
from dynamic_credentials import dynamic_credential_entry

HOST = "https://yce-api-01.makeupar.com"
VAULT_CONNECTION = "custom.youcam"
HELPER_PATH = os.path.expanduser(
    "~/workspace/custom-connectors/custom.youcam/bin/youcam-api.py"
)


def _vault_headers() -> dict:
    """Fresh Authorization header via the vault surrogate exchange."""
    entry = dynamic_credential_entry(VAULT_CONNECTION)
    surrogate = str(entry["surrogate"]).strip()
    if not surrogate.startswith("hsurr:"):
        raise RuntimeError("vault did not return a surrogate credential")
    return {"Authorization": "Bearer " + surrogate}


def _load_helper():
    """Import the vault connector helper module (urllib-based transport)."""
    spec = importlib.util.spec_from_file_location("youcam_api_helper", HELPER_PATH)
    mod = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(mod)
    return mod


# ---------------------------------------------------------------------------
# Provider protocol
# ---------------------------------------------------------------------------
class YouCamProvider:
    is_mock = True

    async def analyze_skin(self, image_bytes: bytes) -> dict:
        """Return {'undertone': warm|cool|neutral, 'skin_type': str, 'scores': {...}}."""
        raise NotImplementedError

    async def render_makeup(self, image_bytes: bytes, effects: list, seed: str = "") -> bytes:
        """Render makeup VTO; returns PNG bytes."""
        raise NotImplementedError

    async def list_look_templates(self) -> list:
        raise NotImplementedError

    async def render_look(self, image_bytes: bytes, template_id: str, seed: str = "") -> bytes:
        """Render a curated Look VTO template ('jackpot' spins)."""
        raise NotImplementedError


# ---------------------------------------------------------------------------
# Deterministic SIMULATED mock (used when no API key is configured)
# ---------------------------------------------------------------------------
class MockYouCamProvider(YouCamProvider):
    """SIMULATED provider. Seeded RNG -> identical input gives identical output,
    so the demo is stable across reruns."""

    is_mock = True

    @staticmethod
    def _rng(image_bytes: bytes, salt: str = "") -> random.Random:
        h = hashlib.sha256(image_bytes + salt.encode()).hexdigest()
        return random.Random(h)

    async def analyze_skin(self, image_bytes: bytes) -> dict:
        rng = self._rng(image_bytes, "skin")
        return {
            "undertone": rng.choice(["warm", "cool", "neutral"]),
            "skin_type": rng.choice(["normal", "combination", "dry", "oily"]),
            "scores": {
                "radiance": rng.randint(55, 92),
                "evenness": rng.randint(50, 90),
                "smoothness": rng.randint(55, 93),
            },
            "simulated": True,
        }

    async def render_makeup(self, image_bytes: bytes, effects: list, seed: str = "") -> bytes:
        lip_hex = "#B5542D"
        for eff in effects or []:
            if eff.get("category") == "lip_color":
                palettes = eff.get("palettes") or [{}]
                lip_hex = palettes[0].get("hex", lip_hex)
        rng = self._rng(image_bytes, "vto:" + seed + ":" + lip_hex)
        img = Image.open(io.BytesIO(image_bytes)).convert("RGB")
        # SIMULATED "render": palette-hued color grade + gentle pop.
        overlay = Image.new("RGB", img.size, lip_hex)
        img = Image.blend(img, overlay, 0.10 + rng.random() * 0.06)
        img = ImageEnhance.Color(img).enhance(1.08)
        img = ImageEnhance.Contrast(img).enhance(1.03)
        buf = io.BytesIO()
        img.save(buf, format="PNG")
        return buf.getvalue()

    async def list_look_templates(self) -> list:
        return [{"template_id": "mock-glam-01", "name": "Simulated Red-Carpet Glam"}]

    async def render_look(self, image_bytes: bytes, template_id: str, seed: str = "") -> bytes:
        return await self.render_makeup(image_bytes, [], seed="jackpot:" + seed)


# ---------------------------------------------------------------------------
# Live YouCam API client
# ---------------------------------------------------------------------------
class LiveYouCamProvider(YouCamProvider):
    """Real YouCam API client. Async task-based endpoints with polling.

    Transport goes through the Secure Vault connector helper
    (``custom.youcam``), which applies the vault surrogate on every request,
    so the real key never appears here. The helper is urllib-based because it
    is the transport proven to work through this environment's egress proxy.
    Blocking calls run in threads to keep the event loop responsive.
    """

    is_mock = False

    def __init__(self):
        self._yc = _load_helper()
        _vault_headers()  # prove the vault credential is reachable

    async def _apicall(self, method: str, path: str, data: dict = None) -> dict:
        """One authenticated JSON call through the vault helper."""
        res = await asyncio.to_thread(self._yc.call, method, path, data)
        status = res.get("http_status")
        if status != 200:
            detail = res.get("error") or res.get("body")
            raise RuntimeError(
                "YouCam %s %s -> HTTP %s: %s"
                % (method, path, status, str(detail)[:300])
            )
        body = res.get("body") or {}
        return body if isinstance(body, dict) else {"data": body}

    async def _download(self, url: str) -> bytes:
        """Result image URLs are public; plain download, no auth needed.

        Uses curl: Python's urllib consistently gets truncated reads through
        this VM's egress proxy on S3 accelerate URLs, while curl completes.
        """

        def _get():
            import subprocess

            last = None
            for _ in range(3):
                try:
                    proc = subprocess.run(
                        ["curl", "-sS", "--max-time", "90", url],
                        capture_output=True,
                        timeout=120,
                    )
                    if proc.returncode == 0 and proc.stdout:
                        return proc.stdout
                    last = RuntimeError(
                        "curl exit %s: %s"
                        % (proc.returncode, proc.stderr.decode()[:200])
                    )
                except Exception as e:
                    last = e
            raise last

        return await asyncio.to_thread(_get)

    async def _upload(self, image_bytes: bytes) -> str:
        res = await asyncio.to_thread(
            self._yc.upload_bytes, bytes(image_bytes), "selfie.png", "image/png"
        )
        if res.get("http_status") != 200:
            raise RuntimeError(
                "file upload -> HTTP %s: %s"
                % (
                    res.get("http_status"),
                    str(res.get("error") or res.get("body"))[:300],
                )
            )
        file_id = res.get("file_id")
        if not file_id:
            raise RuntimeError("file upload: no file_id in response")
        return file_id

    async def _create_task(self, endpoint: str, payload: dict) -> str:
        data = await self._apicall("POST", endpoint, payload)
        task_id = data.get("task_id") or data.get("data", {}).get("task_id")
        if not task_id:
            raise RuntimeError(endpoint + ": no task_id in response")
        return task_id

    async def _poll_task(
        self, base: str, task_id: str, timeout: int = 180, interval: int = 3
    ) -> dict:
        elapsed = 0
        while elapsed < timeout:
            data = await self._apicall("GET", "%s/%s" % (base, task_id))
            payload = data.get("data", data) if isinstance(data, dict) else {}
            status = payload.get("task_status")
            if status == "success":
                return payload
            if status in ("failed", "error"):
                raise RuntimeError("task %s failed (status=%s)" % (task_id, status))
            await asyncio.sleep(interval)
            elapsed += interval
        raise TimeoutError("task %s timed out after %ss" % (task_id, timeout))

    @staticmethod
    def _result_url(payload: dict) -> str:
        """Extract the result image URL from a task payload (handles both shapes)."""
        if not isinstance(payload, dict):
            return ""
        for key in ("result_url", "dst_file_url", "url"):
            if payload.get(key):
                return payload[key]
        results = payload.get("results")
        if isinstance(results, dict):
            return results.get("url") or results.get("download_url") or ""
        if isinstance(results, list) and results:
            first = results[0] if isinstance(results[0], dict) else {}
            return first.get("download_url") or first.get("url") or ""
        return ""

    def _parse_undertone(self, payload: dict) -> str:
        text = str(payload).lower()
        if "warm" in text:
            return "warm"
        if "cool" in text:
            return "cool"
        return "neutral"

    async def analyze_skin(self, image_bytes: bytes) -> dict:
        src = await self._upload(image_bytes)
        task_id = await self._create_task(
            "/s2s/v2.0/task/skin-analysis",
            {"src_file_id": src, "dst_actions": ["skin_type"]},
        )
        payload = await self._poll_task("/s2s/v2.0/task/skin-analysis", task_id)
        scores = {}
        blob = payload.get("data", payload) if isinstance(payload, dict) else {}
        concerns = blob.get("scores") if isinstance(blob, dict) else None
        if not isinstance(concerns, dict):
            concerns = blob if isinstance(blob, dict) else {}
        for concern, vals in concerns.items():
            if isinstance(vals, dict) and ("ui_score" in vals or "raw_score" in vals):
                scores[concern] = vals.get("ui_score", vals.get("raw_score"))
        skin_type = "unknown"
        if isinstance(blob, dict):
            skin_type = str(blob.get("skin_type", payload.get("skin_type", "unknown")))
        return {
            "undertone": self._parse_undertone(payload),
            "skin_type": skin_type,
            "scores": scores,
            "simulated": False,
        }

    async def render_makeup(self, image_bytes: bytes, effects: list, seed: str = "") -> bytes:
        src = await self._upload(image_bytes)
        task_id = await self._create_task(
            "/s2s/v2.0/task/makeup-vto",
            {"src_file_id": src, "effects": effects, "version": "1.0"},
        )
        payload = await self._poll_task("/s2s/v2.0/task/makeup-vto", task_id)
        result_url = self._result_url(payload)
        if not result_url:
            raise RuntimeError("makeup-vto: no result image URL in response")
        return await self._download(result_url)

    async def list_look_templates(self) -> list:
        data = await self._apicall("GET", "/s2s/v2.0/task/template/look-vto")
        inner = data.get("data", {}) if isinstance(data, dict) else {}
        templates = inner.get("templates") or []
        return templates if isinstance(templates, list) else []

    async def render_look(self, image_bytes: bytes, template_id: str, seed: str = "") -> bytes:
        src = await self._upload(image_bytes)
        task_id = await self._create_task(
            "/s2s/v2.0/task/look-vto",
            {"src_file_id": src, "template_id": template_id},
        )
        payload = await self._poll_task("/s2s/v2.0/task/look-vto", task_id)
        result_url = self._result_url(payload)
        if not result_url:
            raise RuntimeError("look-vto: no result image URL in response")
        return await self._download(result_url)


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------
def _lip_palette_entry(hex_color: str, texture: str, intensity: int) -> dict:
    p = {"color": hex_color, "texture": texture, "colorIntensity": intensity}
    if texture in ("gloss", "holographic", "metallic", "sheer", "shimmer"):
        p["gloss"] = 60
    if texture in ("holographic", "metallic", "shimmer"):
        p.update(
            {
                "shimmerColor": hex_color,
                "shimmerIntensity": 50,
                "shimmerDensity": 50,
                "shimmerSize": 50,
            }
        )
    if texture in ("gloss", "sheer", "shimmer"):
        p["transparencyIntensity"] = 50
    return p


def _blush_palette_entry(hex_color: str, texture: str, intensity: int) -> dict:
    p = {"color": hex_color, "colorIntensity": intensity}
    bt = texture if texture in ("matte", "satin", "shimmer") else "matte"
    p["texture"] = bt
    # glowStrength is required by the API for non-matte blush (empirically
    # also for shimmer, despite the docs listing it under satin only).
    p["glowStrength"] = 50
    if bt == "shimmer":
        p.update({"shimmerColor": hex_color, "shimmerDensity": 50})
    return p


def _shadow_palette_entry(hex_color: str, texture: str, intensity: int) -> dict:
    p = {"color": hex_color, "colorIntensity": intensity}
    st = texture if texture in ("matte", "shimmer", "metallic") else "matte"
    p["texture"] = st
    if st in ("shimmer", "metallic"):
        p.update({"shimmerColor": hex_color, "shimmerIntensity": 50})
    if st == "metallic":
        p["metallicIntensity"] = 50
    return p


def palette_to_effects(palette: dict) -> list:
    """Translate a generated palette into Makeup VTO effect payloads (v1.0 schema)."""
    tex = palette["texture"]
    inten = palette["intensity"]
    return [
        {
            "category": "lip_color",
            "shape": {"name": "original"},
            "style": {"type": "full"},
            "palettes": [_lip_palette_entry(palette["lip"]["hex"], tex, inten)],
        },
        {
            "category": "blush",
            "pattern": {"name": "1color1"},
            "palettes": [
                _blush_palette_entry(
                    palette["blush_hex"], tex, max(40, inten - 20)
                )
            ],
        },
        {
            "category": "eye_shadow",
            "pattern": {"name": "3colors1"},
            "palettes": [
                _shadow_palette_entry(h, tex, max(40, inten - 15))
                for h in palette["shadows"][:3]
            ],
        },
    ]


def get_provider() -> YouCamProvider:
    """Factory: live client when the vault holds the YouCam credential,
    else SIMULATED mock."""
    try:
        return LiveYouCamProvider()
    except Exception:
        return MockYouCamProvider()

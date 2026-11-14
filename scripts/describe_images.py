#!/usr/bin/env python3
"""Describe inbox images via OpenRouter (agent's own vision model is unreliable here).

Resumable: writes data/image_descriptions.json as it goes and skips files already done.
Usage: python describe_images.py [dir] [--limit N]
"""
import base64
import glob
import json
import os
import sys
import time
import urllib.request

KEY = open("/opt/data/.secrets/openrouter_key.txt").read().strip()
MODEL = os.environ.get("VISION_MODEL", "qwen/qwen2.5-vl-72b-instruct")
DATA = "/opt/data/projects/burger-lab/data"
OUT = os.path.join(DATA, "image_descriptions.json")
PROMPT = (
    "You are helping a vegetarian burger cart pick photos for WhatsApp group posts. "
    "Describe literally: (1) the main food items visible and any recognisable packaging/branding, "
    "(2) setting/background, (3) lighting quality, (4) any people, hands, or faces, "
    "(5) defects: blur, crop, clutter, dirty surface, reflections, harsh flash, text overlays. "
    "Max 55 words. No marketing language, no guessing at things you cannot see."
)


def load():
    if os.path.exists(OUT):
        try:
            return json.load(open(OUT))
        except Exception:
            return {}
    return {}


def describe(path, attempts=4):
    b64 = base64.b64encode(open(path, "rb").read()).decode()
    body = {
        "model": MODEL,
        "messages": [{"role": "user", "content": [
            {"type": "text", "text": PROMPT},
            {"type": "image_url", "image_url": {"url": f"data:image/jpeg;base64,{b64}"}},
        ]}],
        "max_tokens": 220,
    }
    last = None
    for i in range(attempts):
        try:
            req = urllib.request.Request(
                "https://openrouter.ai/api/v1/chat/completions",
                data=json.dumps(body).encode(),
                headers={"Authorization": f"Bearer {KEY}", "Content-Type": "application/json"},
            )
            with urllib.request.urlopen(req, timeout=120) as r:
                d = json.loads(r.read())
            return d["choices"][0]["message"]["content"].strip().replace("\n", " ")
        except Exception as e:
            last = e
            time.sleep(3 + 4 * i)
    raise last


def main():
    args = [a for a in sys.argv[1:] if not a.startswith("--")]
    limit = None
    for a in sys.argv[1:]:
        if a.startswith("--limit"):
            limit = int(a.split("=")[1]) if "=" in a else None
    d = args[0] if args else os.path.join(DATA, "content_inbox", "2026-11-14")
    files = sorted(glob.glob(os.path.join(d, "*.jpg")) + glob.glob(os.path.join(d, "*.jpeg")) + glob.glob(os.path.join(d, "*.png")))
    store = load()
    todo = [f for f in files if os.path.basename(f) not in store]
    if limit:
        todo = todo[:limit]
    print(f"files={len(files)} done={len(store)} todo={len(todo)}")
    for i, f in enumerate(todo, 1):
        name = os.path.basename(f)
        try:
            txt = describe(f)
            store[name] = {"file": f, "desc": txt, "model": MODEL, "at": time.strftime("%Y-%m-%dT%H:%M:%S")}
            print(f"[{i}/{len(todo)}] {name}: {txt[:110]}")
        except Exception as e:
            print(f"[{i}/{len(todo)}] {name} ERROR {e}")
        json.dump(store, open(OUT, "w"), indent=1)
    print(f"DONE total_described={len(store)}")


if __name__ == "__main__":
    main()

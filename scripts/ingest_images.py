#!/usr/bin/env python3
"""File images into data/content_inbox/<date>/ and index them.

Accepts local paths or http(s) URLs (Discord attachments).
Skips duplicates by content hash so a re-send doesn't double-file.

Usage: python ingest_images.py <path-or-url> [...]
"""
import hashlib
import json
import os
import shutil
import sys
import time
import urllib.request
from datetime import datetime, timedelta, timezone

DATA = "/opt/data/projects/burger-lab/data"
INBOX = os.path.join(DATA, "content_inbox")
IDX = os.path.join(INBOX, "index.json")
IST = timezone(timedelta(hours=5, minutes=30))


def load_idx():
    if os.path.exists(IDX):
        try:
            return json.load(open(IDX))
        except Exception:
            return []
    return []


def known_hashes(idx):
    return {e.get("sha256") for e in idx if e.get("sha256")}


def fetch(src, tmpdir):
    """Return a local path for a path or URL."""
    if src.startswith("http://") or src.startswith("https://"):
        name = src.split("?")[0].rstrip("/").split("/")[-1] or f"img_{int(time.time())}"
        dest = os.path.join(tmpdir, name)
        req = urllib.request.Request(src, headers={"User-Agent": "Mozilla/5.0"})
        with urllib.request.urlopen(req, timeout=60) as r, open(dest, "wb") as fh:
            shutil.copyfileobj(r, fh)
        return dest
    return src


def main(sources):
    os.makedirs(INBOX, exist_ok=True)
    today = datetime.now(IST).strftime("%Y-%m-%d")
    daydir = os.path.join(INBOX, today)
    os.makedirs(daydir, exist_ok=True)
    idx = load_idx()
    seen = known_hashes(idx)
    added, dupes, bad = [], [], []

    for src in sources:
        try:
            local = fetch(src, "/tmp")
            data = open(local, "rb").read()
            if len(data) < 2000:
                bad.append((src, "file too small / not an image"))
                continue
            sha = hashlib.sha256(data).hexdigest()
            if sha in seen:
                dupes.append(src)
                continue
            ext = "png" if data[:2] == b"\x89P" else "jpg"
            name = f"{int(time.time())}_{sha[:8]}.{ext}"
            full = os.path.join(daydir, name)
            open(full, "wb").write(data)
            idx.append({"file": full, "bytes": len(data), "sha256": sha, "source": src,
                        "received_at": datetime.now(IST).isoformat(timespec="seconds"),
                        "used": False})
            seen.add(sha)
            added.append(full)
        except Exception as e:
            bad.append((src, str(e)))

    json.dump(idx, open(IDX, "w"), indent=1)
    print(f"added={len(added)} dupes={len(dupes)} failed={len(bad)} inbox_total={len(idx)}")
    for a in added:
        print("  +", a)
    for b in bad:
        print("  !", b[0][:80], "->", b[1][:80])


if __name__ == "__main__":
    if len(sys.argv) < 2:
        print(__doc__)
        sys.exit(1)
    main(sys.argv[1:])

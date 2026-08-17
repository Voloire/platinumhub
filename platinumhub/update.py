# -*- coding: utf-8 -*-
"""Controllo aggiornamenti: avvisa e basta, non scarica mai nulla da solo."""

import json
import os
import re
import urllib.request

from .config import RELEASES_API, RELEASES_PAGE, UPDATE, VERSION
from .store import get_pref


def _vtuple(v):
    """'v4.1.2' -> (4, 1, 2). Le parti non numeriche (rc, beta) si ignorano."""
    nums = re.findall(r"\d+", str(v or ""))
    return tuple(int(x) for x in nums[:3]) + (0,) * (3 - len(nums[:3]))


def check_update():
    if os.environ.get("PLATINUM_HUB_NO_UPDATE") == "1":
        UPDATE["checked"] = True
        return
    if get_pref("update_check", "1") != "1":
        UPDATE["checked"] = True
        UPDATE["latest"] = ""
        return
    try:
        req = urllib.request.Request(RELEASES_API, headers={
            "Accept": "application/vnd.github+json",
            "User-Agent": "PlatinumHub/" + VERSION})
        with urllib.request.urlopen(req, timeout=6) as r:
            j = json.loads(r.read().decode("utf-8"))
        tag = str(j.get("tag_name") or "")
        if tag and _vtuple(tag) > _vtuple(VERSION):
            UPDATE["latest"] = tag.lstrip("vV")
            UPDATE["url"] = j.get("html_url") or RELEASES_PAGE
            UPDATE["notes"] = (j.get("body") or "")[:1500]
    except Exception:
        pass                     # nessuna rete, GitHub giu', limite di richieste: pazienza
    finally:
        UPDATE["checked"] = True

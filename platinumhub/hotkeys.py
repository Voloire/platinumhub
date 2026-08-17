# -*- coding: utf-8 -*-
"""Scorciatoie globali (Windows): RegisterHotKey mette comandi in coda per la pagina."""

import json
import re
import sys
import threading
import time
import urllib.request

from .store import get_pref


HOTKEYS_DEFAULT = "ctrl+alt+F9:rec, ctrl+alt+F10:next, ctrl+alt+F8:undo, ctrl+alt+F11:mark"
HOTKEY_ACTIONS = ("rec", "next", "undo", "mark")

CMDQ = []                      # comandi in attesa che la pagina li esegua
CMDLOCK = threading.Lock()
TOASTS = {}                    # run_id -> (testo, timestamp) per l'overlay
HOTKEY_STATE = {"active": [], "failed": [], "why": ""}


def push_cmd(action, run=None):
    if action not in HOTKEY_ACTIONS:
        return False
    with CMDLOCK:
        CMDQ.append({"a": action, "run": run, "ts": time.time()})
        del CMDQ[:-20]
    return True


def take_cmds():
    now = time.time()
    with CMDLOCK:
        out = [c for c in CMDQ if now - c["ts"] < 10]
        del CMDQ[:]
    return out


def set_toast(run_id, text):
    TOASTS[run_id] = (str(text)[:90], time.time())


def get_toast(run_id):
    v = TOASTS.get(run_id)
    if not v or time.time() - v[1] > 4:
        return ""
    return v[0]


def parse_hotkeys(spec):
    """'ctrl+alt+F9:rec, ...' -> [(mods, vk, action, testo)] — nessuna eccezione."""
    mods = {"alt": 0x0001, "ctrl": 0x0002, "control": 0x0002,
            "shift": 0x0004, "win": 0x0008}
    out = []
    for chunk in str(spec or "").split(","):
        chunk = chunk.strip()
        if not chunk or ":" not in chunk:
            continue
        combo, action = chunk.rsplit(":", 1)
        action = action.strip().lower()
        if action not in HOTKEY_ACTIONS:
            continue
        m, vk = 0, None
        for part in combo.split("+"):
            part = part.strip().lower()
            if part in mods:
                m |= mods[part]
            elif re.fullmatch(r"f([1-9]|1[0-9]|2[0-4])", part):
                vk = 0x6F + int(part[1:])          # F1 = 0x70 ... F24 = 0x87
            elif len(part) == 1 and part.isalnum():
                vk = ord(part.upper())
        if vk and m:                                # senza modificatori non si registra
            out.append((m, vk, action, combo.strip()))
    return out


def _fire(action, port):
    try:
        req = urllib.request.Request(
            "http://127.0.0.1:%d/api/cmd" % port,
            data=json.dumps({"action": action}).encode("utf-8"),
            headers={"Content-Type": "application/json"})
        urllib.request.urlopen(req, timeout=2).read()
    except Exception:
        pass


def hotkey_worker(spec, port):
    """Registra le scorciatoie e resta in ascolto. Solo Windows."""
    try:
        import ctypes
        from ctypes import wintypes
    except Exception as e:                                   # pragma: no cover
        HOTKEY_STATE["why"] = "ctypes non disponibile (%s)" % e
        return
    u32 = ctypes.windll.user32
    MOD_NOREPEAT = 0x4000
    WM_HOTKEY = 0x0312
    idmap = {}
    for i, (m, vk, action, label) in enumerate(parse_hotkeys(spec), start=1):
        if u32.RegisterHotKey(None, i, m | MOD_NOREPEAT, vk):
            idmap[i] = action
            HOTKEY_STATE["active"].append((label, action))
        else:
            HOTKEY_STATE["failed"].append((label, action))
    if not idmap:
        HOTKEY_STATE["why"] = "nessuna combinazione registrata (gia' occupate?)"
        return
    msg = wintypes.MSG()
    while u32.GetMessageW(ctypes.byref(msg), None, 0, 0) > 0:
        if msg.message == WM_HOTKEY:
            action = idmap.get(msg.wParam)
            if action:
                threading.Thread(target=_fire, args=(action, port), daemon=True).start()


def start_hotkeys(port):
    spec = get_pref("hotkeys", HOTKEYS_DEFAULT)
    if get_pref("hotkeys_on", "1") != "1":
        HOTKEY_STATE["why"] = "disattivate"
        return
    if sys.platform != "win32":
        HOTKEY_STATE["why"] = "solo su Windows"
        return
    threading.Thread(target=hotkey_worker, args=(spec, port), daemon=True).start()
    time.sleep(0.3)

# -*- coding: utf-8 -*-
"""
hermes_sentinel.py - Hermes Sentinel evrensel SDK (yalnizca Python standart kutuphanesi)

Kullanim:
    from hermes_sentinel import Sentinel
    s = Sentinel.init("app-id", "1.0.0", "https://vps.example/sentinel/ingest")
    if s.is_safe_mode(): ...      # boot-loop korumasi
    ... uygulama basariyla acildiktan sonra ...
    s.mark_boot_success()

Garantiler: SDK ana uygulamayi asla cokertmez; ag islemleri yalnizca daemon worker
thread'inde yapilir; veriler istemcide maskelenir; ag yoksa .sentinel_crash.log'a
JSONL yazilir ve ilk basarili baglantida flush edilir.
"""
import atexit
import hashlib
import json
import os
import platform
import queue
import re
import sys
import threading
import time
import traceback
import urllib.request
import uuid

__all__ = ["Sentinel"]
__version__ = "1.0.0"

_DEDUP_WINDOW = 3600.0       # ayni hata icin saniye
_HTTP_TIMEOUT = 5.0
_FATAL_WAIT = 2.0            # kritik cokmede gonderim icin azami bekleme
_QUEUE_MAX = 200
_LOG_MAX_LINES = 500
_MAX_TEXT = 20000
_BOOT_LOOP_LIMIT = 2

# ----------------------------------------------------------------- sanitizasyon
_SANITIZERS = [
    (re.compile(r"(?i)\bBearer\s+[A-Za-z0-9\-._~+/]+=*"), "[REDACTED_SECRET]"),
    (re.compile(r"\bsk-[A-Za-z0-9_\-]{8,}"), "[REDACTED_SECRET]"),
    (re.compile(r"\bAIza[0-9A-Za-z_\-]{20,}"), "[REDACTED_SECRET]"),
    (re.compile(r"\bgh[pousr]_[A-Za-z0-9]{20,}"), "[REDACTED_SECRET]"),
    (re.compile(r"[A-Za-z0-9._%+\-]+@[A-Za-z0-9\-]+(?:\.[A-Za-z0-9\-]+)+"), "[REDACTED_EMAIL]"),
    (re.compile(r"(?i)\b[A-Z]:[\\/]+Users[\\/]+[^\\/\s\"'<>|:*?]+"), "~"),
    (re.compile(r"/(?:home|Users)/[^/\s\"'<>|:*?]+"), "~"),
    (re.compile(r"(?<!\d)[1-9]\d{10}(?!\d)"), "[REDACTED_TCKN]"),
]


def _sanitize_str(text):
    try:
        for rx, repl in _SANITIZERS:
            text = rx.sub(repl, text)
    except Exception:
        pass
    return text


def _sanitize(obj, _depth=0):
    """Dict/list/str icinde ozyinelemeli maskeleme; JSON'a uygun deger dondurur."""
    try:
        if _depth > 6:
            return "[TRUNCATED]"
        if isinstance(obj, str):
            return _sanitize_str(obj)[:_MAX_TEXT]
        if obj is None or isinstance(obj, (bool, int, float)):
            return obj
        if isinstance(obj, dict):
            return {_sanitize_str(str(k)): _sanitize(v, _depth + 1) for k, v in list(obj.items())[:100]}
        if isinstance(obj, (list, tuple, set)):
            return [_sanitize(v, _depth + 1) for v in list(obj)[:100]]
        return _sanitize_str(repr(obj))[:2000]
    except Exception:
        return "[UNSERIALIZABLE]"


# --------------------------------------------------------------------- Sentinel
class Sentinel(object):
    _instance = None
    _init_lock = threading.Lock()

    # ------------------------------------------------------------ yasam dongusu
    @classmethod
    def init(cls, app_id, version, endpoint, public_key=None, auto_hook=True):
        try:
            with cls._init_lock:
                if cls._instance is None:
                    inst = cls(app_id, version, endpoint, public_key)
                    cls._instance = inst
                    if auto_hook:
                        inst._install_hooks()
                return cls._instance
        except Exception:
            try:
                if cls._instance is None:
                    cls._instance = cls._bare()
            except Exception:
                pass
            return cls._instance

    @classmethod
    def get(cls):
        if cls._instance is None:
            try:
                with cls._init_lock:
                    if cls._instance is None:
                        cls._instance = cls._bare()
            except Exception:
                pass
        return cls._instance

    @classmethod
    def _bare(cls):
        """Init edilmeden get() cagrilirsa: ag yapmayan, hicbir sey yapmayan ornek."""
        return cls("unknown", "0", None, None)

    def __init__(self, app_id, version, endpoint, public_key=None):
        self.app_id = str(app_id)
        self.version = str(version)
        self.endpoint = endpoint if (isinstance(endpoint, str) and endpoint.lower().startswith(("http://", "https://"))) else None
        self.public_key = public_key
        self.session_id = uuid.uuid4().hex[:12]
        self._lock = threading.Lock()
        self._file_lock = threading.Lock()
        self._dedup = {}            # fingerprint -> [son_gonderim_zamani, bastirilan_sayac]
        self._queue = queue.Queue(maxsize=_QUEUE_MAX)
        self._worker = None
        self._safe_mode = False
        self._orig_excepthook = None
        self._orig_thread_hook = None
        self._hooked = False
        try:
            base = os.getcwd()
        except Exception:
            base = "."
        self._crash_log = os.path.join(base, ".sentinel_crash.log")
        self._boot_file = os.path.join(base, ".sentinel_boot")
        try:
            self._safe_mode = self._register_boot()
        except Exception:
            self._safe_mode = False
        if self.endpoint:
            try:
                self._start_worker()
                atexit.register(self._drain_at_exit)
            except Exception:
                pass

    # ---------------------------------------------------------- boot-loop korumasi
    def _register_boot(self):
        prior = 0
        try:
            with open(self._boot_file, "r", encoding="utf-8") as f:
                prior = int((f.read() or "0").strip() or 0)
        except Exception:
            prior = 0
        self._write_boot(prior + 1)
        return prior >= _BOOT_LOOP_LIMIT

    def _write_boot(self, n):
        try:
            with self._file_lock:
                tmp = self._boot_file + ".tmp"
                with open(tmp, "w", encoding="utf-8") as f:
                    f.write(str(int(n)))
                os.replace(tmp, self._boot_file)
        except Exception:
            pass

    def mark_boot_success(self):
        try:
            self._write_boot(0)
        except Exception:
            pass

    def is_safe_mode(self):
        try:
            return bool(self._safe_mode)
        except Exception:
            return False

    # ------------------------------------------------------------------ hook'lar
    def _install_hooks(self):
        try:
            if self._hooked:
                return
            self._hooked = True
            self._orig_excepthook = sys.excepthook

            def _excepthook(exc_type, exc_value, exc_tb):
                try:
                    if not issubclass(exc_type, (KeyboardInterrupt, SystemExit)):
                        self._capture(exc_type, exc_value, exc_tb, None, "fatal", True)
                except Exception:
                    pass
                try:
                    (self._orig_excepthook or sys.__excepthook__)(exc_type, exc_value, exc_tb)
                except Exception:
                    pass

            sys.excepthook = _excepthook

            if hasattr(threading, "excepthook"):
                self._orig_thread_hook = threading.excepthook

                def _thread_hook(args):
                    try:
                        if not issubclass(args.exc_type, SystemExit):
                            self._capture(args.exc_type, args.exc_value, args.exc_traceback,
                                          {"thread": getattr(args.thread, "name", None)}, "error", False)
                    except Exception:
                        pass
                    try:
                        (self._orig_thread_hook or threading.__excepthook__)(args)
                    except Exception:
                        pass

                threading.excepthook = _thread_hook
        except Exception:
            pass

    # ------------------------------------------------------------------ genel API
    def capture_exception(self, exc_type=None, exc_value=None, exc_tb=None, extra=None):
        try:
            if exc_type is None:
                exc_type, exc_value, exc_tb = sys.exc_info()
            if exc_type is None:
                return
            self._capture(exc_type, exc_value, exc_tb, extra, "error", False)
        except Exception:
            pass

    def capture_message(self, message, level="info", extra=None):
        try:
            payload = self._base_payload("message", str(level))
            payload["message"] = _sanitize_str(str(message))[:_MAX_TEXT]
            if extra:
                payload["extra"] = _sanitize(extra)
            self._enqueue(payload)
        except Exception:
            pass

    # ----------------------------------------------------------------- dahili
    def _base_payload(self, kind, level):
        return {
            "id": uuid.uuid4().hex,
            "type": kind,
            "level": level,
            "app_id": self.app_id,
            "version": self.version,
            "session_id": self.session_id,
            "safe_mode": self._safe_mode,
            "ts": time.time(),
            "platform": _sanitize_str(platform.platform()),
            "python": platform.python_version(),
        }

    @staticmethod
    def _fingerprint(exc_type, exc_tb):
        fname, line = "?", 0
        try:
            tb = exc_tb
            while tb is not None and tb.tb_next is not None:
                tb = tb.tb_next
            if tb is not None:
                fname = os.path.basename(tb.tb_frame.f_code.co_filename)
                line = tb.tb_lineno
        except Exception:
            pass
        name = getattr(exc_type, "__name__", str(exc_type))
        raw = "%s|%s:%s" % (name, fname, line)
        return hashlib.sha1(raw.encode("utf-8", "replace")).hexdigest()[:16]

    def _capture(self, exc_type, exc_value, exc_tb, extra, level, fatal):
        fp = self._fingerprint(exc_type, exc_tb)
        now = time.time()
        with self._lock:
            entry = self._dedup.get(fp)
            if entry is not None and now - entry[0] < _DEDUP_WINDOW:
                entry[1] += 1           # tekrar: sadece sayaci artir
                return
            suppressed = entry[1] if entry else 0
            self._dedup[fp] = [now, 0]
            if len(self._dedup) > 500:  # bellek siniri
                oldest = sorted(self._dedup.items(), key=lambda kv: kv[1][0])[:100]
                for k, _ in oldest:
                    self._dedup.pop(k, None)
        payload = self._base_payload("exception", level)
        payload["fingerprint"] = fp
        payload["exception_type"] = getattr(exc_type, "__name__", str(exc_type))
        payload["message"] = _sanitize_str(str(exc_value))[:_MAX_TEXT]
        payload["traceback"] = _sanitize_str("".join(traceback.format_exception(exc_type, exc_value, exc_tb)))[:_MAX_TEXT]
        payload["suppressed_count"] = suppressed
        if extra:
            payload["extra"] = _sanitize(extra)
        self._enqueue(payload, wait=fatal)

    def _enqueue(self, payload, wait=False):
        item = {"payload": payload, "done": threading.Event(), "cancel": False}
        if not self.endpoint or self._worker is None:
            self._persist([payload])
            return
        try:
            self._queue.put_nowait(item)
        except queue.Full:
            self._persist([payload])
            return
        if wait:
            # surec olmek uzere: kisa sure gonderimi bekle, olmadiysa diske yaz
            if not item["done"].wait(_FATAL_WAIT):
                with self._lock:
                    if not item["done"].is_set():
                        item["cancel"] = True
                        self._persist([payload])

    # ----------------------------------------------------------------- worker
    def _start_worker(self):
        t = threading.Thread(target=self._run, name="hermes-sentinel", daemon=True)
        self._worker = t
        t.start()

    def _run(self):
        # Acilista bekleyen yerel kayitlari bir kez dene (ana thread'i bloklamaz)
        try:
            if os.path.exists(self._crash_log):
                self._flush_log()
        except Exception:
            pass
        while True:
            try:
                item = self._queue.get()
                try:
                    with self._lock:
                        if item["cancel"]:
                            continue
                    if self._post(item["payload"]):
                        item["done"].set()
                        self._flush_log()
                    else:
                        with self._lock:
                            self._persist([item["payload"]])
                        item["done"].set()
                finally:
                    self._queue.task_done()
            except Exception:
                time.sleep(0.5)

    def _post(self, payload):
        try:
            data = json.dumps(payload, ensure_ascii=False).encode("utf-8")
            req = urllib.request.Request(
                self.endpoint, data=data, method="POST",
                headers={"Content-Type": "application/json; charset=utf-8",
                         "User-Agent": "HermesSentinel/%s" % __version__,
                         "X-Sentinel-App": self.app_id})
            with urllib.request.urlopen(req, timeout=_HTTP_TIMEOUT) as resp:
                return 200 <= getattr(resp, "status", 200) < 300
        except Exception:
            return False

    # ---------------------------------------------------------- yerel JSONL log
    def _persist(self, payloads):
        try:
            with self._file_lock:
                lines = []
                try:
                    with open(self._crash_log, "r", encoding="utf-8") as f:
                        lines = [l for l in f.read().splitlines() if l.strip()]
                except Exception:
                    lines = []
                lines.extend(json.dumps(p, ensure_ascii=False) for p in payloads)
                lines = lines[-_LOG_MAX_LINES:]
                with open(self._crash_log, "w", encoding="utf-8") as f:
                    f.write("\n".join(lines) + "\n")
        except Exception:
            pass

    def _flush_log(self):
        """Yerel loglanmis kayitlari gonder; gonderilemeyenleri geri yaz."""
        try:
            with self._file_lock:
                try:
                    with open(self._crash_log, "r", encoding="utf-8") as f:
                        lines = [l for l in f.read().splitlines() if l.strip()]
                except Exception:
                    return
                try:
                    os.remove(self._crash_log)   # akis sirasinda yeni yazimlar kaybolmasin
                except Exception:
                    pass
            remaining = []
            failed = False
            for line in lines:
                if failed:
                    remaining.append(line)
                    continue
                try:
                    p = json.loads(line)
                except Exception:
                    continue
                if not self._post(p):
                    failed = True
                    remaining.append(line)
            if remaining:
                with self._file_lock:
                    try:
                        with open(self._crash_log, "a", encoding="utf-8") as f:
                            f.write("\n".join(remaining) + "\n")
                    except Exception:
                        pass
        except Exception:
            pass

    def _drain_at_exit(self):
        try:
            end = time.time() + 1.5
            while time.time() < end and self._queue.unfinished_tasks:
                time.sleep(0.05)
        except Exception:
            pass

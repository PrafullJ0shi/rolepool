"""A small polite HTTP client: one User-Agent, per-host rate limits, retries with backoff, and an ETag cache."""
from __future__ import annotations

import hashlib
import json
import threading
import time
from urllib.parse import urlparse

import httpx

from . import config


class HostLimiter:
    def __init__(self, rps: float):
        self.interval = 1.0 / rps
        self.lock = threading.Lock()
        self.next_at: dict[str, float] = {}
        self.host_locks: dict[str, threading.Lock] = {}

    def wait(self, host: str) -> None:
        with self.lock:
            now = time.monotonic()
            at = max(now, self.next_at.get(host, 0.0))
            self.next_at[host] = at + self.interval
        delay = at - time.monotonic()
        if delay > 0:
            time.sleep(delay)


class Client:
    def __init__(self, rps: float = config.PER_HOST_RPS, cache: bool = True):
        self.http = httpx.Client(
            headers={"User-Agent": config.USER_AGENT, "Accept": "application/json, application/xml;q=0.9, */*;q=0.5"},
            timeout=config.TIMEOUT_S,
            follow_redirects=True,
        )
        self.limiter = HostLimiter(rps)
        self.cache = cache
        if cache:
            config.CACHE.mkdir(parents=True, exist_ok=True)
        self.stats = {"requests": 0, "cache_hits": 0, "errors": 0}
        self._slock = threading.Lock()

    def _bump(self, key: str) -> None:
        with self._slock:
            self.stats[key] += 1

    def _cache_path(self, url: str):
        return config.CACHE / (hashlib.sha1(url.encode()).hexdigest() + ".json")

    def get(self, url: str, params: dict | None = None) -> httpx.Response | None:
        full = str(httpx.URL(url, params=params)) if params else url
        host = urlparse(full).netloc
        headers = {}
        cpath = self._cache_path(full)
        cached = None
        if self.cache and cpath.exists():
            try:
                cached = json.loads(cpath.read_text())
                if cached.get("etag"):
                    headers["If-None-Match"] = cached["etag"]
                if cached.get("last_modified"):
                    headers["If-Modified-Since"] = cached["last_modified"]
            except Exception:
                cached = None
        for attempt in range(config.MAX_RETRIES + 1):
            self.limiter.wait(host)
            try:
                self._bump("requests")
                r = self.http.get(full, headers=headers)
            except httpx.HTTPError:
                if attempt == config.MAX_RETRIES:
                    self._bump("errors")
                    return None
                time.sleep(2 ** attempt)
                continue
            if r.status_code == 304 and cached is not None:
                self._bump("cache_hits")
                return httpx.Response(200, content=cached["body"].encode(), request=r.request,
                                      headers={"content-type": cached.get("ctype", "")})
            if r.status_code in (429, 500, 502, 503, 504) and attempt < config.MAX_RETRIES:
                retry_after = r.headers.get("retry-after", "")
                wait = float(retry_after) if retry_after.isdigit() else 2 ** (attempt + 1)
                time.sleep(min(wait, 60))
                continue
            if r.status_code == 200 and self.cache and (r.headers.get("etag") or r.headers.get("last-modified")):
                try:
                    cpath.write_text(json.dumps({
                        "etag": r.headers.get("etag"),
                        "last_modified": r.headers.get("last-modified"),
                        "ctype": r.headers.get("content-type", ""),
                        "body": r.text,
                    }))
                except Exception:
                    pass
            if r.status_code >= 400:
                self._bump("errors")
            return r
        return None

    def get_json(self, url: str, params: dict | None = None):
        r = self.get(url, params)
        if r is None or r.status_code != 200:
            return None
        try:
            return r.json()
        except ValueError:
            return None

    def close(self) -> None:
        self.http.close()

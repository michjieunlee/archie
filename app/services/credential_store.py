"""
Runtime credential store for user-provided integration credentials.

Credentials supplied via the UI override the .env-based defaults from config.Settings.
Stored in-memory only — they do not persist across server restarts.
"""

import threading

_lock = threading.Lock()
_store: dict[str, str] = {}


def set_credential(key: str, value: str) -> None:
    with _lock:
        _store[key] = value


def get_credential(key: str, default: str = "") -> str:
    with _lock:
        return _store.get(key, default)


def remove_credential(key: str) -> None:
    with _lock:
        _store.pop(key, None)


def clear_credentials(prefix: str = "") -> None:
    with _lock:
        if prefix:
            keys_to_remove = [k for k in _store if k.startswith(prefix)]
            for k in keys_to_remove:
                del _store[k]
        else:
            _store.clear()


def has_credential(key: str) -> bool:
    with _lock:
        return key in _store and bool(_store[key])

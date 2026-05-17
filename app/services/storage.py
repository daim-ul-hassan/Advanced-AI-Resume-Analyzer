from __future__ import annotations

import hashlib
import json
import os
import re
import secrets
import shutil
from pathlib import Path
from typing import Any


ROOT_DIR = Path(__file__).resolve().parents[2]

if os.environ.get("VERCEL"):
    DATA_DIR = Path("/tmp/data")
    UPLOADS_DIR = Path("/tmp/uploads")
else:
    DATA_DIR = ROOT_DIR / "data"
    UPLOADS_DIR = ROOT_DIR / "uploads"

USERS_DIR = DATA_DIR / "users"
ACCOUNTS_PATH = DATA_DIR / "accounts.json"

DEFAULT_PROFILE = {"name": "", "theme": "dark-ai"}
DEFAULT_STATE = {
    "resume_filename": "",
    "resume_path": "",
    "resume_text": "",
    "vector_ready": False,
    "job_description": "",
    "last_analysis": None,
}


def ensure_dirs() -> None:
    DATA_DIR.mkdir(parents=True, exist_ok=True)
    UPLOADS_DIR.mkdir(parents=True, exist_ok=True)
    USERS_DIR.mkdir(parents=True, exist_ok=True)


def _read_json(path: Path, default: Any) -> Any:
    if not path.exists():
        return default
    try:
        return json.loads(path.read_text(encoding="utf-8"))
    except json.JSONDecodeError:
        return default


def _write_json(path: Path, payload: Any) -> None:
    ensure_dirs()
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(payload, indent=2), encoding="utf-8")


def _normalize_name(name: str) -> str:
    return re.sub(r"\s+", " ", name.strip().lower())


def _hash_password(password: str, salt: str) -> str:
    return hashlib.pbkdf2_hmac(
        "sha256",
        password.encode("utf-8"),
        salt.encode("utf-8"),
        200_000,
    ).hex()


def _user_dir(user_id: str) -> Path:
    return USERS_DIR / user_id


def _user_profile_path(user_id: str) -> Path:
    return _user_dir(user_id) / "profile.json"


def _user_activity_path(user_id: str) -> Path:
    return _user_dir(user_id) / "activity.json"


def _user_state_path(user_id: str) -> Path:
    return _user_dir(user_id) / "state.json"


def _user_vector_path(user_id: str) -> Path:
    return _user_dir(user_id) / "vector_base.json"


def get_user_upload_dir(user_id: str) -> Path:
    path = UPLOADS_DIR / user_id
    path.mkdir(parents=True, exist_ok=True)
    return path


def load_accounts() -> dict[str, dict[str, Any]]:
    return _read_json(ACCOUNTS_PATH, {})


def save_accounts(accounts: dict[str, dict[str, Any]]) -> None:
    _write_json(ACCOUNTS_PATH, accounts)


def load_profile(user_id: str) -> dict[str, Any]:
    profile = _read_json(_user_profile_path(user_id), DEFAULT_PROFILE.copy())
    if profile.get("theme") not in {"dark-ai", "gradient"}:
        profile["theme"] = "dark-ai"
    return profile


def save_profile(user_id: str, profile: dict[str, Any]) -> None:
    _write_json(_user_profile_path(user_id), profile)


def load_activity(user_id: str) -> list[dict[str, Any]]:
    return _read_json(_user_activity_path(user_id), [])


def save_activity(user_id: str, entries: list[dict[str, Any]]) -> None:
    _write_json(_user_activity_path(user_id), entries)


def load_state(user_id: str) -> dict[str, Any]:
    state = _read_json(_user_state_path(user_id), DEFAULT_STATE.copy())
    merged = DEFAULT_STATE.copy()
    merged.update(state)
    return merged


def save_state(user_id: str, state: dict[str, Any]) -> None:
    merged = DEFAULT_STATE.copy()
    merged.update(state)
    _write_json(_user_state_path(user_id), merged)


def load_vector_base(user_id: str) -> dict[str, Any]:
    return _read_json(_user_vector_path(user_id), {"chunks": []})


def save_vector_base(user_id: str, payload: dict[str, Any]) -> None:
    _write_json(_user_vector_path(user_id), payload)


def create_or_authenticate_user(name: str, password: str, theme: str) -> tuple[str, bool]:
    ensure_dirs()
    if theme not in {"dark-ai", "gradient"}:
        theme = "dark-ai"

    key = _normalize_name(name)
    accounts = load_accounts()
    account = accounts.get(key)

    if account:
        expected_hash = _hash_password(password, account["password_salt"])
        if expected_hash != account["password_hash"]:
            raise ValueError("Incorrect password for this name.")

        user_id = account["user_id"]
        profile = load_profile(user_id)
        profile["name"] = name.strip()
        profile["theme"] = theme
        save_profile(user_id, profile)
        return user_id, False

    user_id = f"{re.sub(r'[^a-z0-9]+', '-', key).strip('-') or 'user'}-{secrets.token_hex(4)}"
    salt = secrets.token_hex(16)
    accounts[key] = {
        "user_id": user_id,
        "password_salt": salt,
        "password_hash": _hash_password(password, salt),
    }
    save_accounts(accounts)

    save_profile(user_id, {"name": name.strip(), "theme": theme})
    save_activity(user_id, [])
    save_state(user_id, DEFAULT_STATE.copy())
    save_vector_base(user_id, {"chunks": []})
    return user_id, True


def delete_user_profile(user_id: str) -> None:
    accounts = load_accounts()
    account_key_to_remove = None
    for key, account in accounts.items():
        if account.get("user_id") == user_id:
            account_key_to_remove = key
            break

    if account_key_to_remove:
        accounts.pop(account_key_to_remove, None)
        save_accounts(accounts)

    shutil.rmtree(_user_dir(user_id), ignore_errors=True)
    shutil.rmtree(UPLOADS_DIR / user_id, ignore_errors=True)

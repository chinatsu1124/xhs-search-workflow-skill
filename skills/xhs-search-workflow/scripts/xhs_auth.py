#!/usr/bin/env python3
import json
import logging
import os
import sys
import time
from pathlib import Path
from typing import Dict, Tuple

import qrcode
import requests
from dotenv import load_dotenv

logger = logging.getLogger(__name__)

CONFIG_DIR = Path(os.environ.get("XHS_SEARCH_WORKFLOW_HOME", Path.home() / ".xhs-search-workflow"))
COOKIE_FILE = CONFIG_DIR / "cookies.json"
QR_CODE_FILE = CONFIG_DIR / "login-qrcode.png"
REQUIRED_COOKIES = {"a1", "web_session"}


def cookie_str_to_dict(cookie_str: str) -> Dict[str, str]:
    cookies: Dict[str, str] = {}
    for item in (cookie_str or "").split(";"):
        item = item.strip()
        if "=" not in item:
            continue
        key, value = item.split("=", 1)
        key = key.strip()
        value = value.strip()
        if key:
            cookies[key] = value
    return cookies


def dict_to_cookie_str(cookies: Dict[str, str]) -> str:
    return "; ".join(f"{key}={value}" for key, value in cookies.items())


def has_required_cookies(cookies: Dict[str, str]) -> bool:
    return REQUIRED_COOKIES.issubset(cookies.keys())


def get_saved_cookie_string() -> str | None:
    if not COOKIE_FILE.exists():
        return None
    try:
        data = json.loads(COOKIE_FILE.read_text(encoding="utf-8"))
        cookies = data.get("cookies", {})
        if isinstance(cookies, dict) and has_required_cookies(cookies):
            return dict_to_cookie_str(cookies)
    except Exception as exc:
        logger.warning("failed to load saved cookies: %s", exc)
    return None


def save_cookies(cookie_str: str) -> None:
    cookies = cookie_str_to_dict(cookie_str)
    if not has_required_cookies(cookies):
        raise ValueError("cookie must contain 'a1' and 'web_session'")
    CONFIG_DIR.mkdir(parents=True, exist_ok=True)
    COOKIE_FILE.write_text(
        json.dumps({"cookies": cookies}, ensure_ascii=False, indent=2),
        encoding="utf-8",
    )
    try:
        COOKIE_FILE.chmod(0o600)
    except OSError:
        logger.debug("failed to chmod cookie file: %s", COOKIE_FILE)


def clear_cookies() -> bool:
    if not COOKIE_FILE.exists():
        return False
    COOKIE_FILE.unlink()
    return True


def _display_qr_text_in_terminal(qr_text: str) -> None:
    qr = qrcode.QRCode(border=1)
    qr.add_data(qr_text)
    qr.make(fit=True)
    matrix = qr.get_matrix()
    border = 2
    width = len(matrix[0]) + border * 2
    padded = [[False] * width for _ in range(border)]
    for row in matrix:
        padded.append(([False] * border) + row + ([False] * border))
    padded.extend([[False] * width for _ in range(border)])
    chars = {
        (False, False): " ",
        (True, False): "▀",
        (False, True): "▄",
        (True, True): "█",
    }
    lines = []
    for idx in range(0, len(padded), 2):
        top = padded[idx]
        bottom = padded[idx + 1] if idx + 1 < len(padded) else [False] * width
        lines.append("".join(chars[(top[col], bottom[col])] for col in range(width)))
    print("\n".join(lines))


def _save_qr_png(qr_text: str) -> Path:
    qr = qrcode.QRCode(border=2, box_size=8)
    qr.add_data(qr_text)
    qr.make(fit=True)
    img = qr.make_image(fill_color="black", back_color="white")
    CONFIG_DIR.mkdir(parents=True, exist_ok=True)
    img.save(QR_CODE_FILE)
    return QR_CODE_FILE


def _load_login_source_cookie(cookie_arg: str = "", env_file: str = "") -> str:
    if cookie_arg:
        return cookie_arg
    if env_file:
        load_dotenv(env_file)
    else:
        load_dotenv(Path.cwd() / ".env")
        load_dotenv(Path(__file__).resolve().parents[1] / ".env")
    return os.getenv("COOKIES", "")


def _sanitize_login_source_cookie(cookie_str: str) -> str:
    cookies = cookie_str_to_dict(cookie_str)
    cookies.pop("web_session", None)
    return dict_to_cookie_str(cookies)


def _session_from_cookie(cookie_str: str) -> requests.Session:
    session = requests.Session()
    cookies = cookie_str_to_dict(cookie_str)
    cookies.pop("web_session", None)
    for key, value in cookies.items():
        session.cookies.set(key, value, domain=".xiaohongshu.com")
    return session


def _cookiejar_to_cookie_str(session: requests.Session) -> str:
    return "; ".join(f"{c.name}={c.value}" for c in session.cookies)


def _extract_data(payload: Dict) -> Dict:
    data = payload.get("data")
    return data if isinstance(data, dict) else {}


def _first_value(mapping: Dict, *keys: str):
    for key in keys:
        value = mapping.get(key)
        if value not in (None, ""):
            return value
    return None


def _signed_request(
    session: requests.Session,
    api: str,
    data,
    method: str = "POST",
    extra_headers: Dict[str, str] | None = None,
) -> Tuple[requests.Response, Dict]:
    from xhs_client import generate_request_params, BASE_URL

    cookie_str = _cookiejar_to_cookie_str(session)
    headers, cookies, payload = generate_request_params(cookie_str, api, data, method)
    headers["origin"] = "https://www.xiaohongshu.com"
    headers["referer"] = "https://www.xiaohongshu.com/"
    if extra_headers:
        headers.update({k: v for k, v in extra_headers.items() if v is not None})
    if method.upper() == "GET":
        response = session.get(BASE_URL + api, headers=headers, cookies=cookies, timeout=30)
    else:
        response = session.post(BASE_URL + api, headers=headers, cookies=cookies, data=payload, timeout=30)
    try:
        parsed = response.json()
    except Exception:
        parsed = {"raw": response.text[:2000]}
    return response, parsed


def _resolve_login_info(session: requests.Session, qr_id: str, code: str) -> Dict:
    _, status_data = _signed_request(
        session,
        f"/api/sns/web/v1/login/qrcode/status?qr_id={qr_id}&code={code}",
        "",
        "GET",
        extra_headers={"x-login-mode": ""},
    )
    status_payload = _extract_data(status_data)
    login_info = status_payload.get("login_info")
    if isinstance(login_info, dict) and _first_value(login_info, "session", "web_session"):
        return login_info

    _, activate_data = _signed_request(session, "/api/sns/web/v1/login/activate", {}, "POST")
    activate_payload = _extract_data(activate_data)
    if _first_value(activate_payload, "session", "web_session"):
        return activate_payload

    raise RuntimeError(
        "unable to resolve login session from qrcode status or activate: "
        f"status={status_data}, activate={activate_data}"
    )


def qrcode_login(timeout_seconds: int = 240, cookie_arg: str = "", env_file: str = "") -> str:
    from xhs_client import bootstrap_anon_cookie_string

    source_cookie = _load_login_source_cookie(cookie_arg=cookie_arg, env_file=env_file)
    source_cookie = _sanitize_login_source_cookie(source_cookie)
    source_cookie = bootstrap_anon_cookie_string(source_cookie, platform="Linux")

    session = _session_from_cookie(source_cookie)

    _, create_data = _signed_request(session, "/api/sns/web/v1/login/qrcode/create", {"qr_type": 1}, "POST")
    if not create_data.get("success"):
        raise RuntimeError(f"create qrcode failed: {create_data}")

    qr_data = _extract_data(create_data)
    qr_id = str(_first_value(qr_data, "qr_id", "qrId") or "")
    code = str(_first_value(qr_data, "code", "xhs_code") or "")
    url = str(_first_value(qr_data, "url", "qr_url") or "")
    if not (qr_id and code and url):
        raise RuntimeError(f"invalid qrcode create response: {create_data}")

    print("Starting pure-request QR code login...")
    qr_file = _save_qr_png(url)
    print("\nScan this QR code with the Xiaohongshu app and confirm login:\n")
    print(f"QR image saved to: {qr_file}")
    print(f"QR url: {url}\n")
    _display_qr_text_in_terminal(url)
    print(f"\nqr_id={qr_id}")
    print(f"code={code}")
    print("\nWaiting for confirmation...")

    loops = max(timeout_seconds // 2, 1)
    last_status = None
    for idx in range(loops):
        _, poll_data = _signed_request(session, "/api/qrcode/userinfo", {"qrId": qr_id, "code": code}, "POST")
        poll_payload = _extract_data(poll_data)
        code_status = _first_value(poll_payload, "codeStatus", "code_status")
        if code_status != last_status:
            if code_status == 1:
                print("QR code scanned. Please confirm login in the Xiaohongshu app.")
            elif code_status == 2:
                print("Login confirmed. Finalizing web session...")
            elif code_status not in (None, 0):
                print(f"QR status changed: codeStatus={code_status}")
            last_status = code_status
        if code_status == 2:
            login_info = _resolve_login_info(session, qr_id, code)
            web_session = _first_value(login_info, "session", "web_session")
            if not web_session:
                raise RuntimeError(f"login info missing session: {login_info}")
            session.cookies.set("web_session", web_session, domain=".xiaohongshu.com")
            secure_session = _first_value(login_info, "secure_session")
            if secure_session:
                session.cookies.set("secure_session", secure_session, domain=".xiaohongshu.com")
            cookie_str = _cookiejar_to_cookie_str(session)
            save_cookies(cookie_str)
            print("Login successful.")
            return cookie_str
        if code_status in (3, -1):
            raise RuntimeError(f"QR code expired or rejected: {poll_data}")
        if idx % 15 == 14:
            print(f"Still waiting... current codeStatus={code_status}")
        time.sleep(2)

    raise RuntimeError("QR code login timed out")

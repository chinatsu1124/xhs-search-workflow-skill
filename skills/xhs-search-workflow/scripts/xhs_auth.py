#!/usr/bin/env python3
import base64
import json
import logging
import os
import subprocess
import sys
import tempfile
import time
from pathlib import Path
from typing import Dict
from urllib.parse import parse_qs, unquote, urlparse


logger = logging.getLogger(__name__)

CONFIG_DIR = Path(os.environ.get("XHS_SEARCH_WORKFLOW_HOME", Path.home() / ".xhs-search-workflow"))
COOKIE_FILE = CONFIG_DIR / "cookies.json"
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


def qrcode_login(timeout_seconds: int = 240) -> str:
    from camoufox.sync_api import Camoufox

    print("Starting QR code login...")
    with Camoufox(headless=True) as browser:
        page = browser.new_page()
        page.goto("https://www.xiaohongshu.com", wait_until="domcontentloaded", timeout=20000)
        time.sleep(3)

        for selector in (
            ".reds-mask",
            '[aria-label="弹窗遮罩"]',
            ".close-button",
            ".reds-popup-close",
        ):
            overlay = page.query_selector(selector)
            if not overlay:
                continue
            try:
                overlay.click(force=True)
                time.sleep(0.8)
            except Exception:
                pass

        login_btn = (
            page.query_selector(".login-btn")
            or page.query_selector('[class*="login"]')
            or page.query_selector('button:has-text("登录")')
        )
        if login_btn:
            try:
                login_btn.click(force=True)
                time.sleep(2.5)
            except Exception:
                logger.debug("login button click failed, trying direct navigation")

        if not (
            page.query_selector(".qrcode-img")
            or page.query_selector('img[class*="qrcode"]')
        ):
            page.goto("https://www.xiaohongshu.com/login", wait_until="domcontentloaded", timeout=20000)
            time.sleep(2.5)

        _ensure_qr_login_tab(page)
        time.sleep(1.5)

        print("\nScan the QR code below with the Xiaohongshu app:\n")
        qr_path = Path(tempfile.mkdtemp(prefix="xhs-qr-")) / "qrcode.png"
        rendered = False
        qr_text = _extract_qr_text_from_page(page)
        if qr_text:
            rendered = _display_qr_text_in_terminal(qr_text)
        if not rendered:
            _capture_qr_image(page, qr_path)
            _display_image_in_terminal(qr_path)

        initial_session = ""
        for cookie in page.context.cookies():
            if cookie["name"] == "web_session" and "xiaohongshu" in cookie.get("domain", ""):
                initial_session = cookie["value"]
                break

        print("\nWaiting for scan confirmation...")
        loops = max(timeout_seconds // 2, 1)
        for idx in range(loops):
            time.sleep(2)
            cookie_dict = {
                cookie["name"]: cookie["value"]
                for cookie in page.context.cookies()
                if "xiaohongshu" in cookie.get("domain", "")
            }
            current_session = cookie_dict.get("web_session", "")
            if has_required_cookies(cookie_dict) and (
                current_session != initial_session or _has_non_guest_user(page)
            ):
                cookie_str = dict_to_cookie_str(cookie_dict)
                save_cookies(cookie_str)
                try:
                    if qr_path.exists():
                        qr_path.unlink()
                    qr_path.parent.rmdir()
                except Exception:
                    pass
                print("Login successful.")
                return cookie_str
            if idx % 15 == 14:
                print("Still waiting...")

    raise RuntimeError("QR code login timed out after 4 minutes")


def _capture_qr_image(page, qr_path: Path) -> None:
    best = _find_best_qr_element(page)
    if best is not None:
        try:
            best.screenshot(path=str(qr_path))
            return
        except Exception:
            pass

    for selector in (
        ".qrcode-img",
        'img[class*="qrcode"]',
        'img[class*="qr-code"]',
        ".login-container img",
        'canvas[class*="qrcode"]',
    ):
        element = page.query_selector(selector)
        if not element:
            continue
        try:
            element.screenshot(path=str(qr_path))
            return
        except Exception:
            continue

    page.screenshot(path=str(qr_path), full_page=False)


def _find_best_qr_element(page):
    try:
        elements = page.query_selector_all("img, canvas")
    except Exception:
        return None

    best = None
    best_score = -10**12
    for element in elements:
        try:
            meta = element.evaluate(
                """(node) => {
                    const rect = node.getBoundingClientRect();
                    const width = rect.width || node.width || node.naturalWidth || 0;
                    const height = rect.height || node.height || node.naturalHeight || 0;
                    const src = node.src || node.getAttribute("src") || "";
                    const id = node.id || "";
                    const cls = node.className || "";
                    return { width, height, src, id, cls };
                }"""
            )
        except Exception:
            continue
        if not isinstance(meta, dict):
            continue
        width = float(meta.get("width", 0) or 0)
        height = float(meta.get("height", 0) or 0)
        if width < 120 or height < 120:
            continue
        ratio = max(width, height) / max(1.0, min(width, height))
        if ratio > 1.35:
            continue
        signature = f"{meta.get('src', '')} {meta.get('id', '')} {meta.get('cls', '')}".lower()
        score = width * height
        if any(key in signature for key in ("qr", "qrcode", "scan", "code")):
            score += 1_000_000
        if any(key in signature for key in ("logo", "icon", "avatar", "favicon")):
            score -= 1_000_000
        if score > best_score:
            best = element
            best_score = score
    return best


def _extract_qr_text_from_page(page) -> str:
    try:
        qr_raw = page.evaluate(
            """() => {
                const values = [];
                const push = (value) => {
                    if (typeof value !== "string") return;
                    const s = value.trim();
                    if (!s || s.length < 8) return;
                    values.push(s);
                };

                const attrs = ["src", "href", "data-url", "data-qr", "data-qrcode", "title"];
                const selectors = [
                    ".qrcode-img",
                    'img[class*="qrcode"]',
                    'img[class*="qr-code"]',
                    '[class*="qrcode"]',
                    '[class*="qr-code"]',
                    'a[href*="qr"]'
                ];
                for (const sel of selectors) {
                    for (const el of document.querySelectorAll(sel)) {
                        for (const attr of attrs) {
                            const value = el.getAttribute && el.getAttribute(attr);
                            if (value) push(value);
                        }
                        if (el.textContent) push(el.textContent);
                    }
                }

                const walk = (node, depth) => {
                    if (!node || depth > 6) return;
                    if (typeof node === "string") {
                        push(node);
                        return;
                    }
                    if (Array.isArray(node)) {
                        for (const item of node) walk(item, depth + 1);
                        return;
                    }
                    if (typeof node !== "object") return;
                    for (const [key, value] of Object.entries(node)) {
                        const normalized = String(key).toLowerCase();
                        if (
                            normalized.includes("qr")
                            || normalized.includes("qrcode")
                            || normalized.includes("code")
                            || normalized.includes("url")
                        ) {
                            walk(value, depth + 1);
                        } else if (depth < 2) {
                            walk(value, depth + 1);
                        }
                    }
                };

                try { walk(window.__INITIAL_STATE__, 0); } catch (e) {}

                const looksLikeQrUrl = (value) => {
                    const s = String(value || "").toLowerCase();
                    return (
                        s.includes("qrcode") ||
                        s.includes("qr_code") ||
                        s.includes("qrlogin") ||
                        s.includes("scan") ||
                        s.includes("qr=") ||
                        s.includes("code=")
                    );
                };

                for (const value of values) {
                    if ((value.startsWith("http://") || value.startsWith("https://")) && looksLikeQrUrl(value)) {
                        return value;
                    }
                    const matched = value.match(/[?&](?:url|redirect_url|qr|qrcode|qrcode_url)=([^&]+)/i);
                    if (matched && matched[1]) {
                        const decoded = decodeURIComponent(matched[1]);
                        if (looksLikeQrUrl(decoded)) return decoded;
                    }
                }
                return "";
            }"""
        )
    except Exception:
        return ""

    if not isinstance(qr_raw, str) or not qr_raw.strip():
        return _extract_qr_text_from_best_element(page)
    candidate = qr_raw.strip()
    if candidate.startswith("data:image/"):
        return ""
    if candidate.startswith("http://") or candidate.startswith("https://"):
        parsed = urlparse(candidate)
        qs = parse_qs(parsed.query)
        for key in ("url", "redirect_url", "qrcode", "qrcode_url", "qr"):
            value = qs.get(key)
            if value and value[0]:
                return unquote(value[0])
        if not _is_likely_qr_url(candidate):
            return _extract_qr_text_from_best_element(page)
    return candidate


def _extract_qr_text_from_best_element(page) -> str:
    best = _find_best_qr_element(page)
    if best is None:
        return ""
    try:
        raw = best.evaluate(
            """(node) => {
                const attrs = ["src", "href", "data-url", "data-qr", "data-qrcode", "title"];
                for (const attr of attrs) {
                    const value = node.getAttribute && node.getAttribute(attr);
                    if (value && String(value).trim()) return String(value).trim();
                }
                return node.src || "";
            }"""
        )
    except Exception:
        return ""
    if not isinstance(raw, str) or not raw.strip():
        return ""
    candidate = raw.strip()
    if candidate.startswith("http://") or candidate.startswith("https://"):
        parsed = urlparse(candidate)
        qs = parse_qs(parsed.query)
        for key in ("url", "redirect_url", "qrcode", "qrcode_url", "qr"):
            value = qs.get(key)
            if value and value[0]:
                return unquote(value[0])
        if _is_likely_qr_url(candidate):
            return candidate
    return ""


def _is_likely_qr_url(url: str) -> bool:
    lowered = (url or "").lower()
    if not (lowered.startswith("http://") or lowered.startswith("https://")):
        return False
    return any(marker in lowered for marker in ("qrcode", "qr_code", "qrlogin", "scan", "qr=", "code="))


def _render_qr_half_blocks(matrix: list[list[bool]]) -> str:
    if not matrix:
        return ""
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
    return "\n".join(lines)


def _display_qr_text_in_terminal(qr_text: str) -> bool:
    try:
        import qrcode
    except ImportError:
        return False
    try:
        qr = qrcode.QRCode(border=0)
        qr.add_data(qr_text)
        qr.make(fit=True)
        print(_render_qr_half_blocks(qr.get_matrix()))
        return True
    except Exception:
        return False


def _display_image_in_terminal(image_path: Path) -> None:
    term_program = os.getenv("TERM_PROGRAM", "")
    term = os.getenv("TERM", "")
    supports_inline = (
        term_program in {"iTerm.app", "WezTerm"}
        or "kitty" in term
        or bool(os.getenv("KITTY_WINDOW_ID"))
    )
    if supports_inline:
        try:
            image_data = base64.b64encode(image_path.read_bytes()).decode("ascii")
            osc = f"\033]1337;File=inline=1;preserveAspectRatio=1;width=40:{image_data}\a"
            sys.stdout.write(osc)
            sys.stdout.write("\n")
            sys.stdout.flush()
            return
        except Exception:
            pass

    print(f"QR code saved to: {image_path}")
    try:
        if sys.platform == "darwin":
            subprocess.Popen(["open", str(image_path)])
        elif sys.platform == "win32":
            subprocess.Popen(["start", str(image_path)], shell=True)
        else:
            subprocess.Popen(["xdg-open", str(image_path)])
    except Exception:
        print(f"Please open manually: {image_path}")


def _ensure_qr_login_tab(page) -> None:
    for selector in (
        'text=二维码登录',
        'text=扫码登录',
        'button:has-text("二维码")',
        'button:has-text("扫码")',
        '[role="tab"]:has-text("二维码")',
        '[role="tab"]:has-text("扫码")',
    ):
        element = page.query_selector(selector)
        if not element:
            continue
        try:
            element.click(force=True)
            return
        except Exception:
            continue


def _has_non_guest_user(page) -> bool:
    try:
        return bool(
            page.evaluate(
                """() => {
                    const state = window.__INITIAL_STATE__ || {};
                    const user = state.user || {};
                    const userInfo = user.userInfo || user.currentUser || user.loginUser || {};
                    if (userInfo && userInfo.guest === false) return true;
                    const userPageData = user.userPageData || {};
                    const basic = userPageData.basicInfo || userPageData.basic_info || user.basicInfo || user.basic_info || {};
                    return !!(basic && basic.nickname);
                }"""
            )
        )
    except Exception:
        return False

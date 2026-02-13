#!/usr/bin/env python3
import argparse
import json
import os
from pathlib import Path
from urllib.parse import urlparse
from typing import List, Dict, Any

from xhs_client import load_cookies, get_note_info
import requests


def drop_proxy_env() -> None:
    for k in ("HTTP_PROXY", "HTTPS_PROXY", "http_proxy", "https_proxy"):
        os.environ.pop(k, None)


def parse_urls(args: argparse.Namespace) -> List[str]:
    urls: List[str] = []
    if args.url:
        urls.extend(args.url)
    if args.url_file:
        with open(args.url_file, "r", encoding="utf-8") as f:
            for line in f:
                s = line.strip()
                if s and not s.startswith("#"):
                    urls.append(s)
    return urls


def pick_image_url(image_obj: Dict[str, Any]) -> str:
    info_list = image_obj.get("info_list") or []
    if len(info_list) > 1 and info_list[1].get("url"):
        return info_list[1]["url"]
    if len(info_list) > 0 and info_list[0].get("url"):
        return info_list[0]["url"]
    for k in ("url_default", "url_pre", "url"):
        if image_obj.get(k):
            return image_obj[k]
    return ""


def collect_image_urls(note_card: Dict[str, Any]) -> List[str]:
    urls: List[str] = []
    for image_obj in note_card.get("image_list", []) or []:
        u = pick_image_url(image_obj)
        if u:
            urls.append(u)
    return urls


def image_ext_from_url(url: str) -> str:
    p = urlparse(url).path.lower()
    for ext in (".jpg", ".jpeg", ".png", ".webp", ".avif"):
        if p.endswith(ext):
            return ext
    return ".jpg"


def download_images(image_urls: List[str], image_dir: Path, note_id: str) -> List[str]:
    image_dir.mkdir(parents=True, exist_ok=True)
    saved: List[str] = []
    for idx, url in enumerate(image_urls, 1):
        ext = image_ext_from_url(url)
        file_path = image_dir / f"{note_id}_image_{idx}{ext}"
        resp = requests.get(url, timeout=30)
        resp.raise_for_status()
        file_path.write_bytes(resp.content)
        saved.append(str(file_path))
    return saved


def main() -> int:
    parser = argparse.ArgumentParser(description="Fetch note title/desc text for one or more Xiaohongshu note URLs")
    parser.add_argument("--url", action="append", help="Note URL. Can be repeated")
    parser.add_argument("--url-file", help="Text file with one URL per line")
    parser.add_argument("--cookie", default="", help="Cookie string")
    parser.add_argument("--env-file", default="", help="Path to .env containing COOKIES")
    parser.add_argument("--no-env-proxy", action="store_true", help="Disable proxy env vars for this run")
    parser.add_argument("--download-images", action="store_true", help="Download image files for each note")
    parser.add_argument("--image-dir", default="xhs_images", help="Directory to save downloaded images")
    parser.add_argument("--out", help="Write JSON output to a file")
    args = parser.parse_args()

    urls = parse_urls(args)
    if not urls:
        raise SystemExit("Provide at least one --url or --url-file")

    if args.no_env_proxy:
        drop_proxy_env()

    cookies = load_cookies(cookie_arg=args.cookie, env_file=args.env_file)

    rows: List[Dict[str, Any]] = []

    for url in urls:
        success, msg, res = get_note_info(url, cookies)
        row: Dict[str, Any] = {"url": url, "success": success, "msg": msg}
        if success:
            items = (res or {}).get("data", {}).get("items", [])
            if items:
                note = items[0]
                card = note.get("note_card", {})
                image_urls = collect_image_urls(card)
                row.update(
                    {
                        "note_id": note.get("id") or card.get("note_id"),
                        "title": card.get("title") or card.get("display_title") or "",
                        "desc": card.get("desc") or "",
                        "nickname": card.get("user", {}).get("nickname") or "",
                        "image_urls": image_urls,
                    }
                )
                if args.download_images and image_urls:
                    try:
                        saved_files = download_images(image_urls, Path(args.image_dir), str(row["note_id"]))
                        row["downloaded_images"] = saved_files
                    except Exception as e:
                        row["download_error"] = str(e)
        rows.append(row)

    print(json.dumps(rows, ensure_ascii=False, indent=2))
    if args.out:
        with open(args.out, "w", encoding="utf-8") as f:
            json.dump(rows, f, ensure_ascii=False, indent=2)

    failed = [r for r in rows if not r.get("success")]
    return 1 if failed else 0


if __name__ == "__main__":
    raise SystemExit(main())

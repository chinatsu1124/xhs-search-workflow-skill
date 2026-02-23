#!/usr/bin/env python3
import argparse
import json
import os
import re
import time
from pathlib import Path
from typing import Any, Dict, List

import openpyxl
import requests

from xhs_client import get_note_info, load_cookies, search_some_note


def drop_proxy_env() -> None:
    for k in ("HTTP_PROXY", "HTTPS_PROXY", "http_proxy", "https_proxy"):
        os.environ.pop(k, None)


def norm_str(value: str) -> str:
    return re.sub(r"|[\\/:*?\"<>| ]+", "", value).replace("\n", "").replace("\r", "")


def timestamp_to_str(timestamp: int) -> str:
    return time.strftime("%Y-%m-%d %H:%M:%S", time.localtime(timestamp / 1000))


def pick_image_url(image_obj: Dict[str, Any]) -> str:
    info_list = image_obj.get("info_list") or []
    if len(info_list) > 1 and info_list[1].get("url"):
        return info_list[1]["url"]
    if len(info_list) > 0 and info_list[0].get("url"):
        return info_list[0]["url"]
    return ""


def pick_video_url(card: Dict[str, Any]) -> str:
    video = card.get("video") or {}
    streams = (((video.get("media") or {}).get("stream") or {}).get("h264") or [])
    if streams:
        for key in ("master_url", "url"):
            value = streams[0].get(key)
            if value:
                return value
    origin_key = ((video.get("consumer") or {}).get("origin_video_key") or "")
    if origin_key:
        return f"https://sns-video-bd.xhscdn.com/{origin_key}"
    return ""


def normalize_note_item(item: Dict[str, Any], note_url: str) -> Dict[str, Any]:
    card = item.get("note_card", {})
    note_type = "图集" if card.get("type") == "normal" else "视频"
    user = card.get("user", {})
    note_id = item.get("id", "")
    image_list = [u for u in (pick_image_url(x) for x in card.get("image_list", [])) if u]
    video_cover = image_list[0] if note_type == "视频" and image_list else ""
    video_addr = pick_video_url(card) if note_type == "视频" else ""

    return {
        "note_id": note_id,
        "note_url": note_url,
        "note_type": note_type,
        "user_id": user.get("user_id", ""),
        "home_url": f"https://www.xiaohongshu.com/user/profile/{user.get('user_id', '')}",
        "nickname": user.get("nickname", ""),
        "avatar": user.get("avatar", ""),
        "title": (card.get("title", "") or "无标题").strip() or "无标题",
        "desc": card.get("desc", ""),
        "liked_count": (card.get("interact_info") or {}).get("liked_count", 0),
        "collected_count": (card.get("interact_info") or {}).get("collected_count", 0),
        "comment_count": (card.get("interact_info") or {}).get("comment_count", 0),
        "share_count": (card.get("interact_info") or {}).get("share_count", 0),
        "video_cover": video_cover,
        "video_addr": video_addr,
        "image_list": image_list,
        "tags": [x.get("name", "") for x in card.get("tag_list", []) if x.get("name")],
        "upload_time": timestamp_to_str(card.get("time", 0) or 0) if card.get("time") else "",
        "ip_location": card.get("ip_location", "未知"),
    }


def save_to_xlsx(rows: List[Dict[str, Any]], file_path: Path) -> None:
    wb = openpyxl.Workbook()
    ws = wb.active
    headers = [
        "笔记id",
        "笔记url",
        "笔记类型",
        "用户id",
        "用户主页url",
        "昵称",
        "头像url",
        "标题",
        "描述",
        "点赞数量",
        "收藏数量",
        "评论数量",
        "分享数量",
        "视频封面url",
        "视频地址url",
        "图片地址url列表",
        "标签",
        "上传时间",
        "ip归属地",
    ]
    ws.append(headers)
    for row in rows:
        ws.append([
            row.get("note_id", ""),
            row.get("note_url", ""),
            row.get("note_type", ""),
            row.get("user_id", ""),
            row.get("home_url", ""),
            row.get("nickname", ""),
            row.get("avatar", ""),
            row.get("title", ""),
            row.get("desc", ""),
            row.get("liked_count", 0),
            row.get("collected_count", 0),
            row.get("comment_count", 0),
            row.get("share_count", 0),
            row.get("video_cover", ""),
            row.get("video_addr", ""),
            json.dumps(row.get("image_list", []), ensure_ascii=False),
            json.dumps(row.get("tags", []), ensure_ascii=False),
            row.get("upload_time", ""),
            row.get("ip_location", ""),
        ])
    file_path.parent.mkdir(parents=True, exist_ok=True)
    wb.save(str(file_path))


def download_binary(url: str, path: Path) -> None:
    resp = requests.get(url, timeout=30, stream=True)
    resp.raise_for_status()
    with path.open("wb") as f:
        for chunk in resp.iter_content(chunk_size=1024 * 512):
            if chunk:
                f.write(chunk)


def download_note_media(note: Dict[str, Any], media_root: Path, mode: str) -> Path:
    note_id = note.get("note_id", "")
    user_id = note.get("user_id", "")
    title = norm_str(note.get("title", "无标题"))[:40] or "无标题"
    nickname = norm_str(note.get("nickname", ""))[:20]
    target = media_root / f"{nickname}_{user_id}" / f"{title}_{note_id}"
    target.mkdir(parents=True, exist_ok=True)

    info_path = target / "info.json"
    info_path.write_text(json.dumps(note, ensure_ascii=False, indent=2), encoding="utf-8")

    if note.get("note_type") == "图集" and mode in ("media", "media-image", "all"):
        for idx, url in enumerate(note.get("image_list", []), 1):
            try:
                download_binary(url, target / f"image_{idx}.jpg")
            except Exception:
                continue

    if note.get("note_type") == "视频" and mode in ("media", "media-video", "all"):
        cover = note.get("video_cover", "")
        video = note.get("video_addr", "")
        if cover:
            try:
                download_binary(cover, target / "cover.jpg")
            except Exception:
                pass
        if video:
            try:
                download_binary(video, target / "video.mp4")
            except Exception:
                pass
    return target


def load_urls(url: List[str], url_file: str) -> List[str]:
    urls: List[str] = []
    if url:
        urls.extend(url)
    if url_file:
        with open(url_file, "r", encoding="utf-8") as f:
            for line in f:
                s = line.strip()
                if s and not s.startswith("#"):
                    urls.append(s)
    return urls


def main() -> int:
    parser = argparse.ArgumentParser(description="Export notes to Excel/media in standalone skill")
    parser.add_argument("--url", action="append", help="Note URL. Can repeat")
    parser.add_argument("--url-file", default="", help="Text file with note URLs")
    parser.add_argument("--query", default="", help="Search query to discover note URLs before export")
    parser.add_argument("--num", type=int, default=10, help="When using --query, number of notes")
    parser.add_argument("--save", default="all", choices=["all", "media", "media-video", "media-image", "excel"], help="Export mode")
    parser.add_argument("--excel", default="xhs_notes.xlsx", help="Excel output path")
    parser.add_argument("--media-dir", default="xhs_media", help="Media output root")
    parser.add_argument("--cookie", default="", help="Cookie string")
    parser.add_argument("--env-file", default="", help="Path to .env containing COOKIES")
    parser.add_argument("--no-env-proxy", action="store_true", help="Disable proxy env vars for this run")
    parser.add_argument("--out", default="", help="Write normalized note JSON to file")
    args = parser.parse_args()

    if args.no_env_proxy:
        drop_proxy_env()

    cookies = load_cookies(cookie_arg=args.cookie, env_file=args.env_file)

    urls = load_urls(args.url or [], args.url_file)
    if args.query:
        success, msg, items = search_some_note(args.query, args.num, cookies)
        if not success:
            raise SystemExit(msg)
        for item in items:
            note_id = item.get("id", "")
            xsec_token = item.get("xsec_token", "")
            if note_id and xsec_token:
                urls.append(f"https://www.xiaohongshu.com/explore/{note_id}?xsec_token={xsec_token}")

    if not urls:
        raise SystemExit("Provide --query or --url/--url-file")

    normalized_rows: List[Dict[str, Any]] = []
    for note_url in urls:
        success, msg, res = get_note_info(note_url, cookies)
        if not success:
            continue
        items = (res or {}).get("data", {}).get("items", [])
        if not items:
            continue
        normalized_rows.append(normalize_note_item(items[0], note_url))

    if args.save in ("all", "excel"):
        save_to_xlsx(normalized_rows, Path(args.excel))

    saved_dirs: List[str] = []
    if args.save in ("all", "media", "media-video", "media-image"):
        media_root = Path(args.media_dir)
        for row in normalized_rows:
            path = download_note_media(row, media_root, args.save)
            saved_dirs.append(str(path))

    payload = {"count": len(normalized_rows), "notes": normalized_rows, "saved_dirs": saved_dirs}
    print(json.dumps(payload, ensure_ascii=False, indent=2))

    if args.out:
        with open(args.out, "w", encoding="utf-8") as f:
            json.dump(payload, f, ensure_ascii=False, indent=2)

    return 0


if __name__ == "__main__":
    raise SystemExit(main())

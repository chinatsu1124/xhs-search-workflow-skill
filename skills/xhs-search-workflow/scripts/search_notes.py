#!/usr/bin/env python3
import argparse
import json
import os
from typing import Any, Dict

from xhs_client import load_cookies, search_some_note


def drop_proxy_env() -> None:
    for k in ("HTTP_PROXY", "HTTPS_PROXY", "http_proxy", "https_proxy"):
        os.environ.pop(k, None)


def main() -> int:
    parser = argparse.ArgumentParser(description="Search Xiaohongshu notes (self-contained skill)")
    parser.add_argument("query", help="Search keyword")
    parser.add_argument("--num", type=int, default=10, help="Number of notes to return")
    parser.add_argument("--sort", type=int, default=0, choices=[0, 1, 2, 3, 4], help="0综合 1最新 2最多点赞 3最多评论 4最多收藏")
    parser.add_argument("--note-type", type=int, default=0, choices=[0, 1, 2], help="0不限 1视频笔记 2普通笔记")
    parser.add_argument("--note-time", type=int, default=0, choices=[0, 1, 2, 3], help="0不限 1一天内 2一周内 3半年内")
    parser.add_argument("--note-range", type=int, default=0, choices=[0, 1, 2, 3], help="0不限 1已看过 2未看过 3已关注")
    parser.add_argument("--pos-distance", type=int, default=0, choices=[0, 1, 2], help="0不限 1同城 2附近")
    parser.add_argument("--geo", default="", help="Geo JSON, e.g. '{\"latitude\":39.9,\"longitude\":116.4}'")
    parser.add_argument("--cookie", default="", help="Cookie string")
    parser.add_argument("--env-file", default="", help="Path to .env containing COOKIES")
    parser.add_argument("--no-env-proxy", action="store_true", help="Disable proxy env vars for this run")
    parser.add_argument("--json", action="store_true", help="Print raw JSON output")
    args = parser.parse_args()

    if args.no_env_proxy:
        drop_proxy_env()

    geo_payload: Any = ""
    if args.geo:
        try:
            geo_payload = json.loads(args.geo)
        except Exception:
            geo_payload = args.geo

    cookies = load_cookies(cookie_arg=args.cookie, env_file=args.env_file)
    success, msg, notes = search_some_note(
        args.query,
        args.num,
        cookies,
        sort_type_choice=args.sort,
        note_type=args.note_type,
        note_time=args.note_time,
        note_range=args.note_range,
        pos_distance=args.pos_distance,
        geo=geo_payload,
    )

    if args.json:
        payload: Dict[str, Any] = {
            "success": success,
            "msg": msg,
            "count": len(notes) if notes else 0,
            "notes": notes or [],
        }
        print(json.dumps(payload, ensure_ascii=False, indent=2))
        return 0 if success else 1

    print(f"success={success}")
    print(f"msg={msg}")
    print(f"count={len(notes) if notes else 0}")
    if notes:
        for i, n in enumerate(notes, 1):
            note_id = n.get("id", "")
            token = n.get("xsec_token", "")
            card = n.get("note_card", {})
            title = card.get("display_title") or card.get("title") or ""
            print(f"{i}. {title}")
            if note_id and token:
                print(f"   https://www.xiaohongshu.com/explore/{note_id}?xsec_token={token}")
    return 0 if success else 1


if __name__ == "__main__":
    raise SystemExit(main())

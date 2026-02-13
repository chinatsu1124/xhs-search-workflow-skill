#!/usr/bin/env python3
import argparse
import json
import os
from typing import Any, Dict, Tuple

from xhs_client import (
    creator_get_all_publish_note_info,
    get_all_likesAndcollects,
    get_all_metions,
    get_all_new_connections,
    get_homefeed_all_channel,
    get_homefeed_recommend_by_num,
    get_note_all_comment,
    get_note_info,
    get_note_no_water_img,
    get_note_no_water_video,
    get_search_keyword,
    get_unread_message,
    get_user_all_collect_note_info,
    get_user_all_like_note_info,
    get_user_all_notes,
    get_user_info,
    get_user_self_info,
    get_user_self_info2,
    load_cookies,
    search_some_user,
)


def drop_proxy_env() -> None:
    for k in ("HTTP_PROXY", "HTTPS_PROXY", "http_proxy", "https_proxy"):
        os.environ.pop(k, None)


def output_result(ok: bool, msg: str, data: Any, out_file: str = "") -> int:
    payload: Dict[str, Any] = {"success": ok, "msg": msg, "data": data}
    text = json.dumps(payload, ensure_ascii=False, indent=2)
    print(text)
    if out_file:
        with open(out_file, "w", encoding="utf-8") as f:
            f.write(text + "\n")
    return 0 if ok else 1


def main() -> int:
    parser = argparse.ArgumentParser(description="Unified CLI for full xhs-search-workflow skill")
    parser.add_argument("--cookie", default="", help="Cookie string")
    parser.add_argument("--env-file", default="", help="Path to .env containing COOKIES")
    parser.add_argument("--no-env-proxy", action="store_true", help="Disable proxy env vars for this run")
    parser.add_argument("--out", default="", help="Write JSON output to file")

    sub = parser.add_subparsers(dest="cmd", required=True)

    p_user_info = sub.add_parser("user-info", help="Get other user info")
    p_user_info.add_argument("--user-id", required=True)

    sub.add_parser("user-self-info", help="Get self info (v1)")
    sub.add_parser("user-self-info2", help="Get self info (v2)")

    p_user_posts = sub.add_parser("user-posts", help="Get all notes posted by user URL")
    p_user_posts.add_argument("--user-url", required=True)

    p_user_likes = sub.add_parser("user-likes", help="Get all liked notes by user URL")
    p_user_likes.add_argument("--user-url", required=True)

    p_user_collects = sub.add_parser("user-collects", help="Get all collected notes by user URL")
    p_user_collects.add_argument("--user-url", required=True)

    p_note_info = sub.add_parser("note-info", help="Get note detail by note URL")
    p_note_info.add_argument("--url", required=True)

    p_comments = sub.add_parser("note-comments", help="Get all comments by note URL")
    p_comments.add_argument("--url", required=True)

    p_kw = sub.add_parser("search-keyword", help="Get search keyword recommendation")
    p_kw.add_argument("--word", required=True)

    p_user_search = sub.add_parser("search-users", help="Search users by keyword")
    p_user_search.add_argument("--query", required=True)
    p_user_search.add_argument("--num", type=int, default=10)

    sub.add_parser("messages-unread", help="Get unread message counters")
    sub.add_parser("messages-mentions", help="Get all mentions")
    sub.add_parser("messages-likes", help="Get all likes/collects")
    sub.add_parser("messages-connections", help="Get all new connections")

    sub.add_parser("homefeed-channels", help="Get homefeed categories")
    p_feed = sub.add_parser("homefeed-recommend", help="Get homefeed recommended items")
    p_feed.add_argument("--category", default="homefeed_recommend")
    p_feed.add_argument("--num", type=int, default=20)

    sub.add_parser("creator-posted", help="Get creator platform posted notes")

    p_nv = sub.add_parser("no-water-video", help="Get no-watermark video URL")
    p_nv.add_argument("--note-id", required=True)

    p_ni = sub.add_parser("no-water-img", help="Convert image URL to no-watermark URL")
    p_ni.add_argument("--img-url", required=True)

    args = parser.parse_args()

    if args.no_env_proxy:
        drop_proxy_env()

    cmd = args.cmd
    ok: bool
    msg: str
    data: Any

    if cmd in ("no-water-video", "no-water-img"):
        cookies = ""
    else:
        cookies = load_cookies(cookie_arg=args.cookie, env_file=args.env_file)

    if cmd == "user-info":
        ok, msg, data = get_user_info(args.user_id, cookies)
    elif cmd == "user-self-info":
        ok, msg, data = get_user_self_info(cookies)
    elif cmd == "user-self-info2":
        ok, msg, data = get_user_self_info2(cookies)
    elif cmd == "user-posts":
        ok, msg, data = get_user_all_notes(args.user_url, cookies)
    elif cmd == "user-likes":
        ok, msg, data = get_user_all_like_note_info(args.user_url, cookies)
    elif cmd == "user-collects":
        ok, msg, data = get_user_all_collect_note_info(args.user_url, cookies)
    elif cmd == "note-info":
        ok, msg, data = get_note_info(args.url, cookies)
    elif cmd == "note-comments":
        ok, msg, data = get_note_all_comment(args.url, cookies)
    elif cmd == "search-keyword":
        ok, msg, data = get_search_keyword(args.word, cookies)
    elif cmd == "search-users":
        ok, msg, data = search_some_user(args.query, args.num, cookies)
    elif cmd == "messages-unread":
        ok, msg, data = get_unread_message(cookies)
    elif cmd == "messages-mentions":
        ok, msg, data = get_all_metions(cookies)
    elif cmd == "messages-likes":
        ok, msg, data = get_all_likesAndcollects(cookies)
    elif cmd == "messages-connections":
        ok, msg, data = get_all_new_connections(cookies)
    elif cmd == "homefeed-channels":
        ok, msg, data = get_homefeed_all_channel(cookies)
    elif cmd == "homefeed-recommend":
        ok, msg, data = get_homefeed_recommend_by_num(args.category, args.num, cookies)
    elif cmd == "creator-posted":
        ok, msg, data = creator_get_all_publish_note_info(cookies)
    elif cmd == "no-water-video":
        ok, msg, value = get_note_no_water_video(args.note_id)
        data = {"note_id": args.note_id, "video_url": value}
    elif cmd == "no-water-img":
        ok, msg, value = get_note_no_water_img(args.img_url)
        data = {"input": args.img_url, "output": value}
    else:
        return output_result(False, f"unknown cmd: {cmd}", {})

    return output_result(ok, msg, data, out_file=args.out)


if __name__ == "__main__":
    raise SystemExit(main())

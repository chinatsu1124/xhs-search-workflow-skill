#!/usr/bin/env python3
import json
import math
import os
import random
import re
import urllib.parse
from pathlib import Path
from typing import Any, Dict, List, Tuple

import execjs
import requests
from dotenv import load_dotenv

BASE_URL = "https://edith.xiaohongshu.com"
SKILL_DIR = Path(__file__).resolve().parents[1]
JS_DIR = SKILL_DIR / "assets" / "js"


def _compile_with_cwd(js_file: Path) -> execjs.ExternalRuntime.Context:
    bootstrap = (
        f"process.chdir({json.dumps(str(JS_DIR))});\n"
        f"globalThis.__XHS_SKILL_JS_DIR={json.dumps(str(JS_DIR))};\n"
    )
    source = js_file.read_text(encoding="utf-8")
    return execjs.compile(bootstrap + source)


_JS_XS = _compile_with_cwd(JS_DIR / "xhs_xs_xsc_56.js")
_JS_XRAY = _compile_with_cwd(JS_DIR / "xhs_xray.js")


def trans_cookies(cookies_str: str) -> Dict[str, str]:
    sep = "; " if "; " in cookies_str else ";"
    return {i.split("=")[0]: "=".join(i.split("=")[1:]) for i in cookies_str.split(sep) if i.strip() and "=" in i}


def load_cookies(cookie_arg: str = "", env_file: str = "") -> str:
    if cookie_arg:
        return cookie_arg
    if env_file:
        load_dotenv(env_file)
    else:
        load_dotenv(Path.cwd() / ".env")
        load_dotenv(SKILL_DIR / ".env")
    ck = os.getenv("COOKIES", "")
    if not ck:
        raise ValueError("COOKIES not found. Provide --cookie or set COOKIES in .env")
    return ck


def generate_x_b3_traceid(length: int = 16) -> str:
    chars = "abcdef0123456789"
    return "".join(chars[math.floor(16 * random.random())] for _ in range(length))


def generate_xray_traceid() -> str:
    return _JS_XRAY.call("traceId")


def get_request_headers_template() -> Dict[str, str]:
    return {
        "authority": "edith.xiaohongshu.com",
        "accept": "application/json, text/plain, */*",
        "accept-language": "zh-CN,zh;q=0.9,en;q=0.8,en-GB;q=0.7,en-US;q=0.6",
        "cache-control": "no-cache",
        "content-type": "application/json;charset=UTF-8",
        "origin": "https://www.xiaohongshu.com",
        "pragma": "no-cache",
        "referer": "https://www.xiaohongshu.com/",
        "sec-ch-ua": '"Not A(Brand";v="99", "Microsoft Edge";v="121", "Chromium";v="121"',
        "sec-ch-ua-mobile": "?0",
        "sec-ch-ua-platform": '"Windows"',
        "sec-fetch-dest": "empty",
        "sec-fetch-mode": "cors",
        "sec-fetch-site": "same-site",
        "user-agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/121.0.0.0 Safari/537.36 Edg/121.0.0.0",
        "x-b3-traceid": "",
        "x-mns": "unload",
        "x-s": "",
        "x-s-common": "",
        "x-t": "",
        "x-xray-traceid": generate_xray_traceid(),
    }


def generate_headers(a1: str, api: str, data: Any = "", method: str = "POST") -> Tuple[Dict[str, str], str]:
    ret = _JS_XS.call("get_request_headers_params", api, data, a1, method)
    headers = get_request_headers_template()
    headers["x-s"] = ret["xs"]
    headers["x-t"] = str(ret["xt"])
    headers["x-s-common"] = ret["xs_common"]
    headers["x-b3-traceid"] = generate_x_b3_traceid()
    payload = ""
    if data not in ("", None):
        payload = json.dumps(data, separators=(",", ":"), ensure_ascii=False)
    return headers, payload


def generate_request_params(cookies_str: str, api: str, data: Any = "", method: str = "POST") -> Tuple[Dict[str, str], Dict[str, str], str]:
    cookies = trans_cookies(cookies_str)
    a1 = cookies.get("a1", "")
    if not a1:
        raise ValueError("cookie missing 'a1'")
    headers, payload = generate_headers(a1, api, data, method)
    return headers, cookies, payload


def _splice(api: str, params: Dict[str, Any]) -> str:
    query_parts: List[str] = []
    for key, value in params.items():
        if value is None:
            continue
        query_parts.append(f"{key}={urllib.parse.quote(str(value))}")
    return f"{api}?{'&'.join(query_parts)}" if query_parts else api


def _request_json(method: str, api: str, cookies_str: str, data: Any = "", params: Dict[str, Any] = None, timeout: int = 30) -> Tuple[bool, str, Dict[str, Any]]:
    try:
        request_api = _splice(api, params or {}) if method.upper() == "GET" else api
        headers, cookies, payload = generate_request_params(cookies_str, request_api, data, method.upper())
        url = BASE_URL + request_api
        if method.upper() == "GET":
            response = requests.get(url, headers=headers, cookies=cookies, timeout=timeout)
        else:
            body = payload.encode("utf-8") if payload else b""
            response = requests.post(url, headers=headers, data=body, cookies=cookies, timeout=timeout)
        res_json = response.json()
        return bool(res_json.get("success", False)), res_json.get("msg", ""), res_json
    except Exception as e:
        return False, str(e), {}


def _parse_user_url(user_url: str) -> Tuple[str, str, str]:
    up = urllib.parse.urlparse(user_url)
    user_id = up.path.split("/")[-1]
    q = urllib.parse.parse_qs(up.query)
    xsec_token = q.get("xsec_token", [""])[0]
    xsec_source = q.get("xsec_source", ["pc_search"])[0]
    return user_id, xsec_token, xsec_source


def _parse_note_url(note_url: str) -> Tuple[str, str, str]:
    up = urllib.parse.urlparse(note_url)
    note_id = up.path.split("/")[-1]
    q = urllib.parse.parse_qs(up.query)
    xsec_token = q.get("xsec_token", [""])[0]
    xsec_source = q.get("xsec_source", ["pc_search"])[0]
    return note_id, xsec_token, xsec_source


# ---------- Homefeed ----------
def get_homefeed_all_channel(cookies_str: str) -> Tuple[bool, str, Dict[str, Any]]:
    return _request_json("GET", "/api/sns/web/v1/homefeed/category", cookies_str)


def get_homefeed_recommend(category: str, cursor_score: str, refresh_type: int, note_index: int, cookies_str: str) -> Tuple[bool, str, Dict[str, Any]]:
    data = {
        "cursor_score": cursor_score,
        "num": 20,
        "refresh_type": refresh_type,
        "note_index": note_index,
        "unread_begin_note_id": "",
        "unread_end_note_id": "",
        "unread_note_count": 0,
        "category": category,
        "search_key": "",
        "need_num": 10,
        "image_formats": ["jpg", "webp", "avif"],
        "need_filter_image": False,
    }
    return _request_json("POST", "/api/sns/web/v1/homefeed", cookies_str, data=data)


def get_homefeed_recommend_by_num(category: str, require_num: int, cookies_str: str) -> Tuple[bool, str, List[Dict[str, Any]]]:
    cursor_score, refresh_type, note_index = "", 1, 0
    note_list: List[Dict[str, Any]] = []
    success, msg = True, "成功"
    try:
        while True:
            success, msg, res_json = get_homefeed_recommend(category, cursor_score, refresh_type, note_index, cookies_str)
            if not success:
                raise RuntimeError(msg)
            items = res_json.get("data", {}).get("items", [])
            if not items:
                break
            note_list.extend(items)
            data = res_json.get("data", {})
            cursor_score = data.get("cursor_score", "")
            refresh_type = 3
            note_index += 20
            if len(note_list) >= require_num:
                break
    except Exception as e:
        success, msg = False, str(e)
    return success, msg, note_list[:require_num]


# ---------- User ----------
def get_user_info(user_id: str, cookies_str: str) -> Tuple[bool, str, Dict[str, Any]]:
    return _request_json("GET", "/api/sns/web/v1/user/otherinfo", cookies_str, params={"target_user_id": user_id})


def get_user_self_info(cookies_str: str) -> Tuple[bool, str, Dict[str, Any]]:
    return _request_json("GET", "/api/sns/web/v1/user/selfinfo", cookies_str)


def get_user_self_info2(cookies_str: str) -> Tuple[bool, str, Dict[str, Any]]:
    return _request_json("GET", "/api/sns/web/v2/user/me", cookies_str)


def get_user_note_info(user_id: str, cursor: str, cookies_str: str, xsec_token: str = "", xsec_source: str = "pc_search") -> Tuple[bool, str, Dict[str, Any]]:
    params = {
        "num": "30",
        "cursor": cursor,
        "user_id": user_id,
        "image_formats": "jpg,webp,avif",
        "xsec_token": xsec_token,
        "xsec_source": xsec_source,
    }
    return _request_json("GET", "/api/sns/web/v1/user_posted", cookies_str, params=params)


def get_user_all_notes(user_url: str, cookies_str: str) -> Tuple[bool, str, List[Dict[str, Any]]]:
    cursor = ""
    notes: List[Dict[str, Any]] = []
    success, msg = True, "成功"
    try:
        user_id, xsec_token, xsec_source = _parse_user_url(user_url)
        while True:
            success, msg, res_json = get_user_note_info(user_id, cursor, cookies_str, xsec_token, xsec_source)
            if not success:
                raise RuntimeError(msg)
            data = res_json.get("data", {})
            page_notes = data.get("notes", [])
            notes.extend(page_notes)
            cursor = str(data.get("cursor", ""))
            if not page_notes or not data.get("has_more", False):
                break
    except Exception as e:
        success, msg = False, str(e)
    return success, msg, notes


def get_user_like_note_info(user_id: str, cursor: str, cookies_str: str, xsec_token: str = "", xsec_source: str = "pc_user") -> Tuple[bool, str, Dict[str, Any]]:
    params = {
        "num": "30",
        "cursor": cursor,
        "user_id": user_id,
        "image_formats": "jpg,webp,avif",
        "xsec_token": xsec_token,
        "xsec_source": xsec_source,
    }
    return _request_json("GET", "/api/sns/web/v1/note/like/page", cookies_str, params=params)


def get_user_all_like_note_info(user_url: str, cookies_str: str) -> Tuple[bool, str, List[Dict[str, Any]]]:
    cursor = ""
    notes: List[Dict[str, Any]] = []
    success, msg = True, "成功"
    try:
        user_id, xsec_token, xsec_source = _parse_user_url(user_url)
        if not xsec_source:
            xsec_source = "pc_user"
        while True:
            success, msg, res_json = get_user_like_note_info(user_id, cursor, cookies_str, xsec_token, xsec_source)
            if not success:
                raise RuntimeError(msg)
            data = res_json.get("data", {})
            page_notes = data.get("notes", [])
            notes.extend(page_notes)
            cursor = str(data.get("cursor", ""))
            if not page_notes or not data.get("has_more", False):
                break
    except Exception as e:
        success, msg = False, str(e)
    return success, msg, notes


def get_user_collect_note_info(user_id: str, cursor: str, cookies_str: str, xsec_token: str = "", xsec_source: str = "pc_search") -> Tuple[bool, str, Dict[str, Any]]:
    params = {
        "num": "30",
        "cursor": cursor,
        "user_id": user_id,
        "image_formats": "jpg,webp,avif",
        "xsec_token": xsec_token,
        "xsec_source": xsec_source,
    }
    return _request_json("GET", "/api/sns/web/v2/note/collect/page", cookies_str, params=params)


def get_user_all_collect_note_info(user_url: str, cookies_str: str) -> Tuple[bool, str, List[Dict[str, Any]]]:
    cursor = ""
    notes: List[Dict[str, Any]] = []
    success, msg = True, "成功"
    try:
        user_id, xsec_token, xsec_source = _parse_user_url(user_url)
        while True:
            success, msg, res_json = get_user_collect_note_info(user_id, cursor, cookies_str, xsec_token, xsec_source)
            if not success:
                raise RuntimeError(msg)
            data = res_json.get("data", {})
            page_notes = data.get("notes", [])
            notes.extend(page_notes)
            cursor = str(data.get("cursor", ""))
            if not page_notes or not data.get("has_more", False):
                break
    except Exception as e:
        success, msg = False, str(e)
    return success, msg, notes


# ---------- Note/Search ----------
def get_note_info(url: str, cookies_str: str) -> Tuple[bool, str, Dict[str, Any]]:
    note_id, xsec_token, xsec_source = _parse_note_url(url)
    data = {
        "source_note_id": note_id,
        "image_formats": ["jpg", "webp", "avif"],
        "extra": {"need_body_topic": "1"},
        "xsec_source": xsec_source,
        "xsec_token": xsec_token,
    }
    return _request_json("POST", "/api/sns/web/v1/feed", cookies_str, data=data)


def get_search_keyword(word: str, cookies_str: str) -> Tuple[bool, str, Dict[str, Any]]:
    return _request_json("GET", "/api/sns/web/v1/search/recommend", cookies_str, params={"keyword": word})


def _search_note_payload(
    query: str,
    page: int,
    sort_type_choice: int = 0,
    note_type: int = 0,
    note_time: int = 0,
    note_range: int = 0,
    pos_distance: int = 0,
    geo: Any = "",
) -> Dict[str, Any]:
    sort_type_map = {
        0: "general",
        1: "time_descending",
        2: "popularity_descending",
        3: "comment_descending",
        4: "collect_descending",
    }
    note_type_map = {0: "不限", 1: "视频笔记", 2: "普通笔记"}
    note_time_map = {0: "不限", 1: "一天内", 2: "一周内", 3: "半年内"}
    note_range_map = {0: "不限", 1: "已看过", 2: "未看过", 3: "已关注"}
    pos_distance_map = {0: "不限", 1: "同城", 2: "附近"}

    geo_payload = ""
    if isinstance(geo, dict):
        geo_payload = json.dumps(geo, separators=(",", ":"), ensure_ascii=False)
    elif isinstance(geo, str):
        geo_payload = geo

    return {
        "keyword": query,
        "page": page,
        "page_size": 20,
        "search_id": generate_x_b3_traceid(21),
        "sort": "general",
        "note_type": 0,
        "ext_flags": [],
        "filters": [
            {"tags": [sort_type_map.get(sort_type_choice, "general")], "type": "sort_type"},
            {"tags": [note_type_map.get(note_type, "不限")], "type": "filter_note_type"},
            {"tags": [note_time_map.get(note_time, "不限")], "type": "filter_note_time"},
            {"tags": [note_range_map.get(note_range, "不限")], "type": "filter_note_range"},
            {"tags": [pos_distance_map.get(pos_distance, "不限")], "type": "filter_pos_distance"},
        ],
        "geo": geo_payload,
        "image_formats": ["jpg", "webp", "avif"],
    }


def search_note(
    query: str,
    cookies_str: str,
    page: int = 1,
    sort_type_choice: int = 0,
    note_type: int = 0,
    note_time: int = 0,
    note_range: int = 0,
    pos_distance: int = 0,
    geo: Any = "",
) -> Tuple[bool, str, Dict[str, Any]]:
    data = _search_note_payload(query, page, sort_type_choice, note_type, note_time, note_range, pos_distance, geo)
    return _request_json("POST", "/api/sns/web/v1/search/notes", cookies_str, data=data)


def search_some_note(
    query: str,
    require_num: int,
    cookies_str: str,
    sort_type_choice: int = 0,
    note_type: int = 0,
    note_time: int = 0,
    note_range: int = 0,
    pos_distance: int = 0,
    geo: Any = "",
) -> Tuple[bool, str, List[Dict[str, Any]]]:
    page = 1
    notes: List[Dict[str, Any]] = []
    success, msg = True, "成功"
    try:
        while True:
            success, msg, res_json = search_note(
                query,
                cookies_str,
                page=page,
                sort_type_choice=sort_type_choice,
                note_type=note_type,
                note_time=note_time,
                note_range=note_range,
                pos_distance=pos_distance,
                geo=geo,
            )
            if not success:
                raise RuntimeError(msg)
            data = res_json.get("data", {})
            items = data.get("items", [])
            notes.extend(items)
            page += 1
            if len(notes) >= require_num or not data.get("has_more", False):
                break
    except Exception as e:
        success, msg = False, str(e)
    return success, msg, notes[:require_num]


def search_user(query: str, cookies_str: str, page: int = 1) -> Tuple[bool, str, Dict[str, Any]]:
    data = {
        "search_user_request": {
            "keyword": query,
            "search_id": generate_x_b3_traceid(21),
            "page": page,
            "page_size": 15,
            "biz_type": "web_search_user",
            "request_id": f"{generate_x_b3_traceid(8)}-{generate_x_b3_traceid(12)}",
        }
    }
    return _request_json("POST", "/api/sns/web/v1/search/usersearch", cookies_str, data=data)


def search_some_user(query: str, require_num: int, cookies_str: str) -> Tuple[bool, str, List[Dict[str, Any]]]:
    page = 1
    users: List[Dict[str, Any]] = []
    success, msg = True, "成功"
    try:
        while True:
            success, msg, res_json = search_user(query, cookies_str, page=page)
            if not success:
                raise RuntimeError(msg)
            data = res_json.get("data", {})
            page_users = data.get("users", [])
            users.extend(page_users)
            page += 1
            if len(users) >= require_num or not data.get("has_more", False):
                break
    except Exception as e:
        success, msg = False, str(e)
    return success, msg, users[:require_num]


# ---------- Comment ----------
def get_note_out_comment(note_id: str, cursor: str, xsec_token: str, cookies_str: str) -> Tuple[bool, str, Dict[str, Any]]:
    params = {
        "note_id": note_id,
        "cursor": cursor,
        "top_comment_id": "",
        "image_formats": "jpg,webp,avif",
        "xsec_token": xsec_token,
    }
    return _request_json("GET", "/api/sns/web/v2/comment/page", cookies_str, params=params)


def get_note_all_out_comment(note_id: str, xsec_token: str, cookies_str: str) -> Tuple[bool, str, List[Dict[str, Any]]]:
    cursor = ""
    out_comments: List[Dict[str, Any]] = []
    success, msg = True, "成功"
    try:
        while True:
            success, msg, res_json = get_note_out_comment(note_id, cursor, xsec_token, cookies_str)
            if not success:
                raise RuntimeError(msg)
            data = res_json.get("data", {})
            comments = data.get("comments", [])
            out_comments.extend(comments)
            cursor = str(data.get("cursor", ""))
            if not comments or not data.get("has_more", False):
                break
    except Exception as e:
        success, msg = False, str(e)
    return success, msg, out_comments


def get_note_inner_comment(comment: Dict[str, Any], cursor: str, xsec_token: str, cookies_str: str) -> Tuple[bool, str, Dict[str, Any]]:
    params = {
        "note_id": comment.get("note_id", ""),
        "root_comment_id": comment.get("id", ""),
        "num": "10",
        "cursor": cursor,
        "image_formats": "jpg,webp,avif",
        "top_comment_id": "",
        "xsec_token": xsec_token,
    }
    return _request_json("GET", "/api/sns/web/v2/comment/sub/page", cookies_str, params=params)


def get_note_all_inner_comment(comment: Dict[str, Any], xsec_token: str, cookies_str: str) -> Tuple[bool, str, Dict[str, Any]]:
    success, msg = True, "成功"
    try:
        if not comment.get("sub_comment_has_more"):
            return True, "成功", comment
        cursor = str(comment.get("sub_comment_cursor", ""))
        sub_comments = comment.get("sub_comments", []) or []
        while True:
            success, msg, res_json = get_note_inner_comment(comment, cursor, xsec_token, cookies_str)
            if not success:
                raise RuntimeError(msg)
            data = res_json.get("data", {})
            comments = data.get("comments", [])
            sub_comments.extend(comments)
            cursor = str(data.get("cursor", ""))
            if not data.get("has_more", False):
                break
        comment["sub_comments"] = sub_comments
    except Exception as e:
        success, msg = False, str(e)
    return success, msg, comment


def get_note_all_comment(url: str, cookies_str: str) -> Tuple[bool, str, List[Dict[str, Any]]]:
    success, msg = True, "成功"
    out_comments: List[Dict[str, Any]] = []
    try:
        note_id, xsec_token, _ = _parse_note_url(url)
        success, msg, out_comments = get_note_all_out_comment(note_id, xsec_token, cookies_str)
        if not success:
            raise RuntimeError(msg)
        for idx, comment in enumerate(out_comments):
            success, msg, new_comment = get_note_all_inner_comment(comment, xsec_token, cookies_str)
            if not success:
                raise RuntimeError(msg)
            out_comments[idx] = new_comment
    except Exception as e:
        success, msg = False, str(e)
    return success, msg, out_comments


# ---------- Message ----------
def get_unread_message(cookies_str: str) -> Tuple[bool, str, Dict[str, Any]]:
    return _request_json("GET", "/api/sns/web/unread_count", cookies_str)


def get_metions(cursor: str, cookies_str: str) -> Tuple[bool, str, Dict[str, Any]]:
    return _request_json("GET", "/api/sns/web/v1/you/mentions", cookies_str, params={"num": "20", "cursor": cursor})


def get_all_metions(cookies_str: str) -> Tuple[bool, str, List[Dict[str, Any]]]:
    cursor = ""
    rows: List[Dict[str, Any]] = []
    success, msg = True, "成功"
    try:
        while True:
            success, msg, res_json = get_metions(cursor, cookies_str)
            if not success:
                raise RuntimeError(msg)
            data = res_json.get("data", {})
            batch = data.get("message_list", [])
            rows.extend(batch)
            cursor = str(data.get("cursor", ""))
            if not data.get("has_more", False):
                break
    except Exception as e:
        success, msg = False, str(e)
    return success, msg, rows


def get_likesAndcollects(cursor: str, cookies_str: str) -> Tuple[bool, str, Dict[str, Any]]:
    return _request_json("GET", "/api/sns/web/v1/you/likes", cookies_str, params={"num": "20", "cursor": cursor})


def get_all_likesAndcollects(cookies_str: str) -> Tuple[bool, str, List[Dict[str, Any]]]:
    cursor = ""
    rows: List[Dict[str, Any]] = []
    success, msg = True, "成功"
    try:
        while True:
            success, msg, res_json = get_likesAndcollects(cursor, cookies_str)
            if not success:
                raise RuntimeError(msg)
            data = res_json.get("data", {})
            batch = data.get("message_list", [])
            rows.extend(batch)
            cursor = str(data.get("cursor", ""))
            if not data.get("has_more", False):
                break
    except Exception as e:
        success, msg = False, str(e)
    return success, msg, rows


def get_new_connections(cursor: str, cookies_str: str) -> Tuple[bool, str, Dict[str, Any]]:
    return _request_json("GET", "/api/sns/web/v1/you/connections", cookies_str, params={"num": "20", "cursor": cursor})


def get_all_new_connections(cookies_str: str) -> Tuple[bool, str, List[Dict[str, Any]]]:
    cursor = ""
    rows: List[Dict[str, Any]] = []
    success, msg = True, "成功"
    try:
        while True:
            success, msg, res_json = get_new_connections(cursor, cookies_str)
            if not success:
                raise RuntimeError(msg)
            data = res_json.get("data", {})
            batch = data.get("message_list", [])
            rows.extend(batch)
            cursor = str(data.get("cursor", ""))
            if not data.get("has_more", False):
                break
    except Exception as e:
        success, msg = False, str(e)
    return success, msg, rows


# ---------- Creator ----------
def creator_get_publish_note_info(page: int, cookies_str: str) -> Tuple[bool, str, Dict[str, Any]]:
    params: Dict[str, Any] = {"tab": "0"}
    if page >= 0:
        params["page"] = str(page)
    return _request_json("GET", "/web_api/sns/v5/creator/note/user/posted", cookies_str, params=params)


def creator_get_all_publish_note_info(cookies_str: str) -> Tuple[bool, str, List[Dict[str, Any]]]:
    page = -1
    notes: List[Dict[str, Any]] = []
    success, msg = True, "成功"
    try:
        while True:
            success, msg, res_json = creator_get_publish_note_info(page, cookies_str)
            if not success:
                raise RuntimeError(msg)
            data = res_json.get("data", {})
            notes.extend(data.get("notes", []))
            page = int(data.get("page", -1))
            if page == -1:
                break
    except Exception as e:
        success, msg = False, str(e)
    return success, msg, notes


# ---------- No-watermark helpers ----------
def get_note_no_water_video(note_id: str) -> Tuple[bool, str, str]:
    try:
        headers = {
            "user-agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/121.0.0.0 Safari/537.36"
        }
        url = f"https://www.xiaohongshu.com/explore/{note_id}"
        response = requests.get(url, headers=headers, timeout=30)
        html = response.text
        matches = re.findall(r'<meta name="og:video" content="(.*?)">', html)
        if not matches:
            return False, "og:video not found", ""
        return True, "成功", matches[0]
    except Exception as e:
        return False, str(e), ""


def get_note_no_water_img(img_url: str) -> Tuple[bool, str, str]:
    try:
        if ".jpg" in img_url:
            img_id = "/".join([split for split in img_url.split("/")[-3:]]).split("!")[0]
            return True, "成功", f"https://sns-img-qc.xhscdn.com/{img_id}"
        if "spectrum" in img_url:
            img_id = "/".join(img_url.split("/")[-2:]).split("!")[0]
            return True, "成功", f"http://sns-webpic.xhscdn.com/{img_id}?imageView2/2/w/format/jpg"
        img_id = img_url.split("/")[-1].split("!")[0]
        return True, "成功", f"https://sns-img-qc.xhscdn.com/{img_id}"
    except Exception as e:
        return False, str(e), ""

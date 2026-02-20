---
name: xhs-search-workflow
description: 使用内置 JS 签名与 Cookie 鉴权运行独立的小红书数据工作流，适用于搜索、提取、导出和创作者数据采集；当需要脱离原仓库稳定复用 Spider_XHS 核心能力时使用。 Use this skill to run a standalone Xiaohongshu workflow with bundled JS signing assets and cookie auth for search, extraction, export, and creator data collection when you need Spider_XHS-derived capabilities without depending on the original repository.
---

# 小红书工作流技能说明 / XHS Workflow Skill Guide

## 中文说明

### 参考库
- 本技能由 `Spider_XHS` 重构而来。
- 参考仓库：`cv-cat/Spider_XHS`
- 参考地址：https://github.com/cv-cat/Spider_XHS

重构原则：
1. 去除对原仓 `apis/`、`xhs_utils/` 的运行时依赖。
2. 将签名 JS 与依赖打包到技能目录。
3. 提供统一 CLI 与分场景脚本，降低调用复杂度。

### 安装
在新机器上首次运行：

```bash
skills/xhs-search-workflow/scripts/setup_env.sh
```

该命令会创建 `skills/xhs-search-workflow/.venv` 并安装 Python 依赖。

### 鉴权输入
- `--cookie "..."`
- 或 `--env-file /path/to/.env`（其中 `COOKIES="..."`）
- 如宿主机代理变量导致失败，添加 `--no-env-proxy`

### 首次使用：如何获取 Cookie
1. 在浏览器登录小红书网页端（确保是已登录状态）。
2. 打开开发者工具 `Network`，筛选 `Fetch/XHR`，刷新页面后任选一条业务请求。
3. 优先选择 `edith.xiaohongshu.com` 的请求并复制 `Request Headers` 里的完整 `cookie` 字段。
4. 其他域名请求也可用，但需满足：
- 请求头里包含完整 Cookie。
- 至少有 `a1`、`web_session`、`gid`。
5. 将 Cookie 写入 `.env`：
```env
COOKIES="完整cookie字符串"
```
6. 首次验证建议先运行：
```bash
skills/xhs-search-workflow/.venv/bin/python \
  skills/xhs-search-workflow/scripts/xhs_full_cli.py \
  --env-file .env --no-env-proxy homefeed-channels
```
7. 若返回“登录已过期”或“无登录信息”，重新登录网页并重新抓取 Cookie。

安全建议：
- 不要在聊天、截图、Git 仓库中泄露 Cookie。
- 将 `.env` 加入 `.gitignore`。

### 脚本清单
- `scripts/search_notes.py`：笔记搜索（支持筛选）
- `scripts/fetch_note_texts.py`：提取标题/正文/图片链接，可选下载图片
- `scripts/xhs_full_cli.py`：统一入口（用户/评论/消息/首页/创作者/无水印）
- `scripts/export_notes.py`：导出 Excel 与媒体文件

### 常用命令

1. 搜索笔记
```bash
skills/xhs-search-workflow/.venv/bin/python \
  skills/xhs-search-workflow/scripts/search_notes.py "汇丰银行" \
  --num 10 --sort 0 --note-type 0 --no-env-proxy --json
```

2. 提取笔记正文与图片链接
```bash
skills/xhs-search-workflow/.venv/bin/python \
  skills/xhs-search-workflow/scripts/fetch_note_texts.py \
  --url-file note_urls.txt --no-env-proxy \
  --timeout 30 --retries 2 --min-interval 4 --max-interval 7 \
  --out note_content.json
```

3. 提取同时下载图片
```bash
skills/xhs-search-workflow/.venv/bin/python \
  skills/xhs-search-workflow/scripts/fetch_note_texts.py \
  --url-file note_urls.txt --no-env-proxy \
  --download-images --image-dir xhs_images \
  --timeout 30 --retries 2 --min-interval 4 --max-interval 7 \
  --out note_content.json
```

4. 统一 CLI 示例（搜索用户）
```bash
skills/xhs-search-workflow/.venv/bin/python \
  skills/xhs-search-workflow/scripts/xhs_full_cli.py \
  --env-file .env --no-env-proxy search-users --query "汇丰银行" --num 10
```

5. 导出 Excel/媒体
```bash
skills/xhs-search-workflow/.venv/bin/python \
  skills/xhs-search-workflow/scripts/export_notes.py \
  --query "汇丰银行" --num 10 --save all \
  --excel xhs_notes.xlsx --media-dir xhs_media --no-env-proxy
```

### `xhs_full_cli.py` 子命令
- `user-info --user-id <id>`
- `user-self-info`
- `user-self-info2`
- `user-posts --user-url <url>`
- `user-likes --user-url <url>`
- `user-collects --user-url <url>`
- `note-info --url <url>`
- `note-comments --url <url>`
- `search-keyword --word <kw>`
- `search-users --query <kw> --num <n>`
- `messages-unread`
- `messages-mentions`
- `messages-likes`
- `messages-connections`
- `homefeed-channels`
- `homefeed-recommend --category <name> --num <n>`
- `creator-posted`
- `no-water-video --note-id <id>`
- `no-water-img --img-url <url>`

### 功能范围与边界
- 覆盖范围：搜索、详情、评论、用户、消息、首页推荐、创作者作品、无水印链接转换、导出。
- 当前边界：以 Cookie 鉴权为主，不内置交互式登录流程。
- 设计优点：脚本职责清晰、统一入口完整、离线资源齐全、迁移成本低。

### 离线与可移植设计
- 签名 JS 打包在 `assets/js/`。
- 离线 `crypto-js` 位于 `assets/js/vendor/crypto-js.js`。
- 运行时不依赖原仓 `Spider_XHS` 的 `apis/` 或 `xhs_utils/`。

### 校验
每次改动后执行：

```bash
skills/xhs-search-workflow/.venv/bin/python \
  "$CODEX_HOME/skills/.system/skill-creator/scripts/quick_validate.py" \
  skills/xhs-search-workflow
```

基础 smoke tests：

```bash
skills/xhs-search-workflow/.venv/bin/python skills/xhs-search-workflow/scripts/xhs_full_cli.py --help
skills/xhs-search-workflow/.venv/bin/python skills/xhs-search-workflow/scripts/export_notes.py --help
```

### 执行注意事项
- 优先使用 `skills/xhs-search-workflow/.venv/bin/python`，避免系统 Python 版本偏差。
- 环境变化后先执行 `scripts/setup_env.sh`。
- 保留 `assets/js/vendor/crypto-js.js` 以保证离线可运行。
- 脚本默认 UTF-8；Windows 下可额外设置 `PYTHONUTF8=1` 与 `PYTHONIOENCODING=utf-8`。
- `scripts/xhs_client.py` 会自动校验 JS 资源并同步 `assets/js/static/xhs_xray_pack{1,2}.js`。
- `xhs_full_cli.py` 全局参数必须在子命令之前。
- 正确：`xhs_full_cli.py --env-file .env --no-env-proxy <subcommand> ...`
- 错误：`xhs_full_cli.py <subcommand> ... --env-file .env`
- `messages-*` 返回可能很大，建议配合 `--out` 输出文件。
- `fetch_note_texts.py` 默认串行节流+重试，适合规避不稳定网络与风控抖动。

### 故障排查
见 `references/troubleshooting.md`。

## English Guide

### Reference Repository
- This skill is refactored from `Spider_XHS`.
- Reference repository: `cv-cat/Spider_XHS`
- Reference URL: https://github.com/cv-cat/Spider_XHS

Refactor principles:
1. Remove runtime dependency on original `apis/` and `xhs_utils` modules.
2. Bundle signing JS assets and dependencies inside this skill.
3. Provide a unified CLI plus scenario scripts for simpler reuse.

### Setup
Run once on a new machine:

```bash
skills/xhs-search-workflow/scripts/setup_env.sh
```

It creates `skills/xhs-search-workflow/.venv` and installs Python dependencies.

### Auth Input
- `--cookie "..."`
- Or `--env-file /path/to/.env` with `COOKIES="..."`
- Add `--no-env-proxy` when host proxy variables break requests.

### First Use: How to Capture Cookie
1. Log in to Xiaohongshu Web in your browser.
2. Open devtools `Network`, filter `Fetch/XHR`, refresh, and pick a business API request.
3. Prefer a request to `edith.xiaohongshu.com`, then copy the full `cookie` value from `Request Headers`.
4. Other request domains can also work if:
- The request contains a full cookie header.
- It includes at least `a1`, `web_session`, and `gid`.
5. Save cookie in `.env`:
```env
COOKIES="your_full_cookie_string"
```
6. First-run verification:
```bash
skills/xhs-search-workflow/.venv/bin/python \
  skills/xhs-search-workflow/scripts/xhs_full_cli.py \
  --env-file .env --no-env-proxy homefeed-channels
```
7. If response shows `登录已过期` / `无登录信息`, re-login in browser and capture cookie again.

Security notes:
- Never paste cookie in chats, screenshots, or Git repositories.
- Keep `.env` in `.gitignore`.

### Script List
- `scripts/search_notes.py`: note search with filters
- `scripts/fetch_note_texts.py`: extract title/text/image URLs, optional image download
- `scripts/xhs_full_cli.py`: unified entry for user/comment/message/homefeed/creator/no-water APIs
- `scripts/export_notes.py`: export note data to Excel and/or media files

### Typical Commands

1. Search notes
```bash
skills/xhs-search-workflow/.venv/bin/python \
  skills/xhs-search-workflow/scripts/search_notes.py "HSBC" \
  --num 10 --sort 0 --note-type 0 --no-env-proxy --json
```

2. Extract note text and image URLs
```bash
skills/xhs-search-workflow/.venv/bin/python \
  skills/xhs-search-workflow/scripts/fetch_note_texts.py \
  --url-file note_urls.txt --no-env-proxy \
  --timeout 30 --retries 2 --min-interval 4 --max-interval 7 \
  --out note_content.json
```

3. Download images while extracting
```bash
skills/xhs-search-workflow/.venv/bin/python \
  skills/xhs-search-workflow/scripts/fetch_note_texts.py \
  --url-file note_urls.txt --no-env-proxy \
  --download-images --image-dir xhs_images \
  --timeout 30 --retries 2 --min-interval 4 --max-interval 7 \
  --out note_content.json
```

4. Unified CLI example (search users)
```bash
skills/xhs-search-workflow/.venv/bin/python \
  skills/xhs-search-workflow/scripts/xhs_full_cli.py \
  --env-file .env --no-env-proxy search-users --query "HSBC" --num 10
```

5. Export Excel/media
```bash
skills/xhs-search-workflow/.venv/bin/python \
  skills/xhs-search-workflow/scripts/export_notes.py \
  --query "HSBC" --num 10 --save all \
  --excel xhs_notes.xlsx --media-dir xhs_media --no-env-proxy
```

### `xhs_full_cli.py` Subcommands
- `user-info --user-id <id>`
- `user-self-info`
- `user-self-info2`
- `user-posts --user-url <url>`
- `user-likes --user-url <url>`
- `user-collects --user-url <url>`
- `note-info --url <url>`
- `note-comments --url <url>`
- `search-keyword --word <kw>`
- `search-users --query <kw> --num <n>`
- `messages-unread`
- `messages-mentions`
- `messages-likes`
- `messages-connections`
- `homefeed-channels`
- `homefeed-recommend --category <name> --num <n>`
- `creator-posted`
- `no-water-video --note-id <id>`
- `no-water-img --img-url <url>`

### Scope and Boundaries
- Coverage: search, note detail, comments, users, messages, homefeed, creator posts, no-watermark conversion, export.
- Boundary: cookie-based auth is the default; interactive login flow is not included.
- Strengths: clear script responsibilities, complete unified CLI, bundled offline assets, and portable deployment.

### Offline and Portability
- Signing JS is bundled in `assets/js/`.
- Offline `crypto-js` is bundled at `assets/js/vendor/crypto-js.js`.
- Runtime does not import `apis/` or `xhs_utils/` from original Spider_XHS.

### Validation
Run after edits:

```bash
skills/xhs-search-workflow/.venv/bin/python \
  "$CODEX_HOME/skills/.system/skill-creator/scripts/quick_validate.py" \
  skills/xhs-search-workflow
```

Basic smoke tests:

```bash
skills/xhs-search-workflow/.venv/bin/python skills/xhs-search-workflow/scripts/xhs_full_cli.py --help
skills/xhs-search-workflow/.venv/bin/python skills/xhs-search-workflow/scripts/export_notes.py --help
```

### Execution Notes
- Prefer `skills/xhs-search-workflow/.venv/bin/python` over system Python.
- Rerun `scripts/setup_env.sh` after environment changes.
- Keep `assets/js/vendor/crypto-js.js` for offline portability.
- Scripts enforce UTF-8 output; on Windows also set `PYTHONUTF8=1` and `PYTHONIOENCODING=utf-8`.
- `scripts/xhs_client.py` auto-checks JS assets and syncs `assets/js/static/xhs_xray_pack{1,2}.js`.
- Put global flags before subcommands in `xhs_full_cli.py`.
- Message endpoints can be large; prefer `--out` files.
- `fetch_note_texts.py` uses serial throttling and retries for stability.

### Troubleshooting
See `references/troubleshooting.md`.

# Quickstart

## 1. 初始化环境

首次在新机器运行：

```bash
skills/xhs-search-workflow/scripts/setup_env.sh
```

该命令会创建 `skills/xhs-search-workflow/.venv` 并安装 Python 依赖。

## 2. 鉴权方式

可用输入：

- `--cookie "..."`
- `--env-file /path/to/.env`，其中 `COOKIES="..."`
- `xhs_full_cli.py login` 二维码登录

如宿主机代理变量导致失败，添加 `--no-env-proxy`。

### 2.1 二维码登录

直接运行：

```bash
skills/xhs-search-workflow/.venv/bin/python \
  skills/xhs-search-workflow/scripts/xhs_full_cli.py login
```

登录流程会：

- 本地 bootstrap 匿名态 cookie，如 `a1`、`webId`、`loadts`、`xsecappid`
- 请求 `qrcode/create -> qrcode/userinfo -> qrcode/status`
- 生成终端二维码
- 生成本地 PNG 二维码图片
- 登录成功后保存会话到本地 `cookies.json`

默认二维码图片位置：

```text
~/.xhs-search-workflow/login-qrcode.png
```

### 2.2 手动准备 Cookie

1. 在浏览器登录小红书网页端。
2. 打开开发者工具 `Network`，筛选 `Fetch/XHR`。
3. 刷新页面并选择一条 `edith.xiaohongshu.com` 的业务请求。
4. 复制 `Request Headers` 中完整 `cookie` 字段。
5. 写入 `.env`：

```env
COOKIES="完整cookie字符串"
```

建议至少包含 `a1`、`web_session`、`gid`。

## 3. 常用命令

### 3.1 登录与状态

```bash
skills/xhs-search-workflow/.venv/bin/python \
  skills/xhs-search-workflow/scripts/xhs_full_cli.py login
```

```bash
skills/xhs-search-workflow/.venv/bin/python \
  skills/xhs-search-workflow/scripts/xhs_full_cli.py status
```

```bash
skills/xhs-search-workflow/.venv/bin/python \
  skills/xhs-search-workflow/scripts/xhs_full_cli.py logout
```

### 3.2 搜索笔记

```bash
skills/xhs-search-workflow/.venv/bin/python \
  skills/xhs-search-workflow/scripts/search_notes.py "汇丰银行" \
  --num 10 --sort 0 --note-type 0 --no-env-proxy --json
```

### 3.3 提取正文与无水印图片链接

```bash
skills/xhs-search-workflow/.venv/bin/python \
  skills/xhs-search-workflow/scripts/fetch_note_texts.py \
  --url-file note_urls.txt --no-env-proxy \
  --timeout 30 --retries 2 --min-interval 4 --max-interval 7 \
  --out note_content.json
```

### 3.4 下载无水印图片

```bash
skills/xhs-search-workflow/.venv/bin/python \
  skills/xhs-search-workflow/scripts/fetch_note_texts.py \
  --url-file note_urls.txt --no-env-proxy \
  --download-images --image-dir xhs_images \
  --timeout 30 --retries 2 --min-interval 4 --max-interval 7 \
  --out note_content.json
```

### 3.5 统一 CLI 示例

```bash
skills/xhs-search-workflow/.venv/bin/python \
  skills/xhs-search-workflow/scripts/xhs_full_cli.py \
  --env-file .env --no-env-proxy search-users --query "汇丰银行" --num 10
```

### 3.6 导出 Excel 与媒体

```bash
skills/xhs-search-workflow/.venv/bin/python \
  skills/xhs-search-workflow/scripts/export_notes.py \
  --query "汇丰银行" --num 10 --save all \
  --excel xhs_notes.xlsx --media-dir xhs_media --no-env-proxy
```

## 4. `xhs_full_cli.py` 子命令

- `login`
- `logout`
- `status`
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

## 5. 校验

```bash
skills/xhs-search-workflow/.venv/bin/python \
  "$CODEX_HOME/skills/.system/skill-creator/scripts/quick_validate.py" \
  skills/xhs-search-workflow
```

```bash
skills/xhs-search-workflow/.venv/bin/python skills/xhs-search-workflow/scripts/xhs_full_cli.py --help
skills/xhs-search-workflow/.venv/bin/python skills/xhs-search-workflow/scripts/export_notes.py --help
```

## 6. 执行注意事项

- 优先使用 `skills/xhs-search-workflow/.venv/bin/python`
- `xhs_full_cli.py` 全局参数必须放在子命令之前
- `messages-*` 返回可能很大，建议配合 `--out`
- `fetch_note_texts.py` 默认串行节流和重试，适合更稳的抓取
- 不要在聊天、截图或 Git 仓库中泄露 Cookie

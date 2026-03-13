---
name: xhs-search-workflow
description: 使用内置 JS 签名与 Cookie/二维码登录运行独立的小红书数据工作流，适用于登录、搜索、提取、导出和创作者数据采集；当需要脱离原仓库稳定复用 Spider_XHS 核心能力，或用户明确要求下载小红书图片、视频、媒体文件并应默认走无水印下载链路时使用。 Use this skill to run a standalone Xiaohongshu workflow with bundled JS signing assets and cookie or QR login for authentication, plus search, extraction, export, and creator data collection when you need Spider_XHS-derived capabilities without depending on the original repository, especially when the user asks to download XHS images, videos, or media files and the workflow should default to no-watermark downloads.
---

# XHS Search Workflow

使用这个 skill 时，优先把它当成一个独立的小红书工作流工具箱，而不是原仓库的薄封装。

## 执行流程

1. 先确认运行环境。
   使用 `skills/xhs-search-workflow/scripts/setup_env.sh` 初始化依赖。
   执行脚本时优先使用 `skills/xhs-search-workflow/.venv/bin/python`。
   需要完整安装、常用命令或校验命令时，打开 `references/quickstart.md`。

2. 先决定鉴权方式。
   已有有效 `COOKIES` 时，直接使用 `--cookie` 或 `--env-file`。
   没有登录态时，运行 `xhs_full_cli.py login` 做二维码登录。
   二维码登录会自动 bootstrap 匿名态 cookie，生成终端二维码和本地 PNG 图片，并把成功会话保存到本地 `cookies.json`。
   需要手动抓 Cookie、查看二维码登录细节或排查登录失败时，打开 `references/quickstart.md` 和 `references/troubleshooting.md`。

3. 按任务选择入口脚本。
   `scripts/xhs_full_cli.py`：统一入口，优先用于登录、状态检查、用户、评论、消息、首页、创作者、无水印链接等通用任务。
   `scripts/search_notes.py`：只做笔记搜索。
   `scripts/fetch_note_texts.py`：提取标题、正文、图片链接，或下载无水印图片。
   `scripts/export_notes.py`：导出 Excel 与媒体文件。

4. 遵守媒体下载默认策略。
   用户一旦明确要求下载图片、视频或媒体包，默认使用无水印链接。
   只有用户明确要求保留原始链接或带水印版本时，才使用原始媒体地址。

5. 控制输出方式。
   返回量较大的接口优先使用 `--out` 落文件。
   需要批量导出时优先使用 `export_notes.py`。
   需要更稳妥的抓取时，保留 `fetch_note_texts.py` 的节流与重试参数。

## 关键资源

- `references/quickstart.md`
  在需要安装、鉴权、常用命令、CLI 子命令、校验命令时打开。

- `references/troubleshooting.md`
  在遇到风控、登录失效、结果为空、接口异常、环境问题时打开。

- `scripts/xhs_auth.py`
  负责二维码登录、本地会话保存、二维码图片生成。

- `scripts/xhs_client.py`
  负责签名请求、Cookie 处理、统一 API 请求封装。

- `assets/js/`
  存放离线签名与运行所需 JS 资源。
  不要删除 `assets/js/vendor/crypto-js.js`。

## 约束

- 不要依赖原仓 `Spider_XHS` 的运行时模块。
- 不要把 Cookie、会话文件或截图泄露到聊天、日志或 Git 仓库。
- 不要把系统 Python 当成默认解释器，除非你已经确认环境兼容。
- 不要在未说明的情况下改成有水印媒体链路。

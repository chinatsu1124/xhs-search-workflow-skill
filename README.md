# xhs-search-workflow-skill

小红书工作流 Skill 仓库。  
该 Skill 基于 `Spider_XHS` 思路重构，目标是提供一个可迁移、可维护、可独立运行的搜索与导出工作流。

## 功能概览

- 笔记搜索（含筛选参数）
- 笔记正文与图片链接提取
- 图片下载与媒体导出
- 用户信息、评论、消息中心、首页推荐数据读取
- 创作者已发布作品数据读取
- 无水印图片/视频链接处理
- Excel 导出

## 仓库结构

```text
xhs-search-workflow-skill/
└── skills/
    └── xhs-search-workflow/
        ├── SKILL.md
        ├── agents/openai.yaml
        ├── scripts/
        ├── references/
        └── assets/js/
```

## 快速开始

1. 克隆仓库

```bash
git clone git@github.com:chinatsu1124/xhs-search-workflow-skill.git
cd xhs-search-workflow-skill
```

2. 初始化运行环境

```bash
skills/xhs-search-workflow/scripts/setup_env.sh
```

3. 准备 Cookie（见下文“首次使用：获取 Cookie”）

4. 先跑一个最小验证命令

```bash
skills/xhs-search-workflow/.venv/bin/python \
  skills/xhs-search-workflow/scripts/xhs_full_cli.py \
  --env-file .env --no-env-proxy homefeed-channels
```

## 首次使用：获取 Cookie

1. 在浏览器登录小红书网页端。
2. 打开开发者工具 `Network`，筛选 `Fetch/XHR`。
3. 刷新页面并选择一条业务请求，优先选择 `edith.xiaohongshu.com`。
4. 从 `Request Headers` 复制完整 `cookie` 字段。
5. 保存到项目根目录 `.env` 文件：

```env
COOKIES="完整cookie字符串"
```

说明：
- 其他域名请求也可用，但建议至少包含 `a1`、`web_session`、`gid`。
- 若返回“登录已过期”或“无登录信息”，重新登录并重新抓取 Cookie。

安全建议：
- 不要在聊天、截图或 Git 仓库里泄露 Cookie。
- 确保 `.env` 已加入 `.gitignore`。

## 常用命令

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

3. 统一 CLI：搜索用户

```bash
skills/xhs-search-workflow/.venv/bin/python \
  skills/xhs-search-workflow/scripts/xhs_full_cli.py \
  --env-file .env --no-env-proxy search-users --query "汇丰银行" --num 10
```

4. 导出 Excel + 媒体

```bash
skills/xhs-search-workflow/.venv/bin/python \
  skills/xhs-search-workflow/scripts/export_notes.py \
  --query "汇丰银行" --num 10 --save all \
  --excel xhs_notes.xlsx --media-dir xhs_media --no-env-proxy
```

## 校验

```bash
skills/xhs-search-workflow/.venv/bin/python \
  "$CODEX_HOME/skills/.system/skill-creator/scripts/quick_validate.py" \
  skills/xhs-search-workflow
```

## 参考库

- `Spider_XHS`：https://github.com/cv-cat/Spider_XHS

## 免责声明

本仓库仅用于学习与技术研究。请遵守平台规则与当地法律法规，勿用于未授权的数据采集或其他违规用途。

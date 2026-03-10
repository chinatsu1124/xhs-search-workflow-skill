# xhs-search-workflow-skill

小红书工作流 Skill 仓库。  
该 Skill 基于 `Spider_XHS` 思路重构，目标是提供一个可迁移、可维护、可独立运行的搜索与导出工作流。

## 功能概览

- 笔记搜索（含筛选参数）
- 笔记正文与图片链接提取
- 图片下载与媒体导出
- 纯请求二维码登录与本地会话保存
- 匿名态 cookie 本地 bootstrap（自动生成 `a1` / `webId` 等基础参数）
- 用户信息、评论、消息中心、首页推荐数据读取
- 创作者已发布作品数据读取
- 无水印图片/视频链接处理
- 下载图片、视频、媒体时默认优先走无水印链路
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

3. 可直接运行二维码登录（新环境无需手动准备 `a1`，Skill 会自动 bootstrap 匿名态 Cookie），或按下文手动准备 Cookie

4. 先跑一个最小验证命令

```bash
skills/xhs-search-workflow/.venv/bin/python \
  skills/xhs-search-workflow/scripts/xhs_full_cli.py \
  --env-file .env --no-env-proxy homefeed-channels
```

也可以直接二维码登录并保存本地会话：

```bash
skills/xhs-search-workflow/.venv/bin/python \
  skills/xhs-search-workflow/scripts/xhs_full_cli.py login
```

说明：
- 当前登录实现为 **纯请求二维码登录**，不是浏览器模拟整链登录。
- 首次在新环境执行 `login` 时，Skill 会先本地生成匿名态 Cookie（包括 `a1`、`webId`、`loadts`、`xsecappid` 等），然后再调用二维码登录相关接口。

## 首次使用：获取 Cookie（可选）

如果你已经有浏览器里的有效登录 Cookie，也可以直接使用：

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
- 若返回“登录已过期”或“无登录信息”，重新登录并重新抓取 Cookie，或重新执行 `login`。

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

2. 提取笔记正文与无水印图片链接

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

4. 导出 Excel + 媒体（默认优先下载无水印图片/视频）

```bash
skills/xhs-search-workflow/.venv/bin/python \
  skills/xhs-search-workflow/scripts/export_notes.py \
  --query "汇丰银行" --num 10 --save all \
  --excel xhs_notes.xlsx --media-dir xhs_media --no-env-proxy
```

5. 查看/清理已保存登录态

```bash
skills/xhs-search-workflow/.venv/bin/python \
  skills/xhs-search-workflow/scripts/xhs_full_cli.py status

skills/xhs-search-workflow/.venv/bin/python \
  skills/xhs-search-workflow/scripts/xhs_full_cli.py logout
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

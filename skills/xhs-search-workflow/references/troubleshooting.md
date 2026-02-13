# XHS Search Troubleshooting

## 1) uv cache permission denied
- Symptom: `Failed to initialize cache at /home/.../.cache/uv ... Permission denied`
- Fix: run with elevated permissions in restricted sandboxes, or use a writable local environment.

## 2) npm install fails with localhost proxy
- Symptom: `connect EPERM 127.0.0.1:10808`
- Fix:
  - `env -u HTTP_PROXY -u HTTPS_PROXY -u http_proxy -u https_proxy npm --prefix skills/xhs-search-workflow/assets/js install`

## 3) npm registry DNS blocked
- Symptom: `EAI_AGAIN registry.npmjs.org` or other DNS lookup failures during `npm install`.
- Fix:
  - Prefer offline file: put `crypto-js.js` into `skills/xhs-search-workflow/assets/js/vendor/`.
  - Re-run `skills/xhs-search-workflow/scripts/setup_env.sh`.

## 4) system python not found
- Symptom: `python: command not found`.
- Fix:
  - Use skill venv interpreter directly: `skills/xhs-search-workflow/.venv/bin/python ...`.

## 5) Python requests still uses proxy
- Symptom: `ProxyError ... 127.0.0.1:10808`
- Fix: add `--no-env-proxy` to script commands.

## 6) DNS resolution fails
- Symptom: `NameResolutionError ... edith.xiaohongshu.com`
- Fix: run in a network-enabled environment.

## 7) Cookie auth failed
- Symptoms: `success=false`, risk/login errors, or empty result.
- Fix:
  - Re-copy full logged-in cookie.
  - Ensure `a1`, `web_session`, `gid` exist.

## 8) JS dependency missing
- Symptom: `Cannot find module 'crypto-js'`
- Fix:
  - Ensure `skills/xhs-search-workflow/assets/js/vendor/crypto-js.js` exists.
  - Or fallback: `npm --prefix skills/xhs-search-workflow/assets/js install`.

## 9) validation script permission denied
- Symptom: `.../quick_validate.py: Permission denied`.
- Fix:
  - Run via Python instead of direct execute:
  - `skills/xhs-search-workflow/.venv/bin/python "$CODEX_HOME/skills/.system/skill-creator/scripts/quick_validate.py" skills/xhs-search-workflow`

## 10) missing yaml module while validating
- Symptom: `ModuleNotFoundError: No module named 'yaml'`.
- Fix:
  - `uv pip install --python skills/xhs-search-workflow/.venv/bin/python pyyaml`

## 11) missing openpyxl on export
- Symptom: `ModuleNotFoundError: No module named 'openpyxl'` when using `export_notes.py`.
- Fix:
  - Re-run setup script, or install manually:
  - `uv pip install --python skills/xhs-search-workflow/.venv/bin/python openpyxl`

## 12) Image download failed
- Symptom: `download_error` in `fetch_note_texts.py` output.
- Fix:
  - Refresh URLs by refetching note data.
  - Use `--no-env-proxy`.
  - Use writable `--image-dir`.

## 13) Comments/user list returns empty
- Cause: target user/note is private, or cookie account has no permission.
- Fix: verify with web UI under same account and refresh cookie.

## 14) Creator endpoint fails
- Symptom: `creator-posted` returns auth/permission errors.
- Cause: cookie not from creator-center-capable account/session.
- Fix: re-login creator center and update cookie.

## 15) Export media is partial
- Cause: some CDN resources expire or block hotlinking.
- Fix: re-run export soon after fetching; use retry by re-running script.

## 16) `xhs_full_cli.py` says unrecognized arguments
- Symptom: `error: unrecognized arguments: --env-file ...` when options are placed after subcommand.
- Fix:
  - Put global options before subcommand:
  - `skills/xhs-search-workflow/.venv/bin/python skills/xhs-search-workflow/scripts/xhs_full_cli.py --env-file .env --no-env-proxy search-users --query "汇丰银行" --num 5`

## 17) `user-posts` fails for old user URL token
- Symptom: `NoneType` errors or empty/failed user post result for previously saved `user_url`.
- Cause: `xsec_token` in `user_url` may expire.
- Fix:
  - Refresh user URL from a fresh search result and retry.
  - Validate with same cookie account in web UI.

## 18) `no-water-video` returns `og:video not found`
- Cause: target note is image note/non-video, or page metadata changed.
- Fix:
  - Retry with a confirmed video note ID.
  - Fallback to `note-info` and inspect `note_card.video` fields when available.

## 19) Message endpoints output is too large
- Symptom: terminal flooded by `messages-mentions/messages-likes/messages-connections`.
- Fix:
  - Use output file:
  - `.../xhs_full_cli.py --env-file .env --out /tmp/messages.json messages-mentions`

## 20) JS parser fails on `Expected ident`
- Symptom: Node/execjs throws syntax error around `Ιnfinity` / `Ιnk`.
- Cause: non-ASCII confusable characters in identifier names.
- Fix:
  - Use ASCII identifiers only (`Infinity` / `Ink`).
  - Verify with: `node -c skills/xhs-search-workflow/assets/js/xhs_xs_xsc_56.js`

## 21) `Cannot find module './static/xhs_xray_pack1.js'`
- Cause: runtime cwd/path differs and relative `./static/*` is missing.
- Fix:
  - Run setup script to sync static packs:
  - `skills/xhs-search-workflow/scripts/setup_env.sh`
  - `xhs_client.py` also auto-creates `assets/js/static/` with required pack files.

## 22) Windows console `UnicodeEncodeError` (GBK)
- Symptom: printing JSON with non-ASCII fails in PowerShell/CMD.
- Fix:
  - Set UTF-8 before running:
  - PowerShell: `$env:PYTHONUTF8='1'; $env:PYTHONIOENCODING='utf-8'`
  - CMD: `set PYTHONUTF8=1 && set PYTHONIOENCODING=utf-8`

## 23) PowerShell fails on `python - <<'PY'`
- Symptom: heredoc syntax error in Windows PowerShell.
- Fix:
  - Use temp file execution instead:
  - `Set-Content tmp.py 'print(\"ok\")'; python tmp.py; Remove-Item tmp.py`

## 24) Batch note fetch hangs or triggers risk-control
- Fix:
  - Use serial mode with built-in throttling/retry:
  - `.../fetch_note_texts.py --timeout 30 --retries 2 --min-interval 4 --max-interval 7`
  - Suggested range in unstable networks: timeout 25-40s, interval 4-7s.

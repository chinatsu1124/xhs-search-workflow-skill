#!/usr/bin/env bash
set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
SKILL_DIR="$(cd "$SCRIPT_DIR/.." && pwd)"
JS_DIR="$SKILL_DIR/assets/js"
VENDOR_CRYPTO="$JS_DIR/vendor/crypto-js.js"
STATIC_DIR="$JS_DIR/static"

cd "$SKILL_DIR"

echo "[1/3] create skill venv"
uv venv .venv

echo "[2/3] install python deps"
uv pip install --python .venv/bin/python requests pyexecjs python-dotenv openpyxl

echo "[3/3] verify bundled crypto-js"
if [[ -f "$VENDOR_CRYPTO" ]]; then
  echo "bundled crypto-js found: $VENDOR_CRYPTO"
else
  echo "bundled crypto-js not found, trying npm install fallback"
  if npm --prefix "$JS_DIR" install; then
    echo "npm install completed"
  else
    echo "npm install failed, retrying without proxy env vars"
    env -u HTTP_PROXY -u HTTPS_PROXY -u http_proxy -u https_proxy npm --prefix "$JS_DIR" install
  fi
fi

mkdir -p "$STATIC_DIR"
cp -f "$JS_DIR/xhs_xray_pack1.js" "$STATIC_DIR/xhs_xray_pack1.js"
cp -f "$JS_DIR/xhs_xray_pack2.js" "$STATIC_DIR/xhs_xray_pack2.js"
echo "xray packs synced to: $STATIC_DIR"

echo "skill environment setup complete"
echo "run with: $SKILL_DIR/.venv/bin/python $SCRIPT_DIR/search_notes.py \"关键词\" --cookie \"...\""
echo "windows tip: set PYTHONUTF8=1 and PYTHONIOENCODING=utf-8 before running scripts"

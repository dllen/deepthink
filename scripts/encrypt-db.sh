#!/bin/bash
# 加密本地明文数据库，生成可提交的 web_content.db.enc
set -euo pipefail

DB_FILE="python_scripts/web_content.db"
ENC_FILE="python_scripts/web_content.db.enc"

if [ -z "${SQLITE_KEY:-}" ]; then
  echo "Error: SQLITE_KEY environment variable is not set." >&2
  echo "Usage: export SQLITE_KEY='your_secret_key' && ./scripts/encrypt-db.sh" >&2
  exit 1
fi

if [ ! -f "$DB_FILE" ]; then
  echo "Error: $DB_FILE not found." >&2
  exit 1
fi

# 先写到临时文件：加密失败时不会破坏现有的 .enc。
TMP_FILE="${ENC_FILE}.tmp"
cleanup() {
  rm -f "$TMP_FILE"
}
trap cleanup EXIT

echo "Encrypting $DB_FILE -> $ENC_FILE ..."
openssl enc -aes-256-cbc -salt -pbkdf2 -iter 200000 \
  -in "$DB_FILE" -out "$TMP_FILE" -pass env:SQLITE_KEY

mv "$TMP_FILE" "$ENC_FILE"
trap - EXIT

echo "Encryption successful: $ENC_FILE"
echo "提交 ${ENC_FILE}；不要提交明文 ${DB_FILE}（已在 .gitignore 中）。"

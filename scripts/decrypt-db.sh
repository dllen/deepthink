#!/bin/bash
# 从加密副本恢复明文数据库（本地或 CI）
set -euo pipefail

DB_FILE="python_scripts/web_content.db"
ENC_FILE="python_scripts/web_content.db.enc"

if [ -z "${SQLITE_KEY:-}" ]; then
  echo "Error: SQLITE_KEY environment variable is not set." >&2
  exit 1
fi

if [ ! -f "$ENC_FILE" ]; then
  echo "Error: $ENC_FILE not found." >&2
  exit 1
fi

if [ -f "$DB_FILE" ]; then
  echo "Overwriting existing $DB_FILE"
fi

openssl enc -d -aes-256-cbc -salt -pbkdf2 -iter 200000 \
  -in "$ENC_FILE" -out "$DB_FILE" -pass env:SQLITE_KEY

echo "Decrypted: $DB_FILE"

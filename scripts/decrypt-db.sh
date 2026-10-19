#!/bin/bash
# 从加密副本恢复明文数据库（本地或 CI）
set -euo pipefail

DB_FILE="python_scripts/web_content.db"
ENC_FILE="python_scripts/web_content.db.enc"
SQLITE_MAGIC="SQLite format 3"

if [ -z "${SQLITE_KEY:-}" ]; then
  echo "Error: SQLITE_KEY environment variable is not set." >&2
  exit 1
fi

if [ ! -f "$ENC_FILE" ]; then
  echo "Error: $ENC_FILE not found." >&2
  exit 1
fi

# 先解到同目录的临时文件：错误的 key 只会产出乱码，不能覆盖现有明文。
TMP_FILE="$(mktemp "${DB_FILE}.tmp.XXXXXX")"
cleanup() {
  rm -f "$TMP_FILE"
}
trap cleanup EXIT

openssl enc -d -aes-256-cbc -salt -pbkdf2 -iter 200000 \
  -in "$ENC_FILE" -out "$TMP_FILE" -pass env:SQLITE_KEY

# 校验解密结果是 SQLite 数据库（第 16 字节是 NUL，比较时去掉）。
HEADER="$(head -c 16 "$TMP_FILE" | tr -d '\000')"
if [ "$HEADER" != "$SQLITE_MAGIC" ]; then
  echo "Error: decrypted data is not a SQLite database (wrong SQLITE_KEY?)." >&2
  echo "Existing $DB_FILE left untouched." >&2
  exit 1
fi

if [ -f "$DB_FILE" ]; then
  echo "Overwriting existing $DB_FILE"
fi
mv "$TMP_FILE" "$DB_FILE"
trap - EXIT

echo "Decrypted: $DB_FILE"

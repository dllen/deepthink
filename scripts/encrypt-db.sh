#!/bin/bash

# HELPER SCRIPT TO ENCRYPT THE DATABASE

DB_FILE="python_scripts/web_content.db"
ENC_FILE="python_scripts/web_content.db.enc"

if [ -z "$SQLITE_KEY" ]; then
  echo "Error: SQLITE_KEY environment variable is not set."
  echo "Usage: export SQLITE_KEY='your_secret_key' && ./scripts/encrypt-db.sh"
  exit 1
fi

if [ ! -f "$DB_FILE" ]; then
  echo "Error: Database file $DB_FILE not found."
  exit 1
fi

echo "Encrypting $DB_FILE..."
openssl aes-256-cbc -salt -pbkdf2 -in "$DB_FILE" -out "$ENC_FILE" -k "$SQLITE_KEY"

if [ $? -eq 0 ]; then
  echo "Encryption successful. Created $ENC_FILE"
else
  echo "Encryption failed."
  exit 1
fi

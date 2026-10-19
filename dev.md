# Developer Guide

## Database Content Security

### Current state

- `python_scripts/web_content.db`（明文 SQLite）是本地工作副本。它被 `.gitignore` 的 `*.db` 忽略，**不再被 git 跟踪**；内容仍以同样的表结构存在，只是不进入版本库。
- `python_scripts/web_content.db.enc` 被 git 跟踪，是**仓库中唯一的数据副本**。它由 `scripts/encrypt-db.sh` 用 `SQLITE_KEY` 加密生成，必须在每次修改 DB 后重新生成并提交。
- CI 在 `test:data` / `check:data` 前运行 `scripts/decrypt-db.sh`，用仓库 secret `SQLITE_KEY` 从 `.enc` 还原明文（只在 runner 上存在，不进版本库）。
- build/deploy 不重新生成数据：直接部署提交的 `static-data.json` / `static-data.js`。
- 明文的全部内容**已经存在于历史提交中**（仓库曾公开跟踪明文 DB）。这是已评估并接受的风险：不重写 Git 历史；如需彻底清除，只能重写历史并强制推送。
- `SQLITE_KEY` 只存在于本地 `.env` 和 GitHub Actions secret 中，仓库和 CI 日志都不应出现它的值。

### Local Development Setup

1. Copy the example file and fill in your keys:

   ```bash
   cp .env.example .env
   chmod 600 .env
   ```

   ```ini
   SQLITE_KEY=your_secret_password_here
   DEEPSEEK_API_KEY=your_deepseek_api_key
   ```

   `SQLITE_KEY` is used to encrypt/decrypt the database; keep it identical to the CI secret. `DEEPSEEK_API_KEY` is used by scraping and category classification. `.env` is ignored by git.

2. Restore the plaintext database (fresh clone, or after deleting it):

   ```bash
   # 脚本只读取环境变量，不会自动加载 .env
   set -a; . ./.env; set +a
   ./scripts/decrypt-db.sh
   ```

   The script decrypts to a temporary file and verifies the `SQLite format 3` header before replacing `web_content.db`, so a wrong `SQLITE_KEY` cannot clobber an existing plaintext DB.

3. Install dependencies exactly as CI does:

   ```bash
   npm ci
   ```

### Daily / weekly workflow

```bash
# after scraping/updating the plaintext DB
npm run gen:static-js
npm run check:data

# re-encrypt and commit the encrypted copy (never the plaintext)
export SQLITE_KEY=...
./scripts/encrypt-db.sh
git add python_scripts/web_content.db.enc src/assets/static-data.json src/assets/static-data.js
```

`git status` should never list `python_scripts/web_content.db` as tracked/staged.

### Encrypting the Database

```bash
export SQLITE_KEY=...
./scripts/encrypt-db.sh
```

This rewrites `python_scripts/web_content.db.enc` from the plaintext DB. Commit the updated `.enc`; the plaintext stays local and ignored.

### Key loss and recovery

- If `SQLITE_KEY` is lost and no plaintext copy survives anywhere, `web_content.db.enc` **cannot be decrypted** — treat the key as part of the data. Keep a password-manager entry and an offline backup of both the key and the plaintext DB.
- If the key is available, restore locally with `./scripts/decrypt-db.sh`; CI restores automatically from the `SQLITE_KEY` secret.
- If the key is lost but a plaintext DB still exists locally, generate a new `.enc` with a new key (`./scripts/encrypt-db.sh`), then update the `SQLITE_KEY` secret in GitHub before pushing.

Configure the CI secret at: repository **Settings → Secrets and variables → Actions → New repository secret**, name `SQLITE_KEY`, value identical to local `.env`.

### GitHub Actions

`deploy.yml` installs with `npm ci` (committed `package-lock.json`), decrypts the database with the `SQLITE_KEY` secret, then runs `npm run test:data`, `npm run check:data`, and `npm run build` before deploying the committed static data artifacts. Third-party actions are pinned to commit SHAs and the workflow declares `permissions: contents: write`.

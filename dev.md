# Developer Guide

## Database Content Security

> ⚠️ 现状说明（2026-10-18）：`python_scripts/web_content.db` 目前是**明文且被 git 跟踪**的，`dev.md` 旧版声称的“明文被忽略、CI 解密数据库”与事实不符。仓库为 public，明文 DB 的全部内容已随历史公开；明文 DB 与加密策略的调整见后续安全治理工作项。

### Current state

- `python_scripts/web_content.db`（明文）被 git 跟踪，是站点数据的唯一真源。
- `python_scripts/web_content.db.enc` 也被 git 跟踪。它由 `scripts/encrypt-db.sh` 生成，但站点构建和 CI 都不读取它。
- CI 不解密数据库：`check:data` 用 sql.js 直接读取仓库中的明文 DB，校验 `static-data.json` / `static-data.js` 与 DB 一致；build/deploy 不重新生成数据。
- `SQLITE_KEY` 只在本地运行 `scripts/encrypt-db.sh` 时需要，不是部署所需的 secret。

### Local Development Setup

1. Copy the example file:

   ```bash
   cp .env.example .env
   ```

2. Edit `.env` and fill in your keys:

   ```ini
   SQLITE_KEY=your_secret_password_here
   DEEPSEEK_API_KEY=your_deepseek_api_key
   ```

   `SQLITE_KEY` is only used by the optional encryption script below. `DEEPSEEK_API_KEY` is used by scraping and category classification.

   *Note: The `.env` file is ignored by git, so your secrets remain safe locally.*

### Encrypting the Database (optional)

```bash
./scripts/encrypt-db.sh
```

This writes `python_scripts/web_content.db.enc`. It does **not** remove the plaintext `web_content.db` from git, and no build or CI step consumes the `.enc` file. Treat it as an ad-hoc encrypted copy, not as leak protection.

### GitHub Actions

The current `deploy.yml` workflow does not decrypt the database and does not need a `SQLITE_KEY` repository secret. It runs `npm run test:data`, `npm run check:data`, then `npm run build`, and deploys the committed static data artifacts directly.

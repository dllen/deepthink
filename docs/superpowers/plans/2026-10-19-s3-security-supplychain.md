# S3 安全与供应链 Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** 明文数据库不再进入仓库，仓库只保留加密副本；依赖可复现、Actions 固定到 SHA。

**Architecture:** 本地明文 DB 继续作为工作副本（gitignored）；每次内容更新后重新加密并提交 `.enc`；CI 用 `SQLITE_KEY` secret 解密后跑 `check:data`。依赖用公网 registry 生成的 lockfile + `npm ci`；Actions 固定 SHA 并声明 `contents: write`。

**Spec:** `docs/superpowers/specs/2026-10-19-s3-security-supplychain-design.md`

---

## Task 1: 加解密脚本

**Files:**
- Modify: `scripts/encrypt-db.sh`
- Create: `scripts/decrypt-db.sh`

- [ ] **Step 1: 重写 encrypt-db.sh**

```bash
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

echo "Encrypting $DB_FILE -> $ENC_FILE ..."
openssl enc -aes-256-cbc -salt -pbkdf2 -iter 200000 \
  -in "$DB_FILE" -out "$ENC_FILE" -pass env:SQLITE_KEY

echo "Encryption successful: $ENC_FILE"
echo "提交 $ENC_FILE；不要提交明文 $DB_FILE（已在 .gitignore 中）。"
```

- [ ] **Step 2: 新增 decrypt-db.sh**

```bash
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
```

- [ ] **Step 3: 赋可执行权限并做往返验证**

```bash
chmod +x scripts/encrypt-db.sh scripts/decrypt-db.sh
cp python_scripts/web_content.db /tmp/web_content.before.db
export SQLITE_KEY="$(grep '^SQLITE_KEY=' .env | cut -d= -f2-)"
./scripts/encrypt-db.sh
./scripts/decrypt-db.sh
shasum -a 256 /tmp/web_content.before.db python_scripts/web_content.db
```

Expected：两个 sha256 完全一致；无 key 时脚本以非零退出并给出提示。

- [ ] **Step 4: 提交**

```bash
git add scripts/encrypt-db.sh scripts/decrypt-db.sh
git commit -m "feat(security): add key-safe encrypt/decrypt scripts"
```

---

## Task 2: 重新生成加密副本并停止跟踪明文

**Files:**
- Modify: `python_scripts/web_content.db.enc`（重新生成，提交）
- Delete tracking: `python_scripts/web_content.db`（保留本地文件）
- Modify: `.gitignore`

- [ ] **Step 1: 重新生成 .enc（已在 Task 1 生成，确认非空且大小合理）**

```bash
ls -l python_scripts/web_content.db.enc
```

Expected：文件 > 1MB。

- [ ] **Step 2: 停止跟踪明文**

```bash
git rm --cached python_scripts/web_content.db
test -f python_scripts/web_content.db && echo "local plaintext kept"
```

- [ ] **Step 3: .gitignore 注释更新**

在 `# Database files` 段改为：

```gitignore
# Database files
# NOTE: the plaintext python_scripts/web_content.db is intentionally NOT tracked.
# Only the encrypted copy (web_content.db.enc) is committed; CI decrypts it with
# the SQLITE_KEY secret. Local dev keeps the plaintext, ignored by *.db below.
*.db
*.sqlite
*.sqlite3
```

- [ ] **Step 4: 验证**

```bash
git ls-files python_scripts/web_content.db | wc -l   # 期望 0
git ls-files python_scripts/web_content.db.enc       # 期望一行
npm run check:data                                   # 本地明文仍可读，224 条
```

- [ ] **Step 5: 提交**

```bash
git add .gitignore python_scripts/web_content.db.enc
git commit -m "chore(security): stop tracking plaintext database"
```

---

## Task 3: CI 解密步骤

**Files:**
- Modify: `.github/workflows/deploy.yml`

- [ ] **Step 1: 在 Install dependencies 之后插入解密步骤**

```yaml
    - name: Decrypt database
      env:
        SQLITE_KEY: ${{ secrets.SQLITE_KEY }}
      run: |
        if [ -z "$SQLITE_KEY" ]; then
          echo "::error::SQLITE_KEY secret is not set"
          exit 1
        fi
        ./scripts/decrypt-db.sh
```

放在 `Check data consistency` 之前（`test:data` 不依赖 DB，可在其前后）。

- [ ] **Step 2: YAML 校验**

```bash
python3 -c "import yaml; d=yaml.safe_load(open('.github/workflows/deploy.yml')); print([s.get('name') for s in d['jobs']['build-and-deploy']['steps']])"
```

Expected：列表包含 `Decrypt database`、`Run data rule tests`、`Check data consistency`、`Build project`。

- [ ] **Step 3: 本地模拟 CI 解密**

```bash
export SQLITE_KEY="$(grep '^SQLITE_KEY=' .env | cut -d= -f2-)"
mv python_scripts/web_content.db /tmp/web_content.saved.db
./scripts/decrypt-db.sh
npm run check:data
mv /tmp/web_content.saved.db python_scripts/web_content.db
```

Expected：check:data 224 条通过。

- [ ] **Step 4: 提交**

```bash
git add .github/workflows/deploy.yml
git commit -m "ci(security): decrypt database before validation"
```

---

## Task 4: 依赖锁文件与 npm ci

**Files:**
- Create: `package-lock.json`
- Modify: `.gitignore`
- Modify: `.github/workflows/deploy.yml`

- [ ] **Step 1: 生成公网 lockfile**

```bash
npm install --package-lock-only --registry=https://registry.npmjs.org
grep -c "corp.kuaishou" package-lock.json || true
```

Expected：内网地址计数为 0。

- [ ] **Step 2: 解除忽略并提交**

从 `.gitignore` 删除 `package-lock.json` 及上方的说明块（改成一句：lockfile 已提交，用于可复现构建）。

```bash
git add .gitignore package-lock.json
git commit -m "chore(deps): commit lockfile resolved from public registry"
```

- [ ] **Step 3: 在干净目录验证 npm ci**

```bash
rm -rf /tmp/npmci && mkdir /tmp/npmci
cp package.json package-lock.json /tmp/npmci/
cd /tmp/npmci && npm ci --ignore-scripts --registry=https://registry.npmjs.org
```

Expected：安装成功（exit 0）。若因 peer 依赖失败：

```bash
# 在仓库根新增 .npmrc：legacy-peer-deps=true
```

然后重试；`npm ci` 仍以 lockfile 为准。

- [ ] **Step 4: CI 改用 npm ci**

`deploy.yml` 的 Install 步骤：

```yaml
    - name: Install dependencies
      run: npm ci
```

- [ ] **Step 5: 提交**

```bash
git add .github/workflows/deploy.yml .npmrc 2>/dev/null || git add .github/workflows/deploy.yml
git commit -m "ci(deps): use npm ci with committed lockfile"
```

---

## Task 5: Actions 固定 SHA 与权限

**Files:**
- Modify: `.github/workflows/deploy.yml`

- [ ] **Step 1: 固定引用**

```yaml
      - uses: actions/checkout@11d5960a326750d5838078e36cf38b85af677262  # v4
      - uses: actions/setup-node@49933ea5288caeca8642d1e84afbd3f7d6820020  # v4
      - uses: peaceiris/actions-gh-pages@373f7f263a76c20808c831209c920827a82a2847  # v3
```

- [ ] **Step 2: 声明权限**

在 `on:` 同级加：

```yaml
permissions:
  contents: write
```

- [ ] **Step 3: 校验**

```bash
grep -n "uses:\|permissions:" .github/workflows/deploy.yml
python3 -c "import yaml; yaml.safe_load(open('.github/workflows/deploy.yml'))"
```

Expected：三个 uses 均为 40 位 SHA；`permissions: contents: write` 存在；YAML 合法。

- [ ] **Step 4: 提交**

```bash
git add .github/workflows/deploy.yml
git commit -m "ci(security): pin actions and declare workflow permissions"
```

---

## Task 6: 文档与最终验收

**Files:**
- Modify: `README.md`、`dev.md`、`AGENTS.md`

- [ ] **Step 1: README 周更流程补加密步骤**

在「每周更新内容」的提交步骤前加：

```
5. 重新加密并提交加密副本：`export SQLITE_KEY=... && ./scripts/encrypt-db.sh`
   （不要提交明文 `python_scripts/web_content.db`）
```

- [ ] **Step 2: dev.md**

- 更新「Current state」：明文 DB 不再跟踪，`.enc` 是仓库中唯一数据副本；
- 补 CI secret `SQLITE_KEY` 的配置方法；
- 补密钥丢失风险与本地恢复方法（`./scripts/decrypt-db.sh`）；
- 说明历史提交中的明文仍存在（已接受风险）。

- [ ] **Step 3: AGENTS.md**

Database 段：明文不跟踪、`.enc` 跟踪、CI 解密、加密命令。

- [ ] **Step 4: 全量验收**

```bash
git ls-files python_scripts/web_content.db | wc -l    # 0
git ls-files python_scripts/web_content.db.enc        # 1 行
npm run test:data && npm run check:data && npm run build && npm run lint
```

Expected：0 / 1 行；test 23、check 224、build 成功、lint 0。

- [ ] **Step 5: 提交**

```bash
git add README.md dev.md AGENTS.md
git commit -m "docs: document encrypted database workflow"
```

---

## Task 7: 推送前 secret 确认与部署验证

- [ ] **Step 1: 请用户在 GitHub 仓库 Settings → Secrets → Actions 配置 `SQLITE_KEY`（与本地 `.env` 同值）。**

- [ ] **Step 2: 确认后 push**

```bash
git push origin main
```

- [ ] **Step 3: 观察 CI**

GitHub Actions 的 `Decrypt database` 与 `check:data` 步骤必须成功；失败时查看是否 secret 未配或解密参数不一致。

- [ ] **Step 4: 生产冒烟**

```bash
curl -s -o /dev/null -w "%{http_code}\n" https://deepthink.global/
```

Expected：200；数据仍 224 条。

---

## Self-Review

- **Spec 覆盖**：§2.1 → Task 1–3；§2.2 → Task 4；§2.3 → Task 5；§2.4 → Task 6；§3 验收 → Task 6/7。
- **风险点**：lockfile 生成必须用公网 registry；`npm ci` 若 peer 失败用 `.npmrc`；推送前必须确认 secret。
- **一致性**：`encrypt-db.sh`/`decrypt-db.sh` 共用 `-iter 200000` 与 `env:SQLITE_KEY`。

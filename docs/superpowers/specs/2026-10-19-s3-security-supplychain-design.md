# S3 设计：明文数据库出库与供应链收敛

- **日期**：2026-10-19
- **状态**：已确认（用户选择 B 方案并确认完整范围）
- **依据审计**：`docs/superpowers/audits/2026-10-18/security-privacy.md`、`build-deploy-repo.md`、`frontend.md` FE-O10
- **范围**：数据库加密与跟踪策略、依赖锁定、GitHub Actions 固定与权限、密钥卫生；不含历史重写、PR 部署门禁、部署后冒烟与 `base` 问题（S4）。

## 1. 决策

| 决策 | 选择 |
|---|---|
| 明文 DB | 停止跟踪（`git rm --cached`），本地保留并由 `*.db` 忽略 |
| 加密副本 | 用当前 224 行 DB 重新生成 `web_content.db.enc` 并跟踪 |
| 加密方式 | `openssl enc -aes-256-cbc -salt -pbkdf2 -iter 200000 -pass env:SQLITE_KEY`（不再用 `-k` 进 argv） |
| CI 校验 | 新增解密步骤，把 `.enc` 解到 gitignored 的明文路径，再跑 `check:data` |
| 历史泄露 | 接受：旧明文仍在 git 历史，无法收回，写入 dev.md 说明 |
| 依赖 | 生成并提交 `package-lock.json`（公网 registry），CI 改 `npm ci` |
| Actions | 固定到 commit SHA（注释保留版本），补 `permissions: contents: write` |
| 密钥卫生 | `.env` 本地权限 600；脚本不回显 key；CI 只用 secret |
| npm audit | 不作为门禁，仅报告结果 |

## 2. 设计

### 2.1 数据库与加密

- `python_scripts/web_content.db`：
  - `git rm --cached`，本地文件保留；`.gitignore` 的 `*.db` 继续生效，并在注释中写明"明文只留本地"。
- `python_scripts/web_content.db.enc`：从当前 DB 用新参数重新生成并提交；这是仓库中唯一的数据副本。
- `scripts/encrypt-db.sh`：`set -euo pipefail`，要求 `SQLITE_KEY` 非空，用 `-pass env:SQLITE_KEY`，`-iter 200000`，输出后打印"记得提交 .enc，勿提交明文"。
- 新增 `scripts/decrypt-db.sh`：同样从环境读 key，解密到 `python_scripts/web_content.db`（已存在时先备份到 `/tmp` 或直接覆盖并提示），用于本地/CI 恢复明文。
- CI（`.github/workflows/deploy.yml`）：在 `Install dependencies` 后、`test:data` 前插入：

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

- 本地周更流程（README/dev.md）：改 DB → `npm run gen:static-js` → `./scripts/encrypt-db.sh` → 提交生成物 + `.enc`；明文始终不入库。

### 2.2 依赖锁定

- `npm install --package-lock-only --registry=https://registry.npmjs.org` 生成 `package-lock.json`；检查无内网 registry URL。
- 从 `.gitignore` 删除 `package-lock.json` 忽略块，提交 lockfile。
- CI：`npm install --legacy-peer-deps` → `npm ci`；若 peer 冲突导致 `npm ci` 失败，则加 `.npmrc`（`legacy-peer-deps=true`）并重试，二者都记录在文档。
- 验证：在临时目录用 `package.json + lockfile` 跑 `npm ci --ignore-scripts`，确认可解析、无内网地址。

### 2.3 Actions 固定与权限

- `actions/checkout` → `11d5960a326750d5838078e36cf38b85af677262`（v4）
- `actions/setup-node` → `49933ea5288caeca8642d1e84afbd3f7d6820020`（v4）
- `peaceiris/actions-gh-pages` → `373f7f263a76c20808c831209c920827a82a2847`（v3）
- workflow 顶层加 `permissions: contents: write`（部署需要推 gh-pages）。
- 不改 PR 触发条件与部署 `if`（S4）。

### 2.4 密钥卫生

- 本地 `.env` 权限改 600（仅提示用户/执行，不入库）；`.env.example` 保持无值。
- 加密/解密脚本不打印 key；CI 不 echo secret。
- `dev.md` 补：如何生成 `.enc`、CI secret 配置、密钥丢失风险。

## 3. 验收

- `git ls-files python_scripts/web_content.db` 为空；`.enc` 在跟踪中。
- 加解密往返：明文 sha256 = 解密后 sha256；在解密副本上 `npm run check:data` 通过（224 条）。
- 本地 `npm run gen:static-js`、`npm run test:data`、`npm run build`、`npm run lint` 全过。
- `npm ci` 在干净目录成功；lockfile 不含内网 registry。
- workflow YAML 合法；Actions 引用为 SHA；`permissions` 存在。
- CI（用户配置 secret 后）：`Decrypt database` 成功，`check:data` 通过，部署成功；生产仍 224 条。

## 4. 风险

| 风险 | 缓解 |
|---|---|
| 用户未配 `SQLITE_KEY` secret → CI 红 | 推送前必须由用户确认已配置；失败时 workflow 明确报错 |
| 密钥丢失 → `.enc` 不可用 | 本地明文仍在；历史明文也可恢复；文档提示备份 key |
| `npm ci` 因 peer 冲突失败 | 退回 `.npmrc legacy-peer-deps=true`；仍失败则保留 `npm install` 并记录 |
| lockfile 写入内网地址 | 生成时强制公网 registry，提交前 grep 校验 |
| 历史明文无法收回 | 已知并接受，文档写明 |
| LibreSSL `-iter` 兼容性 | 本机已验证；CI ubuntu OpenSSL 3 支持 |

## 5. 不在范围

- 历史重写（C 方案）。
- PR 部署门禁、并发/超时、部署后冒烟、`base` 与 Pages 项目别名（S4）。
- npm audit 门禁、依赖升级。
- 内容清理。

## 6. 文件清单

修改：

- `.gitignore`、`scripts/encrypt-db.sh`、`.github/workflows/deploy.yml`、`dev.md`、`README.md`、`AGENTS.md`（如涉及）
- `python_scripts/web_content.db.enc`（重新生成）
- 删除跟踪：`python_scripts/web_content.db`

新增：

- `scripts/decrypt-db.sh`
- `package-lock.json`（生成后提交）
- `.npmrc`（仅当 `npm ci` 需要 legacy-peer-deps）

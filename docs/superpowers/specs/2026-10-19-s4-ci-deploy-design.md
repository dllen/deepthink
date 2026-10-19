# S4 设计：CI 与部署可靠性

- **日期**：2026-10-19
- **状态**：已确认（用户选择"只支持自定义域"与完整方案）
- **依据审计**：`docs/superpowers/audits/2026-10-18/build-deploy-repo.md`
- **生产入口**：`https://deepthink.global`（根路径）。GitHub Pages 项目别名 `dllen.github.io/deepthink/` 不支持，`base` 保持默认。

## 1. 决策

| 决策 | 选择 |
|---|---|
| PR 触发 | 只跑 install/decrypt/test/check/build，不部署 |
| 部署条件 | `push` 到 `main` 或手动 `workflow_dispatch` |
| 并发 | `concurrency: pages-deploy` + `cancel-in-progress: true` |
| 超时 | job `timeout-minutes: 10` |
| 部署后冒烟 | 断言生产 200 + content-type + asset 名与本次构建一致 + `/logo.svg` |
| fork PR 无 secret | decrypt 跳过、`check:data` 跳过（warning），不使 PR 必红 |
| 生产 404 语义 | Cloudflare 对未知路径返回 200+index，冒烟必须比对 asset，不能只看状态码 |
| base / Pages 别名 | 不改，文档明确不支持 |

## 2. 设计

### 2.1 工作流结构

```yaml
on:
  push:
    branches: [main]
  pull_request:
    branches: [main]
  workflow_dispatch:

permissions:
  contents: write

concurrency:
  group: pages-deploy
  cancel-in-progress: true

jobs:
  build-and-deploy:
    runs-on: ubuntu-latest
    timeout-minutes: 10
    steps:
      - checkout / setup-node / npm ci
      - Decrypt database      # secret 缺失时 warning + skip check
      - test:data
      - check:data            # 条件：decrypt 未跳过
      - build
      - Deploy to GitHub Pages  # 条件：push main 或 workflow_dispatch
      - Smoke test production   # 条件同上，带重试
```

### 2.2 冒烟逻辑

部署后执行（`set -euo pipefail`）：

1. `EXPECTED=$(grep -o 'assets/index-[^"]*\.js' dist/index.html | head -1)`
2. 最多重试 6 次、每次间隔 10s：
   - `curl -fsS -D headers -o body https://deepthink.global/`
   - 断言 HTTP 200，`content-type` 含 `text/html`
   - `ACTUAL=$(grep -o 'assets/index-[^"]*\.js' body | head -1)`
   - 若 `ACTUAL == EXPECTED` 则继续，否则 sleep 重试
3. 请求 `https://deepthink.global/$ACTUAL`，断言 200 且 `content-type` 含 `javascript`
4. 请求 `https://deepthink.global/logo.svg`，断言 200 且 `content-type` 含 `image/svg+xml`
5. 任一失败输出诊断（状态码、content-type、期望/实际 asset）并退出 1

### 2.3 fork PR 处理

Decrypt 步骤：

```yaml
    - name: Decrypt database
      id: decrypt
      env:
        SQLITE_KEY: ${{ secrets.SQLITE_KEY }}
      run: |
        if [ -z "$SQLITE_KEY" ]; then
          echo "::warning::SQLITE_KEY not available (fork PR?) — skipping database checks"
          echo "skipped=true" >> "$GITHUB_OUTPUT"
          exit 0
        fi
        ./scripts/decrypt-db.sh
```

`check:data` 步骤加 `if: steps.decrypt.outputs.skipped != 'true'`。

### 2.4 部署条件

```yaml
    - name: Deploy to GitHub Pages
      if: github.event_name == 'workflow_dispatch' || (github.event_name == 'push' && github.ref == 'refs/heads/main')
      ...
```

### 2.5 文档

- README：部署章节写明生产入口、PR 只校验不部署、冒烟内容、手动回滚步骤、Pages 项目别名不支持。
- dev.md：同上，补 `workflow_dispatch` 手动发布。
- CLAUDE.md/AGENTS.md：Git Workflow 段落同步"PR 不部署"。

### 2.6 回滚

- 应用回滚：`git revert <bad-commit> && git push`，CI 重新构建部署。
- 产物回滚：把 `gh-pages` 指回上一个 `deploy:` commit（`git push --force-with-lease origin <deploy-sha>:gh-pages`），文档记录但不建议日常使用。

## 3. 验收

- YAML 合法；三个 action 仍为固定 SHA。
- PR 事件下 `Deploy` 与 `Smoke` 被 `if` 跳过；push main 下执行。
- 本次推送后 CI 成功：deploy + smoke 全绿；生产 `https://deepthink.global/` 200，asset 与构建一致，`/logo.svg` 200。
- 文档更新完成。

## 4. 风险

| 风险 | 缓解 |
|---|---|
| Cloudflare 缓存/延迟导致冒烟短暂失败 | 6 次 × 10s 重试 + 明确诊断输出 |
| Actions 出口访问自定义域被拦 | 失败时输出状态码/content-type；必要时改为只校验 gh-pages 产物 |
| fork PR 跳过数据校验 | 输出 warning；同仓 PR 正常校验 |
| `workflow_dispatch` 手动触发可能重复部署 | 属预期，可手动使用 |

## 5. 不在范围

- `base` 与 Pages 项目别名、Cloudflare 配置。
- 内容清理。
- 历史明文。

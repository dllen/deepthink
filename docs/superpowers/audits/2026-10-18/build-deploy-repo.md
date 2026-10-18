# 构建 / CI / 部署 / 仓库卫生审计

- **审计日期**：2026-10-18（Asia/Shanghai）
- **审计人**：Relay（DevOps Engineer）
- **审计模式**：**只读**。未执行 `npm install` / `npm run build` / `npm run gen:static-js`，未修改代码、配置、数据或提交；唯一写入是本报告。执行了 `git fetch origin --prune`（只更新 remote-ref，不改工作区）。
- **审计对象**：仓库 `dllen/deepthink`（public），生产域名 `https://deepthink.global/`，GitHub Pages 产物分支 `gh-pages`。
- **基准提交**：审计开始时工作区 `main = 22544ca`（与 `origin/main` 无共同祖先）；审计过程中另一成员将工作区 reset 到 `origin/main = 997cd99`（旧线保留为 `backup/local-main-2026-10-18`），故本报告以 **`997cd99`（当前 HEAD、线上对应版本）** 为基准，跨线差异单独标注。
- **同批审计（交叉引用，不重复其深挖）**：`data-pipeline.md`（Pipeline，数据链路）、`security-privacy.md`（Aegis，密钥/DB 加密，H-1）、`testing-quality.md`（Sentinel，测试门禁）、`docs-accuracy.md`（Scribe，文档漂移）。

---

## 0. 结论摘要（TL;DR）

**流水线本身是绿的（31/31 次部署成功，端到端 ~50s），但它证明不了“生产已经更新且可用”。**

三条要点：

1. **生产链路有一层不在仓库里的 Cloudflare 代理**：`deepthink.global` 的 DNS 指向 Cloudflare（`104.21.95.168` / `172.67.146.55`），响应头 `server: cloudflare`，未知路径一律返回 `200 + index.html`（SPA 回退）。GitHub Pages 项目地址 `https://dllen.github.io/deepthink/` 反而是**白屏**（HTML 引用 `/assets/*`，但该域名根下 404）。发布链的关键一层无法 code review、无法重建、无变更记录。
2. **部署无验证**：CI 只证明 `gh-pages` push 成功；没有任何部署后冒烟。而生产 404 被伪装成 200，**只查状态码的监控会漏掉所有资源缺失**。
3. **构建不可复现、仓库有历史包袱**：无 lockfile（CI `npm install --legacy-peer-deps`，本地 Node 22 / CI Node 20，实际解析 vite 4.5.14）；明文 DB（2.68MB）与加密副本（1.42MB）同时被跟踪（加密不提供任何机密性）；`.gitignore` 与实际跟踪状态互相矛盾；本地工作副本在审计开始时与远端是**两条互不相关的历史**（75 vs 85 提交、无共同祖先）。

| 指标 | 值 | 判定 |
|---|---|---|
| 部署 workflow 运行次数 | 31（全部 `push`，全部 `success`） | 绿，但只验证到 push |
| 最近一次部署 | 2026-09-03 11:56 (+08)，`997cd99` | 45 天前 |
| 端到端部署延迟 | push 03:56:21Z → gh-pages 03:56:48Z → 线上 last-modified 03:57:10Z ≈ **49s** | 良好，可作为新鲜度目标 |
| CI job 中位耗时 | **22s** | 良好 |
| 生产 URL 可用性 | `https://deepthink.global/` → 200，`/assets/*.js|css` 200 | 可用 |
| GitHub Pages 项目 URL | `https://dllen.github.io/deepthink/` → 200 但 `/assets/*` 404 → **白屏** | 🟥 损坏别名 |
| 生产 404 语义 | 任意未知路径 → `200 text/html`（index） | 🟥 监控盲区 |
| 仓库 public / 跟踪体积 | public / 4.51MB（DB 2.68MB + enc 1.42MB 占 91%） | 关注 |
| 部署产物版本可追溯性 | `gh-pages` commit message 含源 sha；无 tag、无 build-info | 🟨 |

**发布判定**：当前线上（`997cd99`）可用（已实测），但**“CI 绿 = 生产正确”不成立**，且回滚/冒烟/依赖锁定缺失。建议按 §8 顺序整改；其中 BD-01、BD-02、BD-04、BD-09 是发布可靠性直接相关项。

---

## 1. 审计范围与方法

### 1.1 范围内

- 构建入口与可复现性：`package.json`、`vite.config.js`、`postcss/tailwind`、lockfile、Node/Python 版本策略。
- CI：`.github/workflows/deploy.yml`（43 行）全部触发条件、权限、并发、Action 版本。
- 部署：`gh-pages` 产物、GitHub Pages 项目站、生产自定义域名、Cloudflare 边缘行为、缓存/安全头。
- 仓库卫生：跟踪文件清单与体积、DB/加密副本的历史成本、`.gitignore` 契约、本地副本与远端历史关系、生成物快照。
- 运维面：健康检查/冒烟/可观测性、SLI/SLO、回滚与备份程序、资源与成本。

### 1.2 范围外

- 不跑构建、不装依赖、不生成数据（按任务要求）。
- 不读 `.env` 值（只统计键长/键名）；不使用任何密钥。
- 不访问 GitHub/Cloudflare 管理设置（未认证：`/repos/dllen/deepthink/pages` → 404；无法确认 Pages 自定义域名设置、仓库分支保护、Cloudflare 套餐与规则）。
- 不做数据库内容层审计（见 `data-pipeline.md`）、不做加密强度深挖（见 `security-privacy.md` H-1）。

### 1.3 主要证据命令（可复现）

```bash
# CI 运行历史（公开 API，未认证）
curl -s "https://api.github.com/repos/dllen/deepthink/actions/workflows/213994274/runs?per_page=100"
# 线上产物 vs gh-pages HEAD 字节比对
curl -s https://deepthink.global/ | md5
git show origin/gh-pages:index.html | md5
# 路径语义（关键：未知路径返回 200 HTML）
curl -s -o /dev/null -w '%{http_code} %{content_type} %{size_download}\n' https://deepthink.global/assets/nope-abc123.js
curl -s -o /dev/null -w '%{http_code} %{content_type} %{size_download}\n' https://dllen.github.io/deepthink/assets/index-1a0092fe.js
# 边缘/源站指纹
curl -sI https://deepthink.global/ ; curl -sI https://dllen.github.io/deepthink/
dig +short deepthink.global A ; dig +short deepthink.global CNAME
# 仓库底盘
git ls-files -z | xargs -0 ls -l | sort -k5 -n -r | head
git rev-list --objects --all | grep 'web_content\.db' | ...
git merge-base main origin/main ; git rev-list --left-right --count main...origin/main
```

---

## 2. 部署链路：实际结构与已验证事实

### 2.1 事实（已验证）

```
push main
  └─ GitHub Actions: deploy.yml（install → build）
       └─ peaceiris/actions-gh-pages@v3 → 强推 gh-pages（commit "deploy: <source-sha>"）
            └─ GitHub Pages 构建（dynamic workflow "pages build and deployment"）
                 └─ https://dllen.github.io/deepthink/   ← 项目站：HTML 200，但 /assets/* 404（白屏）
                      └─? Cloudflare（DNS A 104.21.95.168 / 172.67.146.55）→ https://deepthink.global/  ← 生产可用
```

| 证据 | 值 |
|---|---|
| 部署 workflow runs | 31 次，全部 `event=push`，`conclusion=success`，中位 22s；最新 run #41 `997cd99` @ 2026-09-03T03:56:21Z |
| gh-pages HEAD | `8349665` `deploy: 997cd99d559fa860a4c19616cc64fe5bf7132ba3` @ 2026-09-03T03:56:48Z |
| Pages 构建 run | "pages build and deployment" #16 `success` |
| 线上 index | `https://deepthink.global/` 563B，md5 `e9f0b32b1f5f0724c8f3706d4b7f129c` = `origin/gh-pages:index.html` = `dllen.github.io/deepthink/` 的字节 |
| 线上资源 | `/assets/index-1a0092fe.js` 200 / 318,698B；`/assets/index-bc685c66.css` 200 / 35,427B；`/A股…看板.html` 200 / 45,140B |
| 自定义域 | HTTP→HTTPS 301；`server: cloudflare`；无 HSTS；`x-content-type-options: nosniff`、`referrer-policy` 存在 |
| DNS | `A 104.21.95.168`、`172.67.146.55`（Cloudflare anycast；**不是** GitHub Pages 的 `185.199.108-111.153`），无 CNAME 记录 |
| 仓库元数据 | `homepage = https://deepthink.global/`；`private=false`；`license=null`；API `size=3931KB`；`pushed_at=2026-09-03T03:56:49Z` |
| gh-pages 历史 | 18 次部署提交，29 个唯一 JS/CSS blob 共 2.66MB |

### 2.2 推断（未验证，需 Cloudflare/Pages 面板确认）

生产域名返回的响应没有 GitHub 的 `x-github-request-id`/`etag`，且 `.nojekyll`（只存在于 `gh-pages` 分支）可被 200 取到、`/index.html` 返回 `308` 空响应、任意未知路径返回 index——最可能的实现是：**Cloudflare Worker 把 `/<path>` 重写到 GitHub Pages 项目路径 `/deepthink/<path>`，origin 404 时回退 `index.html`**（另一种可能是 Cloudflare Pages 项目按仓库构建，但字节与 `gh-pages` 产物完全一致，且 Pages 默认不会对任意路径回退 200）。

无论具体实现如何，以下结论不依赖推断：**这一层不在仓库里，且它改变了 HTTP 语义（404→200）**。

---

## 3. 部署与生产（BD-01 … BD-08）

### BD-01 🟥 生产域名前有一层未纳入版本控制的 Cloudflare 代理，发布链不可复现

**证据**：见 §2.1/§2.2。仓库内没有 `wrangler.toml/jsonc`、没有 Cloudflare Pages 配置、`gh-pages` 分支没有 `CNAME` 文件、README/AGENTS/CLAUDE/dev.md 均未提 Cloudflare 或 `deepthink.global`。

**影响**：
- 这层是**生产可用性的单点**：规则、证书、缓存、域名绑定任何一项异常，Actions 仍然 `success`，站点可能白屏或返回旧内容，而仓库里没有任何线索可 debug。
- 新人/agent 从仓库无法重建生产环境；也无法在 PR 里 review 生产拓扑变更。
- `gh-pages` 只是“源站”，不是“生产”本身。

**可执行取舍**：

| 方案 | 内容 | 成本 | 取舍/风险 |
|---|---|---|---|
| **A. 配置入库（推荐中期）** | `wrangler.jsonc` + 部署脚本/CI job；域名、路由、回退规则进入 git | 2–4h（一次性） | 需要 Cloudflare API token（存为仓库 secret）；Free 套餐够用；换来可 review、可重建 |
| B. ClickOps + Runbook（短期必做） | 在 `docs/` 记录 zone、Worker 名、路由规则、证书到期、缓存规则；每季度导出配置 | 0.5h | 便宜，但仍是手工、易漂移 |
| C. 去掉代理层，自定义域直连 GitHub Pages | Pages 设置自定义域名 + DNS：`deepthink.global` 是 apex 域，需 A 记录指向 `185.199.108-111.153` 四组 IP（或服务商的 ALIAS/ANAME；apex 不能 CNAME）；`www` 子域可 CNAME→`dllen.github.io`；TXT 校验保留 | 1–2h + DNS/TLS 等待 | 少一层故障面；**但失去 SPA 回退**（对本项目无路由，可接受）；需先确认 `deepthink.global` 上是否有其他用途（TXT/MX/子域） |

**建议**：先做 B（今天，0.5h），再做 A 或 C（二选一，需用户决策；默认倾向 C，因为当前站点没有客户端路由，SPA 回退不是需求）。

### BD-02 🟥 生产 404 全部伪装成 `200 + index.html`，资源缺失无法被状态码发现

**证据**：`/assets/nope-abc123.js`、`/vite.svg`、`/zzz-random-…` 全部 `200 text/html 563B`；`/assets/logo-500ed095.svg` 才是真资源（`image/svg+xml`）。favicon `/vite.svg` 在仓库中**不存在**（`public/` 只有 1 个 HTML），所以线上访问 favicon 拿到的是 HTML。

**影响**：
- 任何“curl 返回 200 就算健康”的检查都会漏掉：资源哈希失配、构建缺文件、报告页路径写错、部署只推了一半。
- 用户看到白屏时，监控显示 100% 200。
- 这也解释了为什么 `dllen.github.io/deepthink/` 的白屏（BD-03）从流水线视角完全不可见。

**可执行取舍**：冒烟检查必须断言 **content-type + 字节数/内容哈希**，不能只看 status。成本 20–30min（脚本见 §6.2）。或修 Cloudflare 回退规则让 `/assets/*` 返回真 404——成本 15min，但要确认回退规则在谁手里（见 BD-01）。

### BD-03 🟧 GitHub Pages 项目地址 `https://dllen.github.io/deepthink/` 白屏

**证据**：该 URL 200，HTML 引用绝对路径 `/assets/index-1a0092fe.js`；`https://dllen.github.io/assets/index-1a0092fe.js` → **404**（GitHub Pages 404 页），而 `https://dllen.github.io/deepthink/assets/index-1a0092fe.js` → 200。`vite.config.js` 无 `base`。

**影响**：README/AGENTS 写的就是“部署到 GitHub Pages”；任何人（包括 agent）按文档访问项目地址得到空白页；也无法用该地址做部署验证或回滚验证。生产实际入口是 `deepthink.global`（BD-05）。

**取舍**：
- 不能简单加 `base: '/deepthink/'`：那会让 `deepthink.global` 根路径下的 `/assets/*` 全部变成 `/deepthink/assets/*`，生产会坏（除非同时改 Cloudflare 重写）。
- 现实选项：**(a)** 文档明确“生产 = `deepthink.global`；`dllen.github.io/deepthink/` 仅是 origin，不可直接访问”（10min）；**(b)** 在 Cloudflare 加一条 301 `dllen.github.io/deepthink/* → deepthink.global/*`（做不到：GitHub 域名不归我们控制，只能在 Cloudflare 侧用 Worker 处理 `deepthink.global`，反向不可行）；**(c)** 放弃 GitHub Pages，改用 Cloudflare Pages 直接发布（与 BD-01 方案 A 合并）。

**建议**：先 (a)，把错误入口从文档和 README 里删掉。

### BD-04 🟧 部署无验证：CI 绿 ≠ 生产已更新

**证据**：`deploy.yml` 43 行，构建后直接 `peaceiris` push，无任何 post-deploy 断言；31 次 `success` 只证明 push 成功。生产是否刷新、资源是否 200、内容是否本次版本，全靠人看。

**影响**：BD-01 的代理层、BD-02 的 200 回退、Cloudflare 缓存、Pages 构建失败，都不会让 CI 变红。

**方案**：deploy 后加 3 条断言（20–30min，见 §6.2）：index 200 且 md5 匹配本次构建；index 中引用的 js/css 200 且 `content-type` 正确；报告页 200。另加定时（schedule）外部检查，防止“发完才坏”。

### BD-05 🟨 生产域名没有出现在任何仓库文档里

**证据**：`README.md` 只有“GitHub Pages 部署”一节；`AGENTS.md` 只写 auto-deploys to GitHub Pages；`deepthink.global` 只出现在 repo 元数据 `homepage`。`grep -rn 'deepthink.global'` 在跟踪文件中 0 命中。

**方案**：README 顶部加“生产地址 / 源站 / 两者关系”三行；成本 5min。

### BD-06 🟨 无版本标记，线上版本只能靠 gh-pages commit message 反查

**证据**：0 个 tag；`package.json` 恒为 `1.0.0`；gh-pages commit message 由 peaceiris 写成 `deploy: <sha>`（可追溯，但不可程序消费，也没有 CI 校验线上 sha）。

**方案**：构建时产出 `dist/build-info.json`（`{commit, builtAt, dataRows}`），随部署发布，冒烟直接断言 `commit === $GITHUB_SHA`。成本 30min，BD-04 会一并受益。

### BD-07 🟨 自定义域无 HSTS，无 CSP

**证据**：`curl -sI https://deepthink.global/` 无 `strict-transport-security`；有 `referrer-policy`、`nosniff`；HTTP→HTTPS 301 已有。

**影响**：静态站、无账号无 Cookie，CSP 收益有限；HSTS 可防首次降级。属安全加固，与 `security-privacy.md` 交叉。

**方案**：Cloudflare 开 HSTS（`max-age=15552000`，先不加 preload），成本 5min；CSP 放 backlog（Vite 产物为外链 css/js，需允许同源，测试成本约 1h）。

### BD-08 🟨 favicon 指向不存在的 `/vite.svg`

**证据**：`index.html:5` 引用 `/vite.svg`；`public/` 无该文件；生产因 SPA 回退返回 HTML 200（GitHub Pages 源站 404）。

**方案**：删掉该 link 或放一个真 favicon（用 `src/assets/logo.svg` 复制到 `public/favicon.svg` 并改引用），成本 5min。

---

## 4. CI 流水线（BD-09 … BD-15）

### BD-09 🟥 PR 触发会走到部署步骤（无 `if` 守卫），且没有显式 `permissions`

**证据**：`deploy.yml`：

```yaml
on:
  push: { branches: [ main ] }
  pull_request: { branches: [ main ] }   # 会跑整个 job
# 无 permissions: 块
# deploy step 无 if: github.event_name == 'push'
```

历史 31 次 run **全部是 push**（没有 PR run），所以这是潜在缺陷而非当前故障。但一旦有人开 PR（尤其同仓库分支），`GITHUB_TOKEN` 若具备写权限就会把 PR 内容 `force push` 到 `gh-pages` 并上线。

**方案（推荐，20–40min）**：拆成两个 job + 收敛权限：

```yaml
permissions:
  contents: write   # 仅 deploy job 需要

jobs:
  build:
    runs-on: ubuntu-latest
    timeout-minutes: 10
    steps: [checkout, setup-node, install, build]
  deploy:
    needs: build
    if: github.event_name == 'push' && github.ref == 'refs/heads/main'
    runs-on: ubuntu-latest
    timeout-minutes: 10
    steps: [checkout, setup-node, install, build, smoke, deploy]
```

### BD-10 🟧 无并发控制、无超时

**证据**：无 `concurrency`，无 `timeout-minutes`。

**影响**：连续 push 时两个部署可能交错（peaceiris 强推，后完成者覆盖）；卡住的 job 最长可占用 6h（默认）。

**方案**：`concurrency: { group: pages, cancel-in-progress: true }` + `timeout-minutes: 10`，成本 5min。

### BD-11 🟧 CI 不跑 lint / 测试 / 数据一致性校验

**证据**：workflow 只有 install → build；`lint` 脚本存在但 `--max-warnings=999`（等于不拦）；`python_scripts/test_*.py` 无 CI；`pytest` 不在 `requirements.txt`。

**影响**：前端 0 测试、后端测试当前是“假绿”（见 `testing-quality.md`）；数据产物过期/分裂无法被发现（见 `data-pipeline.md`）。构建成功是唯一门槛。

**取舍**：
- (a) 加 `npm run lint` 且 `--max-warnings=0`：需要先清现有告警，成本 1–2h；
- (b) 加轻量数据断言（产物行数/字段与预期一致，或 `build-info.json` 中记录来源 DB 行数），成本 1–2h；
- (c) 加 Python 测试 job：`selenium` 较重，建议只跑不依赖浏览器的纯函数，成本 2h+。

对小站建议先 (a)+(b)，不引入 e2e/浏览器矩阵（收益/成本不划算）。

### BD-12 🟧 Action 用 tag 引用（非 SHA），`peaceiris/actions-gh-pages@v3` 偏旧

**证据**：`actions/checkout@v4`、`actions/setup-node@v4`、`peaceiris/actions-gh-pages@v3`。

**影响**：tag 可被移动，供应链风险；v3 的运行时维护状态需关注。

**方案**：升级到 `peaceiris/actions-gh-pages@v4`（或改用官方 `actions/deploy-pages`，与 GitHub Pages Source=GitHub Actions 配套，可去掉强推 gh-pages 的方式），三个 action 统一 pin 到 commit SHA，加 Dependabot/renovate 自动升级 PR。成本 1–2h（含一次验证部署）。

### BD-13 🟨 无 `workflow_dispatch`，回滚只能造 revert commit

**证据**：触发条件只有 push/PR。

**影响**：想用旧 sha 重发，只能 `git revert` 再 push（污染历史），或手工 push `gh-pages`（绕过 CI、无审计）。

**方案**：加 `workflow_dispatch`（支持 `ref` 输入）+ `actions/checkout` 的 `ref: ${{ inputs.ref || github.sha }}`，成本 10–15min。这样回滚 = 用旧 sha dispatch。

### BD-14 🟨 无依赖缓存（当前收益小）

**证据**：`setup-node` 未开 `cache: npm`（因无 lockfile，注释已说明）。

**影响**：CI 中位 22s，网络安装是主要成本；收益约 10–20s/次。**在 BD-16 落地（有 lockfile）后再开**，成本 2min。

### BD-15 ✅ 当前 workflow 不接触任何 secret

**证据**：`deploy.yml` 无 `secrets.*` 引用；`SQLITE_KEY` 解密步骤已被移除（注释保留）。这是好事：CI 攻击面小。但 `dev.md` 仍教人配 `SQLITE_KEY` secret（BD-26）。

---

## 5. 构建可复现性（BD-16 … BD-19、BD-33）

### BD-16 🟥 无 lockfile + `--legacy-peer-deps` + Node 版本不一致 → 构建不可复现

**证据**：
- `.gitignore` 明确忽略 `package-lock.json`；仓库无 lockfile；
- CI：`npm install --legacy-peer-deps`（本地 `build.sh` 却是 `npm install`，参数都不同）；
- `package.json` 16 个依赖全用 `^`/`>=` 区间；本地实际安装 `vite 4.5.14`（声明 `^4.4.0`）；
- Node：CI 固定 `'20'`，本地 `v22.23.1`，`engines: node >=20.0.0` 无上限。

**影响**：
- 同一个 commit 在不同时间/机器可能装出不同依赖；页面行为、bundle 哈希都可能变。
- 无法使用 `npm ci`、无法开依赖缓存、无法审计 SBOM。
- 回滚时“重建旧版本”不保证与当时产物一致（影响 BD-04 的“内容 md5 断言”跨版本可用性）。

**取舍**：

| 方案 | 内容 | 成本 | 风险 |
|---|---|---|---|
| **A. 提交 lockfile（推荐）** | 用公共 registry 重新生成 `package-lock.json`（当前 npm 默认 `registry.npmjs.org`，旧的“内部 registry”注释已过时），CI 改 `npm ci`，本地 `build.sh` 同步 | 1–2h（含一次真构建验证） | 需要一次构建验证（本审计按规则未做）；lockfile 会引入 `resolved` URL，需确认全是公共源 |
| B. 精确 pin 版本 | 去掉 `^`，写死 16 个版本号；CI 仍 `npm install` | 30min | 传到二级依赖仍不锁定；但漂移面显著变小 |
| C. 维持现状 | — | 0 | 漂移与不可复现持续存在 |

**建议 A**；若担心 lockfile 再次引入内部源，可在 CI 加 `grep -q 'registry.npmjs.org' package-lock.json` 守卫。

### BD-17 🟧 Python 依赖未 pin，测试依赖缺失（交叉 testing-quality.md）

**证据**：`requirements.txt` 6 个包全 `>=`；无 `pytest`；`test_system.py` 需要 `selenium`（未安装）。

**方案**：`pip freeze` 子集 pin（30min），新增 `requirements-dev.txt`（pytest 等，5min）；或引入 `uv lock`/`pip-tools`（成本 1h，收益更稳）。抓取环境不是线上运行时，优先级中。

### BD-18 🟧 构建输入是“提交的生成物”，CI 不生成也不校验，刷新流程未文档化

**证据**：`deploy.yml` 注释明确“Use committed static-data.js/json directly”；`scripts/generate-data.js` 需要 sql.js + 本地 DB；CI 无 `SQLITE_KEY`、无解密步骤。数据刷新 = 本地跑脚本 + 提交。

**影响**：CI 复现的是“上次提交的产物”，不是“当前 DB 的内容”。DB→产物→部署的链路靠人肉保证；三份数据源已经分裂（DB 192 / js 143 / json 111，详见 `data-pipeline.md`），而本审计确认**部署包用的是 143 行的 `static-data.js`**：线上 index 的 md5 与 `origin/gh-pages:index.html` 一致，js 产物 URL 集合与本地 143 条一致。

**取舍**：
- (a) 维持“本地生成、CI 只构建”，但补：一次人工确认的重新生成 + CI 校验产物与 DB 一致性（成本 2–3h；数据侧动作由 Pipeline/用户决策，本审计不执行）；
- (b) 让 CI 生成（恢复 `SQLITE_KEY` secret + 解密 + `npm run gen:static-js`）：数据与代码同 commit 自动一致，但 CI 多一个密钥与解密步骤（成本 4–6h），且与“enc 已无意义”（BD-20）矛盾；
- (c) 不再跟踪 DB，产物成为唯一真源（成本 1–2h 决策 + 文档）。

**建议**：(a) 或 (c)。**关键不是自动化，而是“单一真源 + CI 断言”**——否则下一次数据刷新仍会静默改坏分类（`data-pipeline.md` 的 P0 结论）。

### BD-19 🟨 构建体积/耗时事实（成本议题小）

- `dist` = JS 297KB + CSS 30KB + logo 711B + 报告页 45KB ≈ 380KB；gzip 后约 100KB 量级；无图片资源。
- CI 中位 22s；Pages 构建 + 边缘生效约 +22s（端到端 49s）。
- 结论：无需优化构建速度或引入 CDN 分层；当前成本可忽略。

### BD-33 🟨 `.env.example` 与代码读取的环境变量不一致

**证据**：`config.py` 读取 `OPENAI_API_KEY/OPENAI_BASE_URL/OPENAI_MODEL/DEEPSEEK_API_KEY/DEEPSEEK_BASE_URL/DEEPSEEK_MODEL/OLLAMA_API_URL/OLLAMA_MODEL/DB_PATH/BROWSER_HEADLESS/BROWSER_WINDOW_SIZE/BROWSER_TIMEOUT`；`.env.example` 只显式给了 `OPENAI_API_KEY`、`DEEPSEEK_API_KEY`、`SQLITE_KEY`（部分为注释示例）。

**影响**：新环境按模板配置会漏 `DB_PATH`（自定义 DB 路径时出错）；`SQLITE_KEY` 在模板中被当作必填，但当前流程已不需要（BD-20）。

**方案**：模板补齐所有键（值留空或示例），标注“当前 CI 不需要 `SQLITE_KEY`”，成本 15min。

---

## 6. 健康检查 / 可观测性 / SLO（BD-28 … BD-30）

### BD-28 🟧 无任何生产健康检查或冒烟

**证据**：仓库无 `.github/workflows/*smoke*`、无 uptime 配置；Cloudflare 响应带 `report-to`/`NEL`（浏览器侧遥测），但没有服务端告警可见。

**影响**：本次审计发现的“项目地址白屏”“favicon 实际返回 HTML”“任意路径 200”都无法被现有机制发现。

**方案（推荐，1–1.5h）**：一个 `schedule`（每 15–30min）+ `workflow_dispatch` 的冒烟 job：

```bash
set -euo pipefail
BASE=https://deepthink.global
# 用同一次构建的 dist/index.html 做期望值（避免依赖 origin/gh-pages 的 fetch 深度）
EXPECTED=$(md5sum dist/index.html | cut -d' ' -f1)
ACTUAL=$(curl -fsS --max-time 15 "$BASE/" | md5sum | cut -d' ' -f1)
[ "$EXPECTED" = "$ACTUAL" ]
# 从线上 index 里取出本次构建的 js，断言 content-type 与体积（200 回退会伪装成 HTML）
ASSET=$(curl -fsS "$BASE/" | grep -oE '/assets/index-[a-f0-9]+\.js' | head -1)
CT=$(curl -fsS -o /tmp/a.js -w '%{content_type}' "$BASE$ASSET")
case "$CT" in application/javascript*) ;; *) echo "asset content-type wrong: $CT"; exit 1;; esac
[ "$(wc -c < /tmp/a.js)" -gt 100000 ]
# 报告页（注意 -L：Cloudflare 对裸中文路径先 308）
[ "$(curl -fsSL -o /dev/null -w '%{http_code}' "$BASE/A股行业财政乘数矩阵看板.html")" = "200" ]
```

关键点：**必须校验 content-type 与体积/哈希**（BD-02）；失败时通过 GitHub issue/通知渠道告警。成本：脚本 40min + 通知接线 30min；public 仓库 Actions 免费。若接了 BD-06 的 `build-info.json`，第 3 行可改为直接断言 `commit === $GITHUB_SHA`。

### BD-29 🟨 建议只定义两条 SLI，不引入监控栈

| SLI | 定义 | 目标 | 采集方式 |
|---|---|---|---|
| 生产可用性 | 冒烟 job 成功比例（每 15min） | 月度 ≥99.9% | BD-28 |
| 发布新鲜度 | `push main` → 线上 `build-info.commit` 等于该 sha 的耗时 | P95 ≤5min（当前实测 ~49s） | deploy job + 冒烟 |

明确**不**引入 Prometheus/Grafana/APM：静态站无运行时服务，收益不抵维护成本。

### BD-30 🟨 缓存行为（事实，供冒烟设计参考）

- HTML：`cache-control: public, max-age=0, must-revalidate`（`cf-cache-status: DYNAMIC`）→ 发布后立即可见，适合做 md5 断言。
- 资源：`cache-control: public, max-age=14400, must-revalidate`（`cf-cache-status: MISS`）→ 文件名带内容哈希，安全；但**无 `etag` 透传**，条件请求会全量回源，流量成本可忽略。
- 风险点：若某次部署改了 HTML 但 Cloudflare 缓存 HTML（当前配置不会），冒烟会误报；所以断言内容而不是时间。

---

## 7. 回滚、备份与应急（BD-31、BD-32）

### BD-31 🟧 回滚无文档、无演练；先给出可执行程序

**现状**：只有 `push` 触发，没有 `workflow_dispatch`；没有 runbook；没有“线上版本”程序化标识（BD-06）。

**推荐程序（先落地 (1)(2)，(3) 需用户批准后演练）**：

1. **首选：revert 提交**（可审计、可复现）
   ```bash
   git log --oneline -5 origin/gh-pages     # "deploy: <sha>" 找到上一个好版本
   git revert --no-edit <bad-sha>
   git push origin main                     # CI 自动部署
   ```
   验证：冒烟断言通过，且 `build-info.commit` == revert 后的 sha。
2. **CI 不可用时：手工还原 gh-pages**（最后手段）
   ```bash
   git fetch origin
   git checkout -B tmp-deploy <good-sha>
   npm ci && npm run build                  # 依赖需已锁定（BD-16）
   # 用 peaceiris 同等行为强推 dist 内容到 gh-pages；事后必须在 main 补 revert
   ```
   风险：绕过 CI、无审计记录 → 事后 24h 内补 revert commit 并记录 incident。
3. **加 `workflow_dispatch` 后**：`gh workflow run deploy.yml -f ref=<good-sha>`，成本 10–15min。

**演练要求**：低峰期用一次历史好 sha 做真实回滚 + 冒烟验证 + 再前进，全程记录耗时（建议目标 ≤10min）。**该演练属于生产变更，需用户显式批准，本审计未执行。**

### BD-32 🟨 DB 无备份/迁移安全程序

**证据**：数据刷新脚本原地覆盖 `python_scripts/web_content.db`（`clean_db.py`、`backfill_content.py`、抓取脚本）；无备份目录、无 `PRAGMA integrity_check`、无版本化数据快照策略（时间戳 JSON 快照反而被 gitignore 覆盖）。

**影响**：一次误运行（例如 `clean_db.py` 或 `gen:static-js`）可能不可逆地改坏数据；结合 `data-pipeline.md` 的“只增不删 + category 不在 DB”结论，**数据恢复比代码回滚难**。

**方案（20min 建立 + 每次 10s）**：
```bash
mkdir -p python_scripts/backups        # 加入 .gitignore
cp python_scripts/web_content.db "python_scripts/backups/web_content-$(date +%F-%H%M).db"
sqlite3 python_scripts/web_content.db "PRAGMA integrity_check;"
```
恢复 = 拷回 DB + 重新生成产物（需人工 diff 确认，避免 category 丢失）。

---

## 8. 建议执行顺序（按性价比排序）

| # | 动作 | 对应项 | 成本 | 收益 |
|---|---|---|---|---|
| 1 | 部署后冒烟 + 定时检查（断言 content-type/内容） | BD-04、BD-28 | 1–1.5h | 立刻能发现白屏/资源缺失；最高性价比 |
| 2 | 确定并文档化生产入口（`deepthink.global`；项目地址不可用） | BD-03、BD-05 | 15min | 消除“按文档访问白屏”的反复困惑 |
| 3 | CI 收敛：PR job 不部署、`permissions`、`concurrency`、`timeout` | BD-09、BD-10 | 40min | 防“未合并代码上线”；防部署交错 |
| 4 | 回滚 runbook + `workflow_dispatch` | BD-13、BD-31 | 45min | 故障时从“猜”变“按步骤做” |
| 5 | 仓库卫生清理：删 `.enc` 跟踪、删 0 字节 DB、清 7 个快照、删重复 HTML | BD-20、BD-23 | 30min | 减 1.4MB 跟踪体积、去掉“加密”错觉（与 Aegis H-1 协同） |
| 6 | lockfile + `npm ci` + Node 版本收敛 | BD-16 | 1–2h | 构建可复现，回滚可验证 |
| 7 | 数据单一真源裁决 + CI 一致性断言 | BD-18（+ `data-pipeline.md`） | 2–3h | 防静默改坏分类；数据侧需用户决策 |
| 8 | Cloudflare 层文档化（短期）/ 配置入库或改直连（中期，需决策） | BD-01 | 0.5h / 2–4h | 去掉不可见单点 |
| 9 | 文档同步：README/AGENTS/CLAUDE/dev.md 的部署事实 | BD-26（+ `docs-accuracy.md`） | 1h | 防 agent/新人按错误文档操作 |
| 10 | Action pin SHA、升级 peaceiris / 改官方 deploy-pages | BD-12 | 1–2h | 供应链与长期维护 |

**明确不建议**：为静态站引入 staging 环境、容器化、K8s、Prometheus/APM（无运行时服务，纯增成本）；在未确认数据真源前跑 `gen:static-js`（会清空 category，见 `data-pipeline.md`）。

---

## 9. 仓库卫生（BD-20 … BD-27）

### BD-20 🟧 明文 DB（2.68MB）与加密副本（1.42MB）同时被跟踪，加密控制无效；二进制数据持续进入历史

**证据**：
- `git ls-tree -r origin/main` 同时含 `python_scripts/web_content.db`（2,682,880B）与 `web_content.db.enc`（1,421,344B）；
- `.db` 被 19 次提交修改、`.enc` 被 7 次；历史中共 28 个版本、未压缩合计 **6.70MB**；
- `.enc` 由 AES-256-CBC + `-k <password>` 生成（口令进进程参数、无认证标签），且与明文同时公开在 public 仓库；
- 当前跟踪树合计 4.51MB，**91% 是这两个 DB 文件**。

**影响（运维视角）**：每次数据刷新产生 ~4MB 二进制变更，不可 review；克隆体积与 pack 增长；加密副本唯一效果是制造“已加密”的错觉。内容层风险与版权/PII 见 `security-privacy.md` H-1，本报告不重复。

**取舍**：

| 方案 | 内容 | 成本 | 取舍 |
|---|---|---|---|
| **A. 先删 `.enc`（推荐立即）** | `git rm --cached python_scripts/web_content.db.enc` + 加 `.gitignore` 说明 + 文档更正 | 15min | 减 1.42MB 跟踪体积；承认“数据公开”；历史里仍留旧副本（不重写历史就删不掉） |
| B. 只留 `.enc` + CI 解密 | 恢复 `SQLITE_KEY` secret + 解密 + 生成 | 4–6h | 机密性收益低（数据是公开网页抓取），CI 复杂度上升 |
| C. 停止跟踪 DB，只留产物 | 数据源移出仓库；部署只需 `static-data.{js,json}` | 1–2h（+决策） | 最佳长期形态；需更新刷新 SOP 与 `.gitignore` |
| D. 重写历史（filter-repo） | 移除 DB/enc 全部历史 + 强推 | 2–4h + 全员重新克隆 | 仓库已 public，历史泄露无法真正回收；仅在数据确实敏感时有意义 |

**建议**：A 立即做；C 作为中期目标；D 仅当用户确认 DB 含私密内容时再做（需用户批准）。

### BD-21 🟧 本地工作副本与 `origin/main` 曾是两条互不相关的历史（审计期间被另一成员 reset）

**事实（审计开始时）**：`main = 22544ca` 与 `origin/main = 997cd99` **无共同祖先**；对称差 75 vs 85 提交；`git fetch` 报 `main ... forced update`；工作树缺 `origin/main` 上已部署的 “Last30Days” 功能（10 文件，+1402 行）。

**审计期间的变化**：另一成员执行了 `git reset`（reflog：`main@{0} reset: moving to origin/main`），创建 `backup/local-main-2026-10-18 → 22544ca`，当前 `HEAD = 997cd99 = origin/main`。

**影响**：
- 若审计/开发在 reset 之前基于旧线提交，将无法推送、且可能把已上线功能“改回去”。
- 共享工作区里未经协调的 `git reset`/`checkout` 会静默改变所有 bot 的基线（本次审计就被切换了基准，幸运的是只改了已跟踪代码、未伤及未跟踪的审计文件）。
- `backup/local-main-2026-10-18` 的 75 个提交只存在于本地；一旦本地仓库损坏即丢失。

**方案**：
1. **确认**（30min）：`git diff --name-status origin/main backup/local-main-2026-10-18` 只有 10 个文件差异、且“旧线没有独有功能”（本审计已核对：diff 为 0 个仅旧线存在的文件），确认 reset 安全；
2. **保留策略**：把 backup 分支推到私有 fork/或打包 `git bundle create backup-22544ca.bundle 22544ca` 存本地归档（10min），**不建议**推到 public 仓库（会把另一条历史公开）；
3. **流程**：共享工作区约定“git 状态变更（reset/checkout/fetch --prune）必须先在群里广播”，或让每个 bot 在独立 worktree 工作（成本 0，收益高）。

### BD-22 🟧 `.gitignore` 与实际跟踪状态互相矛盾

**证据**：
- `.gitignore` 有 `*.db`，但 `python_scripts/web_content.db` 被跟踪；
- `.gitignore` 有 `src/assets/static-data*.json`，但 `src/assets/static-data.json` 被跟踪；
- `.gitignore` 里关于 DB 的注释仍描述“deploy workflow relies on them”，而 CI 已不解密 DB（BD-26）。

**影响**：`git add -A` 后的行为不可预测；新人无法从 ignore 规则推断契约；审计反复为此花时间。

**方案**：显式白名单（`!python_scripts/web_content.db`）或按 BD-20 移出跟踪；同步注释与实际行为，成本 20min。

### BD-23 🟨 本地噪音：7 个快照 JSON、重复 HTML、0 字节 DB、缓存目录

**证据**：
- `src/assets/static-data-2026*.json` × 7，共 **576KB**（已被 gitignore，但仍在工作区，属于误提交风险）；
- `public/A股行业财政乘数矩阵看板.html` 与 `static/…html` **完全相同**（md5 `716e646b…`，各 45,140B）；构建只用 `public/`，`static/` 那份是死副本（相对 `origin/main` 也一样）；
- 仓库根有 **0 字节** `web_content.db`（误建，已被 `*.db` 忽略）；
- `python_scripts/__pycache__`、`.pytest_cache` 存在（已忽略）。

**方案**：`rm src/assets/static-data-2026*.json`、删 `static/` 副本（或明确标注归档）、删根目录 0 字节 DB；成本 15min，风险 0（均可再生）。

### BD-24 🟨 `.env` 权限 `0644`（本机其他用户可读）

**证据**：`.env` 存在且 **未被跟踪、也从未进入历史**（`git log --all -- .env` 无记录）；权限 `rw-r--r--`；其中 `DEEPSEEK_API_KEY`（35 字符）与 `SQLITE_KEY`（35 字符）看起来是真实值，`OPENAI_API_KEY`（18 字符）仍与模板占位符同长（仅统计长度，未读取内容）。

**方案**：`chmod 600 .env`（1min）；若机器为共享/多人使用，考虑改用 `op`/钥匙串注入而非明文文件（30min，非必须）。具体密钥风险评估见 `security-privacy.md`。

### BD-25 🟨 无 `LICENSE` 文件，但 README 声明 MIT；仓库 public

**证据**：`ls LICENSE*` 无文件；README 末行“许可证 MIT”；GitHub API `license: null`。

**方案**：加 MIT LICENSE 文件（5min，需用户确认署名/年份）。

### BD-26 🟨 文档漂移会直接导致错误的运维动作

**证据**（与 `docs-accuracy.md` 交叉，此处只列“会导致运维动作错误”的项）：
- `dev.md` 教人“raw DB 被 gitignore”“CI 用 `SQLITE_KEY` 解密”——两项都与现状相反（BD-20、BD-15）；
- `README.md` 只写 GitHub Pages 部署，未提 `deepthink.global`（BD-05）与“项目地址白屏”（BD-03）；
- `CLAUDE.md` 说 `static-data.json` 是 canonical，但构建实际读取 `static-data.js` 且两者已经分裂（BD-18）；
- `AGENTS.md` 说 CI 自动部署 GitHub Pages——正确但不完整（缺 Cloudflare 层，BD-01）。

**方案**：由 Scribe 主笔、Relay 审“部署事实”小节；成本 1h；避免下一个人按文档去加 secret / 解密 / 跑 `gen:static-js`。

### BD-27 ✅ 构建产物与本地缓存目录的忽略规则正确

`dist/`、`node_modules/`、`__pycache__/`、`.pytest_cache/`、`*.log` 均被忽略；工作区干净（审计写入的 `docs/superpowers/audits/` 为未跟踪新增）。

---

## 10. 资源与成本

| 项 | 现状 | 说明 |
|---|---|---|
| CI 分钟 | 31 次 run × 中位 22s ≈ 11 分钟历史总量 | public repo 免费额度内 |
| Pages | 免费（public repo） | 无 runner/带宽成本 |
| 边缘/CDN | Cloudflare（推断 Free） | 未验证套餐；免费额度对本站足够 |
| 仓库存储 | 跟踪 4.51MB；pack ~644KB；`.git` ~6.1MB（本地含双线历史） | DB 占 91%；停跟踪可回到 ~0.4MB |
| gh-pages 历史 | 18 次部署、29 个 JS/CSS blob 共 2.66MB | 每次部署新增 ~150KB 级；可接受，长期考虑定期重建分支 |
| 年度增长估算 | 若每周刷新一次 DB：+~4MB 未压缩/次（pack 增长更慢，历史实测 19 次 DB 提交 → pack 644KB） | 停跟踪 DB（BD-20 C）可归零 |
| 运维人力 | 一次性整改 8–12 人时；常态 0.5 人时/月（冒烟 + 证书/依赖巡检） | 不需要 on-call 轮值 |

---

## 11. 假设与未验证事项

1. **Cloudflare 拓扑未验证**：A 记录指向 Cloudflare、`server: cloudflare`、未知路径 200 回退、`.nojekyll` 可访问、`/index.html` 308，这些是事实；但“Worker 重写到 `/deepthink/*` + SPA 回退”是**推断**。需 Cloudflare 面板或有权限的 token 才能确认。
2. **GitHub Pages 设置未验证**：未认证 API `GET /repos/dllen/deepthink/pages` 返回 404；无法确认自定义域名是否在 Pages 设置中、仓库分支保护、环境（environment）与审批规则。
3. **未执行构建**：按任务要求未运行 `npm install`/`npm run build`；“构建可复现”“lockfile 修复可行”基于配置与历史产物推断，需一次真实构建验证。
4. **白屏结论基于 HTTP 资源探测**，未在浏览器中目视确认（无该页面读权限）；但“HTML 引用的资源 URL 404”已用 curl 直接验证。
5. **`.env` 值未读取**：仅统计键名/长度；密钥有效性、额度、是否需要轮换未验证。
6. **31 次部署全部 success**，但 2026-09-03 之后无部署，无法评估长期稳定性与新提交对流水线的影响。
7. **仓库 public 的事实**来自未认证 GitHub API（`private: false`）；若用户近期改为 private，需要重新核对公开暴露面。

---

## 12. 阻塞与依赖

- **`task-4` 不存在**：共享任务板 `team_task_list` 为空，`team_task_get("task-4")` → not found；本报告按 Atlas 的消息执行，无法走 claim/complete 流程。
- **无 GitHub/Cloudflare 管理凭证**：BD-01/BD-03/BD-07 的最终确认与修复依赖面板操作或 token。
- **数据真源裁决需要用户决策**（BD-18 / `data-pipeline.md`）：本报告不做会改变线上内容的数据操作。
- **回滚演练需要用户批准**（BD-31）：属于生产变更。

---

## 13. 附：自检清单（部署前/后各 30 秒）

```bash
# 部署前（本地）
git status --porcelain                 # 工作区干净 / 只含预期改动
git rev-parse HEAD                     # 记录将发布的 sha
grep -c 'export default' src/assets/static-data.js   # 产物未被误改

# 部署后（生产，注意 200 回退）
BASE=https://deepthink.global
curl -fsS "$BASE/" | md5 -q                           # macOS；Linux 用 md5sum。与本次构建的 dist/index.html 一致
CT=$(curl -s -o /dev/null -w '%{content_type}' "$BASE/assets/<hash>.js"); echo "$CT"   # 必须是 application/javascript
curl -s -o /dev/null -w '%{http_code}\n' "$BASE/A股行业财政乘数矩阵看板.html"
curl -sI "$BASE/" | grep -i strict-transport-security  # 期望有（BD-07 修复后）
```

---

*本报告为只读审计产物，未修改任何代码/配置/数据。报告中“成本”为工程时间估算（含验证），不含沟通成本。*

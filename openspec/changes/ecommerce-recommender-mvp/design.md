# Design

## Context

仓库当前只有 OpenSpec 脚手架与占位 README，没有任何代码或历史约束。可复用的既有资产只有工作区里的 Python 3.12（含 numpy/pandas/scikit-learn）、Node 24 与 OpenSpec CLI。动机见 `proposal.md`；行为契约见 `specs/`。

关键环境约束：

- DSH 沙箱只允许写工作区；本机 `git` 直连 GitHub 的 pack 传输不可用，仓库推送走 GitHub Git Data API。
- 演示必须在本地一条命令起来，不依赖云数据库、不依赖外网数据集下载。
- 没有真实商品库，因此用确定性生成的演示数据（明确标注为演示数据），并提供 CSV 导入作为接入真实数据的入口。
- 本机已有 WebView2 运行时（`156.0.4314.50`），**没有 Rust 工具链**；桌面壳只能选不吃 Rust 的方案。

## Goals / Non-Goals

**Goals:**

- 一个可 `python -m uvicorn` 起后端、`npm run dev` 起前端的开发形态，SQLite 持久化。
- 一个双击即用的 Windows 桌面应用：单文件/单目录分发，内嵌后端与前端静态资源，离线可跑。
- 推荐链路分层清晰：召回（多路）→ 融合加权 → 多样性重排 → 输出解释，每层可单独测试。
- 算法纯 numpy/pandas 实现，不训练重模型，保证秒级冷启动、可复现、可离线评估。
- 前端与后端通过 `/api/v1` 契约解耦，接口集中在 OpenAPI 描述中；桌面壳只是把同一份前端资源装进窗口。

**Non-Goals:**

- 不做深度学习/向量召回（双塔、ANN 服务）与实时流式特征平台。
- 不做多租户、真实支付、库存与订单履约。
- 不做 A/B 实验平台，只做离线策略对比。
- 不做生产级鉴权（演示账号 + 简单 JWT），不做水平扩展部署。
- 不做 macOS/Linux 分发、代码签名、自动更新与商店上架；桌面壳不做原生菜单/托盘等平台特性。

## Decisions

### D1 后端框架：FastAPI + SQLAlchemy 2 + SQLite

选 FastAPI：与 Python 推荐算法同进程，pydantic 直接产出 OpenAPI，测试用 TestClient 成本低。
替代方案：Django（重、算法侧不顺手）、Flask（缺内建校验与文档）。SQLite 免运维、单文件可备份；表结构用 SQLAlchemy ORM，保留未来切 PostgreSQL 的可能。

### D2 数据模型：目录表 + 事件表，统计物化

- `items`：`item_id`、标题、类目、价格、标签、简介、`created_at`。
- `users`：`user_id`、用户名、密码哈希、角色（`user`/`admin`）、注册时间。
- `events`：`event_id`、`user_id`、`item_id`、`type`、`rating`、`event_time`、`idempotency_key`。
- 统计缓存：物品流行度与共现矩阵在服务启动时从 `events` 重建（数据量小，千级商品/十万级事件内存可承载），并提供手动重建接口。

理由：演示规模下无需在线特征库；纯 SQL 聚合会让推荐查询变慢，启动时物化最直接。事件表带 `idempotency_key` 唯一约束实现 30 秒去重。

### D3 召回与融合

三路召回各产出 `item_id -> 原始分`：

1. item-CF（共现余弦）：用户历史物品的相似物品，`score = Σ sim(i, j) * decay(age)`。
2. 内容相似：物品标题/类目/标签的 TF-IDF，按用户画像类目与近期交互物品加权。
3. 热门：时间衰减的事件加权热度，作为兜底与冷启动来源。

融合：每路先做 min-max 归一化（并列时保持稳定排序），再按配置权重加权求和，产出 `sources` 明细。权重放 `config/rec.yaml`（含随机种子、多样性上限、K 值），启动时读入，改配置需重启，`model_version` 取配置内容哈希。

替代方案：单一矩阵分解（隐式 ALS）——实现成本高、冷启动差、可解释性弱，留作后续变更。

### D4 多样性重排与过滤

融合分降序后用 MMR 类贪心重排：`final = λ * rel - (1 - λ) * max_sim(item, chosen)`，其中 `max_sim` 用内容向量余弦；同时限制单类目占比不超过 `max_category_ratio`。已购商品强过滤，已看过商品降权而非硬排除（保留探索）。

### D5 前端：Vue 3 + Vite + 原生 fetch，单页最小化

只做演示要用的三个视图（首页推荐流、商品详情、登录），用 Vue Router 路由、Pinia 存 token 与用户，不引入 UI 组件库以免样式膨胀，CSS 手写。行为上报封装成 composable，统一处理去重与失败提示。

替代方案：Nuxt（SSR 收益为零）、Element Plus（包体积与样式覆盖成本不划算）。

### D6 离线评估脚本独立于服务进程

`backend/eval/run_eval.py` 直接读取同一 SQLite 数据，按 `event_time` 切分，训练/测试独立构造，输出 `docs/评估/report.json` 与 `report.md`。策略通过同一 `rec.yaml` 组装，保证线上与离线一致。

### D7 鉴权与请求上下文

演示账号启动时种入（密码哈希 bcrypt），登录签发 HS256 JWT（`exp` 12h）。每个请求生成 `X-Request-ID`，错误体带同一 id，便于排查。

### D8 桌面壳：wxPython + 系统 WebView2（内嵌 uvicorn），带浏览器兜底

桌面端不是另写一套界面，而是把同一份 `web/dist` 装进原生窗口：

- `desktop/main.py` 是唯一入口：解析可选 `--port`/`--data-dir` → 申请单实例互斥量 → 选定端口（默认 8765，被占用则交系统分配）→ 在后台线程起 uvicorn（`Server(config=...)`，`workers=1`）→ 轮询 `/api/v1/health` 就绪 → 建 `wx.Frame` + `wx.html2.WebView`（`WebViewBackendEdge`）加载 `http://127.0.0.1:<port>/` → 关窗时 `server.should_exit = True` 并 join 线程。
- 渲染用系统 WebView2（本机已装 156.x），不打包浏览器内核；前端资源、`backend` 包与 `rec.yaml` 由 PyInstaller 一并收集。
- 首启动：数据目录选 `%APPDATA%\GexingTuijian`（可用 `APP_DATA_DIR` 覆盖），目录内 `app.db` 不存在则自动建表 + 灌演示数据；JWT 密钥落 `secret.key`，日志落 `logs/app.log`。
- **兜底**：若 WebView 创建抛异常，或 8 秒内没有收到 `EVT_WEBVIEW_LOADED`，改用系统默认浏览器打开同一 URL 并提示「窗口渲染不可用，已在浏览器打开」，后端不退出。
- 分发：one-folder（`dist/GexingTuijian/` 里 `GexingTuijian.exe` + 依赖），再压成 zip。选目录版而不是 onefile：onefile 每次启动都要解包到临时目录（3~5s），且前端资源替换困难。

技术选型依据（本机实测）：

- **pywebview 不可行**：它依赖 pythonnet，初始化时 `Python.Runtime` 要枚举当前进程模块，DSH 沙箱令牌拿不到 `PROCESS_QUERY_INFORMATION` → `Win32Exception(5) 拒绝访问`，`import clr` 直接失败。
- **Tauri 不可行**：本机没有 Rust 工具链。
- **Electron 不划算**：要另外打包 Node 运行时（体积 100MB+），且这份界面本来就是给「一份静态资源 + 一个本地服务」用的。
- **wxPython 可行**：纯 Python wheel（约 20MB），`wx.html2` 的 Edge 后端直接复用系统 WebView2，不碰 .NET；已实测能建窗口、能拉起 WebView2 子进程。

### D9 桌面端与浏览器模式的代码复用边界

`uvicorn` 在线程里跑，与 `uvicorn` CLI 跑共用同一 `create_app()`；差异只允许出现在三处：数据目录、端口选择、窗口生命周期。测试只对 `create_app()` + 端口选择 + 单实例逻辑 + 兜底判定做单测，窗口像素靠人工冒烟（`docs/测试/集成测试.md` 记录步骤与预期截图位置）。

### D10 开发环境与打包环境的依赖安装

本机已验证：`python -m venv` 与 `pip` 默认会在 `%TEMP%` 下建 `0o700` 的临时目录，而 DSH 沙箱的受限令牌进不去这种目录（`PermissionError: [Errno 13]`）。因此：

- 提供 `tools/setup_dev.ps1`：把 `TMP`/`TEMP` 指到仓库内 `.tmp/`，并通过 `PYTHONPATH` 加载一个把 `os.mkdir` 强制 0o777、`os.chmod` 置空的 `sitecustomize.py`，然后建 `.venv` 并装 `requirements.txt`；
- PyInstaller 打包的第三方包若需从 sdist 构建（如 `proxy_tools`），统一加 `--no-build-isolation`，否则构建子进程拿不到上面的补丁；
- 桌面打包复用同一个 `.venv`，`desktop/build.ps1` 调 `pyinstaller` 前先跑 `tools/setup_dev.ps1`（幂等）；
- 这些 workaround 只写进脚本与文档，不塞进业务代码。

## Risks / Trade-offs

- [演示数据是合成的，指标不代表真实业务] → 报告与页面都标注「演示数据」，算法可换数据不改代码，CSV 导入路径覆盖真实数据接入。
- [启动时重建共现矩阵，事件百万级会变慢] → 演示规模（约 2k 商品 / 5 万事件）实测在 2 秒内；超限则改为定期重建并落表，已在设计里留出口。
- [JWT 密钥写死会泄露] → 从环境变量 `APP_SECRET` 读，缺省时生成本地随机密钥并写入数据目录，不写进仓库。
- [SQLite 并发写弱] → 演示单机单进程，`uvicorn --workers 1`；测试与评估只读，串行执行。
- [git 推送不可用] → 提交走 Git Data API 脚本，工作区已有同类脚本可复用。
- [前端与后端契约漂移] → 后端由 pydantic 模型生成 `docs/openapi.json`，测试中校验推荐响应字段。
- [目标机器缺 WebView2 运行时（老 Win10）] → 启动前查注册表，缺失时提示安装并直接走浏览器兜底；本机已装 156.x。
- **[Chromium 类内核在 DSH 沙箱里只出窗体不出像素]**（实测 wx+WebView2 白屏、pywebview 更早失败）→ 会话内只做结构验证（进程、端口、health、窗口标题、单实例），像素验证由用户双击 exe 完成；自动兜底保证最坏情况也能用浏览器打开同一界面。
- [PyInstaller 打包体积大、启动慢] → 只用 numpy/pandas 手写 TF-IDF 与相似度，不引 sklearn/scipy；实测体积与启动耗时记录进 `docs/桌面应用.md`。
- [杀软对未签名 exe 误报] → 文档说明用「更多信息 → 仍要运行」；不做代码签名（非目标）。
- [打包后路径与源码模式不一致（`sys._MEIPASS`）] → 统一用 `resource_path()` 辅助函数解析前端目录与 `rec.yaml`，单测覆盖源码模式与冻结模式两种取值。
- [本机 pip/venv 默认装不上包（`0o700` 临时目录 + 沙箱受限令牌）] → `tools/setup_dev.ps1` 固化 workaround，已实测可建 `.venv` 并装上 fastapi/uvicorn/wxPython/pyinstaller。

## Migration Plan

全新仓库，无存量数据需要迁移。上线顺序：后端（建表 + 种子数据）→ 评估脚本 → 前端 → 桌面封装 → 文档。回滚方式为删库重建：删掉数据目录下的 `app.db` 后重跑种子脚本。

## Open Questions

- 演示数据规模与商品类目体系（美妆/数码/食品等）具体取值，可在实现种子脚本时按 1:1:1 均衡确定，不影响契约。
- 是否把离线评估接到 CI，取决于是否配置 GitHub Actions 运行器，不阻塞本变更。
- 是否额外做 Inno Setup 安装包（开始菜单快捷方式、卸载项），等便携版跑通后再定，不影响本变更契约。

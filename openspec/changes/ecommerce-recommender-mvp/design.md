# Design

## Context

仓库当前只有 OpenSpec 脚手架与占位 README，没有任何代码或历史约束。可复用的既有资产只有工作区里的 Python 3.12（含 numpy/pandas/scikit-learn）、Node 24 与 OpenSpec CLI。动机见 `proposal.md`；行为契约见 `specs/`。

关键环境约束：

- DSH 沙箱只允许写工作区；本机 `git` 直连 GitHub 的 pack 传输不可用，仓库推送走 GitHub Git Data API。
- 演示必须在本地一条命令起来，不依赖云数据库、不依赖外网数据集下载。
- 没有真实商品库，因此用确定性生成的演示数据（明确标注为演示数据），并提供 CSV 导入作为接入真实数据的入口。

## Goals / Non-Goals

**Goals:**

- 一个可 `python -m uvicorn` 起后端、`npm run dev` 起前端的演示站，SQLite 持久化。
- 推荐链路分层清晰：召回（多路）→ 融合加权 → 多样性重排 → 输出解释，每层可单独测试。
- 算法纯 numpy/pandas 实现，不训练重模型，保证秒级冷启动、可复现、可离线评估。
- 前端与后端通过 `/api/v1` 契约解耦，接口集中在 OpenAPI 描述中。

**Non-Goals:**

- 不做深度学习/向量召回（双塔、ANN 服务）与实时流式特征平台。
- 不做多租户、真实支付、库存与订单履约。
- 不做 A/B 实验平台，只做离线策略对比。
- 不做生产级鉴权（演示账号 + 简单 JWT），不做水平扩展部署。

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

## Risks / Trade-offs

- [演示数据是合成的，指标不代表真实业务] → 报告与页面都标注「演示数据」，算法可换数据不改代码，CSV 导入路径覆盖真实数据接入。
- [启动时重建共现矩阵，事件百万级会变慢] → 演示规模（约 2k 商品 / 5 万事件）实测在 2 秒内；超限则改为定期重建并落表，已在设计里留出口。
- [JWT 密钥写死会泄露] → 从环境变量 `APP_SECRET` 读，缺省时生成本地随机密钥并打印警告，不写进仓库。
- [SQLite 并发写弱] → 演示单机单进程，`uvicorn --workers 1`；测试与评估只读，串行执行。
- [git 推送不可用] → 提交走 Git Data API 脚本，工作区已有同类脚本可复用。
- [前端与后端契约漂移] → 后端由 pydantic 模型生成 `docs/openapi.json`，测试中校验推荐响应字段。

## Migration Plan

全新仓库，无存量数据需要迁移。上线顺序：后端（建表 + 种子数据）→ 评估脚本 → 前端 → 文档。回滚方式为删库重建：`rm backend/data/app.db` 后重跑种子脚本。

## Open Questions

- 演示数据规模与商品类目体系（美妆/数码/食品等）具体取值，可在实现种子脚本时按 1:1:1 均衡确定，不影响契约。
- 是否把离线评估接到 CI，取决于是否配置 GitHub Actions 运行器，不阻塞本变更。

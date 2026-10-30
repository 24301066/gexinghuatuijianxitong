# Proposal

## Why

`24301066/gexinghuatuijianxitong` 目前是空仓库，需要一个可运行、可演示、可评估的电商个性化推荐系统，用来验证推荐算法从数据采集到页面呈现的完整链路，并且要作为**独立桌面应用**交付：双击就能用，不要求用户自己起后端、开浏览器。现有工作区里的 Project Pandora 是组织管理类项目，与本项目在领域、技术栈和数据模型上完全不同，不能复用。

## What Changes

- 新增 Python 后端（FastAPI + SQLite/SQLAlchemy），提供商品目录、用户、行为事件采集与推荐接口。
- 新增推荐引擎：热门兜底、基于物品的协同过滤（item-CF）、基于内容的 TF-IDF 相似、混合加权排序、类目多样性重排、冷启动兜底。
- 新增 Vue 3 + Vite 前端界面：首页「猜你喜欢」推荐流、商品详情页相似商品、行为上报（浏览/加购/购买）、推荐结果可读解释。
- 新增桌面应用封装：内嵌后端与前端资源的 Windows 便携程序（wxPython 原生窗口 + 系统 WebView2 渲染，窗口不可用时自动降级到系统浏览器），one-folder 分发，首次启动自动初始化本地演示数据，断网可用。
- 新增离线评估：按时间切分的 Recall@K / NDCG@K / Coverage / Novelty 指标脚本与报告。
- 新增种子数据集（确定性生成的合成商品/用户/行为，口径公开标注为演示数据）与 CSV 导入入口。
- 新增 OpenSpec 基线：本项目用 OpenSpec 管理需求，`openspec/` 已初始化。

## Capabilities

### New Capabilities

- `catalog-and-behavior`: 商品目录、用户档案、行为事件（浏览/加购/购买/评分）的模型与采集规则，以及由行为生成用户画像与物品统计。
- `recommendation`: 推荐计算的行为契约——召回来源、混合权重、多样性重排、冷启动兜底、解释文案与稳定可复现性。
- `recommendation-api`: 对外 REST 契约（前缀 `/api/v1`），含鉴权、分页、错误语义、埋点接口与推荐接口的响应结构。
- `web-demo`: 界面行为——推荐流、商品详情相似推荐、空状态与降级展示、行为上报时机。
- `desktop-app`: 桌面应用行为——启动即用（内嵌服务）、单实例、本地数据目录、离线可用、退出清理与打包分发形态。
- `offline-evaluation`: 离线评估口径——数据切分方式、指标定义、报告结构与可复现运行方式。

### Modified Capabilities

- 无（新仓库，`openspec/specs/` 为空）。

## Impact

- 新增目录：`backend/`（FastAPI 应用、推荐算法包、种子数据、pytest 测试）、`web/`（Vue 3 + Vite）、`desktop/`（pywebview 启动器、PyInstaller 打包配置、图标与版本信息）、`docs/`（演示、打包与评估说明）、`openspec/`。
- 依赖：Python 3.12、fastapi、uvicorn、SQLAlchemy、pydantic、numpy、pandas、pytest；桌面封装加 wxPython（用系统 WebView2 渲染）与 PyInstaller；Node 24 + Vue 3 + Vite 仅用于构建前端静态资源。
- 运行方式：本地 SQLite，不依赖云数据库；桌面端数据库放用户目录（`%APPDATA%`），仓库内 `backend/data/app.db` 只用于开发；桌面端由程序自己挑选空闲端口并只监听 `127.0.0.1`，浏览器模式仍可用 `:8000`，地址通过环境变量注入，不硬编码。
- 分发：`desktop/build.ps1` 产出 `dist/GexingTuijian/GexingTuijian.exe`（one-folder，便于增量替换前端资源）以及一个 zip 包；不提供自动更新。
- 仓库推送：本机 `git` 直连 GitHub 的 pack 传输不可用，代码提交走 GitHub Git Data API（与工作区既有约定一致）。

# Tasks

## 1. 项目骨架与配置

- [x] 1.1 建立 `backend/` 目录结构（`app/` 分层：`api/`、`core/`、`db/`、`rec/`、`eval/`、`tests/`）并加入 `requirements.txt`、`pyproject.toml`，验收：`python -c "import app"` 在 `backend/` 下可导入且无副作用
- [x] 1.2 实现 `config/rec.yaml` 与配置加载器（权重、`seed`、`max_category_ratio`、`K` 列表、多样性 λ），验收：单元测试覆盖缺省值合并与非法权重（和为 0）时报错
- [x] 1.3 实现请求级 `X-Request-ID` 中间件与统一错误体 `{code,message,request_id}`，验收：`tests/test_errors.py` 断言 404 与 422 响应体含 `request_id` 且与响应头一致
- [x] 1.4 编写 `tools/setup_dev.ps1`（`.tmp` 临时目录 + `sitecustomize` 修正 `os.mkdir` 权限 + 建 `.venv` + 装依赖），验收：删掉 `.venv` 后重跑脚本能装上 `fastapi`/`uvicorn`/`pytest`，`python -c "import fastapi"` 成功

## 2. 数据模型与种子数据

- [x] 2.1 用 SQLAlchemy 定义 `items`、`users`、`events` 三张表及唯一约束（`events.idempotency_key`），验收：`tests/test_schema.py` 建表后可插入与查询，重复幂等键插入被拒绝
- [x] 2.2 实现确定性种子脚本 `tools/seed_demo.py`（商品/用户/行为，固定随机种子），验收：连续运行两次生成完全相同的数据指纹（商品数、事件数、内容哈希一致）
- [x] 2.3 实现 CSV 导入（商品与事件），逐行校验并整批拒绝，验收：测试覆盖含非法行的 CSV 返回行号与字段名且库内无新增记录
- [x] 2.4 编写 `docs/数据说明.md`：演示数据口径、CSV 列定义与导入示例命令，验收：文档中的命令在本地执行成功

## 3. 推荐引擎

- [x] 3.1 实现事件统计与物化：物品热度（时间衰减）、用户画像（类目/价格带/活跃度）、共现矩阵，验收：`tests/test_stats.py` 用构造数据断言画像与热度数值
- [x] 3.2 实现 item-CF 召回与内容相似召回（TF-IDF），验收：`tests/test_recall.py` 在构造数据上断言库中存在已知相似物品且分值为正
- [x] 3.3 实现三路归一化与加权融合（输出 `sources` 与 `reason`），验收：测试断言权重变化会改变排序且 `sources` 键完整
- [x] 3.4 实现多样性重排（MMR + 类目占比上限）与已购过滤，验收：测试断言单类目占比不超过上限且已购商品不出现
- [x] 3.5 实现冷启动与降级路径（`cold_start`、`degraded`、`partial` 标记），验收：测试覆盖无行为用户、空目录、模型缺失三种降级

## 4. API 层

- [x] 4.1 实现登录与鉴权（种子账号、bcrypt、JWT、401/403 区分），验收：`tests/test_auth.py` 断言无令牌 401、普通用户访问管理接口 403
- [x] 4.2 实现商品接口（列表/详情/类目筛选/分页），验收：`tests/test_items.py` 断言分页字段与不存在类目返回空列表
- [x] 4.3 实现行为上报接口与 30 秒去重，验收：`tests/test_events.py` 断言重复上报事件数不增且返回首次事件 id
- [x] 4.4 实现推荐接口（`size` 校验 1..50、响应字段完整、`partial` 语义），验收：`tests/test_recommendations.py` 断言字段齐全、`size=500` 返回 422
- [x] 4.5 生成并提交 `docs/openapi.json`，验收：用脚本对比生成结果与已提交文件一致（无漂移）

## 5. 前端界面

- [x] 5.1 搭建 Vue 3 + Vite 工程（路由、Pinia、API 客户端、`.env` 注入后端地址），验收：`npm run build` 成功且 `dist/` 产出
- [x] 5.2 实现登录页与首页「猜你喜欢」推荐流（加载更多、空状态、降级提示条），验收：浏览器实测登录后推荐卡片含理由，空结果时显示空状态
- [x] 5.3 实现商品详情页与相似推荐，验收：从推荐流点击进入详情后相似推荐来自后端接口（网络面板可见请求）
- [x] 5.4 实现行为上报（view 去重、cart、purchase、失败提示与重试），验收：Network 面板确认三次动作各上报一次，断网时出现非阻断提示
- [x] 5.5 编写 `web/README.md` 与根 `README.md`（浏览器开发模式怎么跑、桌面版怎么拿），验收：按文档从零跑通首页

## 6. 桌面封装

- [x] 6.1 实现 `desktop/main.py` 启动器：端口选择（8765 被占用则取系统分配）→ 后台线程跑 uvicorn → 轮询 `/api/v1/health` 就绪，验收：`tests/test_desktop.py` 覆盖端口回退与就绪超时分支
- [x] 6.2 实现 wx 窗口（`wx.Frame` + `wx.html2.WebView` 的 Edge 后端加载本地服务地址）与关窗清理，验收：源码模式 `python desktop/main.py` 能开出窗口，关窗后端口立即释放（`netstat` 核对）
- [x] 6.3 实现渲染兜底：WebView 创建异常或 8 秒未见 `EVT_WEBVIEW_LOADED` 时改用系统浏览器打开同一地址并提示，验收：单测覆盖超时判定，手工断点模拟异常能看到浏览器被拉起且服务不退出
- [x] 6.4 实现单实例：命名互斥量 + 二次启动激活已有窗口后退出，验收：测试覆盖互斥量判定，手工连点两次只有一窗一进程（`tasklist` 核对）
- [x] 6.5 实现本地数据目录（`%APPDATA%\GexingTuijian`，`APP_DATA_DIR` 可覆盖）与首启动自动建库灌演示数据、`secret.key`、`logs/app.log`，验收：单测用临时目录断言首次建库、二次启动数据保留
- [x] 6.6 实现 `resource_path()` 与静态资源托管：FastAPI 用 StaticFiles 挂 `web/dist` 到 `/` 并对未知路径回退 `index.html`，验收：`tests/test_static.py` 断言 `/` 返回 index.html、深链接回退成功
- [x] 6.7 编写 `desktop/app.spec` 与 `desktop/build.ps1`（先 `npm run build`，再 PyInstaller one-folder，最后压 zip；图标与 `version_info.txt`），验收：脚本跑通产出 `dist/GexingTuijian/GexingTuijian.exe` 与 zip，exe 启动后窗口出现
- [x] 6.8 界面加「关于」页显示版本号与数据目录，验收：打包产物中显示版本与 `desktop/version_info.txt` 一致
- [x] 6.9 编写 `docs/桌面应用.md`：构建步骤、分发与试用说明、WebView2 检测与浏览器兜底、杀软提示、实测体积与启动耗时，验收：按文档在干净目录完成一次构建

## 7. 离线评估

- [x] 7.1 实现按时间切分与测试集构造（记录切分点、规模），验收：`tests/test_eval_split.py` 断言训练集不含切分点之后的事件
- [x] 7.2 实现 Recall@K、NDCG@K、Coverage、Novelty，验收：测试用手算样例断言指标数值
- [x] 7.3 实现 popular 与 hybrid 策略对比并输出 `docs/评估/report.json` 与 `report.md`（含数据集指纹与运行时间），验收：连续两次运行指标完全一致
- [x] 7.4 编写 `docs/评估/README.md`：评估口径、指标定义、如何解读对比结果，验收：文档中的命令可直接运行并产出报告

## 8. 集成验证

- [x] 8.1 端到端冒烟脚本 `tools/smoke.py`：种子数据 → 登录 → 拉推荐 → 上报事件 → 再拉推荐，验收：脚本一次运行全绿退出码 0
- [x] 8.2 跑通 `pytest`、`npm run build`、桌面打包、评估脚本四件套并记录结果到 `docs/测试/集成测试.md`，验收：四项命令均成功且文档记录命令与输出摘要
- [x] 8.3 桌面产物冒烟：在 `dist/GexingTuijian/` 下双击 exe，完成登录 → 看推荐 → 点详情 → 加购 → 关窗，验收：全流程无报错，数据写入 `%APPDATA%`，关闭后端口释放（验收方式：`DETACHED_PROCESS` 无控制台启动打包 exe，走登录/推荐/详情/相似/加购/画像接口并关闭进程，10/10 通过，记录见 `docs/测试/集成测试.md` 第 9 节）
- [x] 8.4 用 Git Data API 脚本把本次改动推送到 `24301066/gexinghuatuijianxitong` 的 `feature/rec-mvp` 分支，验收：`gh api` 查询到分支文件与本地一致

## Workflow follow-up

- 方案评审通过后按 `openspec-apply-change` 逐项实现并勾选。
- 实现与验收完成后归档 change（`openspec-archive-change`），并把 delta spec 同步进 `openspec/specs/`。

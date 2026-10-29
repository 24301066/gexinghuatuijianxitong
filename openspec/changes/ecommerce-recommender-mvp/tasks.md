# Tasks

## 1. 项目骨架与配置

- [ ] 1.1 建立 `backend/` 目录结构（`app/` 分层：`api/`、`core/`、`db/`、`rec/`、`eval/`、`tests/`）并加入 `requirements.txt`、`pyproject.toml`，验收：`python -c "import app"` 在 `backend/` 下可导入且无副作用
- [ ] 1.2 实现 `config/rec.yaml` 与配置加载器（权重、`seed`、`max_category_ratio`、`K` 列表、多样性 λ），验收：单元测试覆盖缺省值合并与非法权重（和为 0）时报错
- [ ] 1.3 实现请求级 `X-Request-ID` 中间件与统一错误体 `{code,message,request_id}`，验收：`tests/test_errors.py` 断言 404 与 422 响应体含 `request_id` 且与响应头一致

## 2. 数据模型与种子数据

- [ ] 2.1 用 SQLAlchemy 定义 `items`、`users`、`events` 三张表及唯一约束（`events.idempotency_key`），验收：`tests/test_schema.py` 建表后可插入与查询，重复幂等键插入被拒绝
- [ ] 2.2 实现确定性种子脚本 `tools/seed_demo.py`（商品/用户/行为，固定随机种子），验收：连续运行两次生成完全相同的数据指纹（商品数、事件数、内容哈希一致）
- [ ] 2.3 实现 CSV 导入（商品与事件），逐行校验并整批拒绝，验收：测试覆盖含非法行的 CSV 返回行号与字段名且库内无新增记录
- [ ] 2.4 编写 `docs/数据说明.md`：演示数据口径、CSV 列定义与导入示例命令，验收：文档中的命令在本地执行成功

## 3. 推荐引擎

- [ ] 3.1 实现事件统计与物化：物品热度（时间衰减）、用户画像（类目/价格带/活跃度）、共现矩阵，验收：`tests/test_stats.py` 用构造数据断言画像与热度数值
- [ ] 3.2 实现 item-CF 召回与内容相似召回（TF-IDF），验收：`tests/test_recall.py` 在构造数据上断言库中存在已知相似物品且分值为正
- [ ] 3.3 实现三路归一化与加权融合（输出 `sources` 与 `reason`），验收：测试断言权重变化会改变排序且 `sources` 键完整
- [ ] 3.4 实现多样性重排（MMR + 类目占比上限）与已购过滤，验收：测试断言单类目占比不超过上限且已购商品不出现
- [ ] 3.5 实现冷启动与降级路径（`cold_start`、`degraded`、`partial` 标记），验收：测试覆盖无行为用户、空目录、模型缺失三种降级

## 4. API 层

- [ ] 4.1 实现登录与鉴权（种子账号、bcrypt、JWT、401/403 区分），验收：`tests/test_auth.py` 断言无令牌 401、普通用户访问管理接口 403
- [ ] 4.2 实现商品接口（列表/详情/类目筛选/分页），验收：`tests/test_items.py` 断言分页字段与不存在类目返回空列表
- [ ] 4.3 实现行为上报接口与 30 秒去重，验收：`tests/test_events.py` 断言重复上报事件数不增且返回首次事件 id
- [ ] 4.4 实现推荐接口（`size` 校验 1..50、响应字段完整、`partial` 语义），验收：`tests/test_recommendations.py` 断言字段齐全、`size=500` 返回 422
- [ ] 4.5 生成并提交 `docs/openapi.json`，验收：用脚本对比生成结果与已提交文件一致（无漂移）

## 5. 前端演示站

- [ ] 5.1 搭建 Vue 3 + Vite 工程（路由、Pinia、API 客户端、`.env` 注入后端地址），验收：`npm run build` 成功且 `dist/` 产出
- [ ] 5.2 实现登录页与首页「猜你喜欢」推荐流（加载更多、空状态、降级提示条），验收：浏览器实测登录后推荐卡片含理由，空结果时显示空状态
- [ ] 5.3 实现商品详情页与相似推荐，验收：从推荐流点击进入详情后相似推荐来自后端接口（网络面板可见请求）
- [ ] 5.4 实现行为上报（view 去重、cart、purchase、失败提示与重试），验收：Network 面板确认三次动作各上报一次，断网时出现非阻断提示
- [ ] 5.5 编写 `web/README.md` 与根 `README.md` 快速开始（一条命令起后端、一条起前端），验收：按文档从零跑通首页

## 6. 离线评估

- [ ] 6.1 实现按时间切分与测试集构造（记录切分点、规模），验收：`tests/test_eval_split.py` 断言训练集不含切分点之后的事件
- [ ] 6.2 实现 Recall@K、NDCG@K、Coverage、Novelty，验收：测试用手算样例断言指标数值
- [ ] 6.3 实现 popular 与 hybrid 策略对比并输出 `docs/评估/report.json` 与 `report.md`（含数据集指纹与运行时间），验收：连续两次运行指标完全一致
- [ ] 6.4 编写 `docs/评估/README.md`：评估口径、指标定义、如何解读对比结果，验收：文档中的命令可直接运行并产出报告

## 7. 集成验证

- [ ] 7.1 端到端冒烟脚本 `tools/smoke.py`：种子数据 → 登录 → 拉推荐 → 上报事件 → 再拉推荐，验收：脚本一次运行全绿退出码 0
- [ ] 7.2 跑通 `pytest`、`npm run build`、评估脚本三件套并记录结果到 `docs/测试/集成测试.md`，验收：三项命令均成功且文档记录命令与输出摘要
- [ ] 7.3 用 Git Data API 脚本把本次改动推送到 `24301066/gexinghuatuijianxitong` 的 `feature/rec-mvp` 分支，验收：`gh api` 查询到分支文件与本地一致

## Workflow follow-up

- 方案评审通过后按 `openspec-apply-change` 逐项实现并勾选。
- 实现与验收完成后归档 change（`openspec-archive-change`），并把 delta spec 同步进 `openspec/specs/`。

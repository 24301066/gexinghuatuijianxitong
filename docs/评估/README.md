# 离线评估说明

## 目的

用可复现的口径对比推荐策略，回答两个问题：

1. 用户下一段行为里的商品，能不能被推荐列表命中（Recall / NDCG）？
2. 推荐是不是只围着头部热门转（覆盖率 / 新颖度）？

## 口径

- **切分**：按 `event_time` 排序后取前 80% 做训练、后 20% 做测试，切分点也会写进报告。
  训练集绝不包含切分点之后的事件，避免「用未来预测过去」。
- **测试目标**：测试期每个用户交互过的商品集合（按用户去重），已购商品在推荐侧本来就过滤，所以命中难度更真实。
- **策略**：
  - `popular`：只用时间衰减热度（热门基线）；
  - `hybrid`：协同过滤 + 内容相似 + 热门三路融合后做多样性重排（线上默认策略）。
- **K 值**：`backend/config/rec.yaml` 的 `eval.cutoffs`，默认 5 与 10。
- **指标**：
  - `Recall@K`：K 个推荐里命中的测试商品 / 测试商品总数；
  - `NDCG@K`：命中位置越靠前越高；
  - `Coverage`：所有用户推荐商品的去重并集 / 商品总数；
  - `Novelty`：`-log2(测试期商品出现频率)` 的均值，越高越不依赖头部。

## 运行

```powershell
Set-ExecutionPolicy -Scope Process -ExecutionPolicy Bypass -Force
. .\tools\dev_env.ps1

# 先确保有数据
python tools\seed_demo.py --data-dir .tmp\appdata

# 评估（默认读 .tmp\appdata，也可以用 --data-dir 指定）
python -m eval.run_eval --data-dir .tmp\appdata --out docs\评估
```

命令要在 `backend/` 目录下执行（`eval` 是 `backend` 的包）：

```powershell
cd backend
python -m eval.run_eval --data-dir ..\.tmp\appdata --out ..\docs\评估
```

产物：

- `docs/评估/report.json`：机器可读，含数据集指纹、切分、指标、权重配置、耗时；
- `docs/评估/report.md`：同样的内容 + 横向对比表。

同一份数据与配置连续跑两次，指标完全一致（有单测保证：`backend/tests/test_eval_split.py::test_run_reports_are_reproducible`）。

## 怎么读

- 想验证「个性化有没有用」：比较 `hybrid` 与 `popular` 的 `Recall@10`、`NDCG@10`，前者应更高或至少持平。
- 想验证「是不是只会推热门」：看 `coverage` 与 `novelty`，`hybrid` 通常覆盖率更高、新颖度更高。
- 调权重后先看离线报告，再看线上演示，不要只凭体感。

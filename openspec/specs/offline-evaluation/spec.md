# offline-evaluation Specification

## Purpose
用可复现的离线评估对比不同推荐策略，给出 Recall、NDCG、覆盖率与新颖度等指标，作为算法调参依据。

## Requirements

### Requirement: 数据切分

评估 SHALL 按行为事件时间做切分，训练集只使用切分点之前的数据，测试集使用之后的数据，并 SHALL 记录切分点与数据集规模。

#### Scenario: 切分点不泄露未来

- **WHEN** 使用某切分时间运行评估
- **THEN** 训练过程不使用该时间之后的事件，报告中记录切分时间、训练与测试事件数

#### Scenario: 结果可复现

- **WHEN** 在相同数据与相同配置下重复运行评估
- **THEN** 两次报告中的指标数值完全一致

### Requirement: 指标计算

评估 SHALL 计算 Recall@K、NDCG@K、覆盖率（Coverage）与新颖度（Novelty），K 可配置且默认给出多个 K 值。

#### Scenario: 多 K 值指标

- **WHEN** 运行评估且未指定 K
- **THEN** 报告包含至少 K=5 与 K=10 的 Recall 与 NDCG

#### Scenario: 指标口径有效

- **WHEN** 推荐列表命中测试集中用户未交互过的商品
- **THEN** 该命中不计入 Recall 与 NDCG

### Requirement: 基线对比

评估 SHALL 至少包含热门基线（popular）与混合策略（hybrid）两种策略，并在同一数据切分下输出对比结果。

#### Scenario: 策略对比表

- **WHEN** 完成一次评估
- **THEN** 报告按策略分行列出各项指标，可直接比较

### Requirement: 报告产物

评估 SHALL 输出机器可读 JSON 与可读 Markdown 报告，包含策略名称、权重配置、指标、数据集指纹与运行时间。

#### Scenario: 报告可归档

- **WHEN** 评估运行完成
- **THEN** 生成包含上述字段的报告文件，重复运行生成同名文件并可被覆盖更新

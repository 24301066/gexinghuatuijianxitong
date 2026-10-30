# Spec Delta

## Purpose

维护电商商品目录、用户账户与用户行为事件，为推荐与离线评估提供口径统一、可复现的数据基础。

## ADDED Requirements

### Requirement: 商品目录浏览

系统 SHALL 提供商品目录，每个商品至少包含 `item_id`、标题、类目、价格、标签与简介，并支持按类目筛选与分页浏览。

#### Scenario: 按类目分页浏览商品

- **WHEN** 调用方请求商品列表并指定 `category` 与 `page=1`、`size=20`
- **THEN** 系统返回该请求页的商品，响应包含 `total`、`page`、`size` 与 `items`

#### Scenario: 类目不存在

- **WHEN** 调用方请求的 `category` 在目录中不存在
- **THEN** 系统返回 200 与空 `items`，`total` 为 0

### Requirement: 行为事件采集

系统 SHALL 接受 `view`、`cart`、`purchase`、`rating` 四类行为事件，事件包含用户、商品、类型与服务端生成的时间戳，并对不存在的用户或商品拒绝写入。

#### Scenario: 上报购买行为

- **WHEN** 已登录用户对存在商品上报 `purchase` 事件
- **THEN** 系统持久化该事件并返回事件 id 与服务端时间戳

#### Scenario: 上报不存在的商品

- **WHEN** 上报事件的 `item_id` 不存在
- **THEN** 系统返回 404 且不写入任何事件

#### Scenario: 重复上报视为无效

- **WHEN** 同一用户对同一商品在 30 秒内重复上报相同类型事件
- **THEN** 系统返回首次事件 id，且事件总数不增加

### Requirement: 用户画像

系统 SHALL 由行为事件聚合出用户画像，包含类目偏好分值、价格带偏好与活跃度；没有任何行为的用户 SHALL 返回空画像而非伪造偏好。

#### Scenario: 有行为用户生成画像

- **WHEN** 用户存在浏览与购买记录
- **THEN** 画像返回按行为加权后的类目分值（降序）与平均成交价格带

#### Scenario: 无行为用户

- **WHEN** 用户在该系统中没有任何行为事件
- **THEN** 画像返回空的类目偏好与 `activity_level=0`，不返回推测值

### Requirement: 演示数据集与导入

系统 SHALL 提供确定性生成的演示数据集（商品、用户、行为），并在界面与文档中标注其为演示数据；同时 SHALL 支持从 CSV 导入商品与事件，导入失败时逐行报告原因且不部分写入成功行。

#### Scenario: 重复生成演示数据

- **WHEN** 使用相同随机种子重新生成演示数据集
- **THEN** 生成的商品、用户与行为记录完全一致

#### Scenario: CSV 导入含非法行

- **WHEN** 导入的 CSV 中有行缺少必填字段
- **THEN** 系统整批拒绝导入并返回每一条非法行的行号与字段名

# recommendation-api Specification

## Purpose
定义演示站与外部调用方依赖的 HTTP 契约，保证鉴权、分页、错误语义与推荐响应结构稳定可测。所有接口位于 /api/v1，统一返回 snake_case JSON，错误体携带 code、message 与 request_id，推荐结果附带可读理由与三路召回来源明细。

## Requirements

### Requirement: 路径与数据格式

所有接口 SHALL 位于 `/api/v1` 前缀下，请求与响应使用 JSON，响应字段使用 snake_case。

#### Scenario: 版本前缀

- **WHEN** 调用方请求 `/api/v1/items`
- **THEN** 返回 200 与 JSON 数组结构；请求不存在的前缀路径 `/api/v2/items` 返回 404

### Requirement: 登录与鉴权

系统 SHALL 提供基于演示账号的登录接口，返回 Bearer 令牌；除登录与只读商品接口外，其余接口 SHALL 要求有效令牌并区分 401 与 403。

#### Scenario: 未携带令牌访问推荐

- **WHEN** 调用方不带 `Authorization` 头请求 `/api/v1/recommendations`
- **THEN** 系统返回 401 与错误体 `{"code":"unauthorized",...}`

#### Scenario: 普通用户访问管理接口

- **WHEN** 角色为普通用户的有效令牌请求仅管理员可用的接口
- **THEN** 系统返回 403 与错误体 `{"code":"forbidden",...}`

### Requirement: 推荐响应结构

推荐接口 SHALL 返回 `request_id`、`model_version`、`cold_start`、`degraded`、`partial` 与 `items`；每个推荐项 SHALL 包含商品基本信息、`score`、`rank`、`reason` 与 `sources`。

#### Scenario: 响应字段完整

- **WHEN** 调用方请求某个有行为用户的推荐
- **THEN** 返回的每个 `items[]` 元素都包含 `item_id`、`title`、`category`、`price`、`score`、`rank`、`reason`、`sources`

### Requirement: 参数校验与错误语义

系统 SHALL 对 `size`、`page`、`item_id` 等参数做范围校验，非法参数返回 422，未知资源返回 404；错误响应 SHALL 包含 `code`、`message` 与 `request_id`。

#### Scenario: 超出范围的 size

- **WHEN** 请求 `size=500`
- **THEN** 系统返回 422，`message` 说明允许范围

#### Scenario: 错误体可关联

- **WHEN** 任意请求返回 4xx 或 5xx
- **THEN** 响应体中的 `request_id` 与响应头 `X-Request-ID` 一致

### Requirement: 埋点接口

系统 SHALL 提供行为上报接口，接受事件类型与商品 id，返回事件 id 与服务端时间戳；上报成功不要求返回完整推荐重算结果。

#### Scenario: 上报后事件可见

- **WHEN** 调用方成功上报一条 `view` 事件
- **THEN** 用该事件 id 可查询到持久化记录，且用户画像与热门统计随之更新

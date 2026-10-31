# ugc-content Specification

## Purpose
提供买家安利内容（图文与短视频封面）的浏览、详情与购买转化，并让每个商品与帖子在离线环境下都有可展示的封面素材。

## Requirements

### Requirement: 商品与帖子封面

系统 SHALL 为每个商品与帖子提供封面：优先使用数据目录中的人工素材，缺失时生成确定性 SVG 封面。

#### Scenario: 无人工素材时生成封面

- **WHEN** 请求某商品的封面且数据目录下没有该商品图片
- **THEN** 返回 `image/svg+xml` 封面，且同一商品多次请求内容完全一致

#### Scenario: 有人工素材时优先真实图片

- **WHEN** 数据目录存在该商品的 `jpg/png/webp` 图片
- **THEN** 封面接口直接返回该图片文件与对应 MIME 类型

### Requirement: 安利帖子列表与详情

系统 SHALL 提供帖子列表（支持按商品筛选与分页）与帖子详情，帖子包含作者、标题、正文、媒体类型、点赞数、关联商品与封面地址。

#### Scenario: 按商品筛选安利

- **WHEN** 请求某商品的安利列表
- **THEN** 返回的每条帖子都关联该商品，且包含 `cover_url`、`media_type`、`likes`

#### Scenario: 帖子详情带购买入口

- **WHEN** 打开一条帖子的详情
- **THEN** 响应包含关联商品摘要（id/标题/价格/封面），供前端渲染"购买同款"

### Requirement: 视频帖子的呈现

视频帖子 SHALL 暴露媒体类型与时长；当数据目录存在对应 mp4 时前端可播放，否则展示封面与播放占位，不伪造播放能力。

#### Scenario: 无视频文件时的占位

- **WHEN** 帖子 `media_type=video` 但数据目录没有对应 mp4
- **THEN** 帖子详情返回 `has_video=false`，前端展示封面 + 时长角标 + 播放按钮，点击不报错

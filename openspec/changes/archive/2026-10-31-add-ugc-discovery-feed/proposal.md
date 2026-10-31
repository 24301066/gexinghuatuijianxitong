# Proposal

## Why

当前交付是"单页推荐工具"：商品没有图片、没有内容生态、推荐只依赖行为事件。目标是把它做成一个成熟的电商内容社区型应用——用户先看买家的安利图文/短视频，被种草后点进商品购买，而"可能喜欢"页要综合**最近搜索关键词**与**图文/视频停留时长**来推荐。同时桌面端必须自带图片与播放体验，不能依赖外网素材。

## What Changes

- 新增买家安利内容（UGC）：帖子含作者、标题、正文、封面、媒体类型（图文/视频）、关联商品、点赞数；商品与帖子互相可跳转。
- 新增离线可用的封面生成：每个商品/帖子按类目与标题确定性地生成 SVG 封面；若数据目录下存在真实图片则优先使用真实图片，视频支持本地 mp4 封面播放。
- 新增行为信号：`search`（关键词）与 `post_dwell`（帖子停留秒数），写入独立表，不破坏既有 `events` 结构。
- 推荐引擎扩展两路信号：关键词兴趣（搜索词 TF-IDF 与商品内容相似）与停留偏好（停留时长加权的帖子→商品关联），并给出对应推荐理由。
- 复合型界面：顶部搜索 + 底部四 Tab（首页/发现/搜索/我的）；首页混合信息流、发现页 UGC 流、帖子详情页、商品详情页增加"买家安利"、搜索页关键词推荐、我的页展示画像与最近搜索。
- 桌面端：内嵌窗口直接可用（不再跳浏览器），封面与视频封面在窗口内渲染。

## Capabilities

### New Capabilities

- `ugc-content`: 买家安利帖子的数据、封面/视频呈现、点赞与帖子详情、帖子与商品关联。
- `discovery-feed`: 复合信息流（首页混合流、发现流、搜索页）与关键词/停留两类个性化信号在界面上的呈现。

### Modified Capabilities

- `recommendation`: 多路召回新增 `keyword` 与 `dwell` 两路，并补充对应推荐理由与来源字段。

## Impact

- 后端：`backend/app/db/models.py`（新增 `posts`/`searches`/`dwells`）、`app/media/`（封面生成）、`app/rec/engine.py`（两路新信号）、`app/api/routes.py`（/posts、/feed、/search、/media、事件扩展、/me/insights）、`app/db/seed.py`（帖子与示例行为）。
- 前端：`web/src` 重构为多页面布局（HomeView/DiscoverView/PostView/SearchView/MeView + 组件），保留登录与关于。
- 接口：`docs/openapi.json` 重新生成；新增 4 组接口。
- 无需新依赖：封面用 stdlib 生成 SVG，视频用本地文件或封面占位。

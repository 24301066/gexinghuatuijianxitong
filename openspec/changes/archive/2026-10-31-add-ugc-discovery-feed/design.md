# Design

## Context

现有系统（v1）已有商品/用户/行为/推荐/桌面壳。v2 要在不破坏既有数据与接口的前提下，加入 UGC 内容、离线封面与两类新个性化信号，并把界面从单页工具改造成内容社区型应用。约束：完全离线、无新依赖、桌面 exe 直接可用。

## Goals / Non-Goals

**Goals**

- 内容可看：帖子有封面（图文）或视频封面+时长，商品有封面，全部离线生成。
- 推荐更准：搜索关键词与帖子停留时长进入推荐融合，能说出理由。
- 界面成型：顶部搜索 + 底部四 Tab，首页混合流、发现流、帖子详情、商品安利区、搜索页、我的页。
- 兼容 v1：旧数据库自动补建新表，不需要重建；既有测试保持通过。

**Non-Goals**

- 不做真实视频转码/上传；视频只支持本地 mp4 直出与封面占位。
- 不做评论、关注、私信、审核等社区治理功能。
- 不做真实图片 CDN；封面为程序生成的示意插画。

## Decisions

### D1 帖子/搜索/停留三张新表，不动 events

`posts(post_id, author_id, title, body, media_type, video_seconds, product_id, likes, tags, created_at)`、
`searches(search_id, user_id, keyword, created_at)`、`dwells(dwell_id, user_id, post_id, seconds, created_at)`。

理由：`events.item_id` 是 NOT NULL，塞入搜索/停留需要迁移老库；新增表用 `create_all` 即可平滑升级，旧库打开时自动补建。行为上报接口按 `type` 分流：`search` → searches，`post_dwell` → dwells，其余仍走 events。

### D2 封面用确定性 SVG，真实图片优先

`app/media/covers.py` 按 `hash(item_id)` 选配色渐变、按类目选图形符号、标题文字上屏，输出 SVG（矢量、几 KB、无依赖）。`GET /api/v1/media/product/{id}.svg`、`/media/post/{id}.svg`；若 `data/media/products/{id}.{jpg,png,webp}` 存在则直接返回真实文件。帖子视频：存在 `data/media/posts/{id}.mp4` 时以 `<video>` 播放，否则显示封面 + 播放按钮 + 时长角标（诚实占位）。

### D3 两路新信号的算法

- 关键词：把用户最近 N 条搜索词拼接后 tokenize，用商品 TF-IDF 矩阵算余弦，得到 `keyword` 分；搜索词也参与"类目偏好"加权。
- 停留：对用户停留过的帖子，取其 `product_id`，按 `min(seconds, 60)/60` 加权累加到该商品及内容相似商品上，得到 `dwell` 分。
- 融合：权重配置新增 `keyword`、`dwell`（默认 0.2 / 0.2，其余等比重归一化），`sources` 增加两个键；理由文案区分"你搜过 X"与"你看了较久的安利"。

### D4 前端信息架构

顶部固定搜索条；底部 Tab：首页 / 发现 / 搜索 / 我的。首页 = 1 张主推安利大卡 + 混合流（商品卡带推荐理由，安利卡带封面/视频角标/点赞）；发现 = 纯 UGC 双列流；帖子详情 = 媒体区 + 作者 + 正文 + 购买同款 + 同类安利；商品详情 = 商品 + 买家安利 + 相似推荐；搜索 = 关键词提交后出结果 + "根据搜索推荐"；我的 = 画像 + 最近搜索 + 停留过的安利 + 可能喜欢。

### D5 停留计时在前端，秒数上报在离开时

帖子详情进入时记录时间戳，`onBeforeUnmount` / 路由离开 / 页面隐藏时上报 `post_dwell{seconds}`（最小 1 秒、上限 10 分钟），并用 sessionStorage 防重复。

## Risks / Trade-offs

- [生成的封面不够"真实照片"] → 明确标注为演示插画；`data/media/` 放真图即可自动替换，代码不变。
- [停留上报可能丢失（关窗口）] → 页面隐藏/路由离开双通道 + 秒数兜底最小值，丢失只影响少量信号。
- [老库升级] → 只新增表，不改旧表结构；`create_all` 幂等。
- [信息流变重导致首屏变慢] → 封面走 SVG（缓存友好）、首页流分页 10 条、接口一次返回帖子与商品摘要避免 N+1。

## Migration Plan

1. 部署新版本后首次启动：`create_all` 自动补建 `posts/searches/dwells`。
2. 种子脚本在商品为空时照旧生成；若 `posts` 为空则补种子帖子（可重复执行不重复插入）。
3. 回滚：旧版本代码忽略新表即可运行，数据不冲突。

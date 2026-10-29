# 个性化推荐系统（电商）

一个可离线运行的电商个性化推荐演示系统：**Windows 桌面应用**为主交付形态，同一份代码也能用浏览器开发模式跑。

- 后端：Python 3.12 + FastAPI + SQLAlchemy + SQLite
- 前端：Vue 3 + Vite（构建产物由后端托管，桌面端装进原生窗口）
- 桌面壳：wxPython 原生窗口 + 系统 WebView2 渲染，PyInstaller 打包
- 推荐：item-CF + TF-IDF 内容相似 + 时间衰减热门 → 归一化加权融合 → MMR 多样性重排
- 评估：按时间切分，Recall@K / NDCG@K / 覆盖率 / 新颖度

## 三条使用路径

### 1. 桌面版（推荐，双击即用）

```powershell
Set-ExecutionPolicy -Scope Process -ExecutionPolicy Bypass -Force
.\desktop\build.ps1            # 构建前端 + PyInstaller 打包 + 压缩 zip
dist\GexingTuijian\GexingTuijian.exe
```

首次启动会在 `%APPDATA%\GexingTuijian` 建库并灌演示数据，断网可用。
渲染细节与兜底逻辑见 [docs/桌面应用.md](docs/桌面应用.md)。

### 2. 源码模式跑桌面壳

```powershell
Set-ExecutionPolicy -Scope Process -ExecutionPolicy Bypass -Force
.\tools\setup_dev.ps1          # 只做一次：建 .venv 并装依赖
.\desktop\run_desktop.ps1
```

### 3. 浏览器开发模式

```powershell
# 终端 A：后端
Set-ExecutionPolicy -Scope Process -ExecutionPolicy Bypass -Force
. .\tools\dev_env.ps1
cd backend; python -m app.main          # http://127.0.0.1:8000/docs

# 终端 B：前端（Vite 代理 /api 到 8000）
cd web; npm install --ignore-scripts; npm run dev   # http://127.0.0.1:5173
```

演示账号：`demo` / `demo1234`，管理员 `admin` / `demo1234`。

## 目录结构

```
backend/             FastAPI 应用、推荐引擎、种子数据、pytest 测试
  app/               api / core / db / rec / runtime
  config/rec.yaml    权重、多样性、评估口径（改完重启生效）
  eval/              离线评估脚本与指标
  tests/             75+ 条单测
desktop/             wx 启动器、PyInstaller spec、打包与运行脚本
web/                 Vue 3 + Vite 前端
tools/               开发环境、种子数据、CSV 导入、冒烟、OpenAPI 导出
docs/                OpenAPI、数据说明、评估说明、桌面说明、测试记录
openspec/            需求与设计的唯一来源（change: ecommerce-recommender-mvp）
```

## 接口

契约见 [docs/openapi.json](docs/openapi.json)（由代码生成，`python tools/dump_openapi.py --check` 可校验漂移），
运行时可看 `http://127.0.0.1:8000/docs`。

| 方法 | 路径 | 说明 |
|---|---|---|
| GET | `/api/v1/health` | 健康检查、数据规模、模型版本 |
| POST | `/api/v1/auth/login` | 演示账号登录，返回 Bearer 令牌 |
| GET | `/api/v1/items` | 商品分页 / 类目筛选 |
| GET | `/api/v1/items/{id}` | 商品详情 |
| GET | `/api/v1/items/{id}/similar` | 相似商品 |
| GET | `/api/v1/recommendations` | 个性化推荐（含 `reason` / `sources` / `degraded`） |
| POST | `/api/v1/events` | 行为上报（view / cart / purchase / rating，30 秒去重） |
| GET | `/api/v1/me/profile` | 用户画像 |
| GET | `/api/v1/admin/metrics` | 管理员指标（普通用户 403） |
| POST | `/api/v1/admin/model/rebuild` | 重建推荐统计 |

## 验证

```powershell
. .\tools\dev_env.ps1
cd backend; python -m pytest tests -q        # 单测
cd ..; python tools\smoke.py                 # 端到端冒烟
python tools\check_frontend.py               # 前端静态资源 + SPA 回退
cd backend; python -m eval.run_eval --data-dir ..\.tmp\appdata --out ..\docs\评估
```

记录见 [docs/测试/集成测试.md](docs/测试/集成测试.md)。

## 文档

- [数据说明](docs/数据说明.md)：演示数据口径、CSV 导入
- [桌面应用](docs/桌面应用.md)：打包、分发、WebView2 依赖与兜底
- [离线评估](docs/评估/README.md)：指标口径与解读
- [OpenAPI 契约](docs/openapi.json)
- [OpenSpec 变更](openspec/changes/ecommerce-recommender-mvp/)：proposal / specs / design / tasks

## 已知限制

- 演示数据是确定性生成的**合成数据**，指标不代表真实业务效果。
- 用户与鉴权是演示级（PBKDF2 + HS256 JWT），没有注册/找回密码/权限体系。
- 桌面端目前只做 Windows（wx + WebView2）；未做代码签名、自动更新。
- 内嵌 Chromium（WebView2）在 DSH 沙箱里只出窗体不出像素，像素级验证需要在普通桌面会话双击 exe 完成。

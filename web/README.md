# web · 前端

Vue 3 + Vite 单页应用，产物 `dist/` 由后端静态托管（桌面端也从同一份产物加载）。

## 开发

```powershell
npm install --ignore-scripts   # 沙箱里必须 --ignore-scripts（esbuild postinstall 会起管道子进程）
npm run dev                    # http://127.0.0.1:5173，/api 代理到 http://127.0.0.1:8000
```

后端在另一个终端跑：

```powershell
cd ..\backend; python -m app.main
```

## 构建

```powershell
npm run build     # 产出 dist/，后端与桌面打包都读这里
```

注意：`vite build` 会起 esbuild 子进程，在 DSH 沙箱里需要一次性提升权限（`danger-full-access`）才能跑通。

## 环境变量

| 变量 | 作用 | 默认 |
|---|---|---|
| `VITE_API_BASE` | 接口前缀（跨域部署时用） | 空，即同源 |
| `VITE_API_TARGET` | dev server 的代理目标 | `http://127.0.0.1:8000` |

## 页面

| 路由 | 说明 |
|---|---|
| `/login` | 演示账号登录（`demo` / `admin`，密码 `demo1234`） |
| `/` | 猜你喜欢推荐流：加载更多、空状态、降级提示条 |
| `/items/:itemId` | 商品详情 + 相似推荐；打开即上报 view（30 秒内不重复）、加购/购买按钮 |
| `/about` | 版本、模型版本、数据规模、推荐口径 |

## 与后端的约定

- 令牌存 `localStorage`（`gt_token` / `gt_user`），请求头 `Authorization: Bearer …`。
- 所有错误按后端错误体渲染：`{code, message, request_id}`；`request_id` 会显示在错误提示里便于排查。
- 行为上报失败不阻断操作，只弹非阻断提示并允许重试。

# 将 CondenseIt 添加到主屏幕

CondenseIt 以 **渐进式 Web 应用（PWA）** 形式提供。安装在手机或平板后，它以独立窗口打开（无浏览器地址栏），并使用与桌面站点相同的摘要阅读器和面板。

## 开始之前

1. **在移动浏览器中打开你的 CondenseIt URL**（例如部署后的 `https://digest.example.com`，或本地测试期间的 LAN URL）。
2. **登录**（如果你的实例使用密码）。主屏幕快捷方式打开相同来源；只要会话未过期或未清除站点数据，你保持登录状态。
3. **生产环境使用 HTTPS**。iOS 和 Android 要求安全上下文以显示安装提示和可靠的离线图标。LAN 上的本地 `http://` 可能适用于测试，但不适合日常使用。

应用清单（`display: standalone`）和图标从已构建的前端（`/manifest.webmanifest`、PNG 图标和 `apple-touch-icon`）提供。

## iOS（iPhone 和 iPad）

使用 **Safari**。iOS 上的其他浏览器可以书签站点，但 Safari 是真正的主屏幕应用可靠路径。

1. 在 Safari 中打开你的 CondenseIt URL。
2. 点击 **分享** 按钮（带向上箭头的正方形）。
3. 滚动共享表并点击 **添加到主屏幕**。
4. 编辑名称（如果需要）（默认：**CondenseIt**），然后点击 **添加**。

图标出现在你的主屏幕上。启动它打开 CondenseIt，没有 Safari 的标签栏。在小屏幕上，头部包含 **刷新** 控件，因为已安装的 PWA 不获得浏览器的重新按钮。

移除它：长按图标，选择 **移除 App**，然后确认。

## Android

使用 **Chrome**（或其他提供 "Install app" 的 Chromium 浏览器）。

### 通过菜单安装

1. 在 Chrome 中打开你的 CondenseIt URL。
2. 点击 **三点菜单** (⋮)。
3. 点击 **Install app** 或 **Add to Home screen**（措辞因 Chrome 版本和设备而异）。
4. 提示时确认。

Chrome 也可能显示 **Install** 横幅或地址栏中的安装图标，当站点满足 PWA 标准时。CondenseIt 不显示自定义应用内安装按钮；使用上述浏览器 UI。

应用从启动器或主屏幕以独立模式打开。与 iOS 一样，移动布局对已安装的仪表板显示 **刷新** 按钮。

移除它：长按图标并卸载，或打开 **设置 → Apps**，找到 CondenseIt（或你选择的名称）并卸载。

## Desktop（可选）

在桌面 Chrome 或 Edge 上，使用地址栏中的安装控件（安装图标或菜单中的 **Install CondenseIt**），如果出现的话。这是可选的；许多人桌面使用正常的浏览器标签。

## 故障排除

| 问题                             | 尝试什么                                                                                                         |
|----------------------------------|------------------------------------------------------------------------------------------------------------------|
| iOS 上 No **Add to Home Screen** | 使用 Safari，而不是应用内浏览器（Slack、Gmail 等）。首先在 Safari 中打开 URL。                                   |
| Android 上 No **Install app**    | 使用 Chrome；更新 Chrome；确保站点通过 HTTPS 加载。                                                              |
| 图标不正确或缺失                 | 在浏览器中硬刷新一次，然后再次添加。图标与前构建捆绑在一起。                                                     |
| 安装后登出                       | 在安装的应用中重新登录；检查 `DIGEST_PWA_SESSION_SECRET`（或部署的会话密钥）在自托管设置中跨服务器重启是否稳定。 |
| 部署后旧内容                     | 在移动上使用头部的 **刷新**，或在你的浏览器支持 standalone 模式时下拉刷新。                                      |

## 相关文档

- [入门指南](getting-started_zh.md)，首次运行和 Web UI 概览
- [VPS 部署](deploy-vps_zh.md)，HTTPS、域名和生产 URL 设置
- [配置](configuration_zh_part1.md)，认证和会话环境变量

# 用 Claude Code 安全操控 iPhone（经 macOS iPhone Mirroring）
2026-08-30 · Kai · 实测于 iPhone iOS 26.6.1 + macOS 15.6 · **可跨 agent 复用**

工具本体 = `~/Desktop/Celine 小红书/apple-notes-mvp/iphone.sh`（复制即用，无依赖除 `cliclick`）

---

## 1 · 结论先行：有哪些通道，该选哪条

| 通道 | 可用性 | 结论 |
|-|-|-|
| **iPhone Mirroring 窗口 + 截图 + cliclick** | ✅ 唯一实际可用 | **推荐**，零配置、零越狱、不碰 provisioning |
| `xcrun devicectl` | ❌ 本机无（需完整 Xcode） | 且不做任意 App 的 UI 自动化 |
| `libimobiledevice` | ❌ 未装 | 需 USB 配对 + developer disk image |
| WebDriverAgent / Appium | ❌ | 要 provisioning profile，重 |
| 官方 API | ❌ **Apple 至今没有 iPhone Mirroring 的公开 API**（开发者论坛多次确认） | 社区方案一律是「截屏 + CGEvent 点击」 |

**镜像窗口不暴露手机端的 accessibility 树**——它是一路视频流。所以**只能靠像素定位**，AX 查询在窗口里拿不到任何手机 UI 元素。

---

## 2 · 安全护栏（这是「安全」的实质，不是口头保证）

`iphone.sh` 的四条硬机制，缺一不可：

1. **每次动作重读窗口实时矩形** —— 绝不用缓存坐标。窗口被移动/缩放也不会点到窗外。
2. **坐标一律窗口内相对值，越界直接 `exit 1`**，不发送任何点击。
   实测：`./iphone.sh tap 999 999` → `REFUSED: (999,999) 超出手机窗口 322x718`
3. **无窗口 = 拒绝执行**。镜像掉线时它挡下了点击，全程零误触。
   （窗口会闪断 → 已加「重试 5 次 + 重新 activate」，但**重试完仍没有窗口就是拒绝**，绝不猜坐标。）
4. **只截窗口矩形**，不截整个桌面（保护旁边的终端/邮件内容）。

⚠️ **cliclick 是全局输入**：点击会抢当前焦点。**人在用电脑时不要跑**（我为此被叫停过一次，见 [[dont-drive-marks-gui]]）。

---

## 3 · 用法

```bash
./iphone.sh rect                 # 窗口矩形（先跑这个确认连着）
./iphone.sh shot out.png         # 只截手机屏
./iphone.sh tap <rx> <ry> [out]  # 点窗口内相对坐标，自动截图
./iphone.sh swipe <x1> <y1> <x2> <y2> [ms]
./iphone.sh type "text"          # 走 System Events 打字
./iphone.sh key <keycode>        # 36=Return 53=Esc 51=Delete
```

**坐标换算**：截图是 2× Retina。在截图里看到某元素在像素 `(x, y)` → `tap` 参数 = `(x/2, y/2)`。
（本机窗口 322×718 pt → 截图 644×1436 px。）

---

## 4 · 踩过的坑（省下的时间比脚本本身值钱）

1. **`osascript` 取窗口坐标必须 `as integer`** —— 不转换会报 `Can't make ... into type text (-1700)`，
   而且返回值里混着逗号，要 `tr -d ',' | tr -s ' '`。
2. **iPhone Mirroring 进程常驻但 `count of windows = 0`** —— 要先 `open -a "iPhone Mirroring"`，
   而且**窗口会在两次 AX 查询之间闪断**，必须重试。
3. **cliclick 的默认点击在镜像里常被识别成长按**（弹出上下文菜单）。加 `-w 30` 缩短按下时长；
   双击会变成「选中单词」。点不动就先 `key code 53` 清掉菜单再点。
4. **中文输入法会吃掉 `keystroke`**（我打 "AskSia Notes" 变成 "A思考Si啊 Notes"）。
   → **一律 `pbcopy` + `⌘V`**，不要用 keystroke 打非 ASCII 或长串。
5. **Enter 要发给进程**：`tell process "iPhone Mirroring" to key code 36`，
   发给全局 System Events 经常不生效。
6. **手机上 Safari 是「恢复上次」**，不会自动拿到你刚部署的新版 → **每次必须点刷新**，否则你在测旧页面。
7. **Mac 上的 Notes/Shortcuts 走 iCloud = 手机的生产环境**。在 Mac 上造的测试数据会同步到手机。
   要测就一次一条 + 读数据库验证，**绝不批量写**。
8. **镜像会话会自己超时断开**（手机被拿起、锁屏、闲置）。长流程要在每步前 `rect` 确认。

---

## 5 · 什么时候该用它，什么时候不该

**该用**：验证「真机上这个交互到底会不会发生」——分享面板里出不出现某个 App、系统弹窗长什么样、
导入后的产物真实结构。这些**在模拟器和 Mac 上都会给出错误答案**（我在 macOS 15.6 上测一个
iOS 26 才有的能力，烧了 8 轮才发现实验室选错了）。

**不该用**：能用 API / 文件层 / 数据库直接验证的事。像素点击是最贵最脆的手段，
只在「必须看真机 UI 才知道」时才动。

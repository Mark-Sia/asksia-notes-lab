# 增长实验收口：AskSia Library → Apple Notes
2026-08-30 · Kai · **实验结束**（Mark 指令：不要污染正常工作流）

---

## 实验问的问题
把已上线的 course bible 压成一条「结构化秘籍」，让学生**一键放进自己的 Apple 备忘录** —— 技术上做得到吗？做到什么程度？

## 一句话答案
**做得到，但 iOS 强制你在「排版」和「图」之间二选一，不存在同时拿到两者又少交互的路径。**
默认版取「排版 + 零安装」，因为这是**唯一能覆盖全体 C 端用户**的形态。

---

## 交付物（全部在线可体验）

**https://mark-sia.github.io/asksia-notes-lab/n/ecb1101/**

| 用户 | 默认路径 | 需要安装 | 得到 |
|-|-|-|-|
| iOS 26+ | 点按钮 → 选**备忘录** → **导入** | **无** | 排版完整的 note：标题 / 加粗 / 列表 / 双语术语 / 真 tag，图为可点链接 |
| 安卓 · 桌面 · 旧 iOS | 点按钮 → 富文本进剪贴板 → 粘贴 | 无 | 全保真**含图** |
| 重度用户 | **Power mode**（一次性装 Shortcut） | 有，opt-in | 图**内联**在 note 里 |

内容全部来自已上线的 Monash ECB1101 bible（23 页 → 1 条 note），配 Ada 08-28 用 Sia `/studyguide` 真生成的图，**零编造**。

---

## 三份 learnings 文档

1. **`KILL-TEST-2026-08-30.md`** —— 7 条技术路径的实测矩阵 + 根因定位（**主文档**）
2. **`IPHONE-CONTROL-RUNBOOK.md`** —— 用 Claude Code 安全操控 iPhone 的工具与 8 条坑（**已递 Athena 共享**）
3. **`REFLECTION-2026-08-30.md`** —— 中途被叫停时的过程复盘

---

## 技术定论（省下后来人的时间）

**根因**：iOS 里有**两个互斥的转换器**。
- **Notes 自己的 Markdown importer**（系统级、只吃 `.md`）——**保排版，但明确不解析图片资源**：远程 URL 和 data URI 一视同仁降级成链接。
- **Shortcuts 的 `Get Rich Text from HTML`** —— 产物跨进程时已被降为 plain，后面接 `Create Note` / `Append` / `Share` 结果都一样拍平。

**同时被证伪的**：`.html` 文件（备忘录根本不出现在 iOS 分享面板）· `.md`+图一起分享（两个都变成附件，文字不转换）· Safari 网页分享（只存成一个链接）。

**同时被证实的新能力**：`AddFileAttachmentLinkAction`（"Add File"）能把图**内联**进指定 note 且**全程零 UI**；`Create Note` 的正文键是 legacy `WFCreateNoteInput`，`Append to Note` 是 `WFInput`。

---

## 三条会复用的元教训

1. **能力可行 ≠ 该做默认。** Shortcut 方案技术上跑通了，但要求每个 C 端用户装快捷指令 + 点两次 iOS 权限弹窗，还只覆盖 iOS —— 装机门槛会把「学生想不想要」这个信号彻底淹掉。**面向 C 端先问覆盖率，再问优雅度。**
2. **先确认实验室对不对。** 我在 macOS 15.6 上测 iOS 26 才有的能力，烧了 8 轮。
3. **变体第 2 个还不对就停下查原理。** 今天真正的答案（Create Note 强制降级为纯文本，是 Apple 设计）一次 web 搜索就有，我却先烧了 8 轮 GUI。

---

## 现场已清理
- 手机 & Mac 的测试 note：**全删**
- 测试 Shortcut：**全删**（`shortcuts list | grep AskSia` = 0）
- 后台自动化：**0**
- iCloud 云盘 `AskSia-Notes-Test/` 文件夹已无用，可删

## 如果以后要重启
只需 `content.py` 加一门课 + `python3 build.py` + push。所有零件已验证，**不要再去试 Markdown 带图**。

# 🐉 天火五维共振雷达 - Streamlit Cloud 部署指南

> **版本**: 2026.06.12  
> **作者**: jack@ailobstermedia  
> **定位**: 公域引流工具 · 零分数 · 零买卖建议 · 强制合规

---

## 📦 文件结构

```
streamlit_app/
├── app.py                  # 主应用（零分数雷达 + 合规文案 + 星球引流）
├── requirements.txt        # Python依赖
├── precompute_cache.py     # 预计算缓存脚本（解决Cloud资源限制）
├── cache/                  # 预计算缓存目录（运行时自动生成）
│   ├── 000001.json
│   ├── 300308.json
│   └── _meta.json
└── .streamlit/
    └── config.toml         # 主题与服务器配置
```

---

## 🚀 5分钟部署步骤

### Step 1: 准备 GitHub 仓库

1. 新建 GitHub 仓库（如 `tianhuo-radar`）
2. 将本目录所有文件上传至仓库根目录
3. **关键**: 确保 `app.py` 在仓库根目录（或调整 Streamlit Cloud 启动路径）

### Step 2: 配置 Secrets（环境变量）

在 Streamlit Cloud 控制台 → App → Settings → Secrets，添加：

```toml
TUSHARE_TOKEN = "你的tushare_token"
# 如有其他API Key，在此添加
```

> 注意：如果评分脚本依赖 `TUSHARE_TOKEN` 环境变量，app.py 已自动从 Secrets 读取并注入。

### Step 3: 连接 Streamlit Cloud

1. 访问 [share.streamlit.io](https://share.streamlit.io)
2. 点击 **New app** → 选择 GitHub 仓库
3. 主文件路径: `app.py`
4. 点击 **Deploy**

### Step 4: 自定义域名（可选）

在 Streamlit Cloud Settings → Domain 中绑定自定义域名：
- 建议: `radar.ailobstermedia.com` 或类似
- 需要在你的 DNS 提供商添加 CNAME 记录

---

## ⚙️ 路径适配（重要）

app.py 会自动探测以下路径，**无需修改即可运行**：

| 环境 | 自动探测路径 |
|------|-------------|
| 本地开发 | `~/LobsterLite` / 当前工作目录 |
| Streamlit Cloud | `/app` / 仓库根目录 |
| 自定义部署 | `app.py` 的上级目录 |

**如果评分脚本在子目录**，app.py 会自动将以下目录加入 `sys.path`：
- `bots/`
- `tools/`
- `fivewaves/`
- `skyfire2026/`

> 如果评分模块仍无法导入，请检查 `score_md_stocks_deep.py` 或 `single_stock_score.py` 是否在上述目录中。

---

## 🎨 运营配置清单

### 1. 替换星球二维码

在 `app.py` 中搜索 `星球二维码占位`，替换为真实二维码：

```html
<!-- 替换前 -->
<div class="qr-placeholder">
    <p>🌍 星球二维码占位</p>
</div>

<!-- 替换后 -->
<div class="qr-placeholder">
    <img src="https://你的图床地址/qr.png" width="160" alt="星球二维码">
    <p style="margin:4px 0 0 0;font-size:12px;color:#6b7280;">微信扫码，即刻加入</p>
</div>
```

### 2. 公众号菜单配置

公众号后台 → 自定义菜单 → 添加菜单：
- **菜单名称**: 五维雷达
- **菜单类型**: 跳转网页
- **网页链接**: `https://你的streamlit域名/?ref=mp`

### 3. 引流文章模板（公众号）

**标题**: 《免费股票雷达，输入代码看五维图》

**正文要点**:
```
我们做了一个免费工具：输入任意股票代码，生成五维雷达图。

不收费、不注册、不留下任何个人信息。

但有三条铁律：
1. 不显示具体分数（只给颜色）
2. 不给任何买卖建议
3. 所有数据来自公开渠道

完整版8问评分、次日监控池、周期策略，在星球更新。

👉 点击菜单栏「五维雷达」直接使用
👉 或访问：你的域名
```

### 4. 抖音视频结尾话术

```
"想知道你的股票五维图长什么样？
输入代码，免费生成雷达图。
链接我放在评论区置顶了，自取。"
```

---

## 🛡️ 合规检查清单（必须逐项确认）

| 检查项 | 状态 | 说明 |
|--------|------|------|
| 雷达图无径向刻度 | ✅ | `showticklabels=False` |
| Hover不显示数值 | ✅ | `hovertemplate='%{theta}<extra></extra>'` |
| 五维卡片无具体分数 | ✅ | 只显示 🟢积极/🟡中性/🔴谨慎 |
| 无"买入/卖出/持有"字样 | ✅ | 全页面零买卖建议 |
| 强制合规文案 | ✅ | 底部黄色警示框 |
| 星球二维码占位 | ✅ | 需替换为真实图片 |
| 页脚免责声明 | ✅ | "不构成任何投资建议" |
| 无收益率承诺 | ✅ | 无"稳赚/必涨/翻倍"等词汇 |

---

## ⚡ 性能优化（预计算缓存）

Streamlit Cloud 免费版限制：**1GB RAM / 1 CPU**，评分脚本若实时计算大量数据会超时。

### 方案 A: 预计算缓存（推荐）

在本地或服务器定时运行：

```bash
# 本地开发机（你的Dell 7460）定时执行
cd ~/LobsterLite/streamlit_app
python precompute_cache.py

# 自动提交到GitHub（让Cloud读取最新缓存）
git add cache/
git commit -m "cache update: $(date +%Y%m%d)"
git push
```

**crontab 定时（每天15:35盘后）**:
```bash
35 15 * * 1-5 cd ~/LobsterLite/streamlit_app && python precompute_cache.py && cd ~/LobsterLite && git add streamlit_app/cache/ && git commit -m "cache:$(date +\%Y\%m\%d)" && git push
```

### 方案 B: 精简评分逻辑

如果无法预计算，修改 `score_md_stocks_deep.py`：
- 减少并发请求数
- 禁用非必要的数据源
- 使用 `@st.cache_data` 缓存已计算结果（app.py已内置30分钟缓存）

---

## 🔧 故障排查

| 问题 | 原因 | 解决 |
|------|------|------|
| 模块找不到 | 路径未探测到 | 检查 `score_md_stocks_deep.py` 是否在 `bots/`/`tools/`/`fivewaves/` 中 |
| Tushare Token无效 | Secrets未配置 | 在 Streamlit Cloud Settings → Secrets 添加 `TUSHARE_TOKEN` |
| 页面超时 | 实时计算太重 | 使用 `precompute_cache.py` 预生成缓存 |
| 雷达图不显示 | plotly版本问题 | 确保 `requirements.txt` 中 `plotly>=5.18.0` |
| 样式错乱 | Streamlit版本低 | 确保 `streamlit>=1.28.0` |

---

## 📡 与现有系统联动

```
本地Dell 7460（15:30盘后）
    ├── 运行 precompute_cache.py → 生成 cache/*.json
    ├── git push 到 GitHub
    └── Streamlit Cloud 自动拉取最新缓存

用户访问流程：
    公众号菜单 / 抖音评论区 / 文章链接
        → 打开 Streamlit Cloud 页面
        → 输入股票代码
        → 读取 cache（毫秒级）或实时计算
        → 展示零分数雷达图
        → 底部引流至星球/公众号
```

---

## 📝 更新日志

**2026.06.12** - V1.0 初始版本
- 零分数雷达图（无径向刻度、无hover数值）
- 五维状态卡片（积极/中性/谨慎）
- 强制合规文案 + 星球引流占位
- 预计算缓存机制（解决Cloud资源限制）
- 自动路径探测（适配本地/云端多环境）
- Streamlit Secrets 集成（TUSHARE_TOKEN）

---

## ⚠️ 法律声明

本工具仅展示公开数据的可视化分布，**不构成任何投资建议**。完整评分与决策工具仅限付费会员获取。用户应独立判断并承担投资风险。

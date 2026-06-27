"""
天火五维共振雷达 - Streamlit Cloud 部署版
合规要求：零分数显示 | 零买卖建议 | 强制风险提示
增强版：核心财务数据 + 资金流向 + 标签 + HTML报告下载
作者: jack@ailobstermedia
版本: 2026.06.26-enhanced
"""

import streamlit as st
import sys
import os
import json
import random
from pathlib import Path
from datetime import datetime
import textwrap
import base64
import requests

# ==================== 使用统计（仅管理者可见）====================
import uuid
from collections import Counter

def get_client_id():
    if "client_id" not in st.session_state:
        st.session_state.client_id = str(uuid.uuid4())[:8]
    return st.session_state.client_id

def log_access(stock_code: str, source: str):
    """记录访问日志：飞书群机器人 + Supabase（如配置）"""
    client_id = get_client_id()
    now_str = datetime.now().strftime("%Y-%m-%d %H:%M:%S")

    # 方案A：飞书群机器人（实时通知，零成本）
    webhook = st.secrets.get("FEISHU_WEBHOOK_URL", "")
    if webhook:
        try:
            requests.post(webhook, json={
                "msg_type": "text",
                "content": {"text": f"🐉 雷达查询\n股票：{stock_code}\n来源：{source}\n时间：{now_str}\n会话：{client_id}"}
            }, timeout=3)
        except Exception:
            pass

    # 方案B：Supabase（结构化统计，见下文）
    supabase_url = st.secrets.get("SUPABASE_URL", "")
    supabase_key = st.secrets.get("SUPABASE_KEY", "")
    if supabase_url and supabase_key:
        try:
            requests.post(
                f"{supabase_url}/rest/v1/radar_logs",
                headers={
                    "apikey": supabase_key,
                    "Authorization": f"Bearer {supabase_key}",
                    "Content-Type": "application/json",
                    "Prefer": "return=minimal"
                },
                json={
                    "stock_code": stock_code,
                    "source": source,
                    "session_id": client_id,
                    "accessed_at": datetime.utcnow().isoformat()
                },
                timeout=3
            )
        except Exception:
            pass

# ==================== 路径自适应 ====================
POSSIBLE_ROOTS = [
    Path(__file__).parent.parent,
    Path.home() / "LobsterLite",
    Path.cwd(),
    Path("/app"),
]

PROJECT_ROOT = None
for root in POSSIBLE_ROOTS:
    if root.exists() and any((root / d).exists() for d in ["bots", "tools", "fivewaves", "skyfire2026"]):
        PROJECT_ROOT = root
        break

if PROJECT_ROOT:
    for sub in ["", "bots", "tools", "fivewaves", "skyfire2026"]:
        p = str(PROJECT_ROOT / sub) if sub else str(PROJECT_ROOT)
        if p not in sys.path:
            sys.path.insert(0, p)

# ==================== 环境变量读取 ====================
def get_secret(key: str, default: str = "") -> str:
    try:
        return st.secrets.get(key, os.environ.get(key, default))
    except Exception:
        return os.environ.get(key, default)

TUSHARE_TOKEN = get_secret("TUSHARE_TOKEN", "")
if TUSHARE_TOKEN:
    os.environ["TUSHARE_TOKEN"] = TUSHARE_TOKEN

# ==================== 模块探测 ====================
MD_AVAILABLE = False
Q8_AVAILABLE = False
_score_md = None
_score_8q = None

try:
    from score_md_stocks_deep import score_stock as _score_md
    MD_AVAILABLE = True
except Exception:
    pass

try:
    from single_stock_score import score_stock as _score_8q
    Q8_AVAILABLE = True
except Exception:
    pass

# ==================== 页面配置 ====================
st.set_page_config(
    page_title="天火五维共振雷达",
    page_icon="🐉",
    layout="centered",
    initial_sidebar_state="collapsed"
)

# ==================== 自定义CSS ====================
st.markdown("""
<style>
    .stProgress > div > div > div > div { color: transparent !important; }

    /* 股票信息栏 */
    .stock-info-bar {
        background: linear-gradient(135deg, #f0f9ff 0%, #e0f2fe 100%);
        border-radius: 12px;
        padding: 16px 20px;
        margin: 12px 0 20px 0;
        border: 1px solid #bae6fd;
        display: flex;
        justify-content: space-between;
        align-items: center;
        flex-wrap: wrap;
        gap: 12px;
    }
    .stock-info-bar .stock-name {
        font-size: 18px;
        font-weight: 700;
        color: #0c4a6e;
    }
    .stock-info-bar .stock-meta {
        font-size: 13px;
        color: #0369a1;
    }
    .stock-info-bar .data-source {
        font-size: 12px;
        color: #64748b;
        background: #ffffff;
        padding: 4px 10px;
        border-radius: 20px;
        border: 1px solid #e2e8f0;
    }

    /* 雷达图容器 */
    .radar-box {
        background: #ffffff;
        border-radius: 16px;
        padding: 20px;
        margin: 16px 0;
        border: 1px solid #e2e8f0;
        box-shadow: 0 1px 3px rgba(0,0,0,0.05);
    }

    /* 五维卡片 */
    .dim-card-outer {
        background: #ffffff;
        border-radius: 12px;
        padding: 16px 8px;
        text-align: center;
        border: 1px solid #e2e8f0;
        box-shadow: 0 1px 3px rgba(0,0,0,0.04);
        transition: transform 0.2s, box-shadow 0.2s;
    }
    .dim-card-outer:hover {
        transform: translateY(-2px);
        box-shadow: 0 4px 12px rgba(0,0,0,0.08);
    }
    .dim-card-outer .dim-name {
        font-size: 13px;
        color: #475569;
        font-weight: 600;
        margin-bottom: 8px;
    }
    .dim-card-outer .dim-emoji {
        font-size: 32px;
        margin: 4px 0;
    }
    .dim-card-outer .dim-status {
        font-size: 13px;
        font-weight: 700;
        margin: 6px 0 10px 0;
    }
    .dim-card-outer .dim-bar-bg {
        background: #f1f5f9;
        border-radius: 6px;
        height: 8px;
        overflow: hidden;
        margin-top: 4px;
    }
    .dim-card-outer .dim-bar-fill {
        height: 100%;
        border-radius: 6px;
        transition: width 0.8s ease-out;
    }

    /* 未覆盖提示 */
    .uncovered-box {
        background: linear-gradient(135deg, #fef2f2 0%, #fee2e2 100%);
        border-radius: 12px;
        padding: 24px;
        margin: 20px 0;
        border: 1px solid #fecaca;
        text-align: center;
    }
    .uncovered-box h3 {
        color: #991b1b;
        margin: 0 0 12px 0;
        font-size: 18px;
    }
    .uncovered-box p {
        color: #7f1d1d;
        font-size: 14px;
        line-height: 1.6;
        margin: 0;
    }

    /* 合规文案 */
    .compliance-box {
        background-color: #fffbeb;
        border-left: 5px solid #f59e0b;
        padding: 16px;
        border-radius: 8px;
        margin: 24px 0;
        color: #92400e;
        font-size: 14px;
        line-height: 1.6;
    }

    /* 星球CTA */
    .planet-cta {
        background: linear-gradient(135deg, #4f46e5 0%, #7c3aed 100%);
        color: white;
        padding: 28px;
        border-radius: 16px;
        text-align: center;
        margin-top: 32px;
        box-shadow: 0 10px 25px -5px rgba(0, 0, 0, 0.3);
    }
    .qr-placeholder {
        background: white;
        padding: 12px;
        border-radius: 8px;
        display: inline-block;
        margin-top: 12px;
        color: #1f2937;
    }

    /* 页脚 */
    .footer-text {
        text-align: center;
        color: #64748b;
        font-size: 12px;
        margin-top: 40px;
        padding-top: 20px;
        border-top: 1px solid #e2e8f0;
    }

    /* 增强版报告样式 */
    .enhanced-section {
        margin: 16px 0;
    }
    .metric-card {
        background: #ffffff;
        border-radius: 12px;
        padding: 16px;
        border: 1px solid #e2e8f0;
        text-align: center;
    }
    .metric-label {
        font-size: 12px;
        color: #64748b;
        margin-bottom: 4px;
    }
    .metric-value {
        font-size: 20px;
        font-weight: 700;
        color: #1e293b;
    }
    .tag-pill {
        display: inline-block;
        background: linear-gradient(135deg, #ffebee 0%, #ffcdd2 100%);
        color: #c62828;
        padding: 4px 12px;
        border-radius: 20px;
        font-size: 12px;
        font-weight: 500;
        margin: 4px;
    }
</style>
""", unsafe_allow_html=True)

# ==================== 缓存与数据层 ====================
@st.cache_data(ttl=1800, show_spinner=False)
def get_score_result(stock_code: str, mode: str = "auto"):
    """获取评分结果：优先预计算缓存 → 实时计算 → 未覆盖提示"""

    cache_dir = Path(__file__).parent / "cache"
    cache_file = cache_dir / f"{stock_code}.json"

    # 1. 尝试读取预计算缓存（验证数据有效性）
    if cache_file.exists():
        try:
            with open(cache_file, 'r', encoding='utf-8') as f:
                cached = json.load(f)

            dims = cached.get('dimensions', {})
            # 验证：dimensions 存在且至少有一个值 > 0
            if dims and any(v > 0 for v in dims.values()):
                cached["_source"] = "cache"
                if 'radar_chart' not in cached or cached['radar_chart'] is None:
                    cached['radar_chart'] = _build_radar(dims)
                return cached
            else:
                # 缓存存在但数据无效（空 dimensions），删除旧缓存
                cache_file.unlink()
        except Exception:
            pass

    # 2. 缓存未命中/无效，尝试实时计算（Cloud 上可能可用）
    try:
        from scorer_adapter import score_stock as cloud_scorer
        result = cloud_scorer(stock_code)
        if result and result.get('dimensions') and any(v > 0 for v in result['dimensions'].values()):
            # 保存到缓存，下次更快
            result["_source"] = "realtime"
            try:
                with open(cache_file, 'w', encoding='utf-8') as f:
                    json.dump(result, f, ensure_ascii=False, indent=2)
            except:
                pass
            return result
    except Exception:
        pass

    # 3. 本地模块实时计算（开发环境）
    if mode == "md" and MD_AVAILABLE:
        raw = _score_md(stock_code)
        return _standardize_result(raw, source="md")
    elif mode == "8q" and Q8_AVAILABLE:
        raw = _score_8q(stock_code)
        return _adapt_8q(raw)
    elif mode == "auto":
        if MD_AVAILABLE:
            raw = _score_md(stock_code)
            return _standardize_result(raw, source="md")
        elif Q8_AVAILABLE:
            raw = _score_8q(stock_code)
            return _adapt_8q(raw)

    # 4. 未覆盖提示（不显示模拟数据）
    return _uncovered_data(stock_code)

def _standardize_result(raw: dict, source: str = "md") -> dict:
    result = dict(raw) if isinstance(raw, dict) else {}
    dims = result.get('dimensions') or result.get('五维') or {}
    if not dims:
        dims = {
            "趋势动能": result.get('趋势', result.get('trend', 50)),
            "资金质量": result.get('资金', result.get('fund', 50)),
            "估值安全": result.get('估值', result.get('value', 50)),
            "基本面": result.get('基本面', result.get('fundamental', 50)),
            "周期位置": result.get('周期', result.get('cycle', 50))
        }
    result['dimensions'] = dims
    if 'radar_chart' not in result or result['radar_chart'] is None:
        result['radar_chart'] = _build_radar(dims)
    result["_source"] = source
    return result

def _adapt_8q(raw: dict) -> dict:
    dims = {
        "趋势动能": raw.get('Q1_趋势', raw.get('趋势', 50)),
        "资金质量": raw.get('Q6_资金', raw.get('资金', 50)),
        "估值安全": raw.get('Q3_估值', raw.get('估值', 50)),
        "基本面": raw.get('Q2_业绩', raw.get('业绩', 50)),
        "周期位置": raw.get('Q8_周期', raw.get('周期', 50))
    }
    return {
        'dimensions': dims,
        'radar_chart': _build_radar(dims),
        '_source': '8q'
    }

def _build_radar(dims: dict):
    import plotly.graph_objects as go
    categories = list(dims.keys())
    values = list(dims.values())
    values.append(values[0])
    avg = sum(dims.values()) / len(dims) if dims else 50
    if avg >= 70:
        fill_color = 'rgba(34, 197, 94, 0.25)'
        line_color = 'rgb(34, 197, 94)'
    elif avg >= 40:
        fill_color = 'rgba(234, 179, 8, 0.25)'
        line_color = 'rgb(234, 179, 8)'
    else:
        fill_color = 'rgba(239, 68, 68, 0.25)'
        line_color = 'rgb(239, 68, 68)'
    fig = go.Figure(data=go.Scatterpolar(
        r=values,
        theta=categories + [categories[0]],
        fill='toself',
        fillcolor=fill_color,
        line=dict(color=line_color, width=2.5),
        name='五维评估',
        hovertemplate='%{theta}<extra></extra>'
    ))
    fig.update_layout(
        polar=dict(
            radialaxis=dict(
                visible=True, range=[0, 100], showticklabels=False, ticks='',
                gridcolor='#e2e8f0', gridwidth=1
            ),
            angularaxis=dict(
                tickfont=dict(size=13, color='#475569'),
                gridcolor='#e2e8f0', linecolor='#e2e8f0'
            ),
            bgcolor='rgba(0,0,0,0)'
        ),
        showlegend=False,
        paper_bgcolor='rgba(0,0,0,0)',
        plot_bgcolor='rgba(0,0,0,0)',
        margin=dict(l=30, r=30, t=30, b=30),
        height=380
    )
    return fig

def _uncovered_data(stock_code: str) -> dict:
    """未覆盖股票：返回专业提示，不显示模拟数据"""
    return {
        'dimensions': {
            "趋势动能": 0,
            "资金质量": 0,
            "估值安全": 0,
            "基本面": 0,
            "周期位置": 0
        },
        'radar_chart': None,
        '_source': 'uncovered',
        '_notice': '该股票暂未纳入日常监控池',
        'name': stock_code,
        'ts_code': f"{stock_code}.SZ"
    }

def _get_qr_base64(path: str = "planet_qr.png") -> str:
    """自动读取本地二维码图片转 base64，无需手动粘贴字符串"""
    try:
        with open(path, "rb") as f:
            return base64.b64encode(f.read()).decode()
    except Exception:
        return ""

def _status_badge(score: int) -> tuple:
    if score >= 70:
        return ("#16a34a", "积极", "🟢")
    elif score >= 40:
        return ("#ca8a04", "中性", "🟡")
    else:
        return ("#dc2626", "谨慎", "🔴")


# ==================== [新增] 增强版报告展示 ====================

show_enhanced_report


def generate_html_for_streamlit(data: dict) -> str:
    """生成可下载的单文件HTML报告（兼容缺失字段）"""
    
    name = data.get('name', data.get('ts_code', '未知'))
    code = data.get('ts_code', '')
    current = data.get('current', '')
    rating = data.get('rating', '')
    total = data.get('total', 0)
    industry = data.get('industry', '') or data.get('申万行业', '')
    
    # 五维
    dims = data.get('dimensions', {})
    fundamental = min(dims.get("基本面", 0) + dims.get("赛道", 0) + dims.get("护城河", 0), 100)
    trend = min(dims.get("趋势动能", 0) + dims.get("月线MACD", 0) + dims.get("结构突破", 0), 100)
    fund = min(dims.get("资金质量", 0) + dims.get("流量", 0) + dims.get("流向", 0), 100)
    value = min(dims.get("估值安全", 0) + dims.get("价位买点", 0) + dims.get("消息面", 0), 100)
    cycle = min(dims.get("周期位置", 0) + dims.get("大盘加分", 0), 100)
    
    # 财务（兼容缺失）
    profit = data.get('profit') or data.get('利润(亿)', 'N/A')
    roe = data.get('roe') or data.get('ROE', 'N/A')
    g26 = data.get('g26') or data.get('2026E', 'N/A')
    target = data.get('target') or data.get('目标价(元)', 'N/A')
    eps = data.get('eps') or data.get('EPS', 'N/A')
    deviation = data.get('deviation') or data.get('偏离度(%)', 'N/A')
    industry_flow = data.get('industry_flow') or data.get('行业净流入(亿)', 'N/A')
    stock_flow = data.get('stock_flow') or data.get('主力净流入(万元)', 'N/A')
    tags = data.get('tags', '')
    
    # 标签HTML
    tags_html = ""
    if tags and str(tags) not in ['N/A', 'None', '']:
        for t in str(tags).split(","):
            if t.strip():
                tags_html += f'<span class="tg">{t.strip()}</span>'
    
    # 评级颜色
    rating_color = "#e74c3c"
    if rating == "增持":
        rating_color = "#e67e22"
    elif rating == "中性观望":
        rating_color = "#f39c12"
    elif rating in ["减持", "清仓离场"]:
        rating_color = "#95a5a6"
    
    # 财务数据行（有则显示，无则隐藏）
    finance_row = ""
    if str(profit) not in ['N/A', 'None', ''] or str(roe) not in ['N/A', 'None', '']:
        finance_row = f'<div class="card"><div class="card-title">核心财务</div><div class="grid-3"><div class="item"><div class="item-l">净利润</div><div class="item-v">{profit}亿</div></div><div class="item"><div class="item-l">ROE</div><div class="item-v">{roe}%</div></div><div class="item"><div class="item-l">2026E增速</div><div class="item-v">{g26}%</div></div></div></div>'
    
    # 资金流向行
    flow_row = ""
    if str(industry_flow) not in ['N/A', 'None', ''] or str(stock_flow) not in ['N/A', 'None', '']:
        flow_row = f'<div class="card"><div class="card-title">资金流向</div><div class="grid-2"><div class="item"><div class="item-l">行业主力净流入</div><div class="item-v">{industry_flow}亿</div></div><div class="item"><div class="item-l">个股5日主力净流入</div><div class="item-v">{stock_flow}万</div></div></div></div>'
    
    # 标签行
    tags_row = ""
    if tags_html:
        tags_row = f'<div class="card"><div class="card-title">标签</div><div>{tags_html}</div></div>'
    
    html = f"""<!DOCTYPE html>
<html lang="zh-CN"><head><meta charset="UTF-8">
<meta name="viewport" content="width=device-width, initial-scale=1.0">
<title>天火评分 - {name}</title>
<style>
body{{font-family:-apple-system,BlinkMacSystemFont,"Segoe UI",Roboto,sans-serif;background:#f5f7fa;padding:20px;margin:0;color:#333}}
.container{{max-width:700px;margin:0 auto}}
.header{{background:linear-gradient(135deg,#1a1a2e,#16213e);border-radius:16px;padding:24px;color:#fff;margin-bottom:16px}}
h1{{margin:0;font-size:24px}}.code{{opacity:0.7;font-size:13px;margin-top:4px}}
.rating{{display:inline-block;padding:4px 14px;border-radius:20px;font-size:13px;font-weight:600;margin-top:8px;background:{rating_color}}}
.stats{{display:grid;grid-template-columns:repeat(4,1fr);gap:10px;margin-top:16px;padding-top:16px;border-top:1px solid rgba(255,255,255,0.1);text-align:center}}
.stat-v{{font-size:16px;font-weight:700;color:#ffd700}}.stat-l{{font-size:11px;opacity:0.6;margin-top:2px}}
.card{{background:#fff;border-radius:16px;padding:20px;margin-bottom:16px;box-shadow:0 2px 8px rgba(0,0,0,0.04)}}
.card-title{{font-size:16px;font-weight:700;margin-bottom:12px;display:flex;align-items:center;gap:6px}}
.card-title::before{{content:"";width:3px;height:16px;background:#e74c3c;border-radius:2px}}
.grid-3{{display:grid;grid-template-columns:repeat(3,1fr);gap:10px}}
.grid-2{{display:grid;grid-template-columns:repeat(2,1fr);gap:10px}}
.item{{background:#f8f9fa;border-radius:10px;padding:12px;text-align:center}}
.item-l{{font-size:11px;color:#78909c;margin-bottom:4px}}
.item-v{{font-size:16px;font-weight:700;color:#2c3e50}}
.tg{{display:inline-block;background:linear-gradient(135deg,#ffebee,#ffcdd2);color:#c62828;padding:3px 10px;border-radius:20px;font-size:12px;margin:4px}}
.disclaimer{{background:#fff8e1;border:1px solid #ffe0b2;border-radius:12px;padding:14px;margin-top:16px;color:#92400e;font-size:12px;line-height:1.6}}
@media(max-width:600px){{.grid-3,.grid-2{{grid-template-columns:1fr}}.stats{{grid-template-columns:repeat(2,1fr)}}}}
</style></head><body><div class="container">
<div class="header"><h1>{name}</h1><div class="code">{code}　当前价 ¥{current}</div><div class="rating">{rating}</div>
<div class="stats"><div><div class="stat-v">{total}</div><div class="stat-l">综合评分</div></div><div><div class="stat-v">{roe}%</div><div class="stat-l">ROE</div></div><div><div class="stat-v">{g26}%</div><div class="stat-l">2026E</div></div><div><div class="stat-v">{target}</div><div class="stat-l">目标价</div></div></div></div>
<div class="card"><div class="card-title">五维评估</div><div class="grid-3"><div class="item"><div class="item-l">基本面</div><div class="item-v">{fundamental}</div></div><div class="item"><div class="item-l">趋势动能</div><div class="item-v">{trend}</div></div><div class="item"><div class="item-l">资金质量</div><div class="item-v">{fund}</div></div><div class="item"><div class="item-l">估值安全</div><div class="item-v">{value}</div></div><div class="item"><div class="item-l">周期位置</div><div class="item-v">{cycle}</div></div></div></div>
{finance_row}
{flow_row}
{tags_row}
<div class="disclaimer"><strong>⚠️ 不构成投资建议</strong><br>本报告仅展示公开数据可视化，所有决策需由投资者独立判断。完整12维评分与次日监控池仅限星球会员。</div>
</div></body></html>"""
    
    return html

# ==================== UI 主体 ====================
st.title("🐉 天火五维共振雷达")
st.markdown("<p style='color:#475569;font-size:14px;margin-top:-10px;margin-bottom:20px;'>输入6位股票代码，查看五维分布雷达（公开数据可视化 · 零分数 · 零建议）</p>", unsafe_allow_html=True)

code = st.text_input("股票代码", placeholder="如 000001、300308、601899", max_chars=6, label_visibility="collapsed")

if code:
    clean = code.strip()
    if clean.isdigit() and len(clean) == 6:
        with st.spinner("系统扫描中..."):
            try:
                result = get_score_result(clean, mode="auto")
                # 记录访问日志（仅管理者可见）
                source = result.get('_source', 'unknown')                
                log_access(clean, source)


                # === 未覆盖股票：显示专业提示 ===
                if source == 'uncovered':
                    st.markdown(f"""
                    <div class="uncovered-box">
                        <h3>📡 {clean} 暂未纳入日常监控池</h3>
                        <p>
                            天火系统每日盘后自动扫描 <b>龙一/龙二/观察梯队</b> 及 <b>沪深300核心标的</b>。<br>
                            该股票当前不在预计算覆盖范围内。<br><br>
                            🔍 <b>关注公众号「天火同人2026」</b>，获取每日监控池完整名单<br>
                            🌍 <b>加入星球</b>，解锁任意股票实时8问评分与次日监控池
                        </p>
                    </div>
                    """, unsafe_allow_html=True)

                    # 仍然显示引流模块
                    # 星球引流（直接引用本地图片文件）
                    qr_b64 = _get_qr_base64()
                    st.markdown(textwrap.dedent(f"""
                    <div style="background: linear-gradient(135deg, #4f46e5 0%, #7c3aed 100%);
                    color: white; padding: 28px; border-radius: 16px; text-align: center;
                    margin-top: 32px; box-shadow: 0 10px 25px -5px rgba(0,0,0,0.3);">
                    <h2 style="margin:0 0 8px 0;font-size:22px;">📡 天火同人·周期信号日志</h2>
                    <p style="margin:0 0 16px 0;opacity:0.9;font-size:14px;">
                    每日盘后自动扫描全市场 | 五维共振 + 8问评分 + 周期定位
                    </p>
                    <div style="background: white; padding: 16px; border-radius: 12px;
                    display: inline-block; margin: 12px 0; box-shadow: 0 4px 12px rgba(0,0,0,0.15);">
                    <img src="data:image/png;base64,{qr_b64}" width="200" style="border-radius: 8px; display: block;" alt="星球二维码">
                    <p style="margin: 8px 0 0 0; font-size: 13px; color: #374151; font-weight: 600;">
                    微信扫码，加入星球
                    </p>
                    <p style="margin: 4px 0 0 0; font-size: 11px; color: #6b7280;">
                    解锁完整决策包与次日监控池
                    </p>
                    </div>
                    <p style="margin-top: 16px; font-size: 13px; opacity: 0.8;">
                    👇 早鸟价 ¥199/年（原价¥365）· 7天体验期内自助退款
                    </p>
                    </div>
                    """), unsafe_allow_html=True)

                    st.markdown("---")
                    st.markdown("""
                    <div style="text-align:center;color:#475569;font-size:14px;line-height:1.8;">
                        📬 <b>关注公众号「天火同人2026」</b><br>
                        获取每日盘前信号、周期观点与免费雷达入口
                    </div>
                    """, unsafe_allow_html=True)
                    st.stop()

                # === 正常数据展示 ===
                dims = result.get('dimensions', {})
                if not dims or not any(v > 0 for v in dims.values()):
                    st.error("数据异常，请稍后重试")
                    st.stop()

                # 演示模式提示（仅本地开发时可能出现）
                if source == 'demo':
                    st.warning("⚠️ 当前为演示模式，数据为模拟生成。")

                # 股票信息栏
                name = result.get('name', clean)
                ts_code = result.get('ts_code', f"{clean}.SZ")
                industry = result.get('industry', '')
                source_label = {"cache": "预计算缓存", "8q": "8问评分", "md": "五维评分", "realtime": "实时计算"}.get(source, source)

                st.markdown(f"""
                <div class="stock-info-bar">
                    <div>
                        <span class="stock-name">{name} ({ts_code})</span>
                        <span class="stock-meta">　{industry}</span>
                    </div>
                    <div style="display:flex;gap:8px;align-items:center;">
                        <span class="data-source">📡 {source_label}</span>
                        <span class="data-source">🕐 {datetime.now().strftime('%Y-%m-%d')}</span>
                    </div>
                </div>
                """, unsafe_allow_html=True)

                # 雷达图
                st.markdown('<div class="radar-box">', unsafe_allow_html=True)
                st.plotly_chart(
                    result['radar_chart'],
                    width='stretch',
                    config={'displayModeBar': False, 'displaylogo': False, 'responsive': True}
                )
                st.markdown('</div>', unsafe_allow_html=True)

                # 五维评估卡片
                st.subheader("五维评估")
                cols = st.columns(len(dims))

                for idx, (dim, score) in enumerate(dims.items()):
                    color, status, emoji = _status_badge(score)
                    with cols[idx]:
                        st.markdown(f"""
                        <div class="dim-card-outer">
                            <div class="dim-name">{dim}</div>
                            <div class="dim-emoji">{emoji}</div>
                            <div class="dim-status" style="color:{color};">{status}</div>
                            <div class="dim-bar-bg">
                                <div class="dim-bar-fill" style="background:{color};width:{score}%;"></div>
                            </div>
                        </div>
                        """, unsafe_allow_html=True)

                # === [新增] 增强版报告展示 ===
                show_enhanced_report(result)

                # 合规文案
                st.markdown("""
                <div class="compliance-box">
                    <strong>⚠️ 公开数据可视化，不构成投资建议</strong><br>
                    本页面仅展示公开数据的多维度分布可视化，<b>不输出具体分数，不提供任何买卖建议</b>。<br>
                    完整8问评分、次日监控池与周期策略，仅限星球会员获取。<br>
                    <em>投资有风险，入市需谨慎。所有决策需由投资者独立判断。</em>
                </div>
                """, unsafe_allow_html=True)


                # 星球引流（直接引用本地图片文件）
                qr_b64 = _get_qr_base64()
                st.markdown(textwrap.dedent(f"""
                <div style="background: linear-gradient(135deg, #4f46e5 0%, #7c3aed 100%);
                color: white; padding: 28px; border-radius: 16px; text-align: center;
                margin-top: 32px; box-shadow: 0 10px 25px -5px rgba(0,0,0,0.3);">
                <h2 style="margin:0 0 8px 0;font-size:22px;">📡 天火同人·周期信号日志</h2>
                <p style="margin:0 0 16px 0;opacity:0.9;font-size:14px;">
                每日盘后自动扫描全市场 | 五维共振 + 8问评分 + 周期定位
                </p>
                <div style="background: white; padding: 16px; border-radius: 12px;
                display: inline-block; margin: 12px 0; box-shadow: 0 4px 12px rgba(0,0,0,0.15);">
                <img src="data:image/png;base64,{qr_b64}" width="200" style="border-radius: 8px; display: block;" alt="星球二维码">
                <p style="margin: 8px 0 0 0; font-size: 13px; color: #374151; font-weight: 600;">
                微信扫码，加入星球
                </p>
                <p style="margin: 4px 0 0 0; font-size: 11px; color: #6b7280;">
                解锁完整决策包与次日监控池
                </p>
                </div>
                <p style="margin-top: 16px; font-size: 13px; opacity: 0.8;">
                👇 早鸟价 ¥199/年（原价¥365）· 7天体验期内自助退款
                </p>
                </div>
                """), unsafe_allow_html=True)

                # 公众号引流
                st.markdown("---")
                st.markdown("""
                <div style="text-align:center;color:#475569;font-size:14px;line-height:1.8;">
                    📬 <b>关注公众号「天火同人2026」</b><br>
                    获取每日盘前信号、周期观点与免费雷达入口<br>
                    <span style="font-size:12px;">菜单栏点击「五维雷达」→ 输入股票代码即时查看</span>
                </div>
                """, unsafe_allow_html=True)

            except Exception as e:
                st.error(f"扫描失败：{e}")
                st.info("提示：非交易时段部分数据可能缺失，或请检查股票代码是否正确。")
    else:
        st.warning("请输入6位数字股票代码（如 000001、300308、601899）")

# ==================== 管理后台（仅管理者可见）====================
st.markdown("---")
with st.expander("🔒 管理后台"):
    admin_pwd = st.text_input("管理密码", type="password", key="admin_pwd_input")
    if admin_pwd == st.secrets.get("ADMIN_PASSWORD", "tianhuo2026"):
        st.success("验证通过")

        supabase_url = st.secrets.get("SUPABASE_URL", "")
        supabase_key = st.secrets.get("SUPABASE_KEY", "")

        if not supabase_url or not supabase_key:
            st.info("未配置 Supabase，请查看飞书群历史消息获取访问记录。")
        else:
            try:
                # 拉取今日数据
                today = datetime.now().strftime("%Y-%m-%d")
                resp = requests.get(
                    f"{supabase_url}/rest/v1/radar_logs?select=*&accessed_at=gte.{today}T00:00:00",
                    headers={"apikey": supabase_key, "Authorization": f"Bearer {supabase_key}"},
                    timeout=5
                )

                if resp.status_code == 200:
                    data = resp.json()
                    sessions = set(r.get("session_id", "unknown") for r in data)
                    stocks = [r.get("stock_code", "") for r in data]

                    # 核心指标
                    c1, c2, c3 = st.columns(3)
                    c1.metric("📊 今日查询次数", len(data))
                    c2.metric("👤 今日独立访客", len(sessions))
                    c3.metric("🎯 查询股票种数", len(set(stocks)))

                    # 热门股票 TOP5
                    if stocks:
                        st.subheader("🔥 今日热门股票")
                        top5 = Counter(s for s in stocks if s).most_common(5)
                        for code, count in top5:
                            st.write(f"**{code}** — {count} 次")

                    # 来源分布
                    sources = [r.get("source", "unknown") for r in data]
                    if sources:
                        st.subheader("📡 数据来源分布")
                        src_cnt = Counter(sources)
                        st.bar_chart({k: v for k, v in src_cnt.items()})
                else:
                    st.error("拉取统计失败，请检查 Supabase 配置")
            except Exception as e:
                st.error(f"统计服务异常：{e}")
    elif admin_pwd:
        st.error("密码错误")

st.markdown("""
<div class="footer-text">
    © 2026 天火同人 | 数据仅供学习研究，不构成任何投资建议 | 公开数据可视化<br>
    完整决策工具与实时信号，请访问星球或公众号获取
</div>
""", unsafe_allow_html=True)

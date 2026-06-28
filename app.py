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


# ==================== [新增] 统一数据提取（支持 _raw_summary 回退）====================

def _extract_value(result: dict, key: str, default=None, raw_key: str = None):
    """
    统一数据提取：优先 _raw_summary → 顶层字段 → 兼容字段 → 默认值
    """
    raw = result.get('_raw_summary', {})
    raw_key = raw_key or key
    
    # 1. 优先 _raw_summary
    if raw_key in raw and raw[raw_key] is not None and raw[raw_key] != '':
        return raw[raw_key]
    
    # 2. 顶层字段
    if key in result and result[key] is not None and result[key] != '':
        return result[key]
    
    # 3. 兼容字段名
    aliases = {
        'profit': ['利润(亿)', 'profit', '净利润'],
        'roe': ['ROE', 'roe', '净资产收益率'],
        'g26': ['2026E', 'g26', '2026E增速'],
        'target': ['目标价(元)', 'target', '目标价'],
        'eps': ['eps', 'EPS'],
        'deviation': ['偏离度(%)', 'deviation', '偏离度'],
        'industry_flow': ['行业净流入(亿)', 'industry_flow'],
        'stock_flow': ['主力净流入(万元)', 'stock_flow', 'net_inflow_5d'],
        'current': ['current', 'current_price', 'price'],
        'rating': ['rating', '综合评级'],
        'total': ['total', 'score', '综合评分'],
        'comprehensive_rating': ['comprehensive_rating', '机构评级'],
    }
    for alt in aliases.get(key, []):
        if alt in result and result[alt] is not None and result[alt] != '':
            return result[alt]
        if alt in raw and raw[alt] is not None and raw[alt] != '':
            return raw[alt]
    
    return default


# ==================== [修复] 增强版报告展示 ====================

def show_enhanced_report(result: dict):
    """
    增强版报告展示：核心财务数据 + 资金流向 + 标签 + HTML下载
    修复：支持 _raw_summary 数据回退
    """
    # 统一提取数据
    name = result.get('name', '未知')
    code = result.get('ts_code', '')
    current = _extract_value(result, 'current', '')
    # 清理 current_price 中的 emoji
    if isinstance(current, str):
        current = current.replace('📅', '').replace('⚡', '').strip()
    
    rating = _extract_value(result, 'rating', '')
    total = _extract_value(result, 'total', 0)
    comprehensive_rating = _extract_value(result, 'comprehensive_rating', '')
    
    profit = _extract_value(result, 'profit')
    roe = _extract_value(result, 'roe')
    g26 = _extract_value(result, 'g26')
    target = _extract_value(result, 'target')
    eps = _extract_value(result, 'eps')
    deviation = _extract_value(result, 'deviation')
    
    industry_flow = _extract_value(result, 'industry_flow')
    stock_flow = _extract_value(result, 'stock_flow')
    tags = result.get('tags', '')
    
    # 五维
    dims = result.get('dimensions', {})
    
    # === 核心财务数据 ===
    has_finance = any(v is not None and v != '' and v != 'N/A' for v in [profit, roe, g26, target])
    
    if has_finance:
        st.markdown("---")
        st.subheader("📊 核心财务数据")
        
        cols = st.columns(6)
        metrics = [
            ("净利润", f"{profit}亿" if profit is not None else "N/A"),
            ("ROE", f"{roe}%" if roe is not None else "N/A"),
            ("2026E增速", f"{g26}%" if g26 is not None else "N/A"),
            ("目标价", f"¥{target}" if target is not None else "N/A"),
            ("EPS", f"{eps}" if eps is not None else "N/A"),
            ("偏离度", f"{deviation}%" if deviation is not None else "N/A"),
        ]
        for col, (label, value) in zip(cols, metrics):
            with col:
                st.metric(label, value)
    
    # === 资金流向 ===
    has_flow = industry_flow is not None or stock_flow is not None
    if has_flow:
        st.markdown("---")
        st.subheader("💰 资金流向监测")
        f1, f2 = st.columns(2)
        with f1:
            if industry_flow is not None:
                try:
                    fv = float(industry_flow)
                    flow_val = f"+{fv:.2f}亿" if fv > 0 else f"{fv:.2f}亿"
                except:
                    flow_val = str(industry_flow)
                st.metric("行业主力净流入", flow_val)
            else:
                st.metric("行业主力净流入", "N/A")
        with f2:
            if stock_flow is not None:
                try:
                    fv = float(stock_flow)
                    flow_val = f"+{fv:.0f}万" if fv > 0 else f"{fv:.0f}万"
                except:
                    flow_val = str(stock_flow)
                st.metric("个股5日主力净流入", flow_val)
            else:
                st.metric("个股5日主力净流入", "N/A")
    
    # === 标签 ===
    if tags and str(tags) not in ['N/A', 'None', '']:
        st.markdown("---")
        st.subheader("🏷️ 标签")
        tag_list = [t.strip() for t in str(tags).split(",") if t.strip()]
        tag_html = " ".join([f'<span class="tag-pill">{t}</span>' for t in tag_list])
        st.markdown(f"<div style='margin-top:8px;'>{tag_html}</div>", unsafe_allow_html=True)
    
    # === 下载完整HTML报告 ===
    st.markdown("---")
    
    try:
        html_content = generate_html_for_streamlit(result)
        
        file_name = f"{name}_天火评分.html"
        file_name = file_name.replace('/', '_').replace('\\', '_')
        
        st.download_button(
            label="📥 下载完整评分报告（HTML）",
            data=html_content,
            file_name=file_name,
            mime="text/html",
            help="包含五维雷达图、十二维评分、财务数据、资金流向等完整报告",
            use_container_width=True
        )
        st.caption("💡 提示：加入星球可获取每日监控池与实时8问评分")
    except Exception as e:
        st.error(f"报告生成失败: {e}")


# ==================== [修复] 完整HTML报告生成器 ====================

def generate_html_for_streamlit(data: dict) -> str:
    """生成完整的单文件HTML报告（支持 _raw_summary 回退）"""
    
    # 统一提取数据
    name = data.get('name', '未知')
    code = data.get('ts_code', '')
    current = _extract_value(data, 'current', '')
    if isinstance(current, str):
        current = current.replace('📅', '').replace('⚡', '').strip()
    
    rating = _extract_value(data, 'rating', '')
    total = _extract_value(data, 'total', 0)
    comprehensive_rating = _extract_value(data, 'comprehensive_rating', '')
    
    # 五维
    dims = data.get('dimensions', {})
    fundamental = min(dims.get("基本面", 0) + dims.get("赛道", 0) + dims.get("护城河", 0), 100)
    trend = min(dims.get("趋势动能", 0) + dims.get("月线MACD", 0) + dims.get("结构突破", 0), 100)
    fund = min(dims.get("资金质量", 0) + dims.get("流量", 0) + dims.get("流向", 0), 100)
    value = min(dims.get("估值安全", 0) + dims.get("价位买点", 0) + dims.get("消息面", 0), 100)
    cycle = min(dims.get("周期位置", 0) + dims.get("大盘加分", 0), 100)
    
    # 财务数据
    profit = _extract_value(data, 'profit', 'N/A')
    roe = _extract_value(data, 'roe', 'N/A')
    g26 = _extract_value(data, 'g26', 'N/A')
    target = _extract_value(data, 'target', 'N/A')
    eps = _extract_value(data, 'eps', 'N/A')
    deviation = _extract_value(data, 'deviation', 'N/A')
    
    # 资金流向
    industry_flow = _extract_value(data, 'industry_flow', 'N/A')
    stock_flow = _extract_value(data, 'stock_flow', 'N/A')
    
    # 标签
    tags = data.get('tags', '')
    
    # 十二维评分（从 result 或 _raw_summary 提取）
    raw = data.get('_raw_summary', {})
    score_items = []
    score_cfg = [
        ("赛道", data.get('赛道', raw.get('赛道', 0)), 40),
        ("护城河", data.get('护城河', raw.get('护城河', 0)), 30),
        ("业绩", data.get('业绩', raw.get('业绩', 0)), 30),
        ("月线MACD", data.get('月线MACD', raw.get('月线MACD', 0)), 30),
        ("结构突破", data.get('结构突破', raw.get('结构突破', 0)), 30),
        ("关键位置", data.get('关键位置', raw.get('关键位置', 0)), 40),
        ("流量", data.get('流量', raw.get('流量', 0)), 30),
        ("流向", data.get('流向', raw.get('流向', 0)), 40),
        ("流速", data.get('流速', raw.get('流速', 0)), 30),
        ("价位买点", data.get('价位买点', raw.get('价位买点', 0)), 50),
        ("消息面", data.get('消息面', raw.get('消息面', 0)), 30),
    ]
    
    def _score_color(score, max_s):
        pct = score / max_s if max_s > 0 else 0
        if pct >= 0.7: return "#e74c3c"
        elif pct >= 0.4: return "#f39c12"
        else: return "#78909c"
    
    for name_s, score, max_s in score_cfg:
        c = _score_color(score, max_s)
        score_items.append(f'<div class="si"><div class="si-l"><div class="si-dot" style="background:{c}"></div><div class="si-n">{name_s}</div></div><div class="si-v" style="color:{c}">{score}/{max_s}</div></div>')
    
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
    
    # 资金流向样式
    try:
        ind_f = float(industry_flow) if industry_flow not in ['N/A', 'None', ''] else 0
        ind_cls = "in" if ind_f > 0 else "out"
        ind_display = f"{'+' if ind_f > 0 else ''}{ind_f:.2f}亿"
    except:
        ind_cls = "out"
        ind_display = str(industry_flow)
    
    try:
        stk_f = float(stock_flow) if stock_flow not in ['N/A', 'None', ''] else 0
        stk_cls = "in" if stk_f > 0 else "out"
        stk_display = f"{'+' if stk_f > 0 else ''}{stk_f:.0f}万"
    except:
        stk_cls = "out"
        stk_display = str(stock_flow)
    
    html = f"""<!DOCTYPE html>
<html lang="zh-CN"><head><meta charset="UTF-8">
<meta name="viewport" content="width=device-width, initial-scale=1.0">
<title>天火评分 - {name}</title>
<style>
*{margin:0;padding:0;box-sizing:border-box}
body{font-family:-apple-system,BlinkMacSystemFont,"Segoe UI",Roboto,"Helvetica Neue",Arial,sans-serif;background:linear-gradient(135deg,#f5f7fa 0%,#e4e8ec 100%);min-height:100vh;padding:20px;color:#333}
.container{max-width:800px;margin:0 auto}
.header{background:linear-gradient(135deg,#1a1a2e 0%,#16213e 100%);border-radius:16px;padding:24px;color:#fff;margin-bottom:16px;box-shadow:0 10px 40px rgba(0,0,0,0.15)}
.header-top{display:flex;justify-content:space-between;align-items:flex-start;margin-bottom:16px;flex-wrap:wrap;gap:12px}
.header-top h1{margin:0;font-size:24px}
.code{opacity:0.7;font-size:13px;margin-top:4px;font-family:monospace}
.industry{display:inline-block;background:rgba(255,255,255,0.15);padding:4px 12px;border-radius:20px;font-size:12px;margin-top:8px}
.rating-badge{display:inline-block;padding:6px 16px;border-radius:20px;font-size:14px;font-weight:600;margin-top:8px}
.rating-strong{background:#e74c3c}.rating-add{background:#e67e22}.rating-neutral{background:#f39c12}.rating-reduce{background:#95a5a6;color:#333}.rating-sell{background:#7f8c8d}
.price-box{text-align:right}
.price{font-size:32px;font-weight:700;color:#ff6b6b}
.price-label{font-size:12px;opacity:0.6}
.stats{display:grid;grid-template-columns:repeat(4,1fr);gap:10px;margin-top:16px;padding-top:16px;border-top:1px solid rgba(255,255,255,0.1)}
.stat-item{text-align:center}
.stat-value{font-size:16px;font-weight:700;color:#ffd700}
.stat-label{font-size:11px;opacity:0.6;margin-top:2px}
.card{background:#fff;border-radius:16px;padding:20px;margin-bottom:16px;box-shadow:0 2px 8px rgba(0,0,0,0.04)}
.card-title{font-size:16px;font-weight:700;margin-bottom:12px;display:flex;align-items:center;gap:6px}
.card-title::before{content:"";width:3px;height:16px;background:#e74c3c;border-radius:2px}
.grid-3{display:grid;grid-template-columns:repeat(3,1fr);gap:10px}
.grid-2{display:grid;grid-template-columns:repeat(2,1fr);gap:10px}
.item{background:#f8f9fa;border-radius:10px;padding:12px;text-align:center}
.item-label{font-size:11px;color:#78909c;margin-bottom:4px}
.item-value{font-size:16px;font-weight:700;color:#2c3e50}
.item-sub{font-size:10px;color:#90a4ae;margin-top:2px}
.tag-pill{display:inline-block;background:linear-gradient(135deg,#ffebee 0%,#ffcdd2 100%);color:#c62828;padding:3px 10px;border-radius:20px;font-size:12px;font-weight:500;margin:4px}
.flow-card{background:#f8f9fa;border-radius:12px;padding:18px;position:relative;overflow:hidden}
.flow-card::before{content:"";position:absolute;left:0;top:0;bottom:0;width:4px}
.flow-card.in::before{background:#e74c3c}.flow-card.out::before{background:#27ae60}
.flow-title{font-size:12px;color:#78909c;margin-bottom:6px}
.flow-amount{font-size:22px;font-weight:700}
.flow-amount.in{color:#e74c3c}.flow-amount.out{color:#27ae60}
.flow-note{font-size:10px;color:#90a4ae;margin-top:3px}
.score-grid{display:grid;grid-template-columns:repeat(2,1fr);gap:10px}
.score-item{display:flex;align-items:center;justify-content:space-between;padding:10px;background:#f8f9fa;border-radius:10px}
.score-left{display:flex;align-items:center;gap:8px}
.score-dot{width:9px;height:9px;border-radius:50%;flex-shrink:0}
.score-name{font-size:13px;font-weight:500}
.score-value{font-size:14px;font-weight:700;font-family:monospace}
.disclaimer{background:#fff8e1;border:1px solid #ffe0b2;border-radius:12px;padding:14px;margin-top:16px;color:#92400e;font-size:12px;line-height:1.6}
@media(max-width:600px){.grid-3,.grid-2{grid-template-columns:1fr}.stats{grid-template-columns:repeat(2,1fr)}}
</style></head><body><div class="container">
<div class="header"><div class="header-top"><div><h1>{name}</h1><div class="code">{code}</div><div class="industry">{data.get('industry','') or data.get('申万行业','')}</div><div class="rating-badge" style="background:{rating_color}">{rating}</div></div><div class="price-box"><div class="price">¥{current}</div><div class="price-label">当前价</div></div></div><div class="stats"><div class="stat-item"><div class="stat-value">{total}</div><div class="stat-label">综合评分</div></div><div class="stat-item"><div class="stat-value">{roe}%</div><div class="stat-label">ROE</div></div><div class="stat-item"><div class="stat-value">{g26}%</div><div class="stat-label">2026E</div></div><div class="stat-item"><div class="stat-value">{target}</div><div class="stat-label">目标价</div></div></div></div>
<div class="card"><div class="card-title">五维共振雷达</div><div style="display:flex;justify-content:center;padding:10px"><canvas id="radar" width="400" height="350"></canvas></div><div class="grid-3"><div class="item"><div class="item-label">基本面</div><div class="item-value">{fundamental}</div></div><div class="item"><div class="item-label">趋势动能</div><div class="item-value">{trend}</div></div><div class="item"><div class="item-label">资金质量</div><div class="item-value">{fund}</div></div><div class="item"><div class="item-label">估值安全</div><div class="item-value">{value}</div></div><div class="item"><div class="item-label">周期位置</div><div class="item-value">{cycle}</div></div></div></div>
<div class="card"><div class="card-title">十二维评分详情</div><div class="score-grid">{''.join(score_items)}</div></div>
<div class="card"><div class="card-title">核心财务数据</div><div class="grid-3"><div class="item"><div class="item-label">净利润</div><div class="item-value">{profit}亿</div></div><div class="item"><div class="item-label">ROE</div><div class="item-value">{roe}%</div></div><div class="item"><div class="item-label">2026E增速</div><div class="item-value">{g26}%</div></div><div class="item"><div class="item-label">目标价</div><div class="item-value">{target}</div></div><div class="item"><div class="item-label">EPS</div><div class="item-value">{eps}</div></div><div class="item"><div class="item-label">偏离度</div><div class="item-value">{deviation}%</div></div></div><div style="margin-top:12px">{tags_html}</div></div>
<div class="card"><div class="card-title">资金流向监测</div><div class="grid-2"><div class="flow-card {ind_cls}"><div class="flow-title">行业主力资金净流入</div><div class="flow-amount {ind_cls}">{ind_display}</div><div class="flow-note">{data.get('industry','') or data.get('申万行业','')}板块</div></div><div class="flow-card {stk_cls}"><div class="flow-title">个股5日主力净流入</div><div class="flow-amount {stk_cls}">{stk_display}</div><div class="flow-note">最近5个交易日</div></div></div></div>
<div class="disclaimer"><strong>⚠️ 不构成投资建议</strong><br>本报告仅展示公开数据的多维度分布可视化，所有决策需由投资者独立判断。完整12维评分与次日监控池仅限星球会员。</div>
</div><script>
var c=document.getElementById("radar"),x=c.getContext("2d"),d=window.devicePixelRatio||1;
c.width=400*d;c.height=350*d;x.scale(d,d);
var cx=200,cy=170,r=120,ds=["基本面","趋势动能","资金质量","估值安全","周期位置"],sc=[{fundamental},{trend},{fund},{value},{cycle}],mx=100;
for(var i=1;i<=5;i++){{x.beginPath();var ri=r/5*i;for(var j=0;j<5;j++){{var a=Math.PI*2/5*j-Math.PI/2,px=cx+ri*Math.cos(a),py=cy+ri*Math.sin(a);j==0?x.moveTo(px,py):x.lineTo(px,py)}}x.closePath();x.strokeStyle=i==5?"#ddd":"#eee";x.lineWidth=1;x.stroke()}}
for(var i=0;i<5;i++){{var a=Math.PI*2/5*i-Math.PI/2;x.beginPath();x.moveTo(cx,cy);x.lineTo(cx+r*Math.cos(a),cy+r*Math.sin(a));x.strokeStyle="#ddd";x.stroke();var lr=r+25,lx=cx+lr*Math.cos(a),ly=cy+lr*Math.sin(a);x.font="13px sans-serif";x.fillStyle="#666";x.textAlign="center";x.textBaseline="middle";x.fillText(ds[i],lx,ly)}}
x.beginPath();for(var i=0;i<5;i++){{var a=Math.PI*2/5*i-Math.PI/2,ri=sc[i]/mx*r,px=cx+ri*Math.cos(a),py=cy+ri*Math.sin(a);i==0?x.moveTo(px,py):x.lineTo(px,py)}}x.closePath();x.fillStyle="rgba(231,76,60,0.2)";x.fill();x.strokeStyle="#e74c3c";x.lineWidth=2;x.stroke();
for(var i=0;i<5;i++){{var a=Math.PI*2/5*i-Math.PI/2,ri=sc[i]/mx*r,px=cx+ri*Math.cos(a),py=cy+ri*Math.sin(a);x.beginPath();x.arc(px,py,5,0,Math.PI*2);x.fillStyle="#e74c3c";x.fill();x.strokeStyle="#fff";x.lineWidth=2;x.stroke();x.font="bold 12px sans-serif";x.fillStyle="#e74c3c";x.textAlign="center";x.fillText(sc[i],px+18*Math.cos(a),py+18*Math.sin(a))}}
</script></body></html>"""
    
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

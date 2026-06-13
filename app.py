"""
天火五维共振雷达 - Streamlit Cloud 部署版
合规要求：零分数显示 | 零买卖建议 | 强制风险提示
作者: jack@ailobstermedia
版本: 2026.06.13-fix2
"""

import streamlit as st
import sys
import os
import json
import random
from pathlib import Path
from datetime import datetime

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

# ==================== 环境变量读取（Streamlit Secrets）====================
def get_secret(key: str, default: str = "") -> str:
    """优先读取 Streamlit Secrets，其次环境变量"""
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
except Exception as _e:
    pass

try:
    from single_stock_score import score_stock as _score_8q
    Q8_AVAILABLE = True
except Exception as _e:
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
    .stProgress > div > div > div { background-color: #e2e8f0 !important; }

    .radar-box {
        background: #ffffff;
        border-radius: 16px;
        padding: 24px;
        margin: 16px 0;
        border: 1px solid #e2e8f0;
        box-shadow: 0 1px 3px rgba(0,0,0,0.05);
    }

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

    .footer-text {
        text-align: center;
        color: #64748b;
        font-size: 12px;
        margin-top: 40px;
        padding-top: 20px;
        border-top: 1px solid #e2e8f0;
    }
</style>
""", unsafe_allow_html=True)

# ==================== 缓存与数据层 ====================
@st.cache_data(ttl=1800, show_spinner=False)
def get_score_result(stock_code: str, mode: str = "auto"):
    cache_dir = Path(__file__).parent / "cache"
    cache_file = cache_dir / f"{stock_code}.json"
    if cache_file.exists():
        try:
            with open(cache_file, 'r', encoding='utf-8') as f:
                cached = json.load(f)
                cached["_source"] = "cache"
                dims = cached.get('dimensions') or {}
                if dims and 'radar_chart' not in cached:
                    cached['radar_chart'] = _build_radar(dims)
                return cached
        except Exception:
            pass

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

    return _demo_data(stock_code)

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

def _demo_data(stock_code: str) -> dict:
    random.seed(hash(stock_code) % 10000)
    dims = {
        "趋势动能": random.randint(35, 85),
        "资金质量": random.randint(35, 85),
        "估值安全": random.randint(35, 85),
        "基本面": random.randint(35, 85),
        "周期位置": random.randint(35, 85)
    }
    return {
        'dimensions': dims,
        'radar_chart': _build_radar(dims),
        '_source': 'demo',
        '_notice': '当前为演示模式，请部署真实评分模块'
    }

def _status_badge(score: int) -> tuple:
    if score >= 70:
        return ("#22c55e", "积极", "🟢")
    elif score >= 40:
        return ("#eab308", "中性", "🟡")
    else:
        return ("#ef4444", "谨慎", "🔴")

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
                dims = result.get('dimensions', {})

                if not dims:
                    st.error("未获取到评分数据")
                    st.stop()

                if result.get('_source') == 'demo':
                    st.warning("⚠️ 当前为演示模式，数据为模拟生成。")

                # 雷达图
                st.markdown('<div class="radar-box">', unsafe_allow_html=True)
                st.plotly_chart(
                    result['radar_chart'],
                    width='stretch',
                    config={'displayModeBar': False, 'displaylogo': False, 'responsive': True}
                )
                st.markdown('</div>', unsafe_allow_html=True)

                # 五维评估 - 使用原生组件确保在 columns 中可靠渲染
                st.subheader("五维评估")
                cols = st.columns(len(dims))

                for idx, (dim, score) in enumerate(dims.items()):
                    color, status, emoji = _status_badge(score)
                    with cols[idx]:
                        # 使用 st.container + 简化 HTML，避免多行字符串在 columns 中渲染失败
                        with st.container():
                            st.markdown(f"<p style='text-align:center;font-size:13px;color:#475569;font-weight:500;margin:0 0 4px 0;'>{dim}</p>", unsafe_allow_html=True)
                            st.markdown(f"<h1 style='text-align:center;margin:0;font-size:28px;'>{emoji}</h1>", unsafe_allow_html=True)
                            st.markdown(f"<p style='text-align:center;color:{color};font-weight:600;font-size:12px;margin:4px 0 8px 0;'>{status}</p>", unsafe_allow_html=True)
                            st.progress(score / 100, text="")

                # 合规文案
                st.markdown("""
                <div class="compliance-box">
                    <strong>⚠️ 公开数据可视化，不构成投资建议</strong><br>
                    本页面仅展示公开数据的多维度分布可视化，<b>不输出具体分数，不提供任何买卖建议</b>。<br>
                    完整8问评分、次日监控池与周期策略，仅限星球会员获取。<br>
                    <em>投资有风险，入市需谨慎。所有决策需由投资者独立判断。</em>
                </div>
                """, unsafe_allow_html=True)

                # 星球引流
                st.markdown("""
                <div class="planet-cta">
                    <h2 style="margin:0 0 8px 0;font-size:22px;">📡 天火同人·周期与信号日志</h2>
                    <p style="margin:0 0 16px 0;opacity:0.9;font-size:14px;">
                        每日盘后自动扫描全市场 | 五维共振 + 8问评分 + 周期定位
                    </p>
                    <div class="qr-placeholder">
                        <p style="margin:0;font-weight:600;font-size:14px;">🌍 星球二维码占位</p>
                        <p style="margin:4px 0 0 0;font-size:12px;color:#6b7280;">
                            替换为真实二维码图片 &lt;img src="..."&gt;
                        </p>
                    </div>
                    <p style="margin-top:16px;font-size:13px;opacity:0.8;">
                        👇 扫码加入星球，解锁完整决策包与次日监控池
                    </p>
                </div>
                """, unsafe_allow_html=True)

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

st.markdown("""
<div class="footer-text">
    © 2026 天火同人 | 数据仅供学习研究，不构成任何投资建议 | 公开数据可视化<br>
    完整决策工具与实时信号，请访问星球或公众号获取
</div>
""", unsafe_allow_html=True)
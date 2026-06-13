"""
scorer_adapter.py
适配器：将命令行评分脚本封装为 score_stock(code) 函数
不改动原脚本，独立模块
"""

import sys
import os
from pathlib import Path

# ==================== 路径适配（同 app.py）====================
POSSIBLE_ROOTS = [
    Path(__file__).parent.parent,
    Path.home() / "LobsterLite",
    Path.cwd(),
]
for root in POSSIBLE_ROOTS:
    if root.exists():
        for sub in ["", "tools", "bots", "fivewaves", "skyfire2026"]:
            p = str(root / sub) if sub else str(root)
            if p not in sys.path:
                sys.path.insert(0, p)

# Tushare Token
TUSHARE_TOKEN = os.environ.get("TUSHARE_TOKEN", "")
if TUSHARE_TOKEN:
    try:
        import tushare as ts
        ts.set_token(TUSHARE_TOKEN)
    except:
        pass

def _normalize_code(code: str) -> str:
    """统一转换为 ts_code 格式（如 300308 → 300308.SZ）"""
    code = code.strip().replace('.SH', '').replace('.SZ', '').replace('.BJ', '')
    if '.' in code:
        return code
    if code.startswith('6'):
        return code + '.SH'
    elif code.startswith(('0', '3')):
        return code + '.SZ'
    elif code.startswith('8'):
        return code + '.BJ'
    return code + '.SZ'

def _map_8q_to_5d(result: dict) -> dict:
    """
    将 single_stock_score 的 8 问字段映射为五维评分
    映射逻辑基于字段语义，确保雷达图颜色分布合理
    """
    # 趋势动能 = 月线MACD(30%) + 结构突破(25%) + 关键位置(20%) + 赛道(25%)
    trend = (
        float(result.get('月线MACD', 0)) * 0.30 +
        float(result.get('结构突破', 0)) * 0.25 +
        float(result.get('关键位置', 0)) * 0.20 +
        float(result.get('赛道', 0)) * 0.25
    )
    
    # 资金质量 = 流量(35%) + 流向(35%) + 流速(30%)
    fund = (
        float(result.get('流量', 0)) * 0.35 +
        float(result.get('流向', 0)) * 0.35 +
        float(result.get('流速', 0)) * 0.30
    )
    
    # 估值安全 = 价位买点(50%) + 偏离度(50%)
    # 偏离度为负表示低于目标价（越负越安全，分数越高）
    deviation = float(result.get('偏离度(%)', 0))
    if deviation < 0:
        value_score = min(100, 50 + abs(deviation))
    else:
        value_score = max(0, 50 - deviation)
    value = float(result.get('价位买点', 0)) * 0.5 + value_score * 0.5
    
    # 基本面 = 业绩(40%) + ROE(30%) + 2026E增速(30%)
    roe = float(result.get('ROE', 0))
    roe_score = min(100, roe * 3) if roe > 0 else 0  # ROE 30% ≈ 90分
    g26 = float(result.get('2026E', 0))
    g26_score = min(100, g26) if g26 > 0 else 0
    fundamental = (
        float(result.get('业绩', 0)) * 0.40 +
        roe_score * 0.30 +
        g26_score * 0.30
    )
    
    # 周期位置 = 护城河(40%) + 消息面(30%) + 综合评级(30%)
    cycle_map = {'买入': 90, '增持': 75, '中性': 50, '减持': 30, '卖出': 10, '观望': 40}
    comp_rating = str(result.get('comprehensive_rating', '')).strip()
    cycle_score = cycle_map.get(comp_rating, 50)
    cycle = (
        float(result.get('护城河', 0)) * 0.40 +
        float(result.get('消息面', 0)) * 0.30 +
        cycle_score * 0.30
    )
    
    return {
        "趋势动能": round(min(100, max(0, trend)), 1),
        "资金质量": round(min(100, max(0, fund)), 1),
        "估值安全": round(min(100, max(0, value)), 1),
        "基本面": round(min(100, max(0, fundamental)), 1),
        "周期位置": round(min(100, max(0, cycle)), 1),
    }

def score_stock(code: str) -> dict:
    """
    统一评分入口：调用 single_stock_score.score_single_stock()
    返回格式: {"dimensions": {...}, "name": ..., "ts_code": ..., "source": "8q"}
    """
    try:
        import single_stock_score as sss
        ts_code = _normalize_code(code)
        result = sss.score_single_stock(ts_code)
        
        if result is None:
            raise RuntimeError(f"score_single_stock({ts_code}) 返回 None")
        
        # 构建标准化输出
        dimensions = _map_8q_to_5d(result)
        
        return {
            "dimensions": dimensions,
            "name": result.get('name', code),
            "ts_code": result.get('ts_code', ts_code),
            "current_price": result.get('current_display', 0),
            "industry": result.get('行业', ''),
            "source": "8q",
            # 保留关键原始字段供调试
            "_raw_summary": {
                "total": result.get('total'),
                "rating": result.get('rating'),
                "comprehensive_rating": result.get('comprehensive_rating'),
                "偏离度": result.get('偏离度(%)'),
                "目标价": result.get('目标价(元)'),
                "2026E": result.get('2026E'),
                "ROE": result.get('ROE'),
            }
        }
        
    except Exception as e:
        raise RuntimeError(f"评分失败 {code}: {e}")

if __name__ == "__main__":
    # 独立测试
    import json
    code = sys.argv[1] if len(sys.argv) > 1 else "300308"
    r = score_stock(code)
    print(json.dumps(r, ensure_ascii=False, indent=2))

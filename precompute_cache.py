"""
预计算缓存脚本 - 适配器版
调用 scorer_adapter.score_stock() 生成 JSON 缓存
"""

import sys
import json
import os
from pathlib import Path
from datetime import datetime

# 路径适配
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

# 导入适配器
from scorer_adapter import score_stock

# ==================== 股票列表 ====================
WATCHLIST = [
    "000001", "000002", "000333", "000568", "000651", "000725", "000768",
    "000858", "002001", "002007", "002027", "002142", "002230", "002236",
    "002271", "002352", "002415", "002460", "002475", "002594",
    "300014", "300015", "300033", "300059", "300122", "300124", "300274",
    "300308", "300408", "300413", "300433", "300498", "300750", "300760",
    "600009", "600016", "600028", "600030", "600031", "600036", "600048",
    "600276", "600309", "600406", "600436", "600438", "600519", "600547",
    "600570", "600585", "600588", "600660", "600690", "600703", "600745",
    "600809", "600837", "600887", "600900", "600919", "600938", "601012",
    "601066", "601088", "601100", "601138", "601166", "601169", "601211",
    "601288", "601318", "601336", "601398", "601601", "601628", "601668",
    "601688", "601766", "601857", "601888", "601899", "601901", "601933",
    "601985", "603019", "603288", "603501", "603659", "603986", "603993",
    "688008", "688009", "688012", "688036", "688111", "688169", "688223",
    "688256", "688271", "688303", "688396", "688599", "688981",
]

def precompute():
    cache_dir = Path(__file__).parent / "cache"
    cache_dir.mkdir(exist_ok=True)
    
    success = 0
    failed = 0
    
    for code in WATCHLIST:
        try:
            result = score_stock(code)
            
            # 移除不可序列化对象
            for key in ['radar_chart', 'chart', 'fig', 'figure']:
                if key in result:
                    del result[key]
            
            cache_file = cache_dir / f"{code}.json"
            with open(cache_file, 'w', encoding='utf-8') as f:
                json.dump(result, f, ensure_ascii=False, indent=2)
            
            success += 1
            print(f"  ✅ {code} ({result.get('name', '')}) 缓存成功")
            
        except Exception as e:
            failed += 1
            print(f"  ❌ {code} 失败: {str(e)[:100]}")
    
    meta = {
        "update_time": datetime.now().isoformat(),
        "total": len(WATCHLIST),
        "success": success,
        "failed": failed,
        "scorer": "scorer_adapter.score_stock (8q→5d)"
    }
    with open(cache_dir / "_meta.json", 'w', encoding='utf-8') as f:
        json.dump(meta, f, ensure_ascii=False, indent=2)
    
    print(f"\n[INFO] 预计算完成: {success}/{len(WATCHLIST)} 成功, {failed} 失败")
    print(f"[INFO] 缓存目录: {cache_dir}")
    print(f"[INFO] 更新时间: {meta['update_time']}")

if __name__ == "__main__":
    precompute()

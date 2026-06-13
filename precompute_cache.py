"""
预计算缓存脚本 - 并发优化版
用途：本地 Dell 7460 盘后预计算，5线程并发，扩展至 300+ 核心股
解决：单线程 100只×28秒=47分钟 → 5线程 300只≈25分钟
"""

import sys
import json
import os
from pathlib import Path
from datetime import datetime
from concurrent.futures import ThreadPoolExecutor, as_completed
import logging

logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')

# ==================== 路径适配 ====================
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

# ==================== 核心股票池 ====================
WATCHLIST_CORE = [
    # 原有 100 只核心股
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

def get_extended_watchlist():
    """扩展股票池：核心股 + 沪深300成分股 + 科创50"""
    watchlist = set(WATCHLIST_CORE)

    # 尝试从 Tushare 获取沪深300成分股
    try:
        import tushare as ts
        pro = ts.pro_api()
        # 获取最近交易日的沪深300成分股
        df = pro.index_weight(index_code='000300.SH')
        if not df.empty:
            hs300 = df['con_code'].str.replace('.SH', '').str.replace('.SZ', '').tolist()
            watchlist.update(hs300[:200])  # 取前200只（避免过多）
            logging.info(f"[INFO] 沪深300成分股: {len(hs300)} 只，取前 200")
    except Exception as e:
        logging.warning(f"[WARN] 获取沪深300成分股失败: {e}")

    # 尝试获取科创50
    try:
        import tushare as ts
        pro = ts.pro_api()
        df = pro.index_weight(index_code='000688.SH')
        if not df.empty:
            kc50 = df['con_code'].str.replace('.SH', '').str.replace('.SZ', '').tolist()
            watchlist.update(kc50)
            logging.info(f"[INFO] 科创50成分股: {len(kc50)} 只")
    except Exception as e:
        logging.warning(f"[WARN] 获取科创50失败: {e}")

    return sorted(list(watchlist))

def process_single_stock(code: str, cache_dir: Path, scorer):
    """处理单只股票：评分 → 保存缓存"""
    cache_file = cache_dir / f"{code}.json"

    # 如果缓存已存在且今天更新过，跳过
    if cache_file.exists():
        try:
            mtime = datetime.fromtimestamp(cache_file.stat().st_mtime)
            if mtime.date() == datetime.now().date():
                return (code, "skipped", "今日已缓存")
        except:
            pass

    try:
        result = scorer(code)

        # 验证结果有效性
        if not result or not isinstance(result, dict):
            return (code, "failed", "返回非字典")

        dims = result.get('dimensions', {})
        if not dims or not any(v > 0 for v in dims.values()):
            return (code, "failed", "维度数据为空")

        # 移除不可序列化对象
        for key in ['radar_chart', 'chart', 'fig', 'figure']:
            if key in result:
                del result[key]

        # 保存缓存
        with open(cache_file, 'w', encoding='utf-8') as f:
            json.dump(result, f, ensure_ascii=False, indent=2)

        return (code, "success", result.get('name', code))

    except Exception as e:
        return (code, "failed", str(e)[:100])

def precompute(max_workers: int = 5):
    """批量预计算（多线程并发）"""
    cache_dir = Path(__file__).parent / "cache"
    cache_dir.mkdir(exist_ok=True)

    # 导入评分函数
    scorer = None
    try:
        from scorer_adapter import score_stock as scorer
        logging.info("[INFO] 使用 scorer_adapter 评分模块")
    except Exception as e:
        logging.error(f"[ERROR] scorer_adapter 不可用: {e}")
        return

    # 获取股票池
    watchlist = get_extended_watchlist()
    logging.info(f"[INFO] 总股票池: {len(watchlist)} 只")

    # 多线程并发处理
    success = 0
    failed = 0
    skipped = 0

    with ThreadPoolExecutor(max_workers=max_workers) as executor:
        futures = {
            executor.submit(process_single_stock, code, cache_dir, scorer): code 
            for code in watchlist
        }

        for future in as_completed(futures):
            code, status, msg = future.result()
            if status == "success":
                success += 1
                logging.info(f"  ✅ {code} ({msg}) 缓存成功")
            elif status == "skipped":
                skipped += 1
                logging.info(f"  ⏭️ {code} {msg}")
            else:
                failed += 1
                logging.warning(f"  ❌ {code} 失败: {msg}")

    # 写入元数据
    meta = {
        "update_time": datetime.now().isoformat(),
        "total": len(watchlist),
        "success": success,
        "failed": failed,
        "skipped": skipped,
        "scorer": "scorer_adapter.score_stock (8q→5d)",
        "workers": max_workers
    }
    with open(cache_dir / "_meta.json", 'w', encoding='utf-8') as f:
        json.dump(meta, f, ensure_ascii=False, indent=2)

    logging.info(f"\n[INFO] 预计算完成: {success} 成功, {failed} 失败, {skipped} 跳过")
    logging.info(f"[INFO] 缓存目录: {cache_dir}")
    logging.info(f"[INFO] 更新时间: {meta['update_time']}")
    logging.info(f"[INFO] 并发线程: {max_workers}")

if __name__ == "__main__":
    import argparse
    parser = argparse.ArgumentParser()
    parser.add_argument('-w', '--workers', type=int, default=5, help='并发线程数（默认5）')
    args = parser.parse_args()
    precompute(max_workers=args.workers)

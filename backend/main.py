#!/usr/bin/env python3
"""
股票+基金分析决策仪表盘 - Backend API
FastAPI + SQLite + AkShare + DeepSeek AI
"""

import os
import json
import time
import sqlite3
import traceback
from datetime import datetime, timedelta
from pathlib import Path
from contextlib import contextmanager

from fastapi import FastAPI, HTTPException
from fastapi.staticfiles import StaticFiles
from fastapi.responses import FileResponse, JSONResponse
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel
from typing import Optional

import akshare as ak
import pandas as pd
import requests
from dotenv import load_dotenv

# 加载环境变量
_env_file = Path(__file__).parent.parent / ".env"
if _env_file.exists():
    load_dotenv(str(_env_file), override=True)

# ==================== 配置 ====================
DB_PATH = os.getenv("DB_PATH", str(Path(__file__).parent.parent / "data" / "dashboard.db"))
OPENAI_API_KEY = os.getenv("OPENAI_API_KEY", "sk-6dc9b88bda904264a588ead1aa3ea113")
OPENAI_BASE_URL = os.getenv("OPENAI_BASE_URL", "https://api.deepseek.com/v1")
OPENAI_MODEL = os.getenv("OPENAI_MODEL", "deepseek-chat")
CACHE_HOURS = int(os.getenv("CACHE_HOURS", "24"))

# ==================== FastAPI 初始化 ====================
app = FastAPI(title="股票基金分析仪表盘", version="1.0.0")
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# ==================== 数据库 ====================
def init_db():
    """初始化数据库"""
    os.makedirs(os.path.dirname(DB_PATH), exist_ok=True)
    conn = sqlite3.connect(DB_PATH)
    c = conn.cursor()
    
    c.execute('''CREATE TABLE IF NOT EXISTS stocks (
        code TEXT PRIMARY KEY,
        name TEXT NOT NULL,
        added_at TEXT NOT NULL
    )''')
    
    c.execute('''CREATE TABLE IF NOT EXISTS funds (
        code TEXT PRIMARY KEY,
        name TEXT NOT NULL,
        added_at TEXT NOT NULL
    )''')
    
    c.execute('''CREATE TABLE IF NOT EXISTS analysis_cache (
        type TEXT NOT NULL,
        code TEXT NOT NULL,
        analysis_result TEXT,
        data_json TEXT,
        updated_at TEXT NOT NULL,
        PRIMARY KEY (type, code)
    )''')
    
    conn.commit()
    conn.close()

@contextmanager
def get_db():
    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row
    try:
        yield conn
    finally:
        conn.close()

def seed_initial_data():
    """预置初始数据"""
    now = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    stocks = [
        ("002475", "立讯精密", now),
        ("601138", "工业富联", now),
        ("002463", "沪电股份", now),
        ("002916", "深南电路", now),
        ("600183", "生益科技", now),
        ("300394", "天孚通信", now),
        ("600362", "江西铜业", now),
        ("601899", "紫金矿业", now),
        ("603993", "洛阳钼业", now),
        ("600111", "北方稀土", now),
    ]
    funds = [
        ("005786", "银华农业产业股票C", now),
        ("005224", "广发中证基建工程ETF连接C", now),
        ("012635", "国泰中证医疗ETF连接C", now),
    ]
    with get_db() as conn:
        c = conn.cursor()
        existing_stocks = c.execute("SELECT code FROM stocks").fetchall()
        if not existing_stocks:
            c.executemany("INSERT OR IGNORE INTO stocks VALUES (?,?,?)", stocks)
        existing_funds = c.execute("SELECT code FROM funds").fetchall()
        if not existing_funds:
            c.executemany("INSERT OR IGNORE INTO funds VALUES (?,?,?)", funds)
        conn.commit()

# ==================== 数据获取 - 股票 ====================
def get_stock_realtime(code: str) -> dict:
    """获取股票实时行情 - 使用个股实时行情接口"""
    try:
        # 方法1: 使用 stock_bid_ask_em (个股实时数据，更高效)
        try:
            df = ak.stock_bid_ask_em(symbol=code)
            if df is not None and not df.empty:
                data = dict(zip(df["item"], df["value"]))
                # 获取股票名称
                name = ""
                try:
                    info = ak.stock_individual_info_em(symbol=code)
                    if info is not None and not info.empty:
                        name_row = info[info["item"] == "股票简称"]
                        if not name_row.empty:
                            name = str(name_row.iloc[0]["value"])
                except:
                    pass
                
                price = float(data.get("最新", 0))
                prev_close = float(data.get("昨收", 0))
                change = price - prev_close if prev_close else 0
                change_pct = (change / prev_close * 100) if prev_close else 0
                
                return {
                    "code": code,
                    "name": name or code,
                    "price": price,
                    "change_pct": round(change_pct, 2),
                    "change_amount": round(change, 2),
                    "volume": float(data.get("成交量", 0)),
                    "amount": float(data.get("成交额", 0)),
                    "high": float(data.get("最高", 0)),
                    "low": float(data.get("最低", 0)),
                    "open": float(data.get("今开", 0)),
                    "prev_close": prev_close,
                    "pe_ratio": None,
                    "market_cap": 0,
                    "turnover_rate": None,
                }
        except Exception:
            pass
        
        # 方法2: 回退到全市场行情 (兼容旧版)
        df = ak.stock_zh_a_spot_em()
        row = df[df["代码"] == code]
        if row.empty:
            return {}
        row = row.iloc[0]
        return {
            "code": code,
            "name": str(row.get("名称", "")),
            "price": float(row.get("最新价", 0)),
            "change_pct": float(row.get("涨跌幅", 0)),
            "change_amount": float(row.get("涨跌额", 0)),
            "volume": float(row.get("成交量", 0)),
            "amount": float(row.get("成交额", 0)),
            "high": float(row.get("最高", 0)),
            "low": float(row.get("最低", 0)),
            "open": float(row.get("今开", 0)),
            "prev_close": float(row.get("昨收", 0)),
            "pe_ratio": float(row.get("市盈率-动态", 0)) if pd.notna(row.get("市盈率-动态")) else None,
            "market_cap": float(row.get("总市值", 0)),
            "turnover_rate": float(row.get("换手率", 0)) if pd.notna(row.get("换手率")) else None,
        }
    except Exception as e:
        print(f"获取股票 {code} 实时数据失败: {e}")
        return {}


def get_stock_history(code: str, days: int = 60) -> list:
    """获取股票历史K线"""
    try:
        df = ak.stock_zh_a_hist(symbol=code, period="daily", adjust="qfq")
        if df is None or df.empty:
            return []
        df = df.sort_values("日期").tail(days)
        result = []
        for _, row in df.iterrows():
            result.append({
                "date": str(row["日期"]),
                "open": float(row["开盘"]),
                "close": float(row["收盘"]),
                "high": float(row["最高"]),
                "low": float(row["最低"]),
                "volume": float(row["成交量"]),
                "change_pct": float(row.get("涨跌幅", 0)),
            })
        return result
    except Exception as e:
        print(f"获取股票 {code} 历史数据失败: {e}")
        return []


# ==================== 数据获取 - 基金 ====================
def get_fund_realtime(code: str) -> dict:
    """获取基金最新净值数据"""
    try:
        df = ak.fund_open_fund_info_em(symbol=code, indicator="单位净值走势")
        if df is None or df.empty:
            return {}
        
        ncols = len(df.columns)
        if ncols >= 5:
            df.columns = ["日期", "单位净值", "日增长率", "申购状态", "赎回状态"][:ncols]
        elif ncols == 4:
            df.columns = ["日期", "单位净值", "日增长率", "其他"]
        elif ncols == 3:
            df.columns = ["日期", "单位净值", "日增长率"]
        else:
            df.columns = ["日期", "单位净值"][:ncols]
        
        df["日期"] = pd.to_datetime(df["日期"])
        df["单位净值"] = pd.to_numeric(df["单位净值"], errors="coerce")
        if "日增长率" in df.columns:
            df["日增长率"] = pd.to_numeric(df["日增长率"], errors="coerce")
        else:
            df["日增长率"] = df["单位净值"].pct_change() * 100
        df = df.sort_values("日期").tail(60)
        
        latest = df.iloc[-1]
        latest_nav = float(latest["单位净值"])
        
        # 计算各周期涨跌
        def calc_return(n):
            if len(df) >= n:
                old_nav = float(df.iloc[-n]["单位净值"])
                return round((latest_nav - old_nav) / old_nav * 100, 2)
            return None
        
        daily_change = float(latest["日增长率"]) if pd.notna(latest["日增长率"]) else 0
        
        return {
            "code": code,
            "latest_nav": latest_nav,
            "latest_date": latest["日期"].strftime("%Y-%m-%d"),
            "daily_change": round(daily_change, 2),
            "return_5d": calc_return(6),
            "return_20d": calc_return(21),
            "return_60d": calc_return(61),
            "max_nav": round(float(df["单位净值"].max()), 4),
            "min_nav": round(float(df["单位净值"].min()), 4),
            "drawdown_from_high": round((latest_nav - float(df["单位净值"].max())) / float(df["单位净值"].max()) * 100, 2),
        }
    except Exception as e:
        print(f"获取基金 {code} 数据失败: {e}")
        return {}


def get_fund_history(code: str, days: int = 60) -> list:
    """获取基金历史净值"""
    try:
        df = ak.fund_open_fund_info_em(symbol=code, indicator="单位净值走势")
        if df is None or df.empty:
            return []
        
        ncols = len(df.columns)
        if ncols >= 3:
            df.columns = ["日期", "单位净值", "日增长率"] + [f"col{i}" for i in range(ncols - 3)]
        else:
            df.columns = ["日期", "单位净值"] + [f"col{i}" for i in range(ncols - 2)]
        
        df["日期"] = pd.to_datetime(df["日期"])
        df["单位净值"] = pd.to_numeric(df["单位净值"], errors="coerce")
        df = df.sort_values("日期").tail(days)
        
        result = []
        for _, row in df.iterrows():
            result.append({
                "date": str(row["日期"].date()),
                "nav": float(row["单位净值"]),
            })
        return result
    except Exception as e:
        print(f"获取基金 {code} 历史数据失败: {e}")
        return []


# ==================== AI 分析 ====================
def analyze_with_ai(prompt: str, max_tokens: int = 800) -> str:
    """调用 DeepSeek AI"""
    try:
        resp = requests.post(
            f"{OPENAI_BASE_URL}/chat/completions",
            headers={"Authorization": f"Bearer {OPENAI_API_KEY}"},
            json={
                "model": OPENAI_MODEL,
                "messages": [{"role": "user", "content": prompt}],
                "temperature": 0.7,
                "max_tokens": max_tokens,
            },
            timeout=60,
        )
        resp.raise_for_status()
        result = resp.json()
        return result["choices"][0]["message"]["content"]
    except Exception as e:
        print(f"AI 分析失败: {e}")
        return f"AI分析失败: {str(e)}"


def analyze_stock_ai(code: str, name: str, realtime: dict, history: list) -> str:
    """AI分析股票"""
    if not realtime:
        return "❌ 数据获取失败，无法进行AI分析"
    
    recent = history[-20:] if len(history) >= 20 else history
    trend_text = "\n".join([f"  {d['date']}: 收盘{d['close']} 涨跌{d['change_pct']}%" for d in recent[-10:]])
    
    prompt = f"""你是一个专业的A股分析师。请分析以下股票数据，给出简洁的投资建议。

股票: {name}({code})
当前价格: {realtime.get('price', 'N/A')}
今日涨跌: {realtime.get('change_pct', 0):+.2f}%
今开: {realtime.get('open', 'N/A')} | 最高: {realtime.get('high', 'N/A')} | 最低: {realtime.get('low', 'N/A')}
昨收: {realtime.get('prev_close', 'N/A')}
成交量: {realtime.get('volume', 'N/A')}
成交额: {realtime.get('amount', 'N/A')}
市盈率(动态): {realtime.get('pe_ratio', 'N/A')}
总市值: {realtime.get('market_cap', 'N/A')}
换手率: {realtime.get('turnover_rate', 'N/A')}%

近10日走势:
{trend_text}

请用以下格式输出（简洁，适合手机阅读）：
📊 核心结论：（一句话总结当前状态）
📈 趋势判断：（短期走势分析，包含支撑位和压力位）
⚠️ 风险提示：（主要风险点）
💡 操作建议：（买入/持有/减仓/观望，附理由和参考价位）
🎯 评分：（1-100分，附评分理由）"""
    
    return analyze_with_ai(prompt)


def analyze_fund_ai(code: str, name: str, fund_data: dict) -> str:
    """AI分析基金"""
    if not fund_data:
        return "❌ 数据获取失败，无法进行AI分析"
    
    prompt = f"""你是一个专业的基金分析师。请分析以下基金数据，给出简洁的投资建议。

基金: {name}({code})
最新净值: {fund_data.get('latest_nav', 'N/A')} ({fund_data.get('latest_date', 'N/A')})
今日涨跌: {fund_data.get('daily_change', 0):+.2f}%
近5日涨跌: {fund_data.get('return_5d', 'N/A')}%
近20日涨跌: {fund_data.get('return_20d', 'N/A')}%
近60日涨跌: {fund_data.get('return_60d', 'N/A')}%
最高净值: {fund_data.get('max_nav', 'N/A')}
最低净值: {fund_data.get('min_nav', 'N/A')}
距最高回撤: {fund_data.get('drawdown_from_high', 'N/A')}%

请用以下格式输出（简洁，适合手机阅读）：
📊 核心结论：（一句话总结）
📈 趋势判断：（短期/中期走势）
⚠️ 风险提示：（主要风险）
💡 操作建议：（加仓/持有/减仓/观望，附理由）
🎯 评分：（1-100分）"""
    
    return analyze_with_ai(prompt)


# ==================== 缓存逻辑 ====================
def get_cached_analysis(cache_type: str, code: str) -> Optional[dict]:
    """获取缓存的分析结果"""
    with get_db() as conn:
        row = conn.execute(
            "SELECT * FROM analysis_cache WHERE type=? AND code=?",
            (cache_type, code)
        ).fetchone()
        if row:
            updated_at = datetime.strptime(row["updated_at"], "%Y-%m-%d %H:%M:%S")
            if datetime.now() - updated_at < timedelta(hours=CACHE_HOURS):
                return {
                    "analysis": row["analysis_result"],
                    "data": json.loads(row["data_json"]) if row["data_json"] else None,
                    "updated_at": row["updated_at"],
                    "cached": True,
                }
    return None


def save_cache(cache_type: str, code: str, analysis: str, data: dict):
    """保存分析缓存"""
    now = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    with get_db() as conn:
        conn.execute(
            """INSERT OR REPLACE INTO analysis_cache (type, code, analysis_result, data_json, updated_at)
               VALUES (?, ?, ?, ?, ?)""",
            (cache_type, code, analysis, json.dumps(data, ensure_ascii=False), now)
        )
        conn.commit()


# ==================== Pydantic 模型 ====================
class StockAdd(BaseModel):
    code: str
    name: str

class FundAdd(BaseModel):
    code: str
    name: str


# ==================== API 接口 ====================

@app.get("/")
async def index():
    """首页 - 返回前端HTML"""
    html_path = Path(__file__).parent.parent / "frontend" / "index.html"
    if html_path.exists():
        return FileResponse(html_path, media_type="text/html")
    return {"message": "前端文件未找到，API服务运行中"}


# --- 持仓管理 ---
@app.get("/api/stocks")
async def get_stocks():
    """获取持仓股票列表"""
    with get_db() as conn:
        rows = conn.execute("SELECT * FROM stocks ORDER BY added_at DESC").fetchall()
        return [dict(r) for r in rows]


@app.get("/api/funds")
async def get_funds():
    """获取持仓基金列表"""
    with get_db() as conn:
        rows = conn.execute("SELECT * FROM funds ORDER BY added_at DESC").fetchall()
        return [dict(r) for r in rows]


@app.post("/api/stocks")
async def add_stock(item: StockAdd):
    """添加股票"""
    now = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    with get_db() as conn:
        try:
            conn.execute("INSERT INTO stocks (code, name, added_at) VALUES (?,?,?)",
                        (item.code, item.name, now))
            conn.commit()
            return {"status": "ok", "message": f"已添加 {item.name}({item.code})"}
        except sqlite3.IntegrityError:
            raise HTTPException(400, f"股票 {item.code} 已在持仓中")


@app.post("/api/funds")
async def add_fund(item: FundAdd):
    """添加基金"""
    now = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    with get_db() as conn:
        try:
            conn.execute("INSERT INTO funds (code, name, added_at) VALUES (?,?,?)",
                        (item.code, item.name, now))
            conn.commit()
            return {"status": "ok", "message": f"已添加 {item.name}({item.code})"}
        except sqlite3.IntegrityError:
            raise HTTPException(400, f"基金 {item.code} 已在持仓中")


@app.delete("/api/stocks/{code}")
async def delete_stock(code: str):
    """删除股票"""
    with get_db() as conn:
        row = conn.execute("SELECT * FROM stocks WHERE code=?", (code,)).fetchone()
        if not row:
            raise HTTPException(404, f"股票 {code} 不存在")
        conn.execute("DELETE FROM stocks WHERE code=?", (code,))
        conn.commit()
        return {"status": "ok", "message": f"已删除 {row['name']}({code})"}


@app.delete("/api/funds/{code}")
async def delete_fund(code: str):
    """删除基金"""
    with get_db() as conn:
        row = conn.execute("SELECT * FROM funds WHERE code=?", (code,)).fetchone()
        if not row:
            raise HTTPException(404, f"基金 {code} 不存在")
        conn.execute("DELETE FROM funds WHERE code=?", (code,))
        conn.commit()
        return {"status": "ok", "message": f"已删除 {row['name']}({code})"}


# --- 分析接口 ---
@app.get("/api/analyze/stock/{code}")
async def analyze_stock(code: str, force: bool = False):
    """分析任意股票"""
    # 先查缓存
    if not force:
        cached = get_cached_analysis("stock", code)
        if cached:
            cached["code"] = code
            cached["type"] = "stock"
            return cached
    
    # 获取实时数据
    realtime = get_stock_realtime(code)
    name = realtime.get("name", code) if realtime else code
    
    # 获取历史数据
    history = get_stock_history(code)
    
    # AI 分析
    analysis = analyze_stock_ai(code, name, realtime, history)
    
    # 组装结果数据
    data = {
        "realtime": realtime,
        "history": history[-30:],  # 最近30天
    }
    
    # 保存缓存
    save_cache("stock", code, analysis, data)
    
    return {
        "code": code,
        "type": "stock",
        "analysis": analysis,
        "data": data,
        "updated_at": datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
        "cached": False,
    }


@app.get("/api/analyze/fund/{code}")
async def analyze_fund(code: str, force: bool = False):
    """分析任意基金"""
    # 先查缓存
    if not force:
        cached = get_cached_analysis("fund", code)
        if cached:
            cached["code"] = code
            cached["type"] = "fund"
            return cached
    
    # 获取基金数据
    fund_data = get_fund_realtime(code)
    
    # 从数据库获取名称
    with get_db() as conn:
        row = conn.execute("SELECT name FROM funds WHERE code=?", (code,)).fetchone()
        name = row["name"] if row else code
    
    # 获取历史净值
    history = get_fund_history(code)
    
    # AI 分析
    analysis = analyze_fund_ai(code, name, fund_data)
    
    # 组装结果
    data = {
        "fund_info": fund_data,
        "history": history[-30:],
    }
    
    # 保存缓存
    save_cache("fund", code, analysis, data)
    
    return {
        "code": code,
        "type": "fund",
        "name": name,
        "analysis": analysis,
        "data": data,
        "updated_at": datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
        "cached": False,
    }


# --- 仪表盘 ---
@app.get("/api/dashboard")
async def dashboard():
    """获取仪表盘概览数据"""
    with get_db() as conn:
        stocks = conn.execute("SELECT * FROM stocks ORDER BY added_at").fetchall()
        funds = conn.execute("SELECT * FROM funds ORDER BY added_at").fetchall()
    
    stock_quotes = []
    for s in stocks:
        try:
            quote = get_stock_realtime(s["code"])
            if quote:
                quote["name"] = s["name"]
                stock_quotes.append(quote)
            time.sleep(0.1)
        except Exception:
            pass
    
    fund_quotes = []
    for f in funds:
        try:
            quote = get_fund_realtime(f["code"])
            if quote:
                quote["name"] = f["name"]
                fund_quotes.append(quote)
            time.sleep(0.1)
        except Exception:
            pass
    
    return {
        "stocks": stock_quotes,
        "funds": fund_quotes,
        "updated_at": datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
        "summary": {
            "stock_count": len(stock_quotes),
            "fund_count": len(fund_quotes),
            "stocks_up": sum(1 for s in stock_quotes if s.get("change_pct", 0) > 0),
            "stocks_down": sum(1 for s in stock_quotes if s.get("change_pct", 0) < 0),
            "funds_up": sum(1 for f in fund_quotes if f.get("daily_change", 0) > 0),
            "funds_down": sum(1 for f in fund_quotes if f.get("daily_change", 0) < 0),
        }
    }


# ==================== 启动 ====================
@app.on_event("startup")
async def startup():
    init_db()
    seed_initial_data()


if __name__ == "__main__":
    import uvicorn
    init_db()
    seed_initial_data()
    uvicorn.run(app, host="0.0.0.0", port=8000)

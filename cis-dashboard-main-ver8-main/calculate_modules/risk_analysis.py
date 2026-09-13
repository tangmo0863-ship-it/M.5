"""
calculate_modules/risk_analysis.py
--------------------------------------
สูตรคำนวณโมดูล "Risk Analysis" (🛡️) — คู่กับ pages_content/risk_analysis.py

=== DATA CONTRACT (ห้ามลบ/เปลี่ยนชื่อ key เดิมโดยไม่แจ้งทีม — เพิ่ม key ใหม่ได้อิสระ) ===

calculate_risk_module(df_price_ticker, risk_static_row) รับ:
    df_price_ticker  : pd.DataFrame ราคาหุ้น 1 ตัว เรียงตามวันที่ (ต้องมีคอลัมน์ date, close;
                       ถ้ามีคอลัมน์ volume จะคำนวณ Trading Liquidity เพิ่มให้ด้วย)
    risk_static_row  : pd.DataFrame แถวเดียว (หรือ None) จากตาราง stock_risk_static

คืนค่าเป็น dict ที่ต้องมี key เดิมครบ (Data Contract เดิม):
    risk_score, volatility, volatility_calc, max_drawdown, var_95, beta, sharpe_ratio, sortino_ratio

Key ใหม่ที่เพิ่มเข้ามา (ไม่กระทบ contract เดิม):
    cvar_95               : float        Expected Shortfall 95% (%, ค่าเฉลี่ยผลตอบแทนแย่สุด 5% ล่างจริง)
    avg_daily_value_mb    : float หรือ None  มูลค่าซื้อขายเฉลี่ย 60 วันล่าสุด (ล้านบาท/วัน)
    worst_dd_20d          : float หรือ None  % การเปลี่ยนแปลงราคาในช่วง 20 วันทำการที่แย่ที่สุดที่เคยเกิดจริง
    worst_dd_20d_end_date : str หรือ None    วันที่สิ้นสุดของช่วง 20 วันนั้น (YYYY-MM-DD)

build_risk_rolling_history(df_price_ticker) คืน pd.DataFrame
    คอลัมน์ [date, rolling_vol_30d, drawdown_pct] — ไม่เปลี่ยนแปลงจากเดิม

ที่มาของสูตร: ดูละเอียดใน DATA_FORMULA_AUDIT.md หัวข้อ 5
สรุปสั้น: Annualized Volatility, Max Drawdown, VaR (parametric 95%) เป็นสูตรมาตรฐาน
Sharpe/Sortino ตอนนี้หัก Risk-free Rate จริงแล้ว (ดูค่าคงที่ RISK_FREE_RATE_ANNUAL ด้านล่าง)
CVaR เป็นสูตรมาตรฐาน (Historical Expected Shortfall) — ใช้ข้อมูล return จริง ไม่สมมติการแจกแจง
risk_score (คะแนนรวม 0-100) ยังเป็นสูตรแปลงที่กำหนดเองเหมือนเดิม (ไม่ได้แก้)

=== เปลี่ยนแปลงจากเวอร์ชันก่อนหน้า (แจ้งทีมตาม Definition of Done) ===
1. เพิ่ม RISK_FREE_RATE_ANNUAL = 2.0% (ที่มา: BOT Policy Rate เฉลี่ย 2023-2025) เข้าไปในสูตร
   Sharpe/Sortino แทนที่จะสมมติ Rf = 0 เหมือนเดิม
2. เพิ่ม CVaR 95%, Trading Liquidity, Worst 20-Day Drawdown (เกิดขึ้นจริง) เป็น key ใหม่
3. ตัด/ไม่ใช้สูตร "rate_impact" และ "recession_impact" ที่เคยคำนวณในชั้น UI (ประดิษฐ์เองล้วนๆ
   ไม่มีที่มาทางทฤษฎี) — ดูรายละเอียดใน pages_content/risk_analysis.py แทน
"""

import numpy as np
import pandas as pd

from calculate_modules.common import clean_float

# Risk-free Rate (Rf) ต่อปี — ใช้ในสูตร Sharpe/Sortino Ratio
# ที่มา: Bank of Thailand, Policy Interest Rate (อ้างอิงซ้ำจาก CEIC Data) ช่วงปี 2023-2025
#   ก.ย.2023 - ก.ย.2024: คงที่ 2.50%
#   ปลายปี 2024 - 2025: ทยอยลดลงเหลือ 2.25% -> 2.00% -> 1.75% -> 1.50% -> 1.25%
# ค่าเฉลี่ยถ่วงเวลาตลอดช่วงข้อมูลของระบบนี้ (2023-2025) ≈ 2.0% ต่อปี
# 🟡 เป็นค่าคงที่โดยประมาณ (เหมือน WACC ใน fair_value.py) ไม่ใช่ Rf รายวันที่เปลี่ยนตามจริงทุกวัน
RISK_FREE_RATE_ANNUAL = 0.02

# จำนวนวันทำการที่ใช้หาช่วง "แย่ที่สุดที่เคยเกิดจริง" สำหรับ Stress Test แบบอิงข้อมูลจริง (~1 เดือนซื้อขาย)
STRESS_WINDOW_DAYS = 20

# จำนวนวันย้อนหลังที่ใช้เฉลี่ยมูลค่าซื้อขายต่อวัน (Trading Liquidity)
LIQUIDITY_LOOKBACK_DAYS = 60


def calculate_risk_module(df_price_ticker, risk_static_row):
    """Module 5: Risk Analysis (ใช้ Beta/Volatility/Max Drawdown จริงจาก stock_risk_metrics.csv
    ผสมกับความผันผวน/Drawdown/CVaR/Liquidity ที่คำนวณจากราคาย้อนหลังจริงในช่วง 2023-2025)"""
    df = df_price_ticker.sort_values(by='date').copy()
    df['close'] = df['close'].apply(clean_float)
    df['returns'] = df['close'].pct_change()

    daily_vol = df['returns'].std()
    annual_vol_calc = daily_vol * np.sqrt(252) * 100  # Annualized Volatility (มาตรฐาน)

    cum_max = df['close'].cummax()
    drawdown = (df['close'] - cum_max) / cum_max
    max_dd_calc = abs(drawdown.min()) * 100  # Maximum Drawdown (มาตรฐาน)

    var_95 = 1.645 * daily_vol * 100  # Parametric VaR 95% (z-score 1.645)

    # --- CVaR 95% (Expected Shortfall) ---
    # ค่าเฉลี่ยของผลตอบแทนรายวันในกลุ่ม 5% ที่แย่ที่สุดจริง (Historical method)
    # ต่างจาก VaR ตรงที่ไม่สมมติว่าผลตอบแทนแจกแจงแบบ Normal จึงจับ "หางอ้วน" (fat tail) ได้ดีกว่า
    valid_returns = df['returns'].dropna()
    if len(valid_returns) >= 20:
        tail_cutoff = valid_returns.quantile(0.05)
        tail_losses = valid_returns[valid_returns <= tail_cutoff]
        cvar_95 = abs(tail_losses.mean()) * 100 if len(tail_losses) > 0 else var_95
    else:
        cvar_95 = var_95

    # ใช้ค่าจริงจากไฟล์ stock_risk_metrics.csv เป็นหลักถ้ามี ไม่งั้น fallback เป็นค่าที่คำนวณเอง
    if risk_static_row is not None and not risk_static_row.empty:
        beta = clean_float(risk_static_row.iloc[0].get('beta'), default=1.0)
        annual_vol = clean_float(risk_static_row.iloc[0].get('volatility_pct'), default=annual_vol_calc)
        max_dd = abs(clean_float(risk_static_row.iloc[0].get('max_drawdown_pct'), default=max_dd_calc))
    else:
        beta = 1.0
        annual_vol = annual_vol_calc
        max_dd = max_dd_calc

    risk_index = (annual_vol * 0.45) + (max_dd * 0.35) + (var_95 * 2.0)
    risk_score = round(float(np.clip(100 - risk_index, 25, 92)), 1)

    # --- Sharpe / Sortino Ratio (หัก Risk-free Rate จริงแล้ว — ไม่สมมติ Rf = 0 อีกต่อไป) ---
    annual_return = df['returns'].mean() * 252
    sharpe = round(float((annual_return - RISK_FREE_RATE_ANNUAL) / (daily_vol * np.sqrt(252))), 2) if daily_vol > 0 else 0.0
    downside_returns = df['returns'][df['returns'] < 0]
    downside_std = downside_returns.std() if len(downside_returns) > 1 else daily_vol
    sortino = round(float((annual_return - RISK_FREE_RATE_ANNUAL) / (downside_std * np.sqrt(252))), 2) if downside_std > 0 else 0.0

    # --- Trading Liquidity: มูลค่าซื้อขายเฉลี่ยต่อวัน (ล้านบาท) จาก volume x close จริง ---
    avg_daily_value_mb = None
    if 'volume' in df.columns:
        df['traded_value'] = df['close'] * df['volume'].apply(clean_float)
        recent_value = df['traded_value'].tail(LIQUIDITY_LOOKBACK_DAYS)
        if not recent_value.empty:
            avg_daily_value_mb = round(float(recent_value.mean() / 1e6), 2)

    # --- Worst 20-Day Drawdown ที่เคยเกิดขึ้นจริง (แทนสูตร stress test แบบประดิษฐ์เอง) ---
    worst_dd_20d, worst_dd_20d_end_date = None, None
    if len(df) > STRESS_WINDOW_DAYS:
        roll_return = df['close'].pct_change(STRESS_WINDOW_DAYS) * 100
        if roll_return.notna().any():
            worst_idx = roll_return.idxmin()
            worst_dd_20d = round(float(roll_return.loc[worst_idx]), 1)
            worst_dd_20d_end_date = str(df.loc[worst_idx, 'date'])[:10]

    return {
        'risk_score': risk_score,
        'volatility': round(float(annual_vol), 1),
        'volatility_calc': round(float(annual_vol_calc), 1),
        'max_drawdown': round(float(max_dd), 1),
        'var_95': round(float(var_95), 2),
        'cvar_95': round(float(cvar_95), 2),
        'beta': round(float(beta), 2),
        'sharpe_ratio': sharpe,
        'sortino_ratio': sortino,
        'avg_daily_value_mb': avg_daily_value_mb,
        'worst_dd_20d': worst_dd_20d,
        'worst_dd_20d_end_date': worst_dd_20d_end_date,
    }


def build_risk_rolling_history(df_price_ticker):
    """คำนวณ rolling 30 วัน ของ Volatility (annualized) และ Drawdown จากราคาปิดจริง — ไม่เปลี่ยนแปลงจากเดิม"""
    df = df_price_ticker.sort_values(by='date').copy()
    df['close'] = df['close'].apply(clean_float)
    df['returns'] = df['close'].pct_change()

    df['rolling_vol_30d'] = df['returns'].rolling(30).std() * np.sqrt(252) * 100
    cum_max = df['close'].cummax()
    df['drawdown_pct'] = (df['close'] - cum_max) / cum_max * 100

    out = df[['date', 'rolling_vol_30d', 'drawdown_pct']].dropna(subset=['rolling_vol_30d']).copy()
    out = out.set_index('date').resample('W').last().dropna().reset_index()
    return out

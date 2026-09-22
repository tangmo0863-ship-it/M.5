"""
calculate_modules/risk_analysis.py
--------------------------------------
สูตรคำนวณโมดูล "Risk Analysis" (🛡️) — คู่กับ pages_content/risk_analysis.py

=== DATA CONTRACT (ห้ามลบ/เปลี่ยนชื่อ key เดิมโดยไม่แจ้งทีม — เพิ่ม key ใหม่ได้อิสระ) ===

calculate_risk_module(df_price_ticker, risk_static_row) รับ:
    df_price_ticker  : pd.DataFrame ราคาหุ้น 1 ตัว เรียงตามวันที่ (ต้องมีคอลัมน์ date, close)
    risk_static_row  : pd.DataFrame แถวเดียว (หรือ None) จากตาราง stock_risk_static

คืนค่าเป็น dict ที่ต้องมี key เดิมครบ:
    risk_score, volatility, volatility_calc, max_drawdown, var_95, beta, sharpe_ratio, sortino_ratio

--- key ใหม่ (ทุกตัวเป็น scalar เก็บลง SQLite ได้ตรงๆ ไม่มี dict/list ซ้อน — ดู F-1) ---
    cvar_95              : float หรือ None — Conditional VaR / Expected Shortfall 95% (Historical Simulation)
    psr                  : float หรือ None — Probabilistic Sharpe Ratio (%)
    recovery_days        : int หรือ None   — จำนวนวันฟื้นตัวจากจุดต่ำสุดของ Max Drawdown กลับสู่จุดสูงสุดเดิม
    risk_free_rate_annual: float           — อัตราดอกเบี้ยปลอดความเสี่ยงที่ใช้
    risk_dim_tail         : float 0-100    — คะแนนย่อยมิติ Tail Risk (CVaR) ก่อนถ่วงน้ำหนัก ยิ่งสูง=ยิ่งเสี่ยง
    risk_dim_drawdown     : float 0-100    — คะแนนย่อยมิติ Drawdown+Recovery ก่อนถ่วงน้ำหนัก
    risk_dim_volatility   : float 0-100    — คะแนนย่อยมิติ Volatility ก่อนถ่วงน้ำหนัก
    risk_dim_market       : float 0-100    — คะแนนย่อยมิติ Market Risk (Beta) ก่อนถ่วงน้ำหนัก
    risk_dim_quality      : float 0-100    — คะแนนย่อยมิติ Return Quality (PSR) ก่อนถ่วงน้ำหนัก
    beta_verified         : bool           — เสมอ False (ดูเหตุผลใน CHANGELOG รอบที่ 3 / F-4)

=== CHANGELOG ===

รอบที่ 1 (แก้บั๊ก): CVaR/PSR/Recovery Duration เพิ่มใหม่, Sharpe/Sortino หัก Risk-free Rate จริง
รอบที่ 2 (จัดน้ำหนัก risk_score ใหม่): Tail 30% / Drawdown+Recovery 25% / Volatility 20% /
    Market(Beta) 15% / Quality(PSR) 10% แทน 45/35/20% เดิม — ตัด Stress Test (rate/recession) ออก
(รายละเอียดเต็มของรอบที่ 1-2 อยู่ใน DATA_FORMULA_AUDIT.md หัวข้อ 5 และ git history)

รอบที่ 3 (แก้ตามรายงานตรวจสอบภายนอก "Module5_RiskAnalysis_Review_C1-C5" — ผู้ตรวจคนละคนกับที่เขียนโค้ดเดิม):

**สิ่งที่แก้แล้ว (ไม่ต้องรอการตัดสินใจ):**
- **F-1 (สูง):** `risk_score_breakdown` เคยเป็น dict ซ้อนอยู่ใน dict ที่คืนออกไป → `to_sql()` ของ SQLite
  บันทึกไม่ได้เลย (`DatabaseError: ... type 'dict' is not supported`) ทำให้ `calculate_scores.py`
  ล้มทั้งเส้นถ้ารันจริง **แก้โดยแตกเป็น 5 key เดี่ยว** (`risk_dim_tail`, `risk_dim_drawdown`,
  `risk_dim_volatility`, `risk_dim_market`, `risk_dim_quality`) แทนที่ dict เดิม
- **F-7a (กลาง):** เดิมแปลงราคาปิดที่ขาดหาย/อ่านไม่ได้เป็น 0.0 ผ่าน `clean_float` (ค่า default ของ
  ฟังก์ชันนั้นเหมาะกับอัตราส่วนทางการเงิน ไม่เหมาะกับราคา) ถ้าราคาหายไป 1 วันจะกลายเป็นหุ้นราคา 0 บาท
  → ผลตอบแทนวันนั้น -100% แล้วลากค่า Volatility/Sharpe/PSR ทั้งหมดพัง (ทดสอบแล้วได้ risk_score=NaN,
  Sortino=inf) **แก้โดยไม่เติม 0 ให้ราคาที่ขาดหาย ตัดแถวนั้นออกจากการคำนวณแทน**
- **F-8(ง):** เปิดเผยว่าตัวเลขบทลงโทษ Recovery (+10/+7/+3) เป็นการกำหนดเองของผู้พัฒนา ไม่ได้มาจาก
  arXiv:1403.8125 โดยตรง (ผู้ตรวจภายนอกตั้งข้อสงสัยว่าบทความอาจหมายถึงนิยาม "recovery" ต่างจากที่
  ใช้ในโค้ดนี้ — เป็นผลตอบแทนหลัง drawdown ไม่ใช่จำนวนวัน)
- **F-9:** ลดความมั่นใจของการอ้างอิงงานวิจัยในเอกสารลง เพราะยังไม่มีใครตรวจกับต้นฉบับเต็ม (ดูด้านล่าง)

**สิ่งที่ยังไม่แก้ เพราะต้องให้เจ้าของโมดูล/มนุษย์ตัดสินใจก่อน (ห้าม AI เลือกเอง — มีคอมเมนต์ `# TODO(F-x)`
กำกับจุดที่เกี่ยวข้องในโค้ดด้านล่าง):**
- **F-3 (สูง):** ค่า Max Drawdown จากไฟล์ `stock_risk_metrics.csv` ผู้ตรวจภายนอกรายงานว่าเท่ากันทุกหุ้น
  (−29.36% ทั้ง 8 ตัว) ซึ่งเป็นไปไม่ได้ทางสถิติ ต้องเลือกว่าจะ (ก) แก้ไฟล์ต้นทาง หรือ (ข) ใช้ค่าที่คำนวณ
  จากราคาจริงเป็นค่าหลักแทน หรือ (ค) เพิ่มระบบตรวจจับความผิดปกติอัตโนมัติ
- **F-4 (สูง):** Volatility จากไฟล์ไม่ตรงกับที่คำนวณจากราคาจริงในหลายหุ้น และไม่มีใครยืนยันได้ว่า Beta
  ในไฟล์คำนวณจากดัชนีอะไร/ช่วงเวลาไหน (`beta_verified = False` เสมอในเวอร์ชันนี้)
- **F-5 (สูง):** ราคา TRUE กระโดด +68.63% วันเดียว (2023-03-03) จากราคาค้าง (volume=0 หลายวันติด)
  ต้องตัดสินใจว่าจะเริ่มคำนวณสถิติหลังเหตุการณ์ / ตัดวันนั้นออกจากผลตอบแทน / ปล่อยไว้
- **F-6 (กลาง):** VaR ใช้ Parametric ส่วน CVaR ใช้ Historical (คนละวิธี) ทำให้บางกรณี (เช่นหุ้นที่มีราคา
  กระโดดผิดปกติแบบ F-5) VaR อาจมากกว่า CVaR ซึ่งขัดกับหลักการที่ CVaR ต้องแย่กว่า VaR เสมอเมื่อใช้วิธี
  เดียวกัน ต้องเลือกว่าจะเปลี่ยน VaR เป็น Historical ให้เข้าชุดกับ CVaR หรือคงไว้แต่ติดป้ายให้ชัดเจนกว่านี้
- **F-8(ก) (กลาง):** `downside_std` ในสูตร Sortino ปัจจุบันคำนวณส่วนเบี่ยงเบนมาตรฐานของผลตอบแทนขาลง
  "รอบค่าเฉลี่ยของกลุ่มขาลงเอง" (`.std()` ธรรมดา) ไม่ใช่ Downside Deviation ตามตำรา (ซึ่งควรวัดส่วน
  เบี่ยงเบนจาก MAR/target โดยหารด้วยจำนวนข้อมูลทั้งหมด ไม่ใช่แค่จำนวนวันขาลง) ต่างกันไม่เกิน 0.09 ใน
  การทดสอบ แต่เป็นคนละนิยามทางเทคนิค ต้องเลือกว่าจะแก้สูตรให้ตรงตำรา หรือแก้คำอธิบายให้ตรงกับสูตรจริง

⚠️ **F-9 — ระดับความน่าเชื่อถือของงานวิจัยที่อ้างอิง (ยังไม่มีใครตรวจกับต้นฉบับเต็ม):**
ผู้ตรวจภายนอกตรวจสอบเบื้องต้น (บางส่วนค้นเว็บ) แล้วพบข้อสงสัยที่ **ต้องให้ผู้ตรวจสอบที่เป็นมนุษย์ยืนยัน
กับต้นฉบับเต็มก่อน** — ห้ามถือว่าการอ้างอิงเหล่านี้ผ่านการตรวจสอบแล้ว:
  - arXiv:1403.8125 ("Maximum drawdown, recovery, and momentum") อาจเป็นบทความเรื่องกลยุทธ์ momentum
    ที่นิยาม "recovery" เป็นผลตอบแทนหลังจุดตกลึก ไม่ใช่ "จำนวนวัน" ที่โค้ดนี้คำนวณ
  - Sortino, "Mean-Semivariance Behavior" — ชื่อบทความยังไม่ยืนยันได้ว่าถูกต้อง
  - Jorion (2007) กับคำว่า "CVaR เป็น coherent risk measure" — คุณสมบัตินี้มักอ้างอิงจากงานอื่น
    (Artzner et al.) ไม่แน่ใจว่า Jorion กล่าวไว้ตรงจุดนี้จริงหรือไม่
  - "Downside Beta (2006)" — ไม่ได้ระบุชื่อผู้เขียนไว้ ตรวจสอบไม่ได้
  - น้ำหนัก 30/25/20/15/10% และตัวคูณ (×40, ×1.3, ×1.5, ×10) **เป็นดุลยพินิจของผู้พัฒนา ไม่ได้มาจาก
    บทความโดยตรงข้อใดข้อหนึ่ง** — งานวิจัยสนับสนุนแค่ "แนวคิด" ว่าความเสี่ยงขาลงควรมีน้ำหนักมากกว่า
    ความผันผวนสมมาตร ไม่ได้ให้ตัวเลขเจาะจง (ระบุไว้แล้วตั้งแต่รอบที่ 2 เช่นกัน)

=== สิ่งที่ "ทำไม่ได้" ในเวอร์ชันนี้ (ยังไม่เปลี่ยนแปลง) ===
- Downside Beta (β⁻) และ Fama-French 5-Factor Model ยังทำไม่ได้ เพราะไม่มีข้อมูลดัชนีตลาดอ้างอิง
  (SET Index) หรือ factor data (Size/Value/Profitability/Investment) ในระบบปัจจุบัน
"""

import math

import numpy as np
import pandas as pd

from calculate_modules.common import clean_float

# อัตราดอกเบี้ยปลอดความเสี่ยง (Risk-free Rate) รายปี
# ที่มา: อัตราดอกเบี้ยนโยบาย ธนาคารแห่งประเทศไทย (BOT Policy Rate) ช่วง 2023-2025 — ค่าประมาณ ≈ 2.0%
RISK_FREE_RATE_ANNUAL = 0.02

# น้ำหนักถ่วงของแต่ละมิติความเสี่ยงใน risk_score
# ⚠️ ห้ามเปลี่ยนตัวเลขเหล่านี้โดยไม่ได้รับอนุมัติจากเจ้าของโมดูล (ตามกฎในรายงานตรวจสอบ F-9)
RISK_WEIGHT_TAIL = 0.30
RISK_WEIGHT_DRAWDOWN = 0.25
RISK_WEIGHT_VOLATILITY = 0.20
RISK_WEIGHT_MARKET = 0.15
RISK_WEIGHT_QUALITY = 0.10

# F-4: โค้ดนี้ไม่ได้คำนวณ Beta เอง (ดึงจากไฟล์ stock_risk_metrics.csv หรือ fallback = 1.0) และไม่มี
# ข้อมูลดัชนีตลาดในระบบให้ตรวจสอบที่มาของ Beta ในไฟล์ได้ ค่านี้จึงคงเป็น False เสมอจนกว่าจะมีคนยืนยัน
# แหล่งที่มาของ Beta ในไฟล์ต้นทาง (ดู F-4 ในรายงานตรวจสอบ)
BETA_VERIFIED = False


def _clean_price_series(df, price_col='close'):
    """แปลงคอลัมน์ราคาเป็นตัวเลขอย่างปลอดภัย โดย **ไม่เติม 0 ให้ราคาที่ขาดหาย/อ่านไม่ได้** (F-7a)
    ต่างจาก clean_float() ทั่วไปที่ default เป็น 0.0 ซึ่งไม่เหมาะกับราคาหุ้น (ราคา 0 บาท = ผลตอบแทน -100%
    ปลอมในวันถัดไป ทำให้ Volatility/Sharpe/CVaR/PSR ทั้งชุดผิดเพี้ยน) — ตัดแถวที่ราคาหายไปออกแทน"""
    out = df.copy()
    out[price_col] = pd.to_numeric(out[price_col], errors='coerce')
    out = out.dropna(subset=[price_col]).reset_index(drop=True)
    return out


def _compute_cvar(returns, confidence=0.95):
    """CVaR / Expected Shortfall (Historical Simulation)"""
    r = returns.dropna()
    if len(r) < 20:
        return None
    cutoff = np.percentile(r, (1 - confidence) * 100)
    tail = r[r <= cutoff]
    if tail.empty:
        return None
    return round(float(abs(tail.mean()) * 100), 2)


def _compute_psr(returns, sr_benchmark=0.0):
    """Probabilistic Sharpe Ratio"""
    r = returns.dropna()
    n = len(r)
    if n < 30 or r.std() == 0:
        return None

    sr_hat = r.mean() / r.std()
    skew = r.skew()
    kurt = r.kurtosis() + 3  # ปรับ excess kurtosis (pandas) กลับเป็น kurtosis ปกติ (Normal = 3)

    denom_sq = 1 - skew * sr_hat + ((kurt - 1) / 4) * sr_hat ** 2
    if denom_sq <= 0:
        return None
    denom = math.sqrt(denom_sq)

    z = (sr_hat - sr_benchmark) * math.sqrt(n - 1) / denom
    psr = 0.5 * (1 + math.erf(z / math.sqrt(2)))
    return round(float(psr) * 100, 1)


def _compute_recovery_days(df):
    """Recovery Duration — จำนวนวันจากจุดต่ำสุดของ Max Drawdown ถึงวันที่ราคากลับสู่จุดสูงสุดเดิม
    ⚠️ ดู F-9: การอ้างอิง arXiv:1403.8125 สำหรับนิยามนี้ยังไม่ได้ตรวจสอบกับต้นฉบับเต็ม"""
    cum_max = df['close'].cummax()
    drawdown = (df['close'] - cum_max) / cum_max
    if drawdown.isna().all():
        return None

    trough_idx = drawdown.idxmin()
    peak_value = cum_max.loc[trough_idx]
    trough_date = df.loc[trough_idx, 'date']

    after_trough = df[df['date'] > trough_date]
    recovered = after_trough[after_trough['close'] >= peak_value]
    if recovered.empty:
        return None
    recovery_date = recovered.iloc[0]['date']
    return int((recovery_date - trough_date).days)


def _recovery_penalty(recovery_days):
    """แปลง Recovery Duration เป็นคะแนนโทษเพิ่มให้มิติ Drawdown
    🟡 ตัวเลขบทลงโทษ (+10/+7/+3) และเกณฑ์วัน (365/180) เป็นการกำหนดเองของผู้พัฒนา **ไม่ได้มาจาก
    arXiv:1403.8125 โดยตรง** (ดู F-8(ง)/F-9 ในรายงานตรวจสอบ — ยังไม่มีใครยืนยันกับต้นฉบับ)"""
    if recovery_days is None:
        return 10.0
    if recovery_days > 365:
        return 7.0
    if recovery_days > 180:
        return 3.0
    return 0.0


def calculate_risk_module(df_price_ticker, risk_static_row):
    """Module 5: Risk Analysis"""
    df = df_price_ticker.sort_values(by='date').reset_index(drop=True)
    df = _clean_price_series(df, 'close')  # F-7a: ตัดแถวราคาขาดหายออก ไม่เติม 0
    df['returns'] = df['close'].pct_change()

    daily_vol = df['returns'].std()
    annual_vol_calc = daily_vol * np.sqrt(252) * 100

    cum_max = df['close'].cummax()
    drawdown = (df['close'] - cum_max) / cum_max
    max_dd_calc = abs(drawdown.min()) * 100

    # TODO(F-6): VaR ใช้ Parametric ส่วน cvar_95 ด้านล่างใช้ Historical — คนละวิธี อาจทำให้ CVaR < VaR
    # ในกรณีราคาผิดปกติรุนแรง (เช่น F-5) ต้องตัดสินใจว่าจะทำให้เป็นวิธีเดียวกันหรือไม่ก่อนแก้
    var_95 = 1.645 * daily_vol * 100
    cvar_95 = _compute_cvar(df['returns'], confidence=0.95)

    # TODO(F-3, F-4): โค้ดเลือกใช้ค่าจากไฟล์ stock_risk_static ก่อนเสมอโดยไม่ตรวจสอบความสมเหตุสมผล
    # (เช่น ค่าซ้ำกันทุกหุ้น หรือห่างจากค่าที่คำนวณจากราคาจริงมากเกินไป) — ต้องตัดสินใจก่อนว่าจะเปลี่ยน
    # แหล่งความจริง (source of truth) เป็นราคาจริงหรือไม่ ยังไม่เปลี่ยนพฤติกรรมในรอบนี้
    if risk_static_row is not None and not risk_static_row.empty:
        beta = clean_float(risk_static_row.iloc[0].get('beta'), default=1.0)
        annual_vol = clean_float(risk_static_row.iloc[0].get('volatility_pct'), default=annual_vol_calc)
        max_dd = abs(clean_float(risk_static_row.iloc[0].get('max_drawdown_pct'), default=max_dd_calc))
    else:
        beta = 1.0
        annual_vol = annual_vol_calc
        max_dd = max_dd_calc

    # Sharpe/Sortino — หัก Risk-free Rate จริง
    rf_daily = RISK_FREE_RATE_ANNUAL / 252
    excess_returns = df['returns'] - rf_daily
    sharpe = round(float((excess_returns.mean() * 252) / (daily_vol * np.sqrt(252))), 2) if daily_vol > 0 else 0.0

    # TODO(F-8ก): downside_std นี้คือ std() ของกลุ่มผลตอบแทนขาลง "รอบค่าเฉลี่ยของกลุ่มนั้นเอง"
    # ไม่ใช่ Downside Deviation ตามตำรา (ซึ่งควรวัดจาก MAR โดยหารด้วย n ทั้งหมด) ต้องตัดสินใจว่าจะ
    # แก้สูตรให้ตรงตำรา หรือแก้คำอธิบายในเอกสาร/UI ให้ตรงกับสูตรจริงที่ใช้อยู่นี้
    downside_returns = df['returns'][df['returns'] < rf_daily]
    downside_std = downside_returns.std() if len(downside_returns) > 1 else daily_vol
    sortino = round(float((excess_returns.mean() * 252) / (downside_std * np.sqrt(252))), 2) if downside_std > 0 else 0.0

    psr = _compute_psr(df['returns'], sr_benchmark=0.0)
    recovery_days = _compute_recovery_days(df)

    # ---------- risk_score: คะแนนรวมแบบถ่วงน้ำหนัก ----------
    tail_dim = float(np.clip((cvar_95 if cvar_95 is not None else var_95) * 10, 5, 95))
    drawdown_dim = float(np.clip(max_dd * 1.5 + _recovery_penalty(recovery_days), 5, 95))
    volatility_dim = float(np.clip(annual_vol * 1.3, 5, 95))
    market_dim = float(np.clip(beta * 40, 5, 95))
    quality_dim = float(np.clip(100 - psr, 5, 95)) if psr is not None else 50.0

    risk_index = (
        tail_dim * RISK_WEIGHT_TAIL +
        drawdown_dim * RISK_WEIGHT_DRAWDOWN +
        volatility_dim * RISK_WEIGHT_VOLATILITY +
        market_dim * RISK_WEIGHT_MARKET +
        quality_dim * RISK_WEIGHT_QUALITY
    )
    # ถ้าข้อมูลราคาน้อยเกินไปจนคำนวณมิติหลักไม่ได้เลย (เช่น daily_vol เป็น NaN) risk_index จะเป็น NaN
    # ปล่อยให้ risk_score เป็น NaN ต่อไปตามจริง (ห้าม UI แปลงเป็นค่ากลางๆ ปลอมๆ — ดู F-7b ฝั่ง pages_content)
    risk_score = round(float(np.clip(100 - risk_index, 25, 92)), 1) if pd.notna(risk_index) else float('nan')

    return {
        # --- key เดิม (Data Contract เดิม ไม่เปลี่ยน) ---
        'risk_score': risk_score,
        'volatility': round(float(annual_vol), 1) if pd.notna(annual_vol) else None,
        'volatility_calc': round(float(annual_vol_calc), 1) if pd.notna(annual_vol_calc) else None,
        'max_drawdown': round(float(max_dd), 1) if pd.notna(max_dd) else None,
        'var_95': round(float(var_95), 2) if pd.notna(var_95) else None,
        'beta': round(float(beta), 2),
        'sharpe_ratio': sharpe,
        'sortino_ratio': sortino,
        # --- key ใหม่ (ทุกตัวเป็น scalar — แก้ F-1) ---
        'cvar_95': cvar_95,
        'psr': psr,
        'recovery_days': recovery_days,
        'risk_free_rate_annual': RISK_FREE_RATE_ANNUAL,
        'risk_dim_tail': round(tail_dim, 1),
        'risk_dim_drawdown': round(drawdown_dim, 1),
        'risk_dim_volatility': round(volatility_dim, 1),
        'risk_dim_market': round(market_dim, 1),
        'risk_dim_quality': round(quality_dim, 1),
        'beta_verified': BETA_VERIFIED,
    }


def build_risk_rolling_history(df_price_ticker):
    """คำนวณ rolling 30 วัน ของ Volatility (annualized) และ Drawdown จากราคาปิดจริง"""
    df = df_price_ticker.sort_values(by='date').reset_index(drop=True)
    df = _clean_price_series(df, 'close')  # F-7a: ตัดแถวราคาขาดหายออก ไม่เติม 0 (เหมือน calculate_risk_module)
    df['returns'] = df['close'].pct_change()

    df['rolling_vol_30d'] = df['returns'].rolling(30).std() * np.sqrt(252) * 100
    cum_max = df['close'].cummax()
    df['drawdown_pct'] = (df['close'] - cum_max) / cum_max * 100

    out = df[['date', 'rolling_vol_30d', 'drawdown_pct']].dropna(subset=['rolling_vol_30d']).copy()
    out = out.set_index('date').resample('W').last().dropna().reset_index()
    return out

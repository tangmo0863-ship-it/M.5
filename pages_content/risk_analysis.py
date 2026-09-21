"""
pages_content/risk_analysis.py
--------------------------
หน้า "Risk Analysis" ของ CIS Dashboard

วิธีทดสอบหน้านี้แบบเดี่ยว (ไม่ต้องรอทีมคนอื่น):
    streamlit run preview_my_page.py
    (แล้วเลือกโมดูลนี้จาก dropdown ในไฟล์ preview_my_page.py)

ข้อมูลที่ใช้ได้ใน ctx (ดูนิยามเต็มใน common.py -> class PageContext):
    ctx.selected_ticker, ctx.stock_info, ctx.stock_daily, ctx.fin_stock, ctx.sector_peers,
    ctx.scores_df, ctx.fin_df, ctx.feat_imp_df, ctx.backtest_df, ctx.risk_hist_df,
    ctx.health_yearly_df, ctx.fair_value_yearly_df,
    ctx.current_price, ctx.change_pct, ctx.change_val, ctx.change_color, ctx.change_sign, ctx.arrow_sign

ห้ามแก้ CSS ส่วนกลางหรือ helper function ใน common.py จากไฟล์นี้ — ถ้าจำเป็นต้องแก้ ให้แจ้ง Layout Lead ก่อน

=== อัปเดตล่าสุด (แก้ตามรายงานตรวจสอบ Module 5 หัวข้อ C.1-C.5) ===
แก้เฉพาะไฟล์นี้ ไม่แตะ common.py / calculate_modules / โมดูลอื่น
และไม่เปลี่ยนน้ำหนัก 30/25/20/15/10 หรือตัวคูณ (x10, x1.5, x1.3, x40) ใด ๆ

- F-2 (สูง) หน้าจอพังเมื่อค่าจากฐานข้อมูลเป็น NaN:
  เดิมเช็กแค่ `is not None` แล้วสั่ง int() ทันที ทำให้ recovery_days ที่อ่านกลับมาเป็น NaN
  (CCET, HANA, JMART, KCE, THCOM ที่ราคายังไม่กลับไปเท่ายอดเดิม) ทำให้เกิด
  ValueError: cannot convert float NaN to integer
  → เปลี่ยนมาใช้ helper `_num()` ที่รองรับ None / NaN / inf / สตริงว่าง ทุกจุดที่อ่านค่าจาก stock_info
  → เพิ่ม fallback คำนวณ recovery_days สดจากราคา (`_fallback_recovery_days`) ให้ครบทั้ง 3 ตัว
    (เดิมมี fallback แค่ cvar_95 และ psr ตามที่รายงานตรวจพบ)

- F-7 (กลาง) ไม่แสดงค่าปลอมเมื่อคำนวณไม่ได้:
  เดิม `safe(risk_score, 45)` ทำให้หุ้นที่คำนวณไม่ได้ (ข้อมูลน้อยกว่า 3 แถว → NaN)
  ขึ้นหน้าจอเป็น "45 / MODERATE RISK" เหมือนคำนวณได้จริง
  → ตอนนี้แสดง "N/A / NO DATA" เข็มมาตรวัดไม่ขึ้น และทุกตัวเลขอื่นที่ขาดข้อมูลแสดง "N/A" แทนค่า default

- F-6 (กลาง) ข้อความ VaR ขัดกันเอง:
  เดิมกล่องหนึ่งเขียนว่า VaR เป็น Parametric อีกกล่องเขียนว่า Historical Simulation
  และป้าย "Expected 1-Day Maximum Loss" ผิดนิยาม (VaR ไม่ใช่ขาดทุนสูงสุด)
  → แก้ข้อความให้ตรงกับโค้ด backend (VaR = Parametric, CVaR = Historical) และตัดคำว่า Maximum Loss ออก
  → เพิ่มหมายเหตุว่าสองค่าใช้คนละวิธี จึงมีบางกรณีที่ CVaR ออกมาน้อยกว่า VaR ได้
  *** การเลือกว่าจะเปลี่ยน VaR เป็น Historical ให้เหมือนกันหรือไม่ เป็นข้อที่ต้องให้มนุษย์ตัดสินใจ
      ไฟล์นี้จึงแก้แค่ "ข้อความ" ไม่แตะวิธีคำนวณของ backend ***

- F-8 (ข) ข้อความบนหน้าจอไม่ตรงกับโค้ด:
  เดิมเขียนว่า risk_score "ประเมินจาก Beta, Volatility และ Max Drawdown"
  ซึ่งไม่ตรง — ของจริงมี 5 ด้าน (CVaR 30%, Max Drawdown 25%, Volatility 20%, Beta 15%, PSR 10%)
  → แก้ข้อความให้ตรง และระบุชัดว่าน้ำหนักเป็นดุลยพินิจของทีม ยังไม่ผ่านการทดสอบย้อนหลัง
  → การ์ด RISK DIMENSION เดิมคำนวณด้วยสูตรของ UI เอง (คนละชุดกับ risk_score) จึงติดป้ายกำกับไว้ให้ชัด
    แทนที่จะปล่อยให้เข้าใจผิดว่าเป็นองค์ประกอบของคะแนน

- F-4 / F-3 (สูง, รอการตัดสินใจ): ติดป้าย "ที่มายังไม่ได้ตรวจสอบ" ให้ Beta
  และป้ายว่า Max Drawdown / Volatility มาจากไฟล์ stock_risk_static
  (ค่าจริงในไฟล์เท่ากันทุกหุ้น = -29.36% ทำให้ Calmar บนหน้านี้ผิดตามไปด้วย)
  → แก้ที่ต้นทางข้อมูลเท่านั้น ไฟล์นี้ทำได้แค่ไม่กล่าวอ้างเกินจริง

- O-2: PSR เทียบกับ Sharpe = 0 (ไม่หักดอกเบี้ย) ส่วน Sharpe/Sortino หักดอกเบี้ย
  เดิมหมายเหตุเขียนรวมว่า "คำนวณหัก Risk-free Rate แล้ว" → แยกให้ถูกต้อง

ยังไม่ได้แก้ในไฟล์นี้ (ไม่ใช่ขอบเขตของ UI): F-1, F-3, F-4, F-5, F-9
"""
import streamlit as st
import pandas as pd
import numpy as np
import math
import plotly.graph_objects as go
import plotly.express as px
from plotly.subplots import make_subplots

from common import fmt_mb, fmt_ratio, safe, show_chart, render_nav_footer, COMPANY_NAMES, SECTOR_MAP

# ป้ายที่ใช้ตอนไม่มีข้อมูล — ห้ามแทนด้วยตัวเลข default (F-7)
NA_TEXT = "N/A"


def _num(value):
    """แปลงค่าที่อ่านจากฐานข้อมูล/DataFrame ให้เป็น float ที่ใช้งานได้จริง

    คืน None ถ้าใช้ไม่ได้: None, NaN, inf, สตริงว่าง, "nan"/"None"/"-" ฯลฯ
    จุดสำคัญคือ NaN != None — ค่าที่ backend คืนเป็น None พอบันทึกลงฐานข้อมูลแล้วอ่านกลับ
    จะกลายเป็น NaN ซึ่งผ่านเงื่อนไข `is not None` ไปได้ แล้วไปพังตอน int()/format (F-2)
    """
    if value is None:
        return None
    if isinstance(value, str):
        s = value.strip()
        if s == "" or s.lower() in {"nan", "none", "null", "n/a", "na", "-"}:
            return None
        try:
            value = float(s)
        except ValueError:
            return None
    try:
        if pd.isna(value):
            return None
    except (TypeError, ValueError):
        return None
    try:
        f = float(value)
    except (TypeError, ValueError):
        return None
    if not math.isfinite(f):
        return None
    return f


def _fmt(value, spec="{:.2f}", na=NA_TEXT):
    """จัดรูปแบบตัวเลขแบบปลอดภัย ถ้าไม่มีค่าให้แสดง N/A แทนที่จะแสดงค่าปลอมหรือพัง"""
    v = _num(value)
    return na if v is None else spec.format(v)


def _dim(value, func):
    """คำนวณคะแนนการ์ด Risk Dimension คืน None ถ้าไม่มีข้อมูลตั้งต้น (จะได้แสดง N/A ไม่ใช่ค่าเดา)"""
    v = _num(value)
    if v is None:
        return None
    try:
        return int(np.clip(func(v), 5, 95))
    except Exception:
        return None


def _fallback_cvar_95(stock_daily, confidence=0.95):
    """คำนวณ CVaR 95% (Historical Simulation) สดจาก ctx.stock_daily ที่มีอยู่แล้วเสมอทุกหุ้น
    ใช้เป็น fallback กรณี cis_summary_scores ยังไม่มีคอลัมน์ cvar_95 หรือมีแต่เป็น NaN (เช่น ยังไม่ได้รัน
    calculate_scores.py ใหม่หลังอัปเดต calculate_modules/risk_analysis.py) — สูตรเดียวกับ backend
    คืน None เฉพาะกรณีมีข้อมูลราคาน้อยกว่า 20 วันจริงๆ เท่านั้น"""
    try:
        closes = pd.to_numeric(stock_daily['close'], errors='coerce').dropna()
        # ราคา <= 0 เป็นค่าที่เป็นไปไม่ได้ (เกิดจาก clean_float แปลงค่าว่างเป็น 0.0 — ดู F-7)
        # ถ้าปล่อยไว้จะได้ผลตอบแทน -100% แล้วลาก CVaR เพี้ยนทั้งชุด จึงตัดทิ้งก่อนคำนวณ
        closes = closes[closes > 0]
        returns = closes.pct_change().dropna()
        if len(returns) < 20:
            return None
        cutoff = np.percentile(returns, (1 - confidence) * 100)
        tail = returns[returns <= cutoff]
        if tail.empty:
            return None
        return round(float(abs(tail.mean()) * 100), 2)
    except Exception:
        return None


def _fallback_psr(stock_daily, sr_benchmark=0.0):
    """คำนวณ Probabilistic Sharpe Ratio สดจาก ctx.stock_daily เป็น fallback แบบเดียวกับ CVaR
    (สูตรเดียวกับ calculate_modules/risk_analysis.py) คืน None เฉพาะข้อมูลน้อยกว่า 30 วัน
    หรือผลตอบแทนนิ่งสนิท (std=0) จริงๆ เท่านั้น
    หมายเหตุ: SR ในสูตรนี้ไม่ได้หัก risk-free rate (เทียบกับ 0) ตรงกับ backend — ดู O-2"""
    try:
        closes = pd.to_numeric(stock_daily['close'], errors='coerce').dropna()
        closes = closes[closes > 0]
        r = closes.pct_change().dropna()
        n = len(r)
        if n < 30 or r.std() == 0:
            return None
        sr_hat = r.mean() / r.std()
        skew = r.skew()
        kurt = r.kurtosis() + 3
        denom_sq = 1 - skew * sr_hat + ((kurt - 1) / 4) * sr_hat ** 2
        if denom_sq <= 0:
            return None
        denom = math.sqrt(denom_sq)
        z = (sr_hat - sr_benchmark) * math.sqrt(n - 1) / denom
        psr = 0.5 * (1 + math.erf(z / math.sqrt(2)))
        return round(float(psr) * 100, 1)
    except Exception:
        return None


def _fallback_recovery_days(stock_daily):
    """คำนวณ "จำนวนวันที่ใช้ฟื้นตัว" สดจากราคา เป็น fallback ที่เดิมยังไม่มี (F-2)

    นิยามเดียวกับ backend: นับจากวันที่ราคาตกต่ำสุดเทียบกับยอดเดิม (จุด Max Drawdown)
    ไปจนถึงวันแรกที่ราคาปิดกลับมาเท่าหรือสูงกว่ายอดเดิม นับเป็นวันปฏิทิน

    คืนค่าเป็น tuple (สถานะ, จำนวนวัน) เพื่อแยก 3 กรณีที่เดิมปนกันอยู่:
        ("recovered", n)      ฟื้นตัวแล้วใน n วัน
        ("not_recovered", None) ยังไม่ฟื้นกลับสู่ยอดเดิม  <-- เดิมโค้ดพังตรงนี้เพราะเป็น NaN
        ("no_data", None)     ข้อมูลไม่พอจะสรุป (ต้องแสดง N/A ไม่ใช่เดาว่ายังไม่ฟื้น)
    """
    try:
        df = stock_daily[['date', 'close']].copy()
        df['close'] = pd.to_numeric(df['close'], errors='coerce')
        df['date'] = pd.to_datetime(df['date'], errors='coerce')
        df = df.dropna(subset=['date', 'close'])
        df = df[df['close'] > 0].sort_values('date')
        if len(df) < 2:
            return ("no_data", None)

        closes = df['close'].to_numpy(dtype=float)
        dates = df['date'].to_numpy()
        running_peak = np.maximum.accumulate(closes)
        drawdown = closes / running_peak - 1.0
        trough_i = int(np.argmin(drawdown))
        if drawdown[trough_i] >= 0:
            # ไม่เคยตกต่ำกว่ายอดเดิมเลย จึงไม่มีช่วงฟื้นตัวให้วัด
            return ("no_data", None)

        peak_value = float(running_peak[trough_i])
        peak_i = int(np.argmax(closes[:trough_i + 1] >= peak_value))
        after = np.nonzero(closes[trough_i:] >= peak_value)[0]
        if after.size == 0:
            return ("not_recovered", None)

        recovered_i = trough_i + int(after[0])
        days = (pd.Timestamp(dates[recovered_i]) - pd.Timestamp(dates[peak_i])).days
        return ("recovered", int(days))
    except Exception:
        return ("no_data", None)


def render(ctx):
    # --- F-7: ถ้า risk_score คำนวณไม่ได้ (NaN / ไม่มีคอลัมน์) ต้องแสดง N/A
    # ห้ามแทนด้วย 45 เพราะจะกลายเป็น "45 / MODERATE RISK" ปลอม ๆ ที่ดูเหมือนคำนวณได้จริง
    risk_score_num = _num(ctx.stock_info.get('risk_score'))
    has_score = risk_score_num is not None
    risk_score = int(round(risk_score_num)) if has_score else None
    risk_score_txt = f"{risk_score}" if has_score else NA_TEXT

    if not has_score:
        risk_status = "NO DATA"
        risk_color = "#64748B"
    elif risk_score >= 65:
        risk_status = "LOW RISK"
        risk_color = "#10B981"
    elif risk_score >= 40:
        risk_status = "MODERATE RISK"
        risk_color = "#F59E0B"
    else:
        risk_status = "HIGH RISK"
        risk_color = "#EF4444"

    # เดิมใช้ safe(..., default) ทุกตัว ทำให้หุ้นที่ไม่มีข้อมูลแสดงค่า default เหมือนเป็นค่าจริง
    # ตอนนี้เก็บเป็น None แล้วให้จุดที่แสดงผลเลือกเองว่าจะโชว์ N/A หรือซ่อน
    beta_val = _num(ctx.stock_info.get('beta'))
    vol_val = _num(ctx.stock_info.get('volatility'))
    dd_val = _num(ctx.stock_info.get('max_drawdown'))
    de_val_r = _num(ctx.stock_info.get('de_ratio'))
    cr_val_r = _num(ctx.stock_info.get('current_ratio'))

    st.markdown(f"""<div style="display:flex; justify-content:space-between; align-items:flex-end; margin-bottom:15px;">
    <div><div style="font-size:14.5px; color:#64748B; margin-bottom:2px;">Home / Module 5 / Risk Analysis</div>
    <div style="display:flex; align-items:baseline; gap:8px;"><h2 style="margin:0; font-size:23px; font-weight:bold; color:#F8FAFC; letter-spacing:0.5px;">RISK ANALYSIS</h2></div></div>
    <div style="text-align:right; display:flex; align-items:center; gap:16px;">
    <div><span style="font-size:13px; color:#64748B;">Analysis Date</span><br><b style="color:#CBD5E1; font-size:15px;">{ctx.stock_info.get('latest_date','-')}</b></div>
    <div><span style="font-size:13px; color:#64748B;">Data Period</span><br><b style="color:#CBD5E1; font-size:15px;">2023-2025 (3Y)</b></div>
    </div></div>""", unsafe_allow_html=True)

    r1_c1, r1_c2 = st.columns([1.15, 2.85])

    with r1_c1:
        # risk_score นิยามว่า "higher = safer" แต่ arc วาดจากเขียว(ซ้าย)->แดง(ขวา)
        # ต้อง invert (1 - ...) ไม่งั้นคะแนนสูง (ปลอดภัย) จะดันเข็มไปทางแดงแทนที่จะเป็นเขียว
        # ถ้าไม่มีคะแนน → ไม่วาดเข็มเลย ดีกว่าวาดไว้ที่ตำแหน่งเดาสุ่ม (F-7)
        if has_score:
            needle_frac = 1 - min(1.0, risk_score / 100)
            needle_x = 50 - 30 * np.cos(np.pi * needle_frac)
            needle_y = 50 - 40 * np.sin(np.pi * needle_frac)
            needle_svg = (f'<line x1="50" y1="50" x2="{needle_x:.1f}" y2="{needle_y:.1f}" '
                          f'stroke="#F8FAFC" stroke-width="2.5" stroke-linecap="round"/>')
        else:
            needle_svg = ""

        score_suffix = '<span style="font-size:13.5px; color:#64748B;">/100</span>' if has_score else ""
        if has_score:
            # F-8(ข): เดิมเขียนว่าประเมินจาก Beta, Volatility, Max Drawdown ซึ่งไม่ตรงกับโค้ด
            summary_note = (f"ระดับความเสี่ยงของ {ctx.selected_ticker} รวมจาก 5 ด้าน: CVaR 30%, "
                            f"Max Drawdown 25%, Volatility 20%, Beta 15%, PSR 10% "
                            f"(น้ำหนักเป็นดุลยพินิจของทีม ยังไม่ผ่านการทดสอบย้อนหลัง)")
        else:
            summary_note = (f"ยังคำนวณคะแนนความเสี่ยงของ {ctx.selected_ticker} ไม่ได้ "
                            f"(ข้อมูลราคาไม่พอหรือยังไม่ได้คำนวณคะแนนใหม่) — ไม่แสดงค่าประมาณแทน")

        st.markdown(f"""<div style="background-color:#0F172A; border:1px solid #1E293B; border-radius:12px; padding:16px; min-height:260px; display:flex; flex-direction:column; justify-content:space-between; text-align:center;">
    <div style="font-size:14.5px; font-weight:bold; color:#94A3B8; letter-spacing:0.5px; text-align:left;">RISK SUMMARY</div>
    <div style="margin:auto 0;"><svg viewBox="0 0 100 55" style="width:140px; height:90px; display:block; margin:0 auto;">
    <path d="M 12 50 A 38 38 0 0 1 35 15" fill="none" stroke="#10B981" stroke-width="8" stroke-linecap="round" />
    <path d="M 35 15 A 38 38 0 0 1 65 15" fill="none" stroke="#F59E0B" stroke-width="8" />
    <path d="M 65 15 A 38 38 0 0 1 88 50" fill="none" stroke="#EF4444" stroke-width="8" stroke-linecap="round" />
    {needle_svg}
    <circle cx="50" cy="50" r="4" fill="#F8FAFC"/></svg></div>
    <div style="color:{risk_color}; font-size:16.5px; font-weight:bold; margin-top:2px;">{risk_status}</div>
    <div style="font-size:12px; color:#64748B; margin-top:1px;">Risk Score (higher = safer)</div>
    <div style="font-size:21px; font-weight:bold; color:#FFFFFF; line-height:1.1;">{risk_score_txt}{score_suffix}</div></div>
    <div style="font-size:12.5px; color:#94A3B8; line-height:1.35;">{summary_note}</div>
    </div>""", unsafe_allow_html=True)

    with r1_c2:
        # การ์ดชุดนี้ "ไม่ใช่" องค์ประกอบของ risk_score — เป็นมุมมองเสริมที่ UI คำนวณเองด้วยสูตรคนละชุด
        # (มี D/E และ Liquidity ซึ่งไม่ได้อยู่ในคะแนน และไม่มี CVaR/PSR ซึ่งอยู่ในคะแนน) — ดู F-8(ข)
        # TODO: เมื่อ backend แก้ F-1 แล้วบันทึก risk_score_breakdown ลงฐานข้อมูลได้
        #       ควรเปลี่ยนมาอ่านค่าจาก breakdown โดยตรง (ต้องขอชื่อคีย์จากเจ้าของ calculate_modules ก่อน
        #       ไฟล์นี้จึงยังไม่เดาชื่อคีย์)
        market_risk = _dim(beta_val, lambda v: v * 40)
        price_risk = _dim(vol_val, lambda v: v * 1.3)
        financial_risk = _dim(de_val_r, lambda v: v * 25)
        liquidity_risk = _dim(cr_val_r, lambda v: (2.0 - v) * 40)
        downside_risk = _dim(dd_val, lambda v: v * 1.5)
        overall_risk_dim = _dim(risk_score_num, lambda v: 100 - v)

        def risk_dim_card(label, val):
            if val is None:
                # ไม่มีข้อมูลตั้งต้น → วงกลมเทา + N/A (เดิมจะเอาค่า default ไปคำนวณแล้วโชว์เหมือนของจริง)
                return f"""<div style="background:#151E2F; border:1px solid #1E293B; border-radius:10px; padding:10px 4px; text-align:center;">
    <div style="font-size:13px; font-weight:bold; color:#CBD5E1;">{label}</div>
    <div style="margin:8px auto; width:56px; height:56px; border-radius:50%; background:#1E293B; display:flex; align-items:center; justify-content:center;">
    <div style="width:46px; height:46px; border-radius:50%; background-color:#151E2F; display:flex; align-items:center; justify-content:center;"><span style="font-size:13px; color:#64748B;">{NA_TEXT}</span></div></div>
    <div style="color:#64748B; font-size:12.5px; font-weight:bold;">No data</div></div>"""
            c = "#10B981" if val <= 35 else ("#F59E0B" if val <= 60 else "#EF4444")
            lvl = "Low" if val <= 35 else ("Moderate" if val <= 60 else "High")
            return f"""<div style="background:#151E2F; border:1px solid #1E293B; border-radius:10px; padding:10px 4px; text-align:center;">
    <div style="font-size:13px; font-weight:bold; color:#CBD5E1;">{label}</div>
    <div style="margin:8px auto; width:56px; height:56px; border-radius:50%; background:conic-gradient({c} 0% {val}%, #1E293B {val}% 100%); display:flex; align-items:center; justify-content:center;">
    <div style="width:46px; height:46px; border-radius:50%; background-color:#151E2F; display:flex; align-items:center; justify-content:center;"><span style="font-size:15px; color:#FFFFFF;">{val}</span></div></div>
    <div style="color:{c}; font-size:12.5px; font-weight:bold;">{lvl}</div></div>"""

        dims_html = "".join([
            risk_dim_card("Market Risk (Beta)", market_risk),
            risk_dim_card("Price Risk (Vol.)", price_risk),
            risk_dim_card("Financial Risk (D/E)", financial_risk),
            risk_dim_card("Liquidity Risk", liquidity_risk),
            risk_dim_card("Downside Risk (DD)", downside_risk),
            risk_dim_card("Overall Risk", overall_risk_dim),
        ])
        st.markdown(f"""<div style="background-color:#0F172A; border:1px solid #1E293B; border-radius:12px; padding:16px; min-height:260px; display:flex; flex-direction:column; justify-content:space-between;">
    <div style="font-size:14.5px; font-weight:bold; color:#94A3B8; letter-spacing:0.5px;">RISK DIMENSION OVERVIEW ({ctx.selected_ticker})</div>
    <div style="display:grid; grid-template-columns: repeat(6, 1fr); gap:8px; margin:auto 0;">{dims_html}</div>
    <div style="font-size:11px; color:#64748B; border-top:1px solid #1E293B; padding-top:6px; margin-top:8px;">มุมมองเสริมของหน้าจอนี้ คำนวณแยกจาก Risk Score (ใช้ D/E และสภาพคล่องซึ่งไม่ได้อยู่ในคะแนน และไม่ได้ใช้ CVaR/PSR ซึ่งอยู่ในคะแนน) — สเกล 0-100 ยิ่งสูงยิ่งเสี่ยง</div>
    </div>""", unsafe_allow_html=True)

    st.markdown("<div style='margin-top:22px;'></div>", unsafe_allow_html=True)
    r2_c1, r2_c2, r2_c3 = st.columns(3)

    rh = ctx.risk_hist_df[ctx.risk_hist_df['ticker'] == ctx.selected_ticker].sort_values('date') if not ctx.risk_hist_df.empty else pd.DataFrame()

    with r2_c1:
        # F-4: โค้ดไม่ได้คำนวณ Beta เอง (ใช้ค่าจากไฟล์ หรือ 1.0) และยังไม่มีใครยืนยันว่าไฟล์คำนวณจากดัชนีใด
        # จึงต้องติดป้ายไว้ ไม่ใช่แสดงเป็นค่าที่ตรวจสอบแล้ว
        st.markdown(f"""<div style="background-color:#0F172A; border:1px solid #1E293B; border-radius:12px 12px 0 0; padding:12px 14px 0 14px;">
    <div style="font-size:14px; font-weight:bold; color:#94A3B8; letter-spacing:0.5px;">MARKET RISK (BETA) — vs Peers</div>
    <div style="font-size:19px; font-weight:bold; color:#FFFFFF; margin-top:2px;">{_fmt(beta_val)}</div>
    <div style="font-size:11px; color:#64748B; margin-top:2px;">ค่าจากไฟล์ stock_risk_static — ยังไม่ได้ตรวจสอบว่าคำนวณจากดัชนีและช่วงเวลาใด</div></div>""", unsafe_allow_html=True)
        beta_cmp = ctx.scores_df[['ticker', 'beta']].copy()
        beta_cmp['beta'] = pd.to_numeric(beta_cmp['beta'], errors='coerce')
        beta_cmp = beta_cmp.dropna(subset=['beta']).sort_values('beta')
        if not beta_cmp.empty:
            colors_beta = ['#A855F7' if t == ctx.selected_ticker else '#38BDF8' for t in beta_cmp['ticker']]
            fig_beta = go.Figure(go.Bar(x=beta_cmp['beta'], y=beta_cmp['ticker'], orientation='h', marker=dict(color=colors_beta)))
            fig_beta.add_vline(x=1.0, line_width=1, line_dash="dash", line_color="#64748B")
            fig_beta.update_layout(
                height=160, margin=dict(l=40, r=10, t=10, b=20), paper_bgcolor="#0F172A", plot_bgcolor="#0F172A",
                xaxis=dict(tickfont=dict(size=11, color="#64748B"), gridcolor="#1E293B"),
                yaxis=dict(tickfont=dict(size=11, color="#CBD5E1"), gridcolor="#1E293B"), showlegend=False
            )
            show_chart(fig_beta, key="risk_beta", expand_height=550)
        else:
            st.info("ไม่มีข้อมูล")

    with r2_c2:
        # F-4: ตัวเลขหัวการ์ดมาจากไฟล์ แต่กราฟด้านล่างวาดจากราคาจริง (risk_rolling_history)
        # สองอย่างนี้อาจไม่สอดคล้องกัน (HANA ต่างกัน +15.3 จุด, TRUE -21.8) จึงต้องบอกที่มาให้ชัด
        st.markdown(f"""<div style="background-color:#0F172A; border:1px solid #1E293B; border-radius:12px 12px 0 0; padding:12px 14px 0 14px;">
    <div style="font-size:14px; font-weight:bold; color:#94A3B8; letter-spacing:0.5px;">PRICE RISK — Annualized Volatility</div>
    <div style="font-size:19px; font-weight:bold; color:#FFFFFF; margin-top:2px;">{_fmt(vol_val, "{:.1f}%")}</div>
    <div style="font-size:11px; color:#64748B; margin-top:2px;">ตัวเลขนี้มาจากไฟล์ stock_risk_static ส่วนกราฟด้านล่างคำนวณสดจากราคา (Rolling 30D) จึงอาจไม่ตรงกัน</div></div>""", unsafe_allow_html=True)
        if not rh.empty:
            fig_vol = go.Figure()
            fig_vol.add_trace(go.Scatter(x=rh['date'], y=rh['rolling_vol_30d'], mode='lines', line=dict(color='#38BDF8', width=1.8)))
            fig_vol.update_layout(
                height=160, margin=dict(l=30, r=10, t=10, b=20), paper_bgcolor="#0F172A", plot_bgcolor="#0F172A",
                xaxis=dict(tickfont=dict(size=11, color="#64748B"), gridcolor="#1E293B"),
                yaxis=dict(tickfont=dict(size=11, color="#64748B"), gridcolor="#1E293B", zeroline=False), showlegend=False
            )
            show_chart(fig_vol, key="risk_volatility", expand_height=550)
        else:
            st.info("ไม่มีข้อมูล")

    with r2_c3:
        # === F-2: จุดที่หน้าจอพังกับหุ้น 5 จาก 8 ตัว ===
        # เดิม: recovery_days is not None -> int(recovery_days)
        # ค่าที่ backend คืนเป็น None พอบันทึกลงฐานข้อมูลแล้วอ่านกลับจะเป็น NaN (float)
        # ซึ่ง `is not None` เป็นจริง แล้ว int(nan) ระเบิดเป็น ValueError
        # ตอนนี้ใช้ _num() + fallback คำนวณสดจากราคา และแยก "ยังไม่ฟื้น" ออกจาก "ไม่มีข้อมูล"
        recovery_num = _num(ctx.stock_info.get('recovery_days'))
        if recovery_num is not None:
            recovery_txt = f"ฟื้นตัวใน {int(round(recovery_num))} วัน"
        else:
            rec_status, rec_days = _fallback_recovery_days(ctx.stock_daily)
            if rec_status == "recovered":
                recovery_txt = f"ฟื้นตัวใน {rec_days} วัน (คำนวณสดจากราคา)"
            elif rec_status == "not_recovered":
                recovery_txt = "ยังไม่ฟื้นตัวกลับสู่จุดสูงสุดเดิม"
            else:
                recovery_txt = f"{NA_TEXT} (ข้อมูลราคาไม่พอจะสรุป)"

        st.markdown(f"""<div style="background-color:#0F172A; border:1px solid #1E293B; border-radius:12px 12px 0 0; padding:12px 14px 0 14px;">
    <div style="font-size:14px; font-weight:bold; color:#94A3B8; letter-spacing:0.5px;">DRAWDOWN — Actual (2023-2025)</div>
    <div style="font-size:19px; font-weight:bold; color:#EF4444; margin-top:2px;">{('-' + _fmt(dd_val, '{:.1f}%')) if _num(dd_val) is not None else NA_TEXT}</div>
    <div style="font-size:11.5px; color:#94A3B8; margin-top:2px;">Recovery: {recovery_txt}</div>
    <div style="font-size:11px; color:#64748B; margin-top:2px;">ค่าจากไฟล์ stock_risk_static — ต้องยืนยันที่มาก่อนใช้ตัดสินใจ (อยู่ระหว่างตรวจสอบตาม F-3)</div></div>""", unsafe_allow_html=True)
        if not rh.empty:
            fig_dd = go.Figure()
            fig_dd.add_trace(go.Scatter(x=rh['date'], y=rh['drawdown_pct'], mode='lines', line=dict(color='#EF4444', width=1.5), fill='tozeroy', fillcolor='rgba(239,68,68,0.2)'))
            fig_dd.update_layout(
                height=160, margin=dict(l=30, r=10, t=10, b=20), paper_bgcolor="#0F172A", plot_bgcolor="#0F172A",
                xaxis=dict(tickfont=dict(size=11, color="#64748B"), gridcolor="#1E293B"),
                yaxis=dict(tickfont=dict(size=11, color="#64748B"), gridcolor="#1E293B", zeroline=False), showlegend=False
            )
            show_chart(fig_dd, key="risk_drawdown", expand_height=550)
        else:
            st.info("ไม่มีข้อมูล")

    st.markdown("<div style='margin-top:22px;'></div>", unsafe_allow_html=True)
    r3_c1, r3_c2 = st.columns(2)

    with r3_c1:
        # ลำดับความสำคัญ: 1) ใช้ cvar_95 จาก cis_summary_scores ถ้ามี "และเป็นตัวเลขจริง"
        # 2) ถ้าไม่มีหรือเป็น NaN → คำนวณสดจาก ctx.stock_daily แทนทันที
        # 3) ถ้าคำนวณไม่ได้จริงๆ (ข้อมูลราคาน้อยกว่า 20 วัน) → ซ่อนช่อง CVaR ไปเลย ไม่โชว์ N/A
        # (เดิมเช็ก `is None` อย่างเดียว ค่า NaN จากฐานข้อมูลจึงเล็ดลอดไปถึงการ format — F-2)
        cvar_val = _num(ctx.stock_info.get('cvar_95'))
        if cvar_val is None:
            cvar_val = _num(_fallback_cvar_95(ctx.stock_daily))

        var_num = _num(ctx.stock_info.get('var_95'))
        var_txt = ("-" + _fmt(var_num)) + "%" if var_num is not None else NA_TEXT

        # F-6: เดิมกล่องหนึ่งบอกว่า VaR เป็น Parametric อีกกล่องบอกว่า Historical Simulation
        # ของจริงใน backend คือ VaR = Parametric (1.645 x std), CVaR = Historical
        # และป้าย "Expected 1-Day Maximum Loss" ผิดนิยาม — VaR ไม่ใช่ขาดทุนสูงสุด
        if cvar_val is not None:
            cvar_txt = "-" + _fmt(cvar_val) + "%"
            downside_metrics_html = f"""<div style="display:grid; grid-template-columns: 1fr 1fr; gap:8px; text-align:center; margin:auto 0;">
    <div><div style="font-size:22px; font-weight:bold; color:#EF4444;">{var_txt}</div><div style="font-size:12px; color:#64748B;">VaR 95% (Parametric)</div></div>
    <div><div style="font-size:22px; font-weight:bold; color:#EF4444;">{cvar_txt}</div><div style="font-size:12px; color:#64748B;">CVaR 95% (Historical)</div></div>
    </div>
    <div style="font-size:12px; color:#64748B; border-top:1px solid #1E293B; padding-top:6px;">VaR = ระดับขาดทุนรายวันที่ไม่ควรแย่ไปกว่านี้ใน 95% ของวัน (ไม่ใช่ขาดทุนสูงสุด) คำนวณแบบ Parametric | CVaR = ขาดทุนเฉลี่ยจริงของวันที่แย่กว่าเส้น VaR คำนวณจากข้อมูลจริง (Historical) — สองค่านี้ใช้คนละวิธี จึงมีบางหุ้นที่ CVaR ออกมาน้อยกว่า VaR อยู่ระหว่างทบทวนให้ใช้วิธีเดียวกัน</div>"""
        else:
            downside_metrics_html = f"""<div style="margin:auto 0;">
    <div style="font-size:24px; font-weight:bold; color:#EF4444;">{var_txt}</div><div style="font-size:12.5px; color:#64748B;">VaR 95% (Parametric) — ระดับขาดทุนรายวันที่ไม่ควรแย่ไปกว่านี้ใน 95% ของวัน</div>
    </div>
    <div style="font-size:12px; color:#64748B; border-top:1px solid #1E293B; padding-top:6px;">CVaR ยังคำนวณไม่ได้เนื่องจากข้อมูลราคาย้อนหลังไม่พอ (ต้องมีอย่างน้อย 20 วัน)</div>"""

        st.markdown(f"""<div style="background-color:#0F172A; border:1px solid #1E293B; border-radius:12px; padding:14px; min-height:225px; display:flex; flex-direction:column; justify-content:space-between;">
    <div style="font-size:14px; font-weight:bold; color:#94A3B8; letter-spacing:0.5px;">DOWNSIDE RISK (Daily)</div>
    {downside_metrics_html}
    </div>""", unsafe_allow_html=True)

    with r3_c2:
        # Calmar หารด้วย Max Drawdown ที่มาจากไฟล์ ถ้าค่านั้นผิด Calmar ก็ผิดตาม (F-3)
        # ที่แก้ได้ในไฟล์นี้คือไม่ให้พัง/ไม่โชว์ค่าปลอม ส่วนความถูกต้องต้องแก้ที่ต้นทางข้อมูล
        closes_for_ret = pd.to_numeric(ctx.stock_daily['close'], errors='coerce')
        closes_for_ret = closes_for_ret[closes_for_ret > 0]
        avg_ret = _num(closes_for_ret.pct_change().mean())
        dd_num = _num(dd_val)
        if avg_ret is not None and dd_num is not None and dd_num > 0:
            calmar = _num(round(avg_ret * 252 * 100 / dd_num, 2))
        else:
            calmar = None

        rf_num = _num(ctx.stock_info.get('risk_free_rate_annual'))
        rf_pct = rf_num * 100 if rf_num is not None else 2.0

        psr_val = _num(ctx.stock_info.get('psr'))
        if psr_val is None:
            psr_val = _num(_fallback_psr(ctx.stock_daily))

        base_cells = f"""<div style="background:#151E2F; border:1px solid #1E293B; border-radius:6px; padding:6px 2px;"><div style="font-size:12px; color:#64748B;">Sharpe</div><div style="font-size:15px; font-weight:bold; color:#F8FAFC;">{_fmt(ctx.stock_info.get('sharpe_ratio'))}</div></div>
    <div style="background:#151E2F; border:1px solid #1E293B; border-radius:6px; padding:6px 2px;"><div style="font-size:12px; color:#64748B;">Sortino</div><div style="font-size:15px; font-weight:bold; color:#F8FAFC;">{_fmt(ctx.stock_info.get('sortino_ratio'))}</div></div>
    <div style="background:#151E2F; border:1px solid #1E293B; border-radius:6px; padding:6px 2px;"><div style="font-size:12px; color:#64748B;">Calmar</div><div style="font-size:15px; font-weight:bold; color:#F8FAFC;">{_fmt(calmar)}</div></div>"""

        # O-2: Sharpe/Sortino หัก risk-free rate แต่ PSR เทียบกับ Sharpe = 0 (ไม่หัก)
        # เดิมหมายเหตุเขียนรวมว่า "คำนวณหัก Risk-free Rate แล้ว" ซึ่งไม่ตรงกับ PSR
        rf_note = (f"Sharpe / Sortino คำนวณหัก Risk-free Rate (~{rf_pct:.1f}%/ปี, อ้างอิง BOT Policy Rate "
                   f"เฉลี่ย 2023-2025 — ยังไม่ได้แนบแหล่งข้อมูลทางการ) แล้ว")
        if psr_val is not None:
            # คำนวณได้ → เพิ่มช่อง PSR เป็นคอลัมน์ที่ 4 พร้อมคำอธิบายในหมายเหตุ
            grid_cols = 4
            ratio_cells = base_cells + f"""
    <div style="background:#151E2F; border:1px solid #1E293B; border-radius:6px; padding:6px 2px;"><div style="font-size:12px; color:#64748B;">PSR</div><div style="font-size:15px; font-weight:bold; color:#F8FAFC;">{psr_val:.0f}%</div></div>"""
            footnote = (f"{rf_note} | PSR = ความน่าจะเป็นที่ Sharpe Ratio จริง &gt; 0 เมื่อพิจารณาความเบ้/โด่งของข้อมูล "
                        f"(เทียบกับ 0 จึงไม่ได้หัก Risk-free Rate เหมือนสองค่าแรก) — อ้างอิงที่ระบุในโค้ด: "
                        f"Bailey &amp; L&oacute;pez de Prado (2012) ยังรอผู้ตรวจสอบยืนยันต้นฉบับ")
        else:
            # คำนวณไม่ได้จริงๆ (ข้อมูลน้อยกว่า 30 วัน หรือผลตอบแทนนิ่งสนิท) → ไม่มีช่อง PSR เลย ไม่โชว์ N/A
            grid_cols = 3
            ratio_cells = base_cells
            footnote = rf_note

        st.markdown(f"""<div style="background-color:#0F172A; border:1px solid #1E293B; border-radius:12px; padding:14px; min-height:225px; display:flex; flex-direction:column; justify-content:space-between;">
    <div style="font-size:14px; font-weight:bold; color:#94A3B8; letter-spacing:0.5px;">RISK-ADJUSTED RETURN (actual, 2023-2025)</div>
    <div style="display:grid; grid-template-columns: repeat({grid_cols}, 1fr); gap:6px; text-align:center; margin:auto 0;">
    {ratio_cells}
    </div><div style="font-size:11.5px; color:#CBD5E1; border-top:1px solid #1E293B; padding-top:6px;">{footnote}</div>
    </div>""", unsafe_allow_html=True)

    st.markdown("<div style='margin-top:22px;'></div>", unsafe_allow_html=True)
    r4_c1, r4_c2 = st.columns([1.35, 1.65])

    with r4_c1:
        # เกณฑ์ D/E < 1 และ Max Drawdown < 30% ยังไม่มีแหล่งอ้างอิง และใช้เกณฑ์เดียวกันทุกอุตสาหกรรม
        # (กลุ่มโทรคมนาคมทุนหนักมี D/E สูงโดยธรรมชาติ) จึงติดป้ายว่าเป็นเกณฑ์ภายใน
        risk_pts = []
        if beta_val is None:
            risk_pts.append(("–", "#64748B", "ไม่มีข้อมูล Beta"))
        elif beta_val < 1:
            risk_pts.append(("✔", "#10B981", f"Beta {beta_val:.2f} ต่ำกว่าตลาด ความผันผวนสัมพัทธ์ต่ำ"))
        else:
            risk_pts.append(("●", "#EF4444", f"Beta {beta_val:.2f} สูงกว่าตลาด อ่อนไหวต่อความผันผวนตลาดมาก"))

        if de_val_r is None:
            risk_pts.append(("–", "#64748B", "ไม่มีข้อมูล D/E"))
        elif de_val_r < 1:
            risk_pts.append(("✔", "#10B981", f"ภาระหนี้สินต่ำ D/E = {de_val_r:.2f} เท่า"))
        else:
            risk_pts.append(("●", "#EF4444", f"ภาระหนี้สินค่อนข้างสูง D/E = {de_val_r:.2f} เท่า"))

        if dd_val is None:
            risk_pts.append(("–", "#64748B", "ไม่มีข้อมูล Max Drawdown"))
        elif dd_val < 30:
            risk_pts.append(("✔", "#10B981", f"Max Drawdown {dd_val:.1f}% อยู่ในเกณฑ์ควบคุมได้"))
        else:
            risk_pts.append(("●", "#EF4444", f"Max Drawdown {dd_val:.1f}% ค่อนข้างลึก ควรระวังช่วงตลาดผันผวน"))

        risk_pts_html = "".join([f'<div style="display:flex; gap:6px; margin-bottom:3px;"><span style="color:{c};">{icon}</span><span>{txt}</span></div>' for icon, c, txt in risk_pts])
        st.markdown(f"""<div style="background-color:#0F172A; border:1px solid #1E293B; border-radius:12px; padding:14px; min-height:210px; display:flex; flex-direction:column; justify-content:space-between;">
    <div style="font-size:14px; font-weight:bold; color:#94A3B8; letter-spacing:0.5px;">RISK FACTORS HIGHLIGHT ({ctx.selected_ticker})</div>
    <div style="font-size:12.5px; color:#CBD5E1; line-height:1.45; margin:auto 0;">{risk_pts_html}</div>
    <div style="font-size:11px; color:#64748B; border-top:1px solid #1E293B; padding-top:6px;">เกณฑ์ D/E &lt; 1 และ Max Drawdown &lt; 30% เป็นเกณฑ์ภายในของทีม ใช้เท่ากันทุกอุตสาหกรรม ยังไม่มีแหล่งอ้างอิงกำกับ</div>
    </div>""", unsafe_allow_html=True)

    with r4_c2:
        # F-8(ข): ข้อความสรุปต้องตรงกับสิ่งที่โค้ดคำนวณจริง และต้องไม่แสดงตัวเลขที่ไม่มี
        if has_score:
            summary_line = (f"หุ้น <b>{ctx.selected_ticker}</b> มีคะแนนความเสี่ยงรวมอยู่ที่ "
                            f"<b>{risk_score}/100 ({risk_status})</b> คำนวณจาก 5 ด้าน "
                            f"(CVaR, Max Drawdown, Volatility, Beta, PSR) โดยมีค่าประกอบที่แสดงบนหน้านี้: "
                            f"Beta = {_fmt(beta_val)}, Volatility รายปี = {_fmt(vol_val, '{:.1f}%')}, "
                            f"Max Drawdown = {_fmt(dd_val, '{:.1f}%')} ในช่วง 2023-2025")
        else:
            summary_line = (f"ยังสรุปคะแนนความเสี่ยงของ <b>{ctx.selected_ticker}</b> ไม่ได้ "
                            f"เนื่องจากข้อมูลไม่พอหรือยังไม่ได้คำนวณคะแนนใหม่ "
                            f"ค่าที่มีอยู่: Beta = {_fmt(beta_val)}, Volatility รายปี = {_fmt(vol_val, '{:.1f}%')}, "
                            f"Max Drawdown = {_fmt(dd_val, '{:.1f}%')}")

        st.markdown(f"""<div style="background-color:#0F172A; border:1px solid #1E293B; border-radius:12px; padding:14px; min-height:210px; display:flex; flex-direction:column; justify-content:space-between;">
    <div><div style="font-size:14px; font-weight:bold; color:#94A3B8; letter-spacing:0.5px; margin-bottom:6px;">EXPLAINABLE RISK SUMMARY</div>
    <p style="font-size:13px; color:#CBD5E1; line-height:1.5; margin:0;">
    {summary_line}
    </p></div>
    <div style="font-size:12px; color:#F59E0B; background:rgba(245,158,11,0.08); border-left:3px solid #F59E0B; padding:5px 8px; border-radius:4px;">
    <b>ข้อสังเกต:</b> น้ำหนัก 5 ด้าน (30/25/20/15/10) เป็นการปรับแต่งของผู้พัฒนา ยังไม่ผ่านการทดสอบย้อนหลัง และค่า Beta / Volatility / Max Drawdown บางส่วนมาจากไฟล์ที่ยังอยู่ระหว่างตรวจสอบที่มา — ควรใช้ประกอบการพิจารณาเท่านั้น</div>
    </div>""", unsafe_allow_html=True)

    render_nav_footer("m5", prev_page=" 🔮 AI Prediction", next_page=" 📊 Industry Benchmark")

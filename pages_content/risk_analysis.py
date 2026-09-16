# Patch: pages_content/risk_analysis.py (v2 — รวมกับคำขอให้ตัด rate/recession stress test ออก)

ใช้คู่กับ `calculate_modules/risk_analysis.py` เวอร์ชันใหม่ (แนบมาด้วย)

---

## Patch 1 — การ์ด "DOWNSIDE RISK (VAR 95%, daily)" → เพิ่ม CVaR จริง

**เดิม (r3_c1):**
```python
    with r3_c1:
        st.markdown(f"""<div style="background-color:#0F172A; border:1px solid #1E293B; border-radius:12px; padding:14px; min-height:225px; display:flex; flex-direction:column; justify-content:space-between;">
    <div style="font-size:14px; font-weight:bold; color:#94A3B8; letter-spacing:0.5px;">DOWNSIDE RISK (VAR 95%, daily)</div>
    <div style="font-size:24px; font-weight:bold; color:#EF4444; margin:auto 0;">-{safe(ctx.stock_info.get('var_95')):.2f}%<div style="font-size:12.5px; color:#64748B; font-weight:normal;">Expected 1-Day Maximum Loss</div></div>
    <div style="font-size:12px; color:#64748B; border-top:1px solid #1E293B; padding-top:6px;">คำนวณจาก Historical Simulation (2023-2025)</div>
    </div>""", unsafe_allow_html=True)
```

**ใหม่:**
```python
    with r3_c1:
        cvar_val = ctx.stock_info.get('cvar_95')
        cvar_display = f"-{safe(cvar_val):.2f}%" if cvar_val is not None else "N/A"
        st.markdown(f"""<div style="background-color:#0F172A; border:1px solid #1E293B; border-radius:12px; padding:14px; min-height:225px; display:flex; flex-direction:column; justify-content:space-between;">
    <div style="font-size:14px; font-weight:bold; color:#94A3B8; letter-spacing:0.5px;">DOWNSIDE RISK (Daily)</div>
    <div style="display:grid; grid-template-columns: 1fr 1fr; gap:8px; text-align:center; margin:auto 0;">
    <div><div style="font-size:22px; font-weight:bold; color:#EF4444;">-{safe(ctx.stock_info.get('var_95')):.2f}%</div><div style="font-size:12px; color:#64748B;">VaR 95%</div></div>
    <div><div style="font-size:22px; font-weight:bold; color:#EF4444;">{cvar_display}</div><div style="font-size:12px; color:#64748B;">CVaR 95%</div></div>
    </div>
    <div style="font-size:12px; color:#64748B; border-top:1px solid #1E293B; padding-top:6px;">VaR = ขาดทุนสูงสุดที่คาดใน 95% ของวัน | CVaR = ขาดทุนเฉลี่ยจริงในวันที่แย่กว่านั้น (จับ tail risk ได้ดีกว่า)</div>
    </div>""", unsafe_allow_html=True)
```

---

## Patch 2 — การ์ด "RISK-ADJUSTED RETURN" → เพิ่ม PSR

**ใหม่ (แทนที่บล็อก r3_c2 เดิมทั้งหมด):**
```python
    with r3_c2:
        avg_ret = ctx.stock_daily['close'].pct_change().mean() * 252
        calmar = round(avg_ret * 100 / dd_val, 2) if dd_val > 0 else 0
        rf_pct = safe(ctx.stock_info.get('risk_free_rate_annual'), 0.02) * 100
        psr_val = ctx.stock_info.get('psr')
        psr_display = f"{psr_val:.0f}%" if psr_val is not None else "N/A"
        st.markdown(f"""<div style="background-color:#0F172A; border:1px solid #1E293B; border-radius:12px; padding:14px; min-height:225px; display:flex; flex-direction:column; justify-content:space-between;">
    <div style="font-size:14px; font-weight:bold; color:#94A3B8; letter-spacing:0.5px;">RISK-ADJUSTED RETURN (actual, 2023-2025)</div>
    <div style="display:grid; grid-template-columns: repeat(4, 1fr); gap:6px; text-align:center; margin:auto 0;">
    <div style="background:#151E2F; border:1px solid #1E293B; border-radius:6px; padding:6px 2px;"><div style="font-size:12px; color:#64748B;">Sharpe</div><div style="font-size:15px; font-weight:bold; color:#F8FAFC;">{safe(ctx.stock_info.get('sharpe_ratio')):.2f}</div></div>
    <div style="background:#151E2F; border:1px solid #1E293B; border-radius:6px; padding:6px 2px;"><div style="font-size:12px; color:#64748B;">Sortino</div><div style="font-size:15px; font-weight:bold; color:#F8FAFC;">{safe(ctx.stock_info.get('sortino_ratio')):.2f}</div></div>
    <div style="background:#151E2F; border:1px solid #1E293B; border-radius:6px; padding:6px 2px;"><div style="font-size:12px; color:#64748B;">Calmar</div><div style="font-size:15px; font-weight:bold; color:#F8FAFC;">{calmar:.2f}</div></div>
    <div style="background:#151E2F; border:1px solid #1E293B; border-radius:6px; padding:6px 2px;"><div style="font-size:12px; color:#64748B;">PSR</div><div style="font-size:15px; font-weight:bold; color:#F8FAFC;">{psr_display}</div></div>
    </div><div style="font-size:11.5px; color:#CBD5E1; border-top:1px solid #1E293B; padding-top:6px;">คำนวณหัก Risk-free Rate (~{rf_pct:.1f}%/ปี) แล้ว | PSR = ความน่าจะเป็นที่ Sharpe Ratio จริง &gt; 0 เมื่อพิจารณาความเบ้/โด่งของข้อมูล</div>
    </div>""", unsafe_allow_html=True)
```

---

## Patch 3 — การ์ด Drawdown → เพิ่ม Recovery Duration

**เดิม (r2_c3 หัวการ์ด):**
```python
    with r2_c3:
        st.markdown(f"""<div style="background-color:#0F172A; border:1px solid #1E293B; border-radius:12px 12px 0 0; padding:12px 14px 0 14px;">
    <div style="font-size:14px; font-weight:bold; color:#94A3B8; letter-spacing:0.5px;">DRAWDOWN — Actual (2023-2025)</div>
    <div style="font-size:19px; font-weight:bold; color:#EF4444; margin-top:2px;">-{dd_val:.1f}%</div></div>""", unsafe_allow_html=True)
```

**ใหม่:**
```python
    with r2_c3:
        recovery_days = ctx.stock_info.get('recovery_days')
        recovery_txt = f"ฟื้นตัวใน {int(recovery_days)} วัน" if recovery_days is not None else "ยังไม่ฟื้นตัวกลับสู่จุดสูงสุดเดิม"
        st.markdown(f"""<div style="background-color:#0F172A; border:1px solid #1E293B; border-radius:12px 12px 0 0; padding:12px 14px 0 14px;">
    <div style="font-size:14px; font-weight:bold; color:#94A3B8; letter-spacing:0.5px;">DRAWDOWN — Actual (2023-2025)</div>
    <div style="font-size:19px; font-weight:bold; color:#EF4444; margin-top:2px;">-{dd_val:.1f}%</div>
    <div style="font-size:11.5px; color:#94A3B8; margin-top:2px;">Recovery: {recovery_txt}</div></div>""", unsafe_allow_html=True)
```

---

## Patch 4 — ตัด Stress Test (rate_impact, recession_impact) ออก เหลือแค่ Market Crash

**เดิม (r3_c3 ทั้งบล็อก):**
```python
    with r3_c3:
        crash_impact = round(beta_val * -20, 1)
        rate_impact = round(-vol_val * 0.35, 1)
        recession_impact = round(beta_val * -15 - dd_val * 0.1, 1)
        st.markdown(f"""<div style="background-color:#0F172A; border:1px solid #1E293B; border-radius:12px; padding:14px; min-height:225px; display:flex; flex-direction:column; justify-content:space-between;">
    <div style="font-size:14px; font-weight:bold; color:#94A3B8; letter-spacing:0.5px;">STRESS TEST SCENARIO (Beta-implied)</div>
    <table style="width:100%; font-size:13px; color:#CBD5E1; border-collapse:collapse; margin:auto 0;">
    <tr style="border-bottom:1px solid #1E293B; color:#64748B; font-size:12.5px;"><th style="text-align:left; padding:3px 0;">Scenario</th><th style="text-align:right;">Est. Impact</th></tr>
    <tr style="border-bottom:1px solid #1E293B;"><td style="padding:3px 0;">Market Crash (SET -20%)</td><td style="text-align:right; color:#EF4444; font-weight:bold;">{crash_impact:+.1f}%</td></tr>
    <tr style="border-bottom:1px solid #1E293B;"><td style="padding:3px 0;">Volatility Shock</td><td style="text-align:right; color:#EF4444; font-weight:bold;">{rate_impact:+.1f}%</td></tr>
    <tr><td style="padding:3px 0;">Recession Scenario</td><td style="text-align:right; color:#EF4444; font-weight:bold;">{recession_impact:+.1f}%</td></tr>
    </table><div style="font-size:12px; color:#64748B; border-top:1px solid #1E293B; padding-top:6px;">ประมาณจาก Beta = {beta_val:.2f} คูณ shock ของตลาด</div>
    </div>""", unsafe_allow_html=True)
```

**ใหม่ (เหลือแค่ Market Crash ที่มี CAPM รองรับ — ตัด rate_impact/recession_impact ออก):**
```python
    with r3_c3:
        crash_impact = round(beta_val * -20, 1)
        st.markdown(f"""<div style="background-color:#0F172A; border:1px solid #1E293B; border-radius:12px; padding:14px; min-height:225px; display:flex; flex-direction:column; justify-content:space-between;">
    <div style="font-size:14px; font-weight:bold; color:#94A3B8; letter-spacing:0.5px;">MARKET CRASH IMPACT (Beta-implied)</div>
    <div style="text-align:center; margin:auto 0;">
    <div style="font-size:32px; font-weight:bold; color:#EF4444;">{crash_impact:+.1f}%</div>
    <div style="font-size:12.5px; color:#94A3B8; margin-top:4px;">ถ้าตลาด (SET) ร่วง -20%</div>
    </div>
    <div style="font-size:12px; color:#64748B; border-top:1px solid #1E293B; padding-top:6px;">ประมาณจาก Beta = {beta_val:.2f} × Market Shock ตามทฤษฎี CAPM (Impact = β × Market Return) — ใช้ได้เฉพาะกรณี "ตลาดร่วงทั้งกระดาน" เท่านั้น</div>
    </div>""", unsafe_allow_html=True)
```

> การ์ดนี้จะโล่งกว่าเดิม (เหลือตัวเลขเดียวแทนตาราง 3 แถว) ถ้า Layout Lead (คนที่ 10) เห็นว่าไม่สมดุลกับ
> การ์ดข้างๆ อาจพิจารณาลด `min-height` หรือรวม column ใหม่ — เป็นเรื่อง Layout ไม่กระทบตัวเลข

---

## หมายเหตุสำหรับ DATA_FORMULA_AUDIT.md (หัวข้อ 5) — ให้ Auditor คนที่ 9 อัปเดต

- หัวข้อ 5.4 (Risk Score รวม): เปลี่ยนจาก "Volatility 45% + Max Drawdown 35% + VaR×2.0" เป็นสูตรใหม่
  Tail(CVaR) 30% + Drawdown+Recovery 25% + Volatility 20% + Market(Beta) 15% + Quality(PSR) 10%
  ระบุว่าเป็นการจัดลำดับตามน้ำหนักหลักฐานวรรณกรรม ไม่ใช่ตัวเลขที่พิสูจน์ทางสถิติ (ยังเป็น 🟡)
- หัวข้อ 5.6 (Stress Test): **ลบ rate_impact และ recession_impact ออกจากเอกสารทั้งหมด** เหลือเฉพาะ
  Market Crash (Beta-implied) ซึ่งมีทฤษฎี CAPM รองรับโดยตรง (Impact = β × Market Shock)

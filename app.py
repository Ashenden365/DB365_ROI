# app.py
# ROI Quick Check (Healthcare SMB) — Streamlit prototype
# Prototype for DigitalBunker365.com. Results show ONLY after pressing "Go".
# Three columns after Go: Results | Similar orgs | Next steps (simple).
# Tweaks: larger company name in top brand bar; assumptions moved to bottom below 3 columns.

import urllib.parse
from datetime import datetime

import streamlit as st
import streamlit.components.v1 as components

# ---------------------------
# Page config & global styles
# ---------------------------
st.set_page_config(
    page_title="ROI Quick Check — Digital Bunker 365",
    page_icon="🧮",
    layout="wide",
    initial_sidebar_state="collapsed",
)

st.markdown(
    """
    <style>
      :root {
        --text: #0f172a;
        --muted: #475569;
        --accent: #0ea5e9;
        --card-bg: #ffffff;
        --chip-bg: #f1f5f9;
        --border: #e2e8f0;
      }
      html, body, [class*="css"]  {
        font-family: -apple-system, BlinkMacSystemFont, "Segoe UI", Roboto, Helvetica, Arial, "Apple Color Emoji","Segoe UI Emoji";
        color: var(--text);
      }
      .brandbar {
        display:flex; align-items:center; justify-content:space-between;
        border-bottom:1px solid var(--border); padding:.6rem 0; margin-bottom:.8rem;
      }
      .brandbar a {
        text-decoration:none; color:var(--text); font-weight:700;
        /* Bigger company name */
        font-size: clamp(1.05rem, 2.2vw, 1.35rem);
      }
      .badge {
        background: var(--chip-bg); border:1px solid var(--border);
        border-radius:999px; padding:.2rem .6rem; font-size:.85rem; white-space:nowrap;
      }
      .hero h1 {
        font-size: clamp(1.6rem, 4vw, 2.2rem);
        margin: 0 0 .2rem 0; line-height: 1.2;
        background: linear-gradient(90deg, var(--accent), #6366f1, #10b981);
        -webkit-background-clip: text; background-clip: text; -webkit-text-fill-color: transparent;
      }
      .subcopy { color: var(--muted); margin-bottom:.75rem; }
      .chips { display:flex; flex-wrap:wrap; gap:.5rem; margin:.25rem 0 1rem 0; }
      .chip {
        display:inline-flex; align-items:center; gap:.4rem;
        background: var(--chip-bg); border:1px solid var(--border);
        border-radius:999px; padding:.25rem .6rem; font-size:.85rem; white-space:nowrap;
      }
      .card {
        background: var(--card-bg);
        border: 1px solid var(--border);
        border-radius: 16px;
        padding: 14px 16px;
        box-shadow: 0 1px 2px rgba(15, 23, 42, .04);
        margin-bottom: .6rem;
      }
      .plan { border-left: 6px solid var(--accent); }
      .kpi .label { color: var(--muted); font-size:.9rem; }
      .kpi .value { font-weight:700; font-size:1.6rem; margin-top:.25rem; }
      .kpi .sub   { color: var(--muted); font-size:.9rem; margin-top:.15rem; }
      .kpi-grid-2 { display:grid; gap:12px; grid-template-columns: 1fr; }
      @media (min-width: 900px) { .kpi-grid-2 { grid-template-columns: repeat(2, 1fr); } }
      .actions { display:flex; flex-wrap:wrap; gap:.5rem; margin:.4rem 0 1rem; }
      .btn {
        display:inline-block; text-decoration:none; text-align:center;
        border-radius:10px; padding:.6rem .9rem; border:1px solid var(--border); background:#ffffff;
      }
      .btn-primary { background: var(--accent); color:#fff; border-color: var(--accent); }
      .btn:hover { filter: brightness(0.98); }
      .link { color: var(--accent); text-decoration:none; }
      .footer-note { color: var(--muted); font-size:.85rem; }
      @media print {
        .stSidebar, .actions, .inputs .stButton { display:none !important; }
        .card { break-inside: avoid; }
      }
    </style>
    """,
    unsafe_allow_html=True,
)

# ---------------------------
# Helpers & constants
# ---------------------------
def clamp(x, lo, hi): return max(lo, min(hi, x))
def format_currency(x):
    try: return f"${int(round(x, 0)):,}"
    except Exception: return "$0"
def format_hours(x): return f"{x:.1f} h/mo"
def risk_reduction_label(pct):
    if pct >= 30: return "High"
    elif pct >= 20: return "Moderate"
    else: return "Modest"

OPS_REDUCTION = {"Minimum": 0.35, "Standard": 0.25, "Advanced": 0.15}
PHISH_REDUCTION = {"Minimum": 0.30, "Standard": 0.22, "Advanced": 0.15}
INCIDENTS_DIVISOR = {"Minimum": 120.0, "Standard": 180.0, "Advanced": 260.0}
LOSS_PER_INCIDENT = 25000.0
MAX_ANNUAL_INCIDENTS = 8.0
MIN_ANNUAL_INCIDENTS = 0.2

# ---------------------------
# Brand bar & Hero
# ---------------------------
st.markdown(
    """
    <div class="brandbar">
      <div><a href="https://www.digitalbunker365.com/" target="_blank" rel="noopener">Digital Bunker 365</a></div>
      <div class="badge">Prototype · ROI Simulator</div>
    </div>
    """,
    unsafe_allow_html=True,
)
st.markdown(
    """
    <div class="hero">
      <h1>ROI Quick Check (30 sec)</h1>
      <div class="subcopy">
        Anonymous input. We do not store data. HIPAA/BAA-ready.
        This is a prototype for <a class="link" href="https://www.digitalbunker365.com/" target="_blank" rel="noopener">DigitalBunker365.com</a>.
      </div>
      <div class="chips">
        <div class="chip">Takes ~30 seconds</div>
        <div class="chip">HIPAA / BAA</div>
        <div class="chip">No data stored</div>
        <div class="chip">Estimates only</div>
      </div>
    </div>
    """,
    unsafe_allow_html=True,
)

# ---------------------------
# Inputs (form) — keep current version
# ---------------------------
st.markdown("### Your Organization")
with st.form(key="roi_form", clear_on_submit=False):
    st.markdown('<div class="inputs">', unsafe_allow_html=True)
    industry = st.selectbox("Industry", ["Healthcare SMB", "Non-profit (Education)", "Other"], index=0,
                            help="Used for messaging only in this prototype. Calculations are industry-agnostic.")
    staff = st.number_input("Number of staff (headcount)", min_value=1, step=1, value=50,
                            help="All staff in the organization.")
    it_staff = st.number_input("Dedicated IT/Security FTE", min_value=0, step=1, value=1,
                               help="Number of full-time equivalents focused on IT/Security.")
    level = st.selectbox("Current security/control level", ["Minimum", "Standard", "Advanced"], index=0,
                         help="Reflects your current state. Lower current level ⇒ larger potential savings.")
    hipaa = st.selectbox("HIPAA compliance required?", ["Yes", "No"], index=0)
    hourly = st.number_input("Blended labor cost ($/hour) (optional)", min_value=0.0, step=1.0, value=65.0,
                             help="Used for labor savings. Default reflects a typical blended rate for SMBs.")
    devices_opt = st.number_input("Endpoints / devices (optional)", min_value=0, step=1, value=0,
                                  help="Leave 0 to auto-estimate as ~1.2 × staff.")
    st.markdown('</div>', unsafe_allow_html=True)
    submitted = st.form_submit_button("Go 🚀", type="primary")

# Persist snapshot between submits
if "roi" not in st.session_state:
    st.session_state["roi"] = None

# ---------------------------
# Compute on submit
# ---------------------------
if submitted:
    devices = devices_opt if devices_opt > 0 else int(round(staff * 1.2))
    current_ops = max(0.4 * staff + 8.0 * it_staff + 0.03 * devices, 12.0)

    ops_reduction_rate = OPS_REDUCTION[level]
    phish_reduction_pct = PHISH_REDUCTION[level] * 100
    hours_saved = current_ops * ops_reduction_rate
    labor_savings_monthly = hours_saved * max(hourly, 0.0)

    annual_incidents_baseline = clamp(staff / INCIDENTS_DIVISOR[level], MIN_ANNUAL_INCIDENTS, MAX_ANNUAL_INCIDENTS)
    annual_avoided_loss = annual_incidents_baseline * LOSS_PER_INCIDENT * PHISH_REDUCTION[level]
    affordability_cap_monthly = labor_savings_monthly + (annual_avoided_loss / 12.0)

    # Plan recommendation heuristic
    risk_score, reasons = 0.0, []
    if hipaa == "Yes": risk_score += 1.0; reasons.append("Requires HIPAA/BAA")
    if staff >= 100: risk_score += 1.0; reasons.append("100+ staff scale")
    elif staff >= 30: risk_score += 0.5; reasons.append("30–99 staff scale")
    if it_staff == 0: risk_score += 1.0; reasons.append("No dedicated IT/Sec FTE")
    elif it_staff <= 2: risk_score += 0.5; reasons.append("Limited IT/Sec capacity")
    if level == "Minimum": risk_score += 1.0; reasons.append("Current controls: Minimum")
    elif level == "Standard": risk_score += 0.5; reasons.append("Current controls: Standard")
    if staff > 0 and (devices / staff) > 1.5: risk_score += 0.5; reasons.append("High device density")

    plan = "Essential" if risk_score < 1.0 else ("Standard" if risk_score < 2.0 else "Advanced")

    st.session_state["roi"] = dict(
        industry=industry, staff=staff, it_staff=it_staff, level=level, hipaa=hipaa,
        hourly=hourly, devices=devices,
        current_ops=current_ops, hours_saved=hours_saved,
        labor_savings_monthly=labor_savings_monthly,
        phish_reduction_pct=phish_reduction_pct,
        annual_incidents_baseline=annual_incidents_baseline,
        annual_avoided_loss=annual_avoided_loss,
        affordability_cap_monthly=affordability_cap_monthly,
        plan=plan, reasons=reasons
    )

# ---------------------------
# Three-column layout AFTER Go (Results | Similar orgs | Next steps)
# ---------------------------
roi = st.session_state.get("roi")
if roi:
    col_results, col_cases, col_next = st.columns([1.4, 1.0, 1.0])

    # ---- Column 1: Your Results ----
    with col_results:
        st.markdown("### Your Results")
        st.markdown('<div class="kpi-grid-2">', unsafe_allow_html=True)

        st.markdown(
            f"""
            <div class="card plan">
              <div class="kpi">
                <div class="label">Recommended plan</div>
                <div class="value">{roi['plan']}</div>
                <div class="sub">Why: {", ".join(roi['reasons']) if roi['reasons'] else "Balanced needs"}</div>
              </div>
            </div>
            """,
            unsafe_allow_html=True,
        )
        st.markdown(
            f"""
            <div class="card">
              <div class="kpi">
                <div class="label">Monthly workload reduction</div>
                <div class="value">{format_hours(roi['hours_saved'])}</div>
                <div class="sub">≈ {format_currency(roi['labor_savings_monthly'])} / month</div>
              </div>
            </div>
            """,
            unsafe_allow_html=True,
        )
        tone = risk_reduction_label(roi['phish_reduction_pct'])
        st.markdown(
            f"""
            <div class="card">
              <div class="kpi">
                <div class="label">Phishing risk reduction</div>
                <div class="value">{int(round(roi['phish_reduction_pct']))}%</div>
                <div class="sub">{tone} improvement potential</div>
              </div>
            </div>
            """,
            unsafe_allow_html=True,
        )
        st.markdown(
            f"""
            <div class="card">
              <div class="kpi">
                <div class="label">Annual avoided losses (estimate)</div>
                <div class="value">{format_currency(roi['annual_avoided_loss'])}</div>
                <div class="sub">Baseline incidents: {roi['annual_incidents_baseline']:.2f} / year</div>
              </div>
            </div>
            """,
            unsafe_allow_html=True,
        )
        st.markdown(
            f"""
            <div class="card">
              <div class="kpi">
                <div class="label">Investment affordability (cap)</div>
                <div class="value">{format_currency(roi['affordability_cap_monthly'])} / mo</div>
                <div class="sub">ROI &gt; 0 if monthly cost ≤ this</div>
              </div>
            </div>
            """,
            unsafe_allow_html=True,
        )
        st.markdown(
            f"""
            <div class="card">
              <div class="kpi">
                <div class="label">Inputs snapshot (from last “Go”)</div>
                <div class="sub">Industry: {roi['industry']}</div>
                <div class="sub">Staff: {roi['staff']} • IT FTE: {roi['it_staff']}</div>
                <div class="sub">Level: {roi['level']} • HIPAA: {roi['hipaa']}</div>
                <div class="sub">Devices: {roi['devices']} • Hourly: {format_currency(roi['hourly'])}</div>
              </div>
            </div>
            """,
            unsafe_allow_html=True,
        )
        st.markdown('</div>', unsafe_allow_html=True)

    # ---- Column 2: Similar organizations ----
    with col_cases:
        st.markdown("### Similar organizations that succeeded (Healthcare SMB)")

        def case_card(title, before, after, link="#"):
            st.markdown(
                f"""
                <div class="card">
                  <div class="kpi">
                    <div class="label">{title}</div>
                    <div class="sub"><strong>Before:</strong> {before}</div>
                    <div class="sub"><strong>After:</strong> {after}</div>
                    <div class="sub"><a class="link" href="{link}">View details →</a></div>
                  </div>
                </div>
                """,
                unsafe_allow_html=True
            )

        case_card(
            "Community Health Clinic (45 staff)",
            "Ad-hoc patching, HIPAA anxiety, frequent phishing clicks.",
            "Monthly reports, visible HIPAA posture, 24 h/mo workload reduction."
        )
        case_card(
            "Non-profit Rehab Center (80 staff)",
            "No dedicated IT; endpoint sprawl.",
            "Standard plan; 28% phishing reduction; $36k/yr loss avoidance."
        )
        case_card(
            "Dental Network (120 staff)",
            "Mixed vendors, limited MFA coverage.",
            "Advanced plan; 18 h/mo saved in ops; predictable compliance cadence."
        )

    # ---- Column 3: Next steps ----
    with col_next:
        st.markdown("### Next steps")

        # Save as PDF
        components.html(
            """
            <div class="actions">
              <button class="btn btn-primary" onclick="window.print()">Save as PDF</button>
            </div>
            """,
            height=50,
        )

        # Email CTA
        email_to = "contact@digitalbunker365.com"  # change to production alias if needed
        subject = "ROI Quick Check — Request detailed report"
        body_lines = [
            "Hi Digital Bunker 365 team,",
            "",
            "Please send me a detailed ROI report based on my quick check.",
            "",
            f"Industry: {roi['industry']}",
            f"Staff: {roi['staff']}, IT FTE: {roi['it_staff']}, Devices: {roi['devices']}",
            f"Current level: {roi['level']}, HIPAA: {roi['hipaa']}",
            f"Monthly workload reduction: {format_hours(roi['hours_saved'])} (≈ {format_currency(roi['labor_savings_monthly'])}/mo)",
            f"Phishing risk reduction: {int(round(roi['phish_reduction_pct']))}%",
            f"Annual avoided losses: {format_currency(roi['annual_avoided_loss'])}",
            f"Affordability cap (monthly): {format_currency(roi['affordability_cap_monthly'])}",
            "",
            "Thanks!"
        ]
        body = urllib.parse.quote("\n".join(body_lines))
        subject_q = urllib.parse.quote(subject)
        mailto_url = f"mailto:{email_to}?subject={subject_q}&body={body}"
        st.markdown(f'<a class="btn" href="{mailto_url}">Email me a detailed report</a>', unsafe_allow_html=True)

        st.caption("Tip: Adjust inputs above and press **Go** again to refresh results.")

    # ---------------------------
    # Assumptions at the very bottom (below the three columns)
    # ---------------------------
    st.markdown("---")
    with st.expander("Assumptions, formulas & limitations (please read)"):
        st.markdown(
            f"""
- **Estimates only.** Results are a directional guide for budgeting and value visualization.
- **We do not store inputs.** This prototype does not persist your data.
- **Formulas (prototype-grade):**
  - Current monthly ops hours = `0.4 × staff + 8 × IT_FTE + 0.03 × devices` (min 12 h).
  - Workload reduction rate by current level: **Minimum 35%**, **Standard 25%**, **Advanced 15%**.
  - Phishing incident reduction potential by current level: **Minimum 30%**, **Standard 22%**, **Advanced 15%**.
  - Annual incidents baseline (pre-solution) = `staff / {{120, 180, 260}}` for levels {{Minimum, Standard, Advanced}}, clamped to **[0.2, 8]**.
  - **Annual avoided losses** = `baseline incidents × ${int(LOSS_PER_INCIDENT):,} × reduction rate`.
  - **Affordability cap (monthly)** = `labor savings per month + (annual avoided losses / 12)`.
- **Plan recommendation heuristic (prototype):** weighs HIPAA need, size, IT coverage, current controls, and device density to suggest **Essential / Standard / Advanced**.
- **HIPAA/BAA:** Indication is for messaging; full compliance depends on your implementation, agreements, and controls.
- **Branding:** This is a prototype for **DigitalBunker365.com** and is not a public price quote.
            """
        )

# ---------------------------
# Footer
# ---------------------------
st.markdown(
    """
    <div class="footer-note">
      © {year} <a class="link" href="https://www.digitalbunker365.com/" target="_blank" rel="noopener">Digital Bunker 365</a> — Prototype for value visualization without public pricing.
    </div>
    """.format(year=datetime.now().year),
    unsafe_allow_html=True,
)


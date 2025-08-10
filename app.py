# app.py
# Digital Bunker 365 — ROI Quick Check (Healthcare SMB)
# -----------------------------------------------------
# Purpose: Lightweight, value-first ROI calculator for first impressions.
# Notes:
# - This is a prototype. All coefficients/assumptions are illustrative and should be
#   calibrated with customer discovery and field data.
# - We intentionally set defaults on the conservative-to-high side for first-view anchoring
#   (e.g., hourly rate, loss per incident) so the Investment Cap is not underestimated.

import math
from typing import Tuple, Dict
import streamlit as st

# -----------------------------
# Global UI Config
# -----------------------------
st.set_page_config(
    page_title="Digital Bunker 365 — ROI Quick Check",
    page_icon="🛡️",
    layout="wide",
    initial_sidebar_state="collapsed",
)

# -----------------------------
# Styling (sticky notice + clean cards)
# -----------------------------
STICKY_CSS = """
<style>
/***** Base tweaks *****/
.block-container {padding-top: 1.2rem;}

/***** Sticky top notice *****/
.sticky-box {
  position: sticky;
  top: 0;
  z-index: 999;
  margin-bottom: 0.75rem;
  border: 1px solid rgba(0,0,0,0.1);
  border-radius: 10px;
  background: #eef6ff; /* light info */
  box-shadow: 0 3px 10px rgba(0,0,0,0.04);
}
.sticky-inner {padding: 0.9rem 1rem;}
.sticky-title {font-weight: 700; font-size: 0.95rem; margin-bottom: 0.25rem;}
.sticky-body {font-size: 0.9rem; line-height: 1.35;}
.sticky-body a {text-decoration: underline;}

/***** Soft cards for results *****/
.card {
  border: 1px solid rgba(0,0,0,0.08);
  border-radius: 12px;
  background: #ffffff;
  padding: 1rem 1rem 0.75rem 1rem;
  box-shadow: 0 2px 8px rgba(0,0,0,0.04);
}
.card h4 {margin: 0 0 0.35rem 0; font-size: 1.05rem}
.card .meta {color: #666; font-size: 0.85rem; margin-bottom: 0.35rem}
.kpi {font-weight: 800; font-size: 1.25rem;}
.kpi-sub {color: #555; font-size: 0.9rem;}
.badge {display: inline-block; padding: 0.2rem 0.5rem; border-radius: 999px; font-size: 0.75rem;}
.badge.green {background:#eaf7ea; color:#106a10; border: 1px solid #bfe1bf}
.badge.amber {background:#fff6e6; color:#7a4b00; border: 1px solid #f2d49a}
.badge.gray {background:#f2f2f2; color:#333; border: 1px solid #ddd}

/***** Anchors *****/
.anchor {scroll-margin-top: 110px;} /* ensure anchor not hidden beneath sticky */
</style>
"""

st.markdown(STICKY_CSS, unsafe_allow_html=True)

# -----------------------------
# Constants (prototype defaults — tuned for higher first-impression Cap)
# -----------------------------
LOSS_PER_INCIDENT_DEFAULT = 25_000.0  # USD, per incident (prototype default: higher)
OPS_REDUCTION = {  # by current control maturity
    "Minimum": 0.35,
    "Standard": 0.25,
    "Advanced": 0.15,
}
PHISH_REDUCTION = {
    "Minimum": 0.30,
    "Standard": 0.22,
    "Advanced": 0.15,
}
# Baseline annual phishing/related incidents ~ employees / divisor (rough heuristic)
INCIDENT_DIVISOR = {
    "Minimum": 120.0,
    "Standard": 180.0,
    "Advanced": 260.0,
}
INCIDENTS_MIN, INCIDENTS_MAX = 0.5, 8.0  # clamp range (raised min to avoid under-signaling)

# -----------------------------
# Helper functions
# -----------------------------

def current_ops_hours(staff: int, it_fte: int, devices: int | None) -> float:
    """Approximate current monthly ops hours for IT/Sec.
    - staff: total employees
    - it_fte: dedicated IT/Sec FTE
    - devices: endpoints (if None -> estimate)
    """
    if devices is None:
        # simple estimate: ~1.2 devices per person (laptop/phone/misc)
        devices = max(int(round(staff * 1.2)), 0)
    base = 0.4 * staff + 8.0 * it_fte + 0.03 * devices
    return max(base, 12.0)  # floor at 12h/month


def baseline_incidents(staff: int, maturity: str) -> float:
    div = INCIDENT_DIVISOR.get(maturity, INCIDENT_DIVISOR["Standard"])
    raw = staff / div
    return max(min(raw, INCIDENTS_MAX), INCIDENTS_MIN)


def plan_recommendation(staff: int, it_fte: int, maturity: str, hipaa: bool) -> Tuple[str, str]:
    """Very light heuristic for prototype plan guidance.
    Returns (plan_name, reason).
    """
    score = 0
    # scale by size
    if staff <= 25:
        score += 0
    elif staff <= 50:
        score += 1
    elif staff <= 100:
        score += 2
    else:
        score += 3

    # IT staffing scarcity tends to push higher plan (need more managed controls)
    if it_fte == 0:
        score += 2
    elif it_fte == 1:
        score += 1

    # low maturity -> higher plan
    score += {"Minimum": 2, "Standard": 1, "Advanced": 0}.get(maturity, 1)

    # HIPAA compliance increases need for governance
    if hipaa:
        score += 1

    if score >= 5:
        return "Advanced", "Larger scale / low maturity and/or limited IT coverage; HIPAA elevates governance needs."
    if score >= 3:
        return "Standard", "Balanced footprint or moderate maturity; targeted risk reduction with manageable ops load."
    return "Essential", "Smaller footprint and/or stronger maturity; start with core controls and grow as needed."


def currency(x: float) -> str:
    return f"${x:,.0f}"


def pct(x: float) -> str:
    return f"{x*100:.0f}%"


# -----------------------------
# Sticky top notice
# -----------------------------
with st.container():
    st.markdown(
        """
        <div class="sticky-box"><div class="sticky-inner">
        <div class="sticky-title">Purpose</div>
        <div class="sticky-body">This tool estimates the <b>potential value</b> of adopting Digital Bunker 365 — in saved workload, reduced risks, and an indicative <i>Investment Cap</i> (max monthly spend with ROI ≥ 0).</div>
        <div class="sticky-title" style="margin-top:0.5rem;">Important</div>
        <div class="sticky-body">The <b>Investment Cap is <u>not</u> our price</b>. It is a value-based budget guide. Actual plans & pricing will be tailored in a conversation with our team. <a href="#assumptions">Learn more</a>.</div>
        </div></div>
        """,
        unsafe_allow_html=True,
    )

# -----------------------------
# Header
# -----------------------------
st.title("🛡️ Digital Bunker 365 — ROI Quick Check")
st.caption("Prototype · Healthcare SMB focus · Value-first conversation starter")

# -----------------------------
# Inputs
# -----------------------------
left, right = st.columns([1.1, 1.4], gap="large")

with left:
    st.subheader("Your Organization")
    industry = st.selectbox(
        "Industry",
        ["Healthcare (SMB)", "Professional Services", "Non-profit", "Other"],
        index=0,
        help="Used for messaging in prototype. Coefficients may be specialized in production.",
    )
    staff = st.number_input(
        "Number of staff (headcount)", min_value=1, step=1, value=50,
        help="Full-time and part-time staff combined (approximate).",
    )
    it_fte = st.number_input(
        "Dedicated IT/Security FTE", min_value=0, step=1, value=1,
        help="Number of full-time equivalents focused on IT/Security.",
    )
    maturity = st.selectbox(
        "Current control maturity",
        ["Minimum", "Standard", "Advanced"],
        index=0,
        help="Rough self-assessment of current controls and practices.",
    )
    hipaa = st.checkbox("HIPAA applies", value=True, help="Protected health information handling.")
    devices_opt = st.number_input(
        "Endpoints / devices (optional)", min_value=0, step=1, value=0,
        help="If 0, we will estimate ~1.2 devices per employee.",
    )
    hourly_rate = st.number_input(
        "Blended labor cost ($/hour) (optional)", min_value=0.0, step=1.0, value=65.0,
        help="Loaded hourly cost for internal ops (prototype default set higher for first-view).",
    )

    st.divider()
    with st.expander("Advanced assumptions (optional)"):
        loss_per_incident = st.number_input(
            "Loss per incident (USD)", min_value=1_000.0, step=1_000.0, value=LOSS_PER_INCIDENT_DEFAULT,
            help="Direct/indirect cost per relevant incident (prototype default higher for healthcare).",
        )
        st.caption("Ops & phishing reduction rates depend on maturity (see Assumptions below).")

    go = st.button("Go", type="primary")

with right:
    st.subheader("Your Results")
    # Compute on first load as well for instant first impression.
    if go or True:
        devices = devices_opt if devices_opt > 0 else None
        curr_ops = current_ops_hours(staff, it_fte, devices)
        ops_red = OPS_REDUCTION[maturity]
        hours_saved = curr_ops * ops_red
        labor_savings_month = hours_saved * hourly_rate

        phish_red = PHISH_REDUCTION[maturity]
        baseline = baseline_incidents(staff, maturity)
        avoided_losses_annual = baseline * phish_red * (loss_per_incident if 'loss_per_incident' in locals() else LOSS_PER_INCIDENT_DEFAULT)
        cap = labor_savings_month + avoided_losses_annual / 12.0

        plan, reason = plan_recommendation(staff, it_fte, maturity, hipaa)

        c1, c2, c3 = st.columns(3)
        with c1:
            st.markdown("<div class='card'>", unsafe_allow_html=True)
            st.markdown("<h4>Recommended plan</h4>", unsafe_allow_html=True)
            st.markdown(f"<div class='kpi'>{plan}</div>", unsafe_allow_html=True)
            st.markdown(f"<div class='kpi-sub'><b>Why:</b> {reason}</div>", unsafe_allow_html=True)
            st.markdown("</div>", unsafe_allow_html=True)

        with c2:
            st.markdown("<div class='card'>", unsafe_allow_html=True)
            st.markdown("<h4>Monthly workload reduction</h4>", unsafe_allow_html=True)
            st.markdown(f"<div class='kpi'>{hours_saved:,.1f} h/mo</div>", unsafe_allow_html=True)
            st.markdown(f"<div class='kpi-sub'>{currency(labor_savings_month)}/mo equivalent</div>", unsafe_allow_html=True)
            badge_class = "green" if ops_red >= 0.30 else ("amber" if ops_red >= 0.20 else "gray")
            st.markdown(f"<span class='badge {badge_class}'>reduction: {pct(ops_red)}</span>", unsafe_allow_html=True)
            st.markdown("</div>", unsafe_allow_html=True)

        with c3:
            st.markdown("<div class='card'>", unsafe_allow_html=True)
            st.markdown("<h4>Phishing risk reduction</h4>", unsafe_allow_html=True)
            st.markdown(f"<div class='kpi'>{pct(phish_red)}</div>", unsafe_allow_html=True)
            tone = "High" if phish_red >= 0.28 else ("Moderate" if phish_red >= 0.20 else "Modest")
            st.markdown(f"<div class='kpi-sub'>Improvement potential: <b>{tone}</b></div>", unsafe_allow_html=True)
            st.markdown("</div>", unsafe_allow_html=True)

        c4, c5 = st.columns(2)
        with c4:
            st.markdown("<div class='card'>", unsafe_allow_html=True)
            st.markdown("<h4>Annual avoided losses (estimate)</h4>", unsafe_allow_html=True)
            st.markdown(f"<div class='kpi'>{currency(avoided_losses_annual)}</div>", unsafe_allow_html=True)
            st.markdown(f"<div class='kpi-sub'>Baseline: ~{baseline:.2f} incidents/year</div>", unsafe_allow_html=True)
            st.markdown("</div>", unsafe_allow_html=True)

        with c5:
            st.markdown("<div class='card'>", unsafe_allow_html=True)
            st.markdown("<h4>Investment affordability (cap)</h4>", unsafe_allow_html=True)
            st.markdown(f"<div class='kpi'>{currency(cap)}/mo</div>", unsafe_allow_html=True)
            st.markdown("<div class='kpi-sub'>ROI ≥ 0 if monthly cost ≤ this cap</div>", unsafe_allow_html=True)
            st.markdown("<span class='badge gray'>Value-based guide • Not our price</span>", unsafe_allow_html=True)
            st.markdown("</div>", unsafe_allow_html=True)

        st.markdown("### Inputs snapshot")
        snapshot_cols = st.columns(3)
        with snapshot_cols[0]:
            st.write("**Industry**", industry)
            st.write("**Headcount**", staff)
            st.write("**IT/Sec FTE**", it_fte)
        with snapshot_cols[1]:
            st.write("**Maturity**", maturity)
            st.write("**HIPAA**", "Yes" if hipaa else "No")
            st.write("**Devices**", devices if devices is not None else int(round(staff * 1.2)))
        with snapshot_cols[2]:
            st.write("**Hourly cost**", currency(hourly_rate) + "/h")
            st.write("**Loss/incident**", currency(loss_per_incident if 'loss_per_incident' in locals() else LOSS_PER_INCIDENT_DEFAULT))

# -----------------------------
# Assumptions, formulas & limitations
# -----------------------------
st.divider()
st.markdown('<a name="assumptions" class="anchor"></a>', unsafe_allow_html=True)
st.subheader("Assumptions, formulas & limitations (please read)")

with st.expander("Show details", expanded=False):
    st.markdown(
        """
- **Purpose of this calculator**: Provide an **indicative** value-based view (saved workload, avoided losses) and a **budget guide** (Investment Cap). It is **not** a quote.
- **Current monthly ops hours**: \(0.4 \times \text{staff} + 8.0 \times \text{IT FTE} + 0.03 \times \text{devices}\), floored at **12 h/mo**. Devices default to **~1.2 per staff** if blank.
- **Ops reduction rate** (by maturity): Minimum **35%**, Standard **25%**, Advanced **15%**.
- **Phishing reduction rate** (by maturity): Minimum **30%**, Standard **22%**, Advanced **15%**.
- **Baseline annual incidents**: \(\text{staff} / D\), where D=120 (Minimum), 180 (Standard), 260 (Advanced). Clamped to **0.5–8.0**.
- **Loss per incident** (prototype default): **$25,000** (adjustable under Advanced assumptions).
- **Annual avoided losses**: baseline \(\times\) phishing reduction \(\times\) loss/incident.
- **Investment Cap (monthly)**: **Labor savings/mo** + **(Annual avoided losses / 12)**. This is the **ROI ≥ 0 boundary**, not our price.

**Limitations**: This is a prototype using simplified heuristics. Real outcomes depend on control scope, user behavior, threat landscape, and integration quality. Calibrate coefficients with field data. In HIPAA contexts, consider breach notification, downtime, legal, and reputational impacts which may raise loss estimates.
        """,
        unsafe_allow_html=False,
    )

st.caption("© Digital Bunker 365 — Prototype for discussion. For tailored proposals, please contact us.")


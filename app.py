import io
import json
from datetime import date
from statistics import mean

import streamlit as st
import pandas as pd
from reportlab.lib import colors
from reportlab.lib.enums import TA_CENTER
from reportlab.lib.pagesizes import A4
from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle
from reportlab.lib.units import mm
from reportlab.platypus import (
    SimpleDocTemplate, Paragraph, Spacer, Table, TableStyle, PageBreak,
    KeepTogether
)

st.set_page_config(page_title="Karaansaw CPP / CCP Test Report", page_icon="⚙️", layout="wide")

NAVY = "#1F274B"
TEAL = "#83CED1"
GOLD = "#A4854E"

st.markdown(f"""
<style>
:root {{ --ks-navy: {NAVY}; --ks-teal: {TEAL}; --ks-gold: {GOLD}; }}
.block-container {{padding-top: 1.2rem; padding-bottom: 3rem; max-width: 1500px;}}
header[data-testid="stHeader"] {{background: rgba(255,255,255,0.88);}}
h1, h2, h3 {{color: {NAVY}; letter-spacing: -0.025em;}}
h1 {{font-weight: 800;}}
h2 {{font-weight: 750; margin-top: .35rem;}}
[data-testid="stCaptionContainer"] {{color: #667085;}}
div[data-testid="stMetric"] {{background: linear-gradient(145deg,#ffffff,#f7fbfc); border: 1px solid #dbe5e8; padding: 16px 18px; border-radius: 14px; box-shadow: 0 2px 8px rgba(31,39,75,.035); min-height: 112px;}}
div[data-testid="stMetricLabel"] p {{color: #596579; font-weight: 650; font-size: .86rem;}}
div[data-testid="stMetricValue"] {{color: {NAVY}; font-size: clamp(1.15rem,2vw,1.8rem); font-weight: 800;}}
div[data-testid="stForm"] {{border: 1px solid #e2e8f0; border-radius: 18px; padding: 1.1rem 1.2rem 1.2rem; background: #fff;}}
div[data-testid="stExpander"] {{border: 1px solid #e2e8f0; border-radius: 12px; overflow: hidden;}}
.stButton button, .stDownloadButton button, div[data-testid="stFormSubmitButton"] button {{border-radius: 10px; font-weight: 700; min-height: 2.8rem;}}
.stButton button[kind="primary"], div[data-testid="stFormSubmitButton"] button[kind="primary"] {{background: {NAVY}; border-color: {NAVY};}}
.karaansaw-hero {{background: linear-gradient(120deg,{NAVY} 0%,#303d70 67%,#245d68 100%); color: white; padding: 25px 28px; border-radius: 20px; margin: 0 0 1rem 0; box-shadow: 0 12px 28px rgba(31,39,75,.14);}}
.karaansaw-hero h1 {{color: white !important; margin: 0 0 6px 0; font-size: clamp(1.65rem,3vw,2.35rem);}}
.karaansaw-hero p {{color: #e4f1f4; margin: 0; font-size: 1rem;}}
.karaansaw-eyebrow {{color: {TEAL}; text-transform: uppercase; letter-spacing: .14em; font-weight: 800; font-size: .72rem; margin-bottom: 8px;}}
.karaansaw-note {{padding: 13px 16px; border-left: 4px solid {TEAL}; background: #f0fafa; border-radius: 0 10px 10px 0; color: #344054; margin: .65rem 0 1rem;}}
.karaansaw-section {{font-size: .78rem; text-transform: uppercase; letter-spacing: .1em; font-weight: 800; color: #697586; margin: .4rem 0 .7rem;}}
.karaansaw-result {{background: #f2fbfb; border: 1px solid #cde9e9; border-radius: 16px; padding: 16px 18px;}}
.karaansaw-small {{font-size: .82rem; color: #667085;}}
[data-testid="stTabs"] button {{font-weight: 700;}}
@media (max-width: 700px) {{ .block-container {{padding-left: 1rem; padding-right: 1rem;}} div[data-testid="stMetric"] {{padding: 12px;}} }}
</style>
""", unsafe_allow_html=True)

def money(v):
    return f"{v:,.2f}"

def safe_div(a, b):
    return a / b if b else 0.0

def valid_edge_values(values):
    result = []
    for x in values:
        if x is None:
            continue
        try:
            value = float(x)
        except (TypeError, ValueError):
            continue

        if value > 0:
            result.append(value)

    return result


def calc(data):
    old_edges = valid_edge_values(data["old_edge_pieces"])
    new_edges = valid_edge_values(data["new_edge_pieces"])

    if not old_edges or not new_edges:
        raise ValueError(
            "Enter at least one measured edge result greater than zero for both tools."
        )

    l0, l1 = mean(old_edges), mean(new_edges)
    e0, e1 = data["old_usable_edges"], data["new_usable_edges"]
    p0, p1 = data["old_insert_price"], data["new_insert_price"]
    monthly = data["monthly_accepted_output"]
    annual_n = monthly * 12
    life0, life1 = l0 * e0, l1 * e1
    cpp0, cpp1 = safe_div(p0, life0), safe_div(p1, life1)
    tool_cost0, tool_cost1 = cpp0 * annual_n, cpp1 * annual_n
    tool_saving = tool_cost0 - tool_cost1

    # Supporting cost assumptions (same calculation scope as the supplied workbook)
    a = data["assumptions"]
    edge_events0, edge_events1 = safe_div(annual_n, l0), safe_div(annual_n, l1)
    machine_hours0 = edge_events0 * a["machine_stop_min"] / 60
    machine_hours1 = edge_events1 * a["machine_stop_min"] / 60
    operator_hours0 = edge_events0 * a["operator_min"] / 60
    operator_hours1 = edge_events1 * a["operator_min"] / 60
    qc_hours0 = edge_events0 * a["qc_min"] / 60
    qc_hours1 = edge_events1 * a["qc_min"] / 60

    machine_saving = (machine_hours0 - machine_hours1) * a["machine_rate"]
    operator_saving = (operator_hours0 - operator_hours1) * a["operator_rate"]
    qc_saving = (qc_hours0 - qc_hours1) * a["qc_rate"]

    inserts0, inserts1 = safe_div(annual_n, life0), safe_div(annual_n, life1)
    stock0 = inserts0 * a["stock_coverage_months"] / 12 * p0
    stock1 = inserts1 * a["stock_coverage_months"] / 12 * p1
    carrying0, carrying1 = stock0 * a["carrying_rate"], stock1 * a["carrying_rate"]
    carrying_saving = carrying0 - carrying1

    offset_events0 = annual_n * a["offsets_old_per_1000"] / 1000
    offset_events1 = annual_n * a["offsets_new_per_1000"] / 1000
    offset_cost0 = offset_events0 * a["offset_min_old"] / 60 * (a["machine_rate"] + a["operator_rate"])
    offset_cost1 = offset_events1 * a["offset_min_new"] / 60 * (a["machine_rate"] + a["operator_rate"])
    offset_saving = offset_cost0 - offset_cost1

    scrap_saving = annual_n * (a["rejects_old_rate"] - a["rejects_new_rate"]) * a["reject_cost"]
    rework_saving = annual_n * (a["rework_old_rate"] - a["rework_new_rate"]) * a["rework_cost"]
    orders_saving = (a["orders_old"] - a["orders_new"]) * a["order_cost"]
    failures_saving = (a["failures_old"] - a["failures_new"]) * a["failure_cost"]

    extra = {
        "Machine downtime": machine_saving,
        "Operator intervention": operator_saving,
        "Post-change QC": qc_saving,
        "Inventory carrying cost": carrying_saving,
        "Wear-offset corrections": offset_saving,
        "Tool-related scrap": scrap_saving,
        "Tool-related rework": rework_saving,
        "Orders and shipments": orders_saving,
        "Unexpected failures": failures_saving,
    }
    extra_benefit = sum(extra.values())
    total_benefit = tool_saving + extra_benefit

    # Workbook's comparison denominator: existing annual tool cost + assessed support costs.
    existing_compared_cost = (
        tool_cost0 + machine_hours0 * a["machine_rate"]
        + operator_hours0 * a["operator_rate"] + qc_hours0 * a["qc_rate"]
        + carrying0 + offset_cost0
        + annual_n * a["rejects_old_rate"] * a["reject_cost"]
        + annual_n * a["rework_old_rate"] * a["rework_cost"]
        + a["orders_old"] * a["order_cost"]
        + a["failures_old"] * a["failure_cost"]
    )
    proposed_compared_cost = existing_compared_cost - total_benefit
    ccp0, ccp1 = safe_div(existing_compared_cost, annual_n), safe_div(proposed_compared_cost, annual_n)
    reduction = safe_div(total_benefit, existing_compared_cost)
    hours_released = machine_hours0 - machine_hours1
    idle_kwh_saved = hours_released * a["idle_power_kw"]

    return {
        "l0": l0, "l1": l1, "life0": life0, "life1": life1,
        "cpp0": cpp0, "cpp1": cpp1, "tool_cost0": tool_cost0,
        "tool_cost1": tool_cost1, "tool_saving": tool_saving,
        "annual_n": annual_n, "edge_events0": edge_events0, "edge_events1": edge_events1,
        "hours_released": hours_released, "idle_kwh_saved": idle_kwh_saved,
        "extra": extra, "extra_benefit": extra_benefit, "total_benefit": total_benefit,
        "existing_compared_cost": existing_compared_cost,
        "proposed_compared_cost": proposed_compared_cost, "ccp0": ccp0, "ccp1": ccp1,
        "reduction": reduction, "inserts0": inserts0, "inserts1": inserts1,
        "machine_saving": machine_saving, "operator_saving": operator_saving,
        "qc_saving": qc_saving, "carrying_saving": carrying_saving,
        "offset_saving": offset_saving, "scrap_saving": scrap_saving,
        "rework_saving": rework_saving, "orders_saving": orders_saving,
        "failures_saving": failures_saving,
    }

def make_pdf(d, r):
    buff = io.BytesIO()
    doc = SimpleDocTemplate(
        buff, pagesize=A4, rightMargin=16*mm, leftMargin=16*mm,
        topMargin=15*mm, bottomMargin=16*mm, title="CPP / CCP Cutting Tool Test Report"
    )
    styles = getSampleStyleSheet()
    styles.add(ParagraphStyle(name="ReportTitle", parent=styles["Title"], textColor=colors.HexColor(NAVY),
                              fontSize=20, leading=24, alignment=TA_CENTER, spaceAfter=6))
    styles.add(ParagraphStyle(name="Section", parent=styles["Heading2"], textColor=colors.HexColor(NAVY),
                              fontSize=12, leading=15, spaceBefore=10, spaceAfter=6))
    styles.add(ParagraphStyle(name="SmallNote", parent=styles["BodyText"], fontSize=8, leading=10,
                              textColor=colors.HexColor("#4b5563")))
    story = []
    story.append(Paragraph("KARAANSAW INDUSTRIAL GROUP", styles["ReportTitle"]))
    story.append(Paragraph("CUTTING TOOL ECONOMICS - CPP / CCP TEST REPORT", styles["Heading2"]))
    story.append(Spacer(1, 4*mm))
    info = [
        ["Customer", d["customer"], "Engineer", d["engineer"]],
        ["Distributor", d["distributor"] or "—", "Test date", str(d["test_date"])],
        ["Workpiece", d["workpiece"], "Material / hardness", d["material"] or "—"],
        ["Operation", d["operation"], "Machine", d["machine"] or "—"],
        ["Existing tool", d["old_tool"], "Proposed tool", d["new_tool"]],
        ["Currency", d["currency"], "Annual accepted output", f'{r["annual_n"]:,.0f}'],
    ]
    t = Table(info, colWidths=[30*mm, 55*mm, 32*mm, 55*mm])
    t.setStyle(TableStyle([
        ("BACKGROUND",(0,0),(0,-1),colors.HexColor("#eef1f7")),
        ("BACKGROUND",(2,0),(2,-1),colors.HexColor("#eef1f7")),
        ("TEXTCOLOR",(0,0),(0,-1),colors.HexColor(NAVY)),
        ("TEXTCOLOR",(2,0),(2,-1),colors.HexColor(NAVY)),
        ("FONTNAME",(0,0),(-1,-1),"Helvetica"),
        ("FONTSIZE",(0,0),(-1,-1),8),
        ("GRID",(0,0),(-1,-1),0.35,colors.HexColor("#d1d5db")),
        ("VALIGN",(0,0),(-1,-1),"MIDDLE"),
        ("TOPPADDING",(0,0),(-1,-1),6),("BOTTOMPADDING",(0,0),(-1,-1),6),
    ]))
    story.append(t)
    story.append(Paragraph("1. Trial conditions", styles["Section"]))
    conditions = [
        ["Parameter", "Existing tool", "Proposed tool"],
        ["Insert / grade", d["old_insert"], d["new_insert"]],
        ["Cutting speed (m/min)", f'{d["old_vc"]:g}', f'{d["new_vc"]:g}'],
        ["RPM (min^-1)", f'{d["old_rpm"]:g}', f'{d["new_rpm"]:g}'],
        ["Feed (mm/rev)", f'{d["old_feed"]:g}', f'{d["new_feed"]:g}'],
        ["Depth of cut (mm)", f'{d["old_ap"]:g}', f'{d["new_ap"]:g}'],
        ["Coolant", d["old_coolant"], d["new_coolant"]],
        ["Usable edges / insert", str(d["old_usable_edges"]), str(d["new_usable_edges"])],
        ["Insert price", f'{d["currency"]} {money(d["old_insert_price"])}', f'{d["currency"]} {money(d["new_insert_price"])}'],
        ["Average accepted pieces / edge", f'{r["l0"]:.4f}', f'{r["l1"]:.4f}'],
        ["Accepted pieces / insert", f'{r["life0"]:.4f}', f'{r["life1"]:.4f}'],
    ]
    t = Table(conditions, colWidths=[64*mm, 54*mm, 54*mm], repeatRows=1)
    t.setStyle(TableStyle([
        ("BACKGROUND",(0,0),(-1,0),colors.HexColor(NAVY)),("TEXTCOLOR",(0,0),(-1,0),colors.white),
        ("GRID",(0,0),(-1,-1),0.35,colors.HexColor("#d1d5db")),("FONTSIZE",(0,0),(-1,-1),8),
        ("ROWBACKGROUNDS",(0,1),(-1,-1),[colors.white,colors.HexColor("#f8fafc")]),
        ("TOPPADDING",(0,0),(-1,-1),5),("BOTTOMPADDING",(0,0),(-1,-1),5),
    ]))
    story.append(t)
    story.append(Paragraph("2. CPP — insert consumption cost", styles["Section"]))
    cpp_table = [
        ["Metric", "Existing tool", "Proposed tool"],
        ["CPP / accepted piece", f'{d["currency"]} {money(r["cpp0"])}', f'{d["currency"]} {money(r["cpp1"])}'],
        ["Annual insert cost", f'{d["currency"]} {money(r["tool_cost0"])}', f'{d["currency"]} {money(r["tool_cost1"])}'],
        ["Annual tool-only saving", "", f'{d["currency"]} {money(r["tool_saving"])}'],
    ]
    t = Table(cpp_table, colWidths=[64*mm,54*mm,54*mm])
    t.setStyle(TableStyle([
        ("BACKGROUND",(0,0),(-1,0),colors.HexColor(NAVY)),("TEXTCOLOR",(0,0),(-1,0),colors.white),
        ("GRID",(0,0),(-1,-1),0.35,colors.HexColor("#d1d5db")),("FONTSIZE",(0,0),(-1,-1),8),
        ("BACKGROUND",(0,-1),(-1,-1),colors.HexColor("#e9f7f7")),
        ("TOPPADDING",(0,0),(-1,-1),6),("BOTTOMPADDING",(0,0),(-1,-1),6),
    ]))
    story.append(t)
    story.append(Paragraph("3. CCP — assessed annual economic comparison", styles["Section"]))
    rows = [["Cost / benefit category", f"Annual saving ({d['currency']})"]]
    rows += [[k, money(v)] for k,v in r["extra"].items()]
    rows += [["Additional assessed benefit", money(r["extra_benefit"])],
             ["Tool-only saving", money(r["tool_saving"])],
             ["TOTAL ANNUAL ECONOMIC BENEFIT", money(r["total_benefit"])],
             ["Existing CCP / accepted piece", money(r["ccp0"])],
             ["Proposed CCP / accepted piece", money(r["ccp1"])],
             ["Compared cost reduction", f'{r["reduction"]:.2%}'],
             ["Machine hours released / year", f'{r["hours_released"]:.2f}'],
             ["Estimated idle energy reduction (kWh/year)", f'{r["idle_kwh_saved"]:.2f}']]
    t = Table(rows, colWidths=[112*mm,60*mm], repeatRows=1)
    t.setStyle(TableStyle([
        ("BACKGROUND",(0,0),(-1,0),colors.HexColor(NAVY)),("TEXTCOLOR",(0,0),(-1,0),colors.white),
        ("GRID",(0,0),(-1,-1),0.35,colors.HexColor("#d1d5db")),("FONTSIZE",(0,0),(-1,-1),8),
        ("ROWBACKGROUNDS",(0,1),(-1,-1),[colors.white,colors.HexColor("#f8fafc")]),
        ("BACKGROUND",(0,len(rows)-6),(-1,len(rows)-6),colors.HexColor("#e9f7f7")),
        ("FONTNAME",(0,len(rows)-6),(-1,len(rows)-6),"Helvetica-Bold"),
        ("TOPPADDING",(0,0),(-1,-1),5),("BOTTOMPADDING",(0,0),(-1,-1),5),
    ]))
    story.append(t)
    story.append(Spacer(1, 5*mm))
    story.append(Paragraph("Assumptions and interpretation", styles["Section"]))
    story.append(Paragraph(
        "CPP includes insert consumption cost only. CCP is an internal comparison label for insert cost plus the assessed supporting-cost categories above; it is not the complete factory cost per part. "
        "Machine hours valued at an hourly rate represent released capacity and are not automatically cash savings. Energy is reported physically and is not charged a second time. "
        "Yellow/example inputs in the source workbook should be replaced with factory measurements before this report is used as a verified customer claim.",
        styles["SmallNote"]))
    if d["remarks"]:
        story.append(Spacer(1, 3*mm))
        story.append(Paragraph("<b>Remarks:</b> " + d["remarks"].replace("&","&amp;").replace("<","&lt;").replace(">","&gt;"), styles["SmallNote"]))
    def footer(canvas, doc):
        canvas.saveState()
        canvas.setStrokeColor(colors.HexColor(TEAL))
        canvas.line(16*mm, 12*mm, 194*mm, 12*mm)
        canvas.setFont("Helvetica", 7)
        canvas.setFillColor(colors.HexColor("#6b7280"))
        canvas.drawString(16*mm, 7*mm, "Karaansaw Industrial Group | CPP / CCP test report")
        canvas.drawRightString(194*mm, 7*mm, f"Page {doc.page}")
        canvas.restoreState()
    doc.build(story, onFirstPage=footer, onLaterPages=footer)
    return buff.getvalue()

st.markdown("""
<div class="karaansaw-hero">
  <div class="karaansaw-eyebrow">KARAANSAW · SALES ENGINEERING</div>
  <h1>Cutting Tool Economics</h1>
  <p>CPP / CCP comparison · Trial results · Annual savings report</p>
</div>
""", unsafe_allow_html=True)
st.markdown('<div class="karaansaw-note"><b>Built for customer meetings.</b> Enter measured tool-test results, compare the current and proposed solution, and generate a customer-ready PDF. Keep measured results separate from estimated factory-cost assumptions.</div>', unsafe_allow_html=True)

with st.form("test_form"):
    st.header("1. Report identity")
    c1,c2,c3 = st.columns(3)
    customer = c1.text_input("Customer / user name", "M AND DALVI ENGINEERING")
    engineer = c2.text_input("Engineer name", "Narayan")
    distributor = c3.text_input("Distributor", "CREATOR CUTTING TOOLS")
    c1,c2,c3 = st.columns(3)
    test_date = c1.date_input("Test date", date.today())
    currency = c2.text_input("Currency code", "INR").strip().upper() or "INR"
    operation = c3.text_input("Operation", "OD TURNING")
    c1,c2,c3 = st.columns(3)
    workpiece = c1.text_input("Workpiece name", "BEARING")
    material = c2.text_input("Material / hardness", "FORGE STEEL")
    machine = c3.text_input("Machine type", "CNC")
    c1,c2 = st.columns(2)
    old_tool = c1.text_input("Existing tool / brand", "WINTECH")
    new_tool = c2.text_input("Proposed tool / brand", "WURNHER")

    st.header("2. Tool and cutting conditions")
    c1,c2 = st.columns(2)
    with c1:
        st.subheader("Existing tool")
        old_insert = st.text_input("Insert code / grade — existing", "TNMG 1060412 DQ 1125")
        old_vc = st.number_input("Cutting speed Vc (m/min) — existing", min_value=0.0, value=240.0)
        old_rpm = st.number_input("RPM — existing", min_value=0.0, value=1600.0)
        old_feed = st.number_input("Feed (mm/rev) — existing", min_value=0.0, value=0.24, format="%.4f")
        old_ap = st.number_input("Depth of cut (mm) — existing", min_value=0.0, value=0.8)
        old_coolant = st.selectbox("Coolant — existing", ["Wet", "Dry", "MQL", "Other"])
        old_usable_edges = st.number_input("Usable edges per insert — existing", min_value=1, max_value=32, value=6)
        old_insert_price = st.number_input("Insert price — existing", min_value=0.0, value=195.0)
    with c2:
        st.subheader("Proposed tool")
        new_insert = st.text_input("Insert code / grade — proposed", "TNMG 160412 PM4 CP 2555")
        new_vc = st.number_input("Cutting speed Vc (m/min) — proposed", min_value=0.0, value=220.0)
        new_rpm = st.number_input("RPM — proposed", min_value=0.0, value=1600.0)
        new_feed = st.number_input("Feed (mm/rev) — proposed", min_value=0.0, value=0.24, format="%.4f")
        new_ap = st.number_input("Depth of cut (mm) — proposed", min_value=0.0, value=0.8)
        new_coolant = st.selectbox("Coolant — proposed", ["Wet", "Dry", "MQL", "Other"])
        new_usable_edges = st.number_input("Usable edges per insert — proposed", min_value=1, max_value=32, value=6)
        new_insert_price = st.number_input("Insert price — proposed", min_value=0.0, value=220.0)

    st.header("3. Trial results — accepted pieces per edge")
    st.caption("Leave unused edge rows empty. Record the same acceptance criteria and stopping rule for both tools.")
    labels = ["1st edge","2nd edge","3rd edge","4th edge","5th edge","6th edge","7th edge","8th edge"]
    old_edge_pieces, new_edge_pieces = [], []
    for i in range(0,8,2):
        cols = st.columns(4)
        for j in range(i,min(i+2,8)):
            value=float([30, 31, 30, 30, 31, 30, 0, 0][j])
            new_edge_pieces.append(cols[(j-i)*2+1].number_input(f"{labels[j]} — proposed", min_value=0.0, value=float([30, 31, 30, 30, 31, 30, 0, 0][j]), key=f"new_edge_{j}", help="Enter 0 if not used; zeros are ignored."))
    old_edge_pieces = [x if x > 0 else None for x in old_edge_pieces]
    new_edge_pieces = [x if x > 0 else None for x in new_edge_pieces]
    monthly_accepted_output = st.number_input("Monthly accepted production volume", min_value=1, value=20000, step=100)

    st.header("4. Supporting-cost assumptions")
    st.caption("The default values below are illustrative examples from the workbook, not universal industry rates. Replace them with factory evidence.")
    with st.expander("Machine, operator, QC and inventory", expanded=True):
        c1,c2,c3 = st.columns(3)
        machine_stop_min = c1.number_input("Machine stop per edge change (min)", min_value=0.0, value=5.0)
        machine_rate = c2.number_input(f"Machine rate ({currency}/hour)", min_value=0.0, value=1200.0)
        idle_power_kw = c3.number_input("Idle power (kW)", min_value=0.0, value=2.0)
        c1,c2,c3 = st.columns(3)
        operator_min = c1.number_input("Active operator work per edge change (min)", min_value=0.0, value=5.0)
        operator_rate = c2.number_input(f"Operator rate ({currency}/hour)", min_value=0.0, value=300.0)
        qc_min = c3.number_input("Post-change QC time (min)", min_value=0.0, value=3.0)
        c1,c2 = st.columns(2)
        qc_rate = c1.number_input(f"QC rate ({currency}/hour)", min_value=0.0, value=600.0)
        stock_coverage_months = c2.number_input("Stock coverage (months)", min_value=0.0, value=1.0)
        carrying_rate_pct = st.number_input("Annual inventory carrying rate (%)", min_value=0.0, value=20.0)
    with st.expander("Offsets, quality, purchasing and failures", expanded=True):
        c1,c2,c3,c4 = st.columns(4)
        offsets_old_per_1000 = c1.number_input("Existing offsets / 1,000 pieces", min_value=0.0, value=3.0)
        offsets_new_per_1000 = c2.number_input("Proposed offsets / 1,000 pieces", min_value=0.0, value=2.8)
        offset_min_old = c3.number_input("Existing minutes per offset", min_value=0.0, value=2.0)
        offset_min_new = c4.number_input("Proposed minutes per offset", min_value=0.0, value=2.0)
        c1,c2,c3,c4 = st.columns(4)
        rejects_old_pct = c1.number_input("Existing extra rejects per accepted piece (%)", min_value=0.0, value=0.5)
        rejects_new_pct = c2.number_input("Proposed extra rejects per accepted piece (%)", min_value=0.0, value=0.4)
        reject_cost = c3.number_input(f"Incremental reject cost ({currency}/case)", min_value=0.0, value=200.0)
        rework_old_pct = c4.number_input("Existing rework cases per accepted piece (%)", min_value=0.0, value=1.0)
        c1,c2,c3,c4 = st.columns(4)
        rework_new_pct = c1.number_input("Proposed rework cases per accepted piece (%)", min_value=0.0, value=0.8)
        rework_cost = c2.number_input(f"Incremental rework cost ({currency}/case)", min_value=0.0, value=80.0)
        orders_old = c3.number_input("Existing orders / shipments per year", min_value=0.0, value=12.0)
        orders_new = c4.number_input("Proposed orders / shipments per year", min_value=0.0, value=11.0)
        c1,c2,c3 = st.columns(3)
        order_cost = c1.number_input(f"Cost per order / shipment ({currency})", min_value=0.0, value=150.0)
        failures_old = c2.number_input("Existing unexpected failures per year", min_value=0.0, value=2.0)
        failures_new = c3.number_input("Proposed unexpected failures per year", min_value=0.0, value=1.9)
        failure_cost = st.number_input(f"Incremental loss per failure ({currency})", min_value=0.0, value=400.0)
    remarks = st.text_area("Remarks / test limitations", "Cutting speeds differ; cutting cycle times are unavailable and are excluded from this comparison.")

    submitted = st.form_submit_button("Calculate report", type="primary", use_container_width=True)

if submitted:
    data = {
        "customer":customer,"engineer":engineer,"distributor":distributor,"test_date":test_date,
        "currency":currency,"operation":operation,"workpiece":workpiece,"material":material,"machine":machine,
        "old_tool":old_tool,"new_tool":new_tool,"old_insert":old_insert,"new_insert":new_insert,
        "old_vc":old_vc,"new_vc":new_vc,"old_rpm":old_rpm,"new_rpm":new_rpm,
        "old_feed":old_feed,"new_feed":new_feed,"old_ap":old_ap,"new_ap":new_ap,
        "old_coolant":old_coolant,"new_coolant":new_coolant,
        "old_usable_edges":old_usable_edges,"new_usable_edges":new_usable_edges,
        "old_insert_price":old_insert_price,"new_insert_price":new_insert_price,
        "old_edge_pieces":old_edge_pieces,"new_edge_pieces":new_edge_pieces,
        "monthly_accepted_output":monthly_accepted_output,"remarks":remarks,
        "assumptions":{
            "machine_stop_min":machine_stop_min,"machine_rate":machine_rate,"idle_power_kw":idle_power_kw,
            "operator_min":operator_min,"operator_rate":operator_rate,"qc_min":qc_min,"qc_rate":qc_rate,
            "stock_coverage_months":stock_coverage_months,"carrying_rate":carrying_rate_pct/100,
            "offsets_old_per_1000":offsets_old_per_1000,"offsets_new_per_1000":offsets_new_per_1000,
            "offset_min_old":offset_min_old,"offset_min_new":offset_min_new,
            "rejects_old_rate":rejects_old_pct/100,"rejects_new_rate":rejects_new_pct/100,"reject_cost":reject_cost,
            "rework_old_rate":rework_old_pct/100,"rework_new_rate":rework_new_pct/100,"rework_cost":rework_cost,
            "orders_old":orders_old,"orders_new":orders_new,"order_cost":order_cost,
            "failures_old":failures_old,"failures_new":failures_new,"failure_cost":failure_cost,
        }
    }
    try:
        result = calc(data)
        st.session_state["report_data"] = data
        st.session_state["report_result"] = result
    except ValueError as e:
        st.error(str(e))

if "report_result" in st.session_state:
    d = st.session_state["report_data"]
    r = st.session_state["report_result"]
    st.divider()
    st.markdown('<div class="karaansaw-section">Customer meeting view</div>', unsafe_allow_html=True)
    st.header("Results at a glance")
    if r["total_benefit"] >= 0:
        st.markdown(f'<div class="karaansaw-result"><b>Estimated annual economic benefit</b><br><span style="font-size:1.65rem;font-weight:800;color:{NAVY}">{d["currency"]} {money(r["total_benefit"])}</span><br><span class="karaansaw-small">Based on the inputs and cost assumptions entered below. Confirm assumptions before presenting this as a verified saving.</span></div>', unsafe_allow_html=True)
    else:
        st.warning("The current assumptions indicate a negative annual economic benefit. Review prices, tool-life data and supporting-cost inputs before presenting the result.")
    st.write("")
    c1,c2,c3,c4 = st.columns(4)
    c1.metric("CPP · Existing", f'{d["currency"]} {money(r["cpp0"])}', help="Insert consumption cost per accepted piece.")
    c2.metric("CPP · Proposed", f'{d["currency"]} {money(r["cpp1"])}', delta=f'{(r["cpp0"]-r["cpp1"]):,.2f} {d["currency"]} / piece', help="Insert consumption cost per accepted piece.")
    c3.metric("Annual tool-only saving", f'{d["currency"]} {money(r["tool_saving"])}')
    c4.metric("Compared cost reduction", f'{r["reduction"]:.1%}')

    c1,c2,c3 = st.columns(3)
    c1.metric("CCP · Existing", f'{d["currency"]} {money(r["ccp0"])}', help="Only includes the cost categories assessed in this model.")
    c2.metric("CCP · Proposed", f'{d["currency"]} {money(r["ccp1"])}', help="Only includes the cost categories assessed in this model.")
    c3.metric("Machine hours released / year", f'{r["hours_released"]:,.1f} h')

    overview_tab, detail_tab, report_tab = st.tabs(["Savings overview", "Cost breakdown", "Export report"])
    with overview_tab:
        st.subheader("Annual cost comparison")
        compare_df = pd.DataFrame({
            "Tool-only annual cost": [r["tool_cost0"], r["tool_cost1"]],
            "Assessed annual comparison cost": [r["existing_compared_cost"], r["proposed_compared_cost"]],
        }, index=["Existing tool", "Proposed tool"])
        st.bar_chart(compare_df, use_container_width=True)
        c1,c2 = st.columns(2)
        c1.markdown("**Tool-life comparison**")
        life_df = pd.DataFrame({"Accepted pieces per edge": [r["l0"], r["l1"]], "Accepted pieces per insert": [r["life0"], r["life1"]]}, index=["Existing tool", "Proposed tool"])
        c1.bar_chart(life_df, use_container_width=True)
        c2.markdown("**Annual impact**")
        impact_df = pd.DataFrame({"Amount": [r["tool_saving"], r["extra_benefit"], r["total_benefit"]]}, index=["Tool-only saving", "Additional assessed benefit", "Total estimated benefit"])
        c2.bar_chart(impact_df, use_container_width=True)
        st.caption("Charts are based on entered values. The annual comparison is not a complete factory cost model and must not be presented as a guaranteed saving.")
    with detail_tab:
        st.subheader("Annual benefit by category")
        df = pd.DataFrame([{"Category":k, f"Annual saving ({d['currency']})":v} for k,v in r["extra"].items()])
        st.dataframe(df, use_container_width=True, hide_index=True, column_config={f"Annual saving ({d['currency']})": st.column_config.NumberColumn(format="%.2f")})
        st.subheader("Key operating figures")
        operating_df = pd.DataFrame([
            {"Metric":"Annual accepted production", "Existing tool":r["annual_n"], "Proposed tool":r["annual_n"]},
            {"Metric":"Insert consumption per year (estimated)", "Existing tool":r["inserts0"], "Proposed tool":r["inserts1"]},
            {"Metric":"Tool-change events per year (estimated)", "Existing tool":r["edge_events0"], "Proposed tool":r["edge_events1"]},
            {"Metric":"Machine hours used for tool changes", "Existing tool":safe_div(r["edge_events0"] * d["assumptions"]["machine_stop_min"],60), "Proposed tool":safe_div(r["edge_events1"] * d["assumptions"]["machine_stop_min"],60)},
        ])
        st.dataframe(operating_df, use_container_width=True, hide_index=True)
    with report_tab:
        st.subheader("Customer-ready report")
        st.write(f"**Customer:** {d['customer']}  ·  **Test date:** {d['test_date']}  ·  **Operation:** {d['operation']}")
        st.write(f"**Existing tool:** {d['old_tool']} — {d['old_insert']}")
        st.write(f"**Proposed tool:** {d['new_tool']} — {d['new_insert']}")
        st.markdown('<div class="karaansaw-note">Before sharing the PDF, confirm that measured edge life, prices, annual production and any supporting-cost assumptions reflect the customer’s actual process.</div>', unsafe_allow_html=True)
        pdf = make_pdf(d, r)
        safe_customer = "".join(ch if ch.isalnum() or ch in "-_" else "_" for ch in d["customer"]).strip("_") or "customer"
        st.download_button(
            "Download customer PDF report",
            data=pdf,
            file_name=f"CPP_CCP_Report_{safe_customer}_{d['test_date']}.pdf",
            mime="application/pdf",
            type="primary",
            use_container_width=True
        )
        payload = {"report_data": {k:(str(v) if isinstance(v,date) else v) for k,v in d.items()}, "results":r}
        st.download_button("Download calculation data (JSON)", data=json.dumps(payload, indent=2, ensure_ascii=False),
                           file_name=f"CPP_CCP_Data_{safe_customer}.json", mime="application/json", use_container_width=True)
else:
    st.info("Complete the form and select **Calculate report** to see the customer-meeting dashboard and generate a PDF.")

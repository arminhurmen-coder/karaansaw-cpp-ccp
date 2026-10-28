from datetime import date
from io import BytesIO
from statistics import mean
from math import isfinite
from xml.sax.saxutils import escape

import pandas as pd
import plotly.express as px
import streamlit as st
from reportlab.lib import colors
from reportlab.lib.pagesizes import A4
from reportlab.lib.styles import getSampleStyleSheet
from reportlab.lib.units import mm
from reportlab.platypus import SimpleDocTemplate, Paragraph, Spacer, Table, TableStyle

st.set_page_config(page_title="Karaansaw CPP / CCP", page_icon="⚙️", layout="wide")
st.title("Karaansaw CPP / CCP Economic Comparison")
st.caption("Compare existing and proposed cutting tools using measured trials and entered cost assumptions.")

with st.expander("Definitions and assumptions"):
    st.markdown("""
    - **CPP** = insert price ÷ (average accepted pieces per edge × usable edges per insert).
    - **Assessed annual cost** = annual tool cost plus the listed supporting-cost categories.
    - Use the same acceptance criteria and stopping rule for both trials.
    - Trial fields start at zero; zero means unused and is ignored. Enter real results for both tools.
    - Cost defaults are illustrative, not universal rates. Validate before presenting savings as confirmed.
    """)

def valid_edges(values):
    result = []
    for item in values:
        try:
            value = float(item)
            if isfinite(value) and value > 0:
                result.append(value)
        except (TypeError, ValueError):
            pass
    return result

def div(n, d):
    return n / d if d > 0 else 0.0

def cash(n, currency):
    return f"{currency} {n:,.2f}"

def make_pdf(meta, m, edge_df, costs_df):
    bio = BytesIO()
    doc = SimpleDocTemplate(bio, pagesize=A4, rightMargin=12*mm, leftMargin=12*mm,
                            topMargin=12*mm, bottomMargin=12*mm)
    styles = getSampleStyleSheet()
    story = [
        Paragraph("Karaansaw CPP / CCP Economic Comparison", styles["Title"]),
        Spacer(1, 4*mm),
        Paragraph(f"<b>Customer:</b> {escape(meta['customer'])} &nbsp; <b>Engineer:</b> {escape(meta['engineer'])} &nbsp; <b>Date:</b> {meta['date']}", styles["Normal"]),
        Paragraph(f"<b>Distributor:</b> {escape(meta['distributor'])} &nbsp; <b>Operation:</b> {escape(meta['operation'])}", styles["Normal"]),
        Paragraph(f"<b>Workpiece:</b> {escape(meta['workpiece'])} &nbsp; <b>Material:</b> {escape(meta['material'])} &nbsp; <b>Machine:</b> {escape(meta['machine'])}", styles["Normal"]),
        Spacer(1, 4*mm),
    ]
    data = [
        ["Metric", "Existing", "Proposed", "Existing − Proposed"],
        ["Tool / brand", meta["old_brand"], meta["new_brand"], ""],
        ["Average pieces / edge", f"{m['avg0']:,.2f}", f"{m['avg1']:,.2f}", f"{m['avg0']-m['avg1']:+,.2f}"],
        ["Pieces / insert", f"{m['life0']:,.2f}", f"{m['life1']:,.2f}", f"{m['life0']-m['life1']:+,.2f}"],
        ["CPP / accepted piece", cash(m["cpp0"],meta["currency"]), cash(m["cpp1"],meta["currency"]), cash(m["cpp0"]-m["cpp1"],meta["currency"])],
        ["Annual tool cost", cash(m["tool0"],meta["currency"]), cash(m["tool1"],meta["currency"]), cash(m["tool0"]-m["tool1"],meta["currency"])],
        ["Annual assessed cost", cash(m["total0"],meta["currency"]), cash(m["total1"],meta["currency"]), cash(m["total0"]-m["total1"],meta["currency"])],
    ]
    table = Table([[escape(str(v)) for v in row] for row in data], colWidths=[53*mm,38*mm,38*mm,43*mm], repeatRows=1)
    table.setStyle(TableStyle([
        ("BACKGROUND",(0,0),(-1,0),colors.HexColor("#1f274b")),("TEXTCOLOR",(0,0),(-1,0),colors.white),
        ("FONTNAME",(0,0),(-1,0),"Helvetica-Bold"),("FONTSIZE",(0,0),(-1,-1),7),
        ("GRID",(0,0),(-1,-1),.35,colors.grey),("VALIGN",(0,0),(-1,-1),"MIDDLE"),
        ("ROWBACKGROUNDS",(0,1),(-1,-1),[colors.white,colors.HexColor("#f3f5f8")])
    ]))
    story += [table, Spacer(1,4*mm), Paragraph("Measured accepted pieces per edge",styles["Heading2"])]
    rows = [["Edge","Existing","Proposed"]]
    for _, r in edge_df.iterrows():
        rows.append([str(int(r["Edge"])), "" if pd.isna(r["Existing"]) else f"{r['Existing']:,.2f}",
                     "" if pd.isna(r["Proposed"]) else f"{r['Proposed']:,.2f}"])
    et = Table(rows, colWidths=[35*mm,60*mm,60*mm], repeatRows=1)
    et.setStyle(TableStyle([("BACKGROUND",(0,0),(-1,0),colors.HexColor("#83ced1")),
                            ("FONTNAME",(0,0),(-1,0),"Helvetica-Bold"),("FONTSIZE",(0,0),(-1,-1),8),
                            ("GRID",(0,0),(-1,-1),.35,colors.grey)]))
    story += [et, Spacer(1,4*mm), Paragraph("Annual supporting-cost breakdown",styles["Heading2"])]
    cr = [["Category","Existing","Proposed","Difference"]]
    for _, r in costs_df.iterrows():
        cr.append([escape(str(r["Category"])),f"{r['Existing']:,.2f}",f"{r['Proposed']:,.2f}",f"{r['Difference']:,.2f}"])
    ct = Table(cr,colWidths=[70*mm,38*mm,38*mm,38*mm],repeatRows=1)
    ct.setStyle(TableStyle([("BACKGROUND",(0,0),(-1,0),colors.HexColor("#1f274b")),
                            ("TEXTCOLOR",(0,0),(-1,0),colors.white),("FONTNAME",(0,0),(-1,0),"Helvetica-Bold"),
                            ("FONTSIZE",(0,0),(-1,-1),7),("GRID",(0,0),(-1,-1),.35,colors.grey)]))
    story += [ct, Spacer(1,4*mm), Paragraph("Assumptions and limitations",styles["Heading2"]),
              Paragraph(f"Monthly accepted output: {meta['monthly']:,.0f}; annualised volume: {meta['monthly']*12:,.0f}.",styles["Normal"]),
              Paragraph("Remarks: "+(escape(meta["remarks"]) if meta["remarks"] else "Not provided."),styles["Normal"]),
              Spacer(1,3*mm),
              Paragraph("This estimate depends on the entered data and assumptions. Validate trial conditions and cost rates before treating savings as verified.",styles["Italic"])]
    doc.build(story)
    return bio.getvalue()

with st.form("cpp_ccp_form"):
    st.header("1. Report identity")
    a,b,c = st.columns(3)
    with a:
        customer = st.text_input("Customer / user name","M AND DALVI ENGINEERING")
        engineer = st.text_input("Engineer name","Narayan")
        distributor = st.text_input("Distributor","CREATOR CUTTING TOOLS")
    with b:
        test_date = st.date_input("Test date",date.today())
        currency = (st.text_input("Currency code","INR").strip().upper() or "INR")
        operation = st.text_input("Operation","OD TURNING")
    with c:
        workpiece = st.text_input("Workpiece name","BEARING")
        material = st.text_input("Material / hardness","FORGE STEEL")
        machine = st.text_input("Machine type","CNC")

    st.header("2. Tool and cutting conditions")
    left,right = st.columns(2)
    with left:
        st.subheader("Existing tool")
        old_brand = st.text_input("Existing tool / brand","WINTECH")
        old_code = st.text_input("Insert code / grade — existing","TNMG 1060412 DQ 1125")
        old_vc = st.number_input("Cutting speed Vc (m/min) — existing",min_value=0.0,value=240.0,step=5.0)
        old_rpm = st.number_input("RPM — existing",min_value=0.0,value=1600.0,step=50.0)
        old_feed = st.number_input("Feed (mm/rev) — existing",min_value=0.0,value=.2400,format="%.4f")
        old_doc = st.number_input("Depth of cut (mm) — existing",min_value=0.0,value=.80,format="%.2f")
        old_coolant = st.selectbox("Coolant — existing",["Wet","Dry","MQL","Other"])
        old_edges_per = st.number_input("Usable edges per insert — existing",min_value=1,max_value=16,value=6)
        old_price = st.number_input("Insert price — existing",min_value=0.0,value=195.0,step=1.0)
    with right:
        st.subheader("Proposed tool")
        new_brand = st.text_input("Proposed tool / brand","WURNHER")
        new_code = st.text_input("Insert code / grade — proposed","TNMG 160412 PM4 CP 2555")
        new_vc = st.number_input("Cutting speed Vc (m/min) — proposed",min_value=0.0,value=240.0,step=5.0)
        new_rpm = st.number_input("RPM — proposed",min_value=0.0,value=1600.0,step=50.0)
        new_feed = st.number_input("Feed (mm/rev) — proposed",min_value=0.0,value=.2400,format="%.4f")
        new_doc = st.number_input("Depth of cut (mm) — proposed",min_value=0.0,value=.80,format="%.2f")
        new_coolant = st.selectbox("Coolant — proposed",["Wet","Dry","MQL","Other"])
        new_edges_per = st.number_input("Usable edges per insert — proposed",min_value=1,max_value=16,value=6)
        new_price = st.number_input("Insert price — proposed",min_value=0.0,value=220.0,step=1.0)

    st.header("3. Trial results — accepted pieces per edge")
    st.caption("Zero means unused. Enter real measured values for at least one edge for BOTH tools.")
    old_trials, new_trials = [], []
    for start in (0,4):
        ec = st.columns(4)
        for off, col in enumerate(ec):
            i = start+off
            with col:
                old_trials.append(st.number_input(f"Edge {i+1} — existing",min_value=0.0,value=0.0,step=1.0,key=f"old_edge_{i}"))
                new_trials.append(st.number_input(f"Edge {i+1} — proposed",min_value=0.0,value=0.0,step=1.0,key=f"new_edge_{i}"))
    monthly = st.number_input("Monthly accepted production volume",min_value=1.0,value=15000.0,step=500.0)

    st.header("4. Supporting-cost assumptions")
    st.caption("Illustrative defaults; replace with customer data where available.")
    x,y,z = st.columns(3)
    with x:
        stop_min = st.number_input("Machine stop per edge change (min)",min_value=0.0,value=5.0,step=.5)
        machine_rate = st.number_input(f"Machine rate ({currency}/hour)",min_value=0.0,value=1200.0,step=50.0)
        operator_min = st.number_input("Operator work per edge change (min)",min_value=0.0,value=5.0,step=.5)
        operator_rate = st.number_input(f"Operator rate ({currency}/hour)",min_value=0.0,value=300.0,step=25.0)
        qc_min = st.number_input("Post-change QC time (min)",min_value=0.0,value=3.0,step=.5)
        qc_rate = st.number_input(f"QC rate ({currency}/hour)",min_value=0.0,value=600.0,step=25.0)
    with y:
        stock_months = st.number_input("Stock coverage (months)",min_value=0.0,value=1.0,step=.5)
        carry_pct = st.number_input("Annual inventory carrying rate (%)",min_value=0.0,value=20.0,step=1.0)
        old_offsets = st.number_input("Existing offsets / 1,000 pieces",min_value=0.0,value=3.0,step=.1)
        new_offsets = st.number_input("Proposed offsets / 1,000 pieces",min_value=0.0,value=2.8,step=.1)
        old_offset_min = st.number_input("Existing minutes per offset",min_value=0.0,value=2.0,step=.5)
        new_offset_min = st.number_input("Proposed minutes per offset",min_value=0.0,value=2.0,step=.5)
        reject_cost = st.number_input(f"Incremental reject cost ({currency}/case)",min_value=0.0,value=200.0,step=10.0)
    with z:
        old_reject = st.number_input("Existing extra rejects per accepted piece (%)",min_value=0.0,value=.5,step=.1)
        new_reject = st.number_input("Proposed extra rejects per accepted piece (%)",min_value=0.0,value=.4,step=.1)
        old_rework = st.number_input("Existing rework cases per accepted piece (%)",min_value=0.0,value=1.0,step=.1)
        new_rework = st.number_input("Proposed rework cases per accepted piece (%)",min_value=0.0,value=.8,step=.1)
        rework_cost = st.number_input(f"Incremental rework cost ({currency}/case)",min_value=0.0,value=80.0,step=5.0)
        old_orders = st.number_input("Existing orders / shipments per year",min_value=0.0,value=12.0,step=1.0)
        new_orders = st.number_input("Proposed orders / shipments per year",min_value=0.0,value=11.0,step=1.0)
        order_cost = st.number_input(f"Cost per order / shipment ({currency})",min_value=0.0,value=150.0,step=10.0)
        old_failures = st.number_input("Existing unexpected failures per year",min_value=0.0,value=2.0,step=.1)
        new_failures = st.number_input("Proposed unexpected failures per year",min_value=0.0,value=1.9,step=.1)
        failure_cost = st.number_input(f"Incremental loss per failure ({currency})",min_value=0.0,value=400.0,step=25.0)
    remarks = st.text_area("Remarks / test limitations")
    submitted = st.form_submit_button("Calculate report",type="primary",use_container_width=True)

if submitted:
    old_vals, new_vals = valid_edges(old_trials), valid_edges(new_trials)
    if not old_vals or not new_vals:
        st.error("Enter at least one measured accepted-piece result greater than zero for BOTH Existing and Proposed tools.")
        st.stop()
    if old_price <= 0 or new_price <= 0:
        st.error("Both insert prices must be greater than zero.")
        st.stop()

    avg0, avg1 = mean(old_vals), mean(new_vals)
    life0, life1 = avg0*old_edges_per, avg1*new_edges_per
    cpp0, cpp1 = div(old_price,life0), div(new_price,life1)
    annual = monthly*12
    tool0, tool1 = cpp0*annual, cpp1*annual
    changes0, changes1 = div(annual,avg0), div(annual,avg1)

    cost_items = [
        ("Machine stop at edge change",changes0*stop_min/60*machine_rate,changes1*stop_min/60*machine_rate),
        ("Operator time at edge change",changes0*operator_min/60*operator_rate,changes1*operator_min/60*operator_rate),
        ("Post-change QC",changes0*qc_min/60*qc_rate,changes1*qc_min/60*qc_rate),
        ("Offset time",annual/1000*old_offsets*old_offset_min/60*machine_rate,annual/1000*new_offsets*new_offset_min/60*machine_rate),
        ("Extra rejects",annual*old_reject/100*reject_cost,annual*new_reject/100*reject_cost),
        ("Rework",annual*old_rework/100*rework_cost,annual*new_rework/100*rework_cost),
        ("Orders / shipments",old_orders*order_cost,new_orders*order_cost),
        ("Unexpected failures",old_failures*failure_cost,new_failures*failure_cost),
        ("Inventory carrying estimate",tool0/12*stock_months*carry_pct/100,tool1/12*stock_months*carry_pct/100),
    ]
    supporting0, supporting1 = sum(v[1] for v in cost_items), sum(v[2] for v in cost_items)
    total0, total1 = tool0+supporting0, tool1+supporting1
    costs_df = pd.DataFrame(cost_items,columns=["Category","Existing","Proposed"])
    costs_df["Difference"] = costs_df["Existing"]-costs_df["Proposed"]
    edge_df = pd.DataFrame({"Edge":range(1,9),
                            "Existing":[v if v>0 else float("nan") for v in old_trials],
                            "Proposed":[v if v>0 else float("nan") for v in new_trials]})

    st.success("Report calculated successfully.")
    st.header("Customer-meeting dashboard")
    st.caption(f"{customer} · {operation} · {test_date.strftime('%d %b %Y')} · {currency}")
    k1,k2,k3,k4 = st.columns(4)
    k1.metric("Existing CPP",cash(cpp0,currency))
    k2.metric("Proposed CPP",cash(cpp1,currency),delta=f"{cash(cpp0-cpp1,currency)} vs existing")
    k3.metric("Annual tool-cost saving",cash(tool0-tool1,currency))
    k4.metric("Annual assessed impact",cash(total0-total1,currency))

    l,r = st.columns(2)
    with l:
        fig = px.bar(pd.DataFrame({"Tool":[old_brand or "Existing",new_brand or "Proposed"],"CPP":[cpp0,cpp1]}),
                     x="Tool",y="CPP",text_auto=".2f",title="Cost per accepted piece (CPP)")
        fig.update_layout(yaxis_title=f"Cost per piece ({currency})",xaxis_title="")
        st.plotly_chart(fig,use_container_width=True)
    with r:
        annual_df = pd.DataFrame({"Tool":[old_brand or "Existing",new_brand or "Proposed"],
                                  "Tool consumption":[tool0,tool1],
                                  "Supporting costs entered":[supporting0,supporting1]})
        annual_df = annual_df.melt(id_vars="Tool",var_name="Cost category",value_name="Annual cost")
        fig2 = px.bar(annual_df,x="Tool",y="Annual cost",color="Cost category",barmode="stack",title="Annual assessed cost")
        fig2.update_layout(yaxis_title=f"Annual cost ({currency})",xaxis_title="")
        st.plotly_chart(fig2,use_container_width=True)

    st.subheader("Measured trial results")
    st.dataframe(edge_df,use_container_width=True,hide_index=True)
    edge_plot = edge_df.melt(id_vars="Edge",var_name="Tool",value_name="Accepted pieces").dropna()
    st.plotly_chart(px.line(edge_plot,x="Edge",y="Accepted pieces",color="Tool",markers=True,title="Accepted pieces per edge"),use_container_width=True)
    st.subheader("Annual supporting-cost breakdown")
    st.dataframe(costs_df.style.format({"Existing":"{:,.2f}","Proposed":"{:,.2f}","Difference":"{:,.2f}"}),use_container_width=True,hide_index=True)

    indicators = pd.DataFrame([
        ["Average accepted pieces per edge",avg0,avg1],
        ["Accepted pieces per insert",life0,life1],
        ["Estimated edge changes per year",changes0,changes1],
        ["Annual tool consumption cost",tool0,tool1],
        ["Annual supporting costs entered",supporting0,supporting1],
        ["Annual assessed cost",total0,total1],
    ],columns=["Metric","Existing","Proposed"])
    st.subheader("Key operating indicators")
    st.dataframe(indicators.style.format({"Existing":"{:,.2f}","Proposed":"{:,.2f}"}),use_container_width=True,hide_index=True)
    st.info("Positive savings mean Existing costs are higher than Proposed. The assessed total only includes listed assumptions; validate them before treating savings as confirmed cash savings.")

    meta = {"customer":customer,"engineer":engineer,"distributor":distributor,"date":test_date.isoformat(),
            "currency":currency,"operation":operation,"workpiece":workpiece,"material":material,"machine":machine,
            "old_brand":old_brand,"new_brand":new_brand,"monthly":monthly,"remarks":remarks}
    metrics = {"avg0":avg0,"avg1":avg1,"life0":life0,"life1":life1,"cpp0":cpp0,"cpp1":cpp1,
               "tool0":tool0,"tool1":tool1,"total0":total0,"total1":total1}
    st.download_button("Download customer report (PDF)",data=make_pdf(meta,metrics,edge_df,costs_df),
                       file_name=f"CPP_CCP_Report_{test_date.isoformat()}.pdf",mime="application/pdf",
                       use_container_width=True)
    st.download_button("Download supporting-cost breakdown (CSV)",data=costs_df.to_csv(index=False).encode("utf-8-sig"),
                       file_name=f"CPP_CCP_Breakdown_{test_date.isoformat()}.csv",mime="text/csv",
                       use_container_width=True)
else:
    st.info("Fill in the form and click Calculate report. Real measured edge results are required for both tools.")

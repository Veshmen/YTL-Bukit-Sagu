"""YTL Bukit Sagu CCUS screening dashboard for Streamlit Community Cloud."""
import base64
import csv
from dataclasses import replace
from html import escape
from io import StringIO
from pathlib import Path

import pandas as pd
import plotly.graph_objects as go
import streamlit as st

from model import Inputs, TECH, compare, dashboard_summary, evaluate, right_sized_fraction, search_designs

ROOT = Path(__file__).resolve().parent
BASE = Inputs()
DEFAULT_TECH = "Solid adsorption"
TEAL = "#087f72"
INK = "#183045"
SIDEBAR_DEFAULTS = {
    "technology": DEFAULT_TECH,
    "efficiency": round(100 * TECH[DEFAULT_TECH]["eta"]),
    "carbon_price": int(BASE.carbon_price_usd_per_net_t),
    "aggregate_price": int(BASE.aggregate_price_usd_per_t),
    "utility_multiplier": BASE.utility_price_multiplier,
}
OBJECTIVES = {
    "Maximize integrated NPV": "Max NPV",
    "Maximize net CO₂e avoided": "Max net CO2e avoided",
    "Minimize abatement cost": "Min cost per net tonne avoided",
}
SENSITIVITIES = {
    "Carbon price": ("carbon_price_usd_per_net_t", 0, 100, "Carbon price (USD/net tCO₂e)", "USD"),
    "Aggregate sale price": ("aggregate_price_usd_per_t", 0, 50, "Aggregate sale price (USD/t)", "USD"),
    "Utility price multiplier": ("utility_price_multiplier", 0.5, 2, "Utility price multiplier", "×"),
    "Capture efficiency": ("capture_efficiency_override", 0.65, 0.95, "Capture efficiency (%)", "%"),
    "Saleable aggregate fraction": ("saleable_fraction", 0, 1, "Saleable aggregate (%)", "%"),
}

st.set_page_config(
    page_title="YTL Bukit Sagu | CCUS Decision Tool",
    page_icon="🏭",
    layout="wide",
    initial_sidebar_state="expanded",
)


def cash(value, digits=0, millions=False):
    if value is None:
        return "—"
    amount = abs(value) / 1e6 if millions else abs(value)
    return f"{'−' if value < 0 else ''}${amount:,.{digits}f}{'M' if millions else ''}"


def annual(value, unit="tCO₂/yr", digits=0):
    return f"{value:,.{digits}f} {unit}"


def money_tone(value):
    return "adverse" if value < 0 else "favorable"


def scenario_controls():
    def reset_scenario():
        st.session_state.update(SIDEBAR_DEFAULTS)

    def load_technology_efficiency():
        selected = st.session_state.technology
        st.session_state.efficiency = round(100 * TECH[selected]["eta"])

    for key, value in SIDEBAR_DEFAULTS.items():
        if key not in st.session_state:
            st.session_state[key] = value

    with st.sidebar:
        st.html(
            '<div class="course-brand"><span class="brand-mark">USM</span>'
            '<span><strong>EKC 503</strong><small>Group 2 · CCUS Project</small></span></div>'
        )
        title, reset = st.columns([3, 1.3], vertical_alignment="center")
        title.markdown("**Scenario inputs**")
        reset.button("Reset", on_click=reset_scenario)
        technology = st.selectbox("Capture technology", tuple(TECH), key="technology", on_change=load_technology_efficiency)
        efficiency = st.slider("Capture efficiency (%)", 65, 95, step=1, key="efficiency")
        carbon = st.slider("Carbon price (USD/net tCO₂e)", 0, 100, step=1, key="carbon_price")
        aggregate = st.slider("Aggregate sale price (USD/t)", 0, 50, step=1, key="aggregate_price")
        utility = st.slider("Utility price multiplier", .50, 2.00, step=.05, format="%.2f×", key="utility_multiplier")
        st.caption("The dashboard recalculates when you change a scenario input.")
    return technology, replace(
        BASE,
        capture_efficiency_override=efficiency / 100,
        carbon_price_usd_per_net_t=carbon,
        aggregate_price_usd_per_t=aggregate,
        utility_price_multiplier=utility,
    )


def scenario_csv(x, cases):
    r = cases["integrated"]
    output = StringIO()
    csv.writer(output).writerows([
        ("Parameter", "Value", "Unit"),
        ("Data status", "Illustrative EKC 503 screening case", ""),
        ("Technology", r["technology"], ""),
        ("Capture efficiency", r["efficiency"] * 100, "%"),
        ("Flue gas treated (integrated)", r["treated_fraction"] * 100, "%"),
        ("Carbon price", x.carbon_price_usd_per_net_t, "USD/net tCO2e"),
        ("Aggregate sale price", x.aggregate_price_usd_per_t, "USD/t sold"),
        ("Utility multiplier", x.utility_price_multiplier, "times base"),
        ("Concrete injection NPV", cases["injection"]["npv_usd"], "USD"),
        ("Slag mineralization NPV", cases["slag"]["npv_usd"], "USD"),
        ("Integrated NPV", r["npv_usd"], "USD"),
        ("Captured CO2", r["captured_t"], "tCO2/year"),
        ("Injected CO2", r["injected_t"], "tCO2/year"),
        ("Concrete fixed CO2", r["ready_fixed_t"], "tCO2/year"),
        ("Slag fixed CO2", r["slag_fixed_t"], "tCO2/year"),
        ("Vented surplus capture", r["vented_t"], "tCO2/year"),
        ("Net CO2e avoided", r["net_avoided_t"], "tCO2e/year"),
        ("Abatement cost before carbon", r["abatement_cost_usd_per_net_t"], "USD/net tCO2e"),
        ("Break-even carbon price", r["break_even_carbon_usd_per_t"], "USD/net tCO2e"),
    ])
    return output.getvalue()


def header(x, cases):
    name, export = st.columns([4, 1.55], vertical_alignment="center")
    name.html('<div class="masthead">YTL Bukit Sagu</div>')
    export.download_button(
        "Download scenario CSV", scenario_csv(x, cases),
        file_name="YTL_Bukit_Sagu_CCUS_Scenario.csv", mime="text/csv", on_click="ignore",
    )
    artwork = base64.b64encode((ROOT / "title_banner.jpg").read_bytes()).decode("ascii")
    st.html(f"""
        <section class="hero" style="--plant-image:url(data:image/jpeg;base64,{artwork})">
          <div class="hero-art" aria-hidden="true"></div>
          <div>
            <p class="eyebrow">Cement decarbonization case study</p>
            <h1>CCUS Decision &amp;<br>Optimization Tool</h1>
            <p class="subtitle">Evaluate capture sizing, CO₂ utilization and project economics.</p>
          </div>
        </section>
        <p class="screening-notice"><strong>Illustrative data</strong>
          <span>Academic screening based on the Week 5–7 submissions. Engineering inputs and revenues require validation.</span>
        </p>
    """)


def kpi(container, title, value, unit="", note="", physical=False, tone=""):
    container.html(f"""
        <article class="kpi-card {'physical' if physical else ''}">
          <h3>{escape(title)}</h3>
          <strong class="kpi-value {tone}">{escape(value)}</strong>
          <span class="kpi-unit">{escape(unit)}</span>
          <p class="kpi-note">{escape(note)}</p>
        </article>
    """)


def show_table(headings, rows, selected=None, style=""):
    head = "".join(f'<th scope="col">{escape(label)}</th>' for label in headings)
    body = []
    for index, row in enumerate(rows):
        first, *rest = row
        cells = "".join(f"<td>{escape(str(value))}</td>" for value in rest)
        body.append(f'<tr class="{"current" if index == selected else ""}"><th scope="row">{escape(str(first))}</th>{cells}</tr>')
    st.html(
        f'<div class="table-scroll" tabindex="0" role="region" aria-label="{escape(headings[0])} table">'
        f'<table class="model-table {style}"><thead><tr>{head}</tr></thead><tbody>{"".join(body)}</tbody></table></div>'
    )


def overview(x, name, cases):
    integrated = cases["integrated"]
    st.subheader("Scenario results")
    st.caption(f"{name} · {integrated['treated_fraction']:.2%} of flue gas treated · Three investment cases and their integrated CO₂ outcomes.")
    financial = (
        ("Concrete injection NPV", cases["injection"], "Incremental ready-mix project"),
        ("Slag mineralization NPV", cases["slag"], "Stand-alone capture and slag project"),
        ("Integrated project NPV", integrated, f"Capture, concrete and slag · {x.life_years} years"),
    )
    for col, (label, case, note) in zip(st.columns(3), financial):
        value = case["npv_usd"]
        kpi(col, label, cash(value, 2, millions=True), "USD", note, tone=money_tone(value))
    physical = (
        ("CO₂ injected into concrete", f"{integrated['injected_t']:,.1f}", "tCO₂/yr", f"{integrated['ready_fixed_t']:,.1f} tCO₂/yr fixed"),
        ("CO₂ mineralized in slag", f"{integrated['slag_fixed_t']:,.0f}", "tCO₂/yr", "Permanent fixation assumed"),
        ("Integrated net CO₂e avoided", f"{integrated['net_avoided_t']:,.0f}", "tCO₂e/yr", "After modeled emissions penalties"),
    )
    for col, args in zip(st.columns(3), physical):
        kpi(col, *args, physical=True)

    st.subheader("Capture technology comparison")
    st.caption(f"Four integrated designs at the same {integrated['efficiency']:.0%} capture efficiency. The active right-sized design is highlighted.")
    full_mea, matched_mea, full_solid, matched_solid = compare(x)
    alternatives = (matched_mea, full_mea, matched_solid, full_solid)
    designs = ("Right-sized", "Full flue gas", "Right-sized", "Full flue gas")
    active = 0 if name == matched_mea["technology"] else 2
    show_table(
        ("Technology", "Design", "Flue gas treated", "Capture (tCO₂/yr)", "Net avoided (tCO₂e/yr)", "NPV (USD)", "LCOC (USD/tCO₂)"),
        [(r["technology"], design, f"{r['treated_fraction']:.2%}", f"{r['captured_t']:,.0f}",
          f"{r['net_avoided_t']:,.0f}", cash(r["npv_usd"], 2, millions=True), cash(r["lcoc_usd_per_captured_t"], 2))
         for r, design in zip(alternatives, designs)],
        selected=active, style="compare-table",
    )
    full = alternatives[active + 1]
    improvement = integrated["npv_usd"] - full["npv_usd"]
    change = "raises" if improvement >= 0 else "lowers"
    st.caption(
        f"For {name.lower()}, right-sizing reduces surplus captured CO₂ by "
        f"{annual(full['vented_t'] - integrated['vented_t'])} and {change} modeled NPV by {cash(abs(improvement), 2, millions=True)}."
    )


def balance_rows(items):
    lines = [
        f'<div class="balance-line {"final" if i == len(items) - 1 else ""}">'
        f"<dt>{escape(label)}</dt><dd>{escape(value)}</dd></div>"
        for i, (label, value) in enumerate(items)
    ]
    st.html(f'<dl class="balance-table">{"".join(lines)}</dl>')


def carbon_and_finance(x, cases):
    r = cases["integrated"]
    st.subheader("Carbon & financial balance")
    st.caption("Integrated capture and utilization at the selected technology’s demand-matched size.")
    carbon, finance = st.columns(2)
    with carbon:
        st.markdown("#### Annual carbon balance")
        chart = go.Figure(go.Bar(
            x=[r["captured_t"], r["permanently_fixed_t"], r["net_avoided_t"]],
            y=["Captured CO₂", "Permanently fixed CO₂", "Net CO₂e avoided"],
            marker_color=["#406883", "#268991", TEAL], orientation="h",
            customdata=["tCO₂/yr", "tCO₂/yr", "tCO₂e/yr"],
            hovertemplate="%{y}: %{x:,.0f} %{customdata}<extra></extra>",
        ))
        chart.update_layout(height=195, margin=dict(l=6, r=10, t=6, b=27), font_color=INK)
        chart.update_yaxes(autorange="reversed", automargin=True)
        chart.update_xaxes(tickformat="~s", title_text="Tonnes per year")
        st.plotly_chart(chart, width="stretch", config={"displayModeBar": False})
        balance_rows([
            ("Modeled Scope 1 baseline", annual(x.baseline_tco2)),
            ("Injected into concrete", annual(r["injected_t"], digits=1)),
            ("Fixed in concrete", annual(r["ready_fixed_t"], digits=1)),
            ("Injected CO₂ released", annual(r["injected_t"] - r["ready_fixed_t"], digits=1)),
            ("Fixed in slag", annual(r["slag_fixed_t"])),
            ("Surplus capture vented", annual(r["vented_t"])),
            ("Site CO₂ remaining unretained", annual(r["unretained_site_t"])),
            ("Avoided cement production", annual(r["avoided_cement_t"], "tCO₂e/yr")),
            ("Capture heat emissions", annual(r["emissions_heat_t"], "tCO₂e/yr")),
            ("Total electricity emissions", annual(r["emissions_electric_t"], "tCO₂e/yr")),
            ("Slag transport emissions", annual(r["emissions_logistics_t"], "tCO₂e/yr")),
            ("Net CO₂e avoided", annual(r["net_avoided_t"], "tCO₂e/yr")),
        ])
    with finance:
        st.markdown("#### Integrated economics")
        balance_rows([
            ("Upfront CAPEX", cash(r["capex_usd"])),
            ("Total operating cost / year", cash(r["annual_opex_usd"])),
            ("Aggregate sales / year", cash(r["aggregate_revenue_usd"])),
            ("Cement savings / year", cash(r["cement_savings_usd"])),
            ("Illustrative carbon revenue / year", cash(r["carbon_scenario_revenue_usd"])),
            ("Net cash flow / year", cash(r["annual_net_usd"])),
            ("LCOC (USD/tCO₂ captured)", cash(r["lcoc_usd_per_captured_t"], 2)),
            ("Abatement cost before carbon (USD/net tCO₂e)", cash(r["abatement_cost_usd_per_net_t"], 2)),
            ("Break-even carbon price (USD/net tCO₂e)", cash(r["break_even_carbon_usd_per_t"], 2)),
            ("Integrated NPV", cash(r["npv_usd"], 2, millions=True)),
        ])
    with st.expander("How the three NPV cases differ"):
        st.markdown("""
- **Concrete injection** covers incremental injection equipment. CO₂ capture is charged at the full-scale reference levelized capture cost for each injected tonne.
- **Slag mineralization** covers a right-sized capture plant serving the slag pathway and the slag facility itself.
- **Integrated project** covers a shared right-sized capture plant, the concrete injection retrofit and the slag facility.

Each NPV measures a distinct investment. Adding the two pathway NPVs would mix different capture-cost allocations.
""")


def sensitivity(x, name):
    st.subheader("One-way sensitivity")
    st.caption("Recalculate the right-sized integrated project while varying one input at a time.")
    variable = st.selectbox("Sensitivity variable", tuple(SENSITIVITIES))
    field, low, high, axis, unit = SENSITIVITIES[variable]
    current = getattr(x, field)
    sweep = sorted({current, *(round(low + (high - low) * i / 20, 6) for i in range(21))})
    results = []
    for value in sweep:
        scenario = replace(x, **{field: value})
        results.append(evaluate(scenario, name, right_sized_fraction(scenario, name)))

    x_values = [s * 100 if unit == "%" else s for s in sweep]
    current_index = sweep.index(current)
    npv = [r["npv_usd"] / 1e6 for r in results]
    chart = go.Figure()
    chart.add_scatter(x=x_values, y=npv, mode="lines", line=dict(color=TEAL, width=3), name="Integrated NPV",
                      hovertemplate="%{x:.3~f}<br>NPV: USD %{y:,.2f}M<extra></extra>")
    chart.add_scatter(x=[x_values[current_index]], y=[npv[current_index]], mode="markers", name="Current scenario",
                      marker=dict(size=11, color="white", line=dict(color=TEAL, width=3)),
                      hovertemplate="Current: %{x:.3~f}<br>NPV: USD %{y:,.2f}M<extra></extra>")
    chart.add_hline(y=0, line_color="#92a6b1", line_width=1)
    chart.update_layout(
        title="Integrated project NPV",
        xaxis_title=axis, yaxis_title="USD millions", height=374,
        margin=dict(l=30, r=24, t=52, b=39), showlegend=False, font_color=INK,
    )
    if unit in {"%", "×"}:
        chart.update_xaxes(ticksuffix=unit)
    st.plotly_chart(chart, width="stretch", config={"displaylogo": False, "scrollZoom": False})
    formatted = f"{current:.0%}" if unit == "%" else f"{current:.2f}×" if unit == "×" else cash(current)
    st.caption(f"Current scenario · {name} · {formatted} · {cash(results[current_index]['npv_usd'], 2, millions=True)} NPV")
    with st.expander("View sensitivity values"):
        st.dataframe(
            pd.DataFrame({
                axis: x_values, "Flue gas treated (%)": [r["treated_fraction"] * 100 for r in results],
                "Net avoided (tCO₂e/yr)": [r["net_avoided_t"] for r in results],
                "NPV (USD)": [r["npv_usd"] for r in results],
            }),
            hide_index=True,
            width="stretch",
            column_config={
                "Flue gas treated (%)": st.column_config.NumberColumn(format="%.2f"),
                "Net avoided (tCO₂e/yr)": st.column_config.NumberColumn(format="%,.0f"),
                "NPV (USD)": st.column_config.NumberColumn(format="dollar"),
            },
        )


def optimization(x):
    st.subheader("Design optimization")
    st.caption("Search both technologies and eligible treatment sizes using the current scenario inputs.")
    control, results = st.columns([.85, 1.15])
    with control:
        with st.form("design-search"):
            st.markdown("#### Objective & constraints")
            objective = st.selectbox("Objective", tuple(OBJECTIVES))
            cap = st.number_input("Maximum flue gas treated (%)", min_value=.1, max_value=100., value=100., step=.1, format="%.1f")
            minimum = st.number_input("Minimum net CO₂e avoided (t/year)", min_value=0, value=0, step=1)
            nonnegative = st.checkbox("Require non-negative NPV")
            submitted = st.form_submit_button("Run optimization", type="primary")
    if submitted:
        st.session_state.search_options = (OBJECTIVES[objective], nonnegative, cap / 100, minimum)
    options = st.session_state.get("search_options", ("Max NPV", False, 1., 0))
    search = search_designs(x, *options)
    with results:
        status = f"{search.feasible:,} of {search.tested:,} candidates meet the applied constraints."
        r = search.best
        if r is None:
            st.warning(f"No feasible candidate. {status} Adjust the constraints or scenario assumptions to search again.")
        else:
            st.markdown("#### Best modeled candidate")
            st.markdown(f"**{r['technology']}**")
            st.caption(f"{r['efficiency']:.0%} capture efficiency · {status}")
            a, b = st.columns(2)
            kpi(a, "Flue gas treated", f"{r['treated_fraction']:.2%}")
            kpi(b, "Integrated NPV", cash(r["npv_usd"], 2, millions=True), "USD", tone=money_tone(r["npv_usd"]))
            a, b = st.columns(2)
            kpi(a, "Net CO₂e avoided", f"{r['net_avoided_t']:,.0f}", "tCO₂e/yr", physical=True)
            kpi(b, "Abatement cost", cash(r["abatement_cost_usd_per_net_t"], 2), "USD/net tCO₂e", physical=True)
            if r["npv_usd"] < 0:
                st.caption("The best feasible candidate has negative NPV under these assumptions.")
        applied_objective, financial_screen, applied_cap, applied_minimum = options
        objective_label = next(label for label, key in OBJECTIVES.items() if key == applied_objective)
        financial_label = " · non-negative NPV required" if financial_screen else ""
        st.caption(f"Applied · {objective_label} · ≤ {applied_cap:.1%} treated · ≥ {applied_minimum:,} tCO₂e/yr{financial_label}")
    st.caption(
        "Both technologies use the sidebar capture efficiency. The search tests 0.5 percentage point increments, "
        "each exact demand match within the limit, and the upper limit. Eligible designs deliver positive net avoidance. "
        "Abatement cost excludes carbon revenue."
    )


def assumptions():
    st.subheader("Model assumptions")
    st.caption("Inputs, methods and evidence gaps for the academic screening case.")
    project = [
        ("Annual Scope 1 CO₂", annual(BASE.baseline_tco2, digits=1), "Week 5"),
        ("Project life / discount rate", f"{BASE.life_years} years / {BASE.discount_rate:.0%}", "Week 5–7 model"),
        ("Capture CAPEX scaling exponent", f"{BASE.capex_exponent:.2f}", "Week 5–7 model"),
        ("Grid / heat emissions factors", f"{BASE.grid_factor_t_per_mwh:g} tCO₂e/MWh / {BASE.heat_factor_t_per_gj:g} tCO₂e/GJ", "Week 5–7 model"),
        ("Capture electricity / heat prices", f"{BASE.capture_electric_price_usd_per_mwh:g} USD/MWh / {BASE.capture_heat_price_usd_per_gj:g} USD/GJ", "Week 5–7 model"),
        ("Default carbon price", f"{BASE.carbon_price_usd_per_net_t:g} USD/net tCO₂e avoided", "Illustrative scenario"),
    ]
    technologies = []
    for name, ref in TECH.items():
        technologies.extend([
            (f"{name} · default efficiency", f"{ref['eta']:.0%}", "Week 5"),
            (f"{name} · heat / electricity", f"{ref['heat']:.2f} / {ref['elec_gj']:.3f} GJ/tCO₂ captured", "Week 5"),
            (f"{name} · reference scale", annual(ref["reference_t"]), "Week 5"),
            (f"{name} · reference CAPEX / annual OPEX", f"{cash(ref['capex'], 2, True)} / {cash(ref['opex'], 2, True)} USD", "Week 5"),
        ])
    concrete = [
        ("Concrete throughput", f"{BASE.concrete_m3_per_year:,.0f} m³/yr", "Week 6"),
        ("Injection / fixed CO₂", f"{BASE.inject_kg_per_m3:g} / {BASE.fixed_kg_per_m3:g} kgCO₂/m³", "Week 6"),
        ("Cement displaced / value", f"{BASE.cement_saved_kg_per_m3:g} kg/m³ / {BASE.cement_usd_per_t:g} USD/t", "Week 6"),
        ("Cement emissions factor", f"{BASE.cement_avoided_tco2e_per_t:g} tCO₂e/t cement", "Week 6"),
        ("Injection power use / price", f"{BASE.injection_kwh_per_kg:g} kWh/kgCO₂ / {BASE.injection_electric_price_usd_per_kwh:.5f} USD/kWh", "Week 6"),
        ("Injection CAPEX / fixed annual OPEX", f"{BASE.injection_capex_usd:,.0f} / {BASE.injection_fixed_opex_usd:,.0f} USD", "Week 6"),
    ]
    slag = [
        ("Slag supply / CO₂ uptake", f"{BASE.slag_supply_t_per_year:,.0f} t/yr / {BASE.slag_uptake_tco2_per_t:.2f} tCO₂/t slag", "Week 7"),
        ("Sale price / saleable share", f"{BASE.aggregate_price_usd_per_t:g} USD/t / {BASE.saleable_fraction:.0%}", "Week 7"),
        ("Purchase / processing / logistics", f"{BASE.slag_purchase_usd_per_t:g} / {BASE.slag_processing_usd_per_t:g} / {BASE.slag_logistics_usd_per_t:g} USD/t slag", "Week 7"),
        ("Carbonation electricity", f"{BASE.slag_kwh_per_tco2:g} kWh/tCO₂ fixed in slag", "Week 7"),
        ("Transport emissions", f"{BASE.slag_logistics_tco2e_per_t:g} tCO₂e/t slag", "Week 7"),
        ("Slag CAPEX / fixed annual OPEX", f"{BASE.slag_capex_usd:,.0f} / {BASE.slag_fixed_opex_usd:,.0f} USD", "Week 7"),
    ]
    for label, rows in (("Project and utilities", project), ("Capture technologies", technologies),
                        ("Ready-mix concrete", concrete), ("Steel slag and aggregate", slag)):
        with st.expander(label, expanded=label == "Project and utilities"):
            show_table(("Parameter", "Base assumption", "Source"), rows, style="compare-table")

    methods, evidence = st.columns(2)
    with methods:
        st.markdown("""
#### Calculation methods

- **Capture sizing.** Multiply annual Scope 1 CO₂ by the treated flue-gas fraction and capture efficiency. To right-size, divide combined concrete and slag demand by full-stream capture capacity, capped at 100%.
- **CO₂ allocation.** Supply the concrete injection line first. Route remaining captured CO₂ to slag within its modeled supply and uptake limit. Surplus capture is modeled as vented.
- **Net CO₂e avoided.** Add permanent fixation and avoided cement production emissions. Subtract heat, electricity and slag transport emissions.
- **Economics.** Scale capture CAPEX by the throughput ratio raised to 0.60 and reference operating cost linearly. Discount flat annual cash flows over 25 years and deduct upfront CAPEX. Break-even carbon price covers annualized costs after non-carbon benefits when net avoidance is positive.
""")
    with evidence:
        st.markdown("""
#### Evidence & limitations

- **Week 5.** Scope 1 baseline, capture-cost and energy benchmarks, and utility emissions factors.
- **Week 6.** Ready-mix throughput, dose, retention and cement displacement.
- **Week 7.** Slag mineralization, aggregate economics, and full versus right-sized results. See the workbook tabs **05 Pathway Inputs**, **06 Combined Results** and **07 Sensitivity BE**.

Validate slag sourcing, sustained uptake, product quality, market demand, utility costs and emissions factors with facility data. The 100% saleable fraction and carbon revenue are illustrative. Verify credit eligibility, permanence and accounting before treating carbon revenue as realizable.
""")
        with st.expander("Technical references from the Week 7 workbook"):
            st.markdown("""
- [Steel-slag carbonation aggregate experiments](https://www.sciencedirect.com/science/article/pii/S2212982016303006) · laboratory uptake benchmark
- [RSC techno-economic analysis](https://doi.org/10.1039/d5su00924c) · illustrative aggregate price
- [Review of steel-slag carbonation](https://doi.org/10.3389/fchem.2020.571504) · electricity intensity range
- [Malaysian EAF slag carbonation study](https://pmc.ncbi.nlm.nih.gov/articles/PMC6812231/) · local technical context
""")


def main():
    st.html(ROOT / "style.css")
    selected_technology, inputs = scenario_controls()
    cases = dashboard_summary(inputs, selected_technology)
    header(inputs, cases)
    overview_tab, balance_tab, sensitivity_tab, optimize_tab, assumptions_tab = st.tabs(
        ["Overview", "Carbon & finance", "Sensitivity", "Optimization", "Assumptions"],
    )
    with overview_tab:
        overview(inputs, selected_technology, cases)
    with balance_tab:
        carbon_and_finance(inputs, cases)
    with sensitivity_tab:
        sensitivity(inputs, selected_technology)
    with optimize_tab:
        optimization(inputs)
    with assumptions_tab:
        assumptions()
    st.html('<footer class="dashboard-footer">Universiti Sains Malaysia · EKC 503 · Group 2</footer>')


if __name__ == "__main__":
    main()

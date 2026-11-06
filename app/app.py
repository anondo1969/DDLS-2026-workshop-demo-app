"""Public educational Streamlit dashboard; no patient-level data or tracking."""

import streamlit as st

from charts import build_comparison_chart, build_trend_chart
from data import (
    CSV_NAME,
    DATA_PATH,
    DataValidationError,
    comparison_for_year,
    filter_trends,
    load_data,
    summarize_area,
)


st.set_page_config(
    page_title="ADHD treatment in Sweden | Explore the data",
    page_icon=":bar_chart:",
    layout="wide",
    initial_sidebar_state="expanded",
)

st.markdown(
    """
    <style>
      .stApp { background: #f7f9fc; color: #1d354e; }
      .block-container { max-width: 1260px; padding-top: 1.6rem; padding-bottom: 3rem; }
      [data-testid="stSidebar"] { background: #eef3f8; border-right: 1px solid #dbe4ed; }
      .hero {
        background: linear-gradient(112deg, #174d76 0%, #147d86 100%);
        color: #fff; border-radius: 18px; padding: 28px 32px 25px;
        margin-bottom: 20px; box-shadow: 0 8px 23px rgba(20, 61, 96, 0.10);
      }
      .hero .eyebrow { font-size: 0.75rem; letter-spacing: .16em; text-transform: uppercase;
        font-weight: 700; color: #cdeef1; margin-bottom: 10px; }
      .hero h1 { color: white; font-size: clamp(1.65rem, 3vw, 2.65rem);
        line-height: 1.12; font-weight: 740; margin: 0 0 14px; }
      .hero p { color: #f0f9ff; font-size: .98rem; max-width: 810px; margin: 0; }
      .section-note { color: #526779; font-size: .92rem; margin: -8px 0 10px; }
      div[data-testid="stMetric"] { background: #fff; border: 1px solid #dce6ef;
        border-radius: 13px; padding: 15px 18px; min-height: 110px; }
      div[data-testid="stMetricLabel"] { color: #516777; }
      div[data-testid="stMetricValue"] { color: #173f63; }
      [data-testid="stPlotlyChart"] { background: #fff; border-radius: 14px;
        border: 1px solid #dce6ef; padding: 7px; }
      hr { border-color: #dce6ef; }
      a { color: #0b6c81; }
    </style>
    """,
    unsafe_allow_html=True,
)

st.markdown(
    """
    <div class="hero">
      <div class="eyebrow">DDLS workshop / Public research dashboard</div>
      <h1>ADHD treatment in Sweden: explore the data</h1>
      <p>Explore annual rates of children and young people aged 0-17 receiving
      ADHD medication treatment. The measure is expressed as
      <strong>treated children and young people per 1,000 inhabitants</strong>,
      not a percentage of people diagnosed with ADHD.</p>
    </div>
    """,
    unsafe_allow_html=True,
)


@st.cache_data(show_spinner=False)
def cached_data():
    return load_data(DATA_PATH)


try:
    df = cached_data()
except DataValidationError as exc:
    st.error("The supplied CSV is missing or failed validation. No replacement data were loaded.")
    for issue in exc.issues:
        st.write("- " + issue)
    st.info(f"Place the original CSV at `data/{CSV_NAME}` in the project root, and restart the app.")
    st.stop()

region_names = sorted(df.loc[df["area_type"] == "Region", "area"].unique().tolist())
all_areas = ["Riket", *region_names]
years = sorted(df["year"].unique().tolist())

with st.sidebar:
    st.subheader("Explore the indicator")
    st.caption("Choose areas for the trend and a separate year for the regional comparison.")
    selected_areas = st.multiselect(
        "Areas in the trend",
        options=all_areas,
        default=["Riket"],
        help="Select one or more areas; Riket is the source-supplied national rate.",
    )
    year_range = st.slider(
        "Trend year range",
        min_value=min(years),
        max_value=max(years),
        value=(min(years), max(years)),
        step=1,
    )
    comparison_year = st.select_slider(
        "Regional comparison year",
        options=years,
        value=max(years),
        help="Independent of the trend year-range filter; always compares all 21 regions.",
    )
    if selected_areas:
        focus_area = (
            selected_areas[0]
            if len(selected_areas) == 1
            else st.selectbox("Area for summary metrics", selected_areas)
        )
    st.divider()
    st.caption("2012-2025 | 22 areas | Aggregate observations only")
    st.markdown("[Original indicator (Vården i siffror)](https://vardenisiffror.se/sv/indikatorer/adhd-behandling-bland-barn-och-unga)")

if not selected_areas:
    st.warning("Select at least one area in the sidebar to view the trends and filtered data.")
    st.stop()

filtered = filter_trends(df, selected_areas, year_range)
summary = summarize_area(filtered, focus_area)
regions, national_rate = comparison_for_year(df, comparison_year)

st.subheader(f"At a glance: {summary.area}")
st.caption("ADHD medication treatment, ages 0-17; rates are per 1,000 inhabitants.")
metric1, metric2, metric3 = st.columns(3)
with metric1:
    st.metric(f"Latest rate ({summary.latest_year})", f"{summary.latest_rate:.2f} per 1,000")
with metric2:
    st.metric(f"Starting rate ({summary.first_year})", f"{summary.first_rate:.2f} per 1,000")
with metric3:
    st.metric(
        f"Absolute change ({summary.first_year}-{summary.latest_year})",
        f"{summary.absolute_change:+.2f} per 1,000",
    )
st.caption("The difference is an absolute rate change per 1,000 inhabitants, not a percentage or a patient count. Increases or decreases do not imply better or worse care.")

st.divider()
st.subheader("ADHD medication treatment rates over time")
st.markdown(
    '<p class="section-note">Annual rate for the selected areas and years. '
    'Use the legend to show or hide lines and hover over points for exact values.</p>',
    unsafe_allow_html=True,
)
st.plotly_chart(
    build_trend_chart(filtered),
    use_container_width=True,
    config={"displaylogo": False, "modeBarButtonsToRemove": ["lasso2d", "select2d"]},
)

st.subheader(f"ADHD medication treatment by region / {comparison_year}")
st.markdown(
    '<p class="section-note">All 21 regions, ordered by rate (highest at top). '
    'The dashed line is the actual Riket value supplied in the CSV, not '
    'an unweighted average of regions.</p>',
    unsafe_allow_html=True,
)
st.plotly_chart(
    build_comparison_chart(regions, national_rate),
    use_container_width=True,
    config={"displaylogo": False, "modeBarButtonsToRemove": ["lasso2d", "select2d"]},
)

st.divider()
st.subheader("Explore the underlying rows")
st.caption("The table and CSV download use the trend area and year-range filters, not the independent comparison year.")
st.dataframe(
    filtered,
    hide_index=True,
    use_container_width=True,
    column_config={
        "year": st.column_config.NumberColumn("Year", format="%d"),
        "area": "Area",
        "area_type": "Area type",
        "treated_per_1000": st.column_config.NumberColumn("ADHD medication-treated per 1,000 inhabitants", format="%.2f"),
    },
)
st.download_button(
    "Download these filtered rows (CSV)",
    data=filtered.to_csv(index=False).encode("utf-8-sig"),
    file_name=f"adhd_treatment_filtered_{year_range[0]}_{year_range[1]}.csv",
    mime="text/csv",
    use_container_width=False,
)

st.divider()
with st.expander("About this indicator and limitations", expanded=True):
    st.markdown(
        """
        **Indicator:** [ADHD-behandling bland barn och unga](https://vardenisiffror.se/sv/indikatorer/adhd-behandling-bland-barn-och-unga)
        (Vården i siffror). The source attributes the indicator to **Läkemedelsregistret,
        Socialstyrelsen**. The indicator covers **ages 0-17**, using the original
        export supplied for the workshop (2012-2025).

        - Values are **aggregated rates**, not individual patient records.
        - Trends and regional differences cannot establish **causation** or ADHD **prevalence**.
        - Rates alone cannot determine **appropriateness of treatment**, **quality of care**, or **individual risk**.
        - A higher or lower value should not be interpreted as inherently better or worse care.
        - **Reuse:** check the original dataset's terms and attribution requirements before public publication.

        This is an educational dashboard, not clinical guidance. No external data,
        accounts, patient uploads, or usage tracking are used.
        """
    )

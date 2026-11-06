"""Plotly figures for the ADHD treatment indicator dashboard."""

import pandas as pd
import plotly.express as px
import plotly.graph_objects as go


INK = "#1d354e"
GRID = "#e5ecf2"
NATIONAL_COLOR = "#174d76"
REGION_COLOR = "#2c7590"
REFERENCE_COLOR = "#b65f34"
RATE_AXIS_LABEL = "ADHD medication treatment (per 1,000 inhabitants)"


def build_trend_chart(filtered: pd.DataFrame) -> go.Figure:
    """One annual line per selected area; years are explicitly sorted."""
    ordered = filtered.sort_values(["area", "year"])
    unique_areas = sorted(ordered["area"].unique())
    palette = px.colors.qualitative.Dark24
    colors = {
        area: NATIONAL_COLOR if area == "Riket" else palette[i % len(palette)]
        for i, area in enumerate(unique_areas)
    }
    fig = px.line(
        ordered,
        x="year",
        y="treated_per_1000",
        color="area",
        markers=True,
        color_discrete_map=colors,
        labels={"year": "Year", "treated_per_1000": RATE_AXIS_LABEL, "area": "Area"},
    )
    fig.update_traces(
        mode="lines+markers",
        line_width=2.8,
        marker_size=7,
        hovertemplate=(
            "<b>%{fullData.name}</b><br>Year: %{x:.0f}"
            "<br>ADHD medication treatment (ages 0-17): "
            "%{y:.2f} per 1,000 inhabitants<extra></extra>"
        ),
    )
    for trace in fig.data:
        if trace.name == "Riket":
            trace.line.width = 4
            trace.marker.size = 8
    many_areas = len(unique_areas) > 5
    legend = (
        dict(title_text="Area", orientation="v", y=1, x=1.02, xanchor="left")
        if many_areas
        else dict(title_text="Area", orientation="h", y=-0.30, x=0, xanchor="left")
    )
    fig.update_layout(
        template="plotly_white",
        height=max(440, len(unique_areas) * 33 + 130) if many_areas else 430,
        margin=dict(l=10, r=205 if many_areas else 16, t=15, b=45 if many_areas else 80),
        font=dict(family="Arial, sans-serif", color=INK, size=13),
        plot_bgcolor="white",
        paper_bgcolor="white",
        hovermode="closest",
        legend=legend,
    )
    fig.update_xaxes(
        tickmode="array",
        tickvals=sorted(ordered["year"].unique().tolist()),
        showgrid=False,
        zeroline=False,
        title_text="Year",
    )
    fig.update_yaxes(
        title_text=RATE_AXIS_LABEL,
        rangemode="tozero",
        gridcolor=GRID,
        zeroline=False,
    )
    return fig


def build_comparison_chart(regions: pd.DataFrame, national_rate: float) -> go.Figure:
    """21 regional rates, ordered ascending, with actual Riket as a reference."""
    ordered = regions.sort_values(["treated_per_1000", "area"], kind="stable")
    fig = go.Figure(
        go.Bar(
            x=ordered["treated_per_1000"].tolist(),
            y=ordered["area"].tolist(),
            orientation="h",
            name="Regions",
            marker=dict(color=REGION_COLOR),
            text=[f"{rate:.2f}" for rate in ordered["treated_per_1000"]],
            textposition="outside",
            textfont=dict(size=11, color=INK),
            hovertemplate=(
                "<b>%{y}</b><br>ADHD medication treatment (ages 0-17): "
                "%{x:.2f} per 1,000 inhabitants<extra></extra>"
            ),
        )
    )
    fig.add_vline(
        x=national_rate,
        line_color=REFERENCE_COLOR,
        line_width=2,
        line_dash="dash",
        annotation_text=f"Riket: {national_rate:.2f}",
        annotation_position="top left",
        annotation_font=dict(color=REFERENCE_COLOR, size=12),
    )
    max_rate = max(float(ordered["treated_per_1000"].max()), national_rate)
    fig.update_layout(
        template="plotly_white",
        height=730,
        margin=dict(l=12, r=58, t=34, b=34),
        font=dict(family="Arial, sans-serif", color=INK, size=12),
        showlegend=False,
        paper_bgcolor="white",
        plot_bgcolor="white",
        bargap=0.26,
    )
    fig.update_xaxes(
        title_text=RATE_AXIS_LABEL,
        range=[0, max_rate * 1.17],
        gridcolor=GRID,
        zeroline=False,
    )
    fig.update_yaxes(
        title_text="Region",
        categoryorder="array",
        categoryarray=ordered["area"].tolist(),
        showgrid=False,
    )
    return fig

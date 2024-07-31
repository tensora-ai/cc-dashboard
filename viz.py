import folium
import numpy as np
import plotly.express as px
import plotly.io as pio
import polars as pl


def icon(text: str):
    return f"""
    <div style="
        font-size: 15px;
        color: white;
        background-color: #524ED2;
        border-radius: 18px;
        width: 56px;
        height: 36px;
        display: flex;
        align-items: center;
        justify-content: center;
        border: 2px solid white;
    ">{text}</div>
"""


def create_map(counts, project):
    # Create a Folium map centered on Germany with ESRI satellite tiles
    m = folium.Map(
        location=[project["lat"], project["lon"]],
        zoom_start=18,
        tiles="https://server.arcgisonline.com/ArcGIS/rest/services/World_Imagery/MapServer/tile/{z}/{y}/{x}",
        attr="ESRI",
        scrollWheelZoom=False,
        zoom_control=False,
    )

    # Add markers for each city with rank numbers
    for k, v in counts.items():
        if k in ["total", "timestamp"]:
            continue
        folium.Marker(
            location=[project["areas"][k]["lat"], project["areas"][k]["lon"]],
            # popup=f"{b}: Rank {d['count']}",
            # tooltip=f"{b}: Rank {d['count']}",
            icon=folium.DivIcon(html=icon(int(v))),
        ).add_to(m)

    # Save the map to an HTML file
    m.save("static/map.html")


def line_chart(df: pl.DataFrame, areas: set[str]):
    df = df.melt(id_vars=["timestamp"], variable_name="area", value_name="count")
    df = df.filter(pl.col("area").is_in(areas))

    fig = px.area(
        df.to_pandas(),
        x="timestamp",
        y="count",
        color="area",
        line_shape="spline",
        height=200,
    )

    fig.update_xaxes(
        tickformat="%H:%M",
        nticks=10,
        title_text=None,  # Hide x-axis label
        tickfont=dict(color="#808080"),  # Medium gray for tick labels
        gridcolor="#808080",  # Medium gray for grid lines
    )

    fig.update_yaxes(
        title_text=None,
        tickfont=dict(color="#808080"),  # Medium gray for tick labels
        gridcolor="#808080",  # Medium gray for grid lines
    )

    fig.update_layout(
        margin=dict(l=0, r=0, t=0, b=0),  # Minimal margins
        legend_title_text="",
        paper_bgcolor="rgba(0,0,0,0)",  # Transparent background
        plot_bgcolor="rgba(0,0,0,0)",  # Transparent plot area
        legend=dict(font=dict(color="#808080")),  # Medium gray for legend text
    )
    return pio.to_html(
        fig, full_html=False, include_plotlyjs=False, config={"displayModeBar": False}
    )


def heatmap_chart(array, crop):
    l, t, r, b = crop
    fig = px.imshow(
        array,
        x=np.linspace(l, r - 0.5, array.shape[1]),
        y=np.linspace(b - 0.5, t, array.shape[0]),
        color_continuous_scale="viridis",
        origin="lower",
        aspect="equal",
        labels={"color": "density"},
        zmin=0,
        zmax=5,
    )
    fig.update_layout(
        margin=dict(l=0, r=0, t=0, b=0),  # Minimal margins
        paper_bgcolor="rgba(0,0,0,0)",  # Transparent background
        plot_bgcolor="rgba(0,0,0,0)",  # Transparent plot area
        font=dict(color="#808080"),  # Medium gray font color
        # xaxis=dict(title=None, showticklabels=False, showgrid=False),
        # yaxis=dict(title=None, showticklabels=False, showgrid=False),
        xaxis=dict(title="Distance (meters)", showticklabels=True, showgrid=False),
        yaxis=dict(title="Distance (meters)", showticklabels=True, showgrid=False),
    )
    return pio.to_html(
        fig, full_html=False, include_plotlyjs=False, config={"displayModeBar": False}
    )

import re
import folium
import pandas as pd
import polars as pl
import plotly.io as pio
import plotly.express as px

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

def line_chart(df: pl.DataFrame, project: dict):
    df = df.melt(id_vars=["timestamp"], variable_name="area", value_name="count")
    df_pandas = df.to_pandas()
    
    fig = px.area(
        df_pandas,
        x="timestamp",
        y="count",
        color="area",
        line_shape="spline",  # This is similar to interpolate="basis" in Altair
        # width=960,
        height=240
    )
    
    # Customize the x-axis
    fig.update_xaxes(
        tickformat="%H:%M",
        nticks=10
    )
    
    # Adjust layout to reduce padding and remove legend title
    fig.update_layout(
        margin=dict(l=0, r=0, t=0, b=0),  # Minimal margins
        legend_title_text=''
    )

    # Convert the figure to HTML
    html = pio.to_html(fig, full_html=False)
    return html

def heatmap_chart(data: list[list]):
    df = pd.DataFrame(data, columns=["x", "y", "z"]).astype(int)
    df = df.drop_duplicates(["x", "y"], keep="first")
    
    fig = px.imshow(
        df.pivot(index="y", columns="x", values="z"),
        color_continuous_scale="viridis",
        origin="upper",
        labels={"color": ""},
        # text_auto=True
    )

    # Adjust layout to reduce padding
    fig.update_layout(
        margin=dict(l=0, r=0, t=0, b=0),  # Minimal margins
        # xaxis=dict(showticklabels=False),
        # yaxis=dict(showticklabels=False),
    )

    # Convert the figure to HTML
    html = pio.to_html(fig, full_html=False, include_plotlyjs=False)
    return html

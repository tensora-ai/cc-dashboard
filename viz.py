import re
import folium
import numpy as np
import pandas as pd
import altair as alt
import vl_convert as vlc
# import plotly.express as px
# import plotly.io as pio


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


# def line_chart2(df: pd.DataFrame, col="total"):
#     fig = px.line(df, x="timestamp", y=col)
#     fig.update_layout(
#         margin=dict(l=0, r=0, t=0, b=0),
#         # showlegend=False,
#         yaxis_title=None,
#         xaxis_title=None,
#         yaxis_gridcolor="rgba(0,0,0,0.2)",
#         xaxis_gridcolor="rgba(0,0,0,0.2)",
#         paper_bgcolor="rgba(0,0,0,0)",
#         plot_bgcolor="rgba(0,0,0,0)",
#     )
#     return pio.to_html(fig, full_html=False, default_height="200px")


# def line_chart(df: pd.DataFrame, project: dict):
#     chart = pygal.StackedLine(fill=True, width=1280, height=240)
#     for col in df.columns:
#         if col in ["total", "timestamp"]:
#             continue
#         chart.add(project["areas"][col]["name"], df[col].to_list())
#     # chart.show_minor_x_labels = False
#     # chart.show_minor_y_labels = False
#     chart.show_dots = False
#     return chart.render(is_unicode=True)


def line_chart(df: pd.DataFrame, project: dict):
    df = df.reset_index()
    df = df.melt(["timestamp"], var_name="position", value_name="count_standard_mask")
    chart = (
        alt.Chart(df, width=960, height=240)
        .mark_area(interpolate="basis")
        .encode(
            x=alt.X("timestamp:T", axis=alt.Axis(format="%H:%M", tickCount=10)),
            y="count_standard_mask:Q",
            color="position:N",
        )
    )
    # rendering charts as SVGs minimizes UI flashes on refresh
    svg = vlc.vegalite_to_svg(chart.to_json())
    svg = re.sub(r' width="\d+"', 'width="100%"', svg)
    svg = re.sub(r' height="\d+"', "", svg)
    return svg


def array_to_heatmap_data(array: np.ndarray):
    rows, cols = array.shape
    x, y = np.meshgrid(range(cols), range(rows))
    data = pd.DataFrame({"x": x.ravel(), "y": y.ravel(), "z": array.ravel()})

    return data


def heatmap_chart(data: list, x_range=(-13, 54), y_range=(0, 45)):
    df = pd.DataFrame(data, columns=["x", "y", "z"])
    df = df[(df.x > x_range[0]) & (df.x < x_range[1])]
    df = df[(df.y > y_range[0]) & (df.y < y_range[1])]
    df.x = df.x.astype(int)
    df.y = df.y.astype(int)
    df.z = df.z.astype(int)

    base = (
        alt.Chart(df)
        .mark_rect()
        .encode(
            x=alt.X("x:O", axis=None),
            y=alt.Y("y:O", axis=None, scale=alt.Scale(reverse=True)),
        )
    )
    heatmap = base.mark_rect().encode(
        alt.Color("z:Q", legend=None).scale(scheme="viridis")
    )
    text = base.mark_text(baseline="middle").encode(
        alt.Text("z:Q"), color=alt.value("black")
    )
    chart = heatmap + text
    svg = vlc.vegalite_to_svg(chart.to_json())
    svg = re.sub(r' width="\d+"', 'width="100%"', svg)
    svg = re.sub(r' height="\d+"', "", svg)
    return svg

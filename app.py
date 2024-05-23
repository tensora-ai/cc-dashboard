import datetime
from fastapi import FastAPI
from fastapi.responses import HTMLResponse
from fastapi.staticfiles import StaticFiles
import azure.storage.blob
from azure.cosmos import CosmosClient
from jinjax import Catalog
import numpy as np

from viz import create_map, line_chart, heatmap_chart
from perspective import compute_homography
from utils import get_capacity, prepare_data, prepare_data2

catalog = Catalog()
catalog.add_folder("components")
catalog.add_folder("dashboards")
app = FastAPI()

app.mount("/static", StaticFiles(directory="static"), name="static")

cosmos_client = CosmosClient.from_connection_string(
    "AccountEndpoint=https://tensora-cosmos.documents.azure.com:443/;AccountKey=3HhuxX00FrreK88mEiCmLNgSypzbVLKwKiBA5mgb0sUQcvaIV2YCDKNBdqEIe0TbsZpBEHg2cuQbACDbtIa2ow==;"
)
cosmos_db = cosmos_client.get_database_client("crowd-counting")
fcn_db = cosmos_db.get_container_client("predictions-nuernberg")
kalkberg_db = cosmos_db.get_container_client("predictions-bad-segeberg")
projects = cosmos_db.get_container_client("projects")


blob_client = azure.storage.blob.BlobServiceClient(
    account_url="https://tensorastorage.blob.core.windows.net/",
    credential="OTC+4iQJevvteUOTaTO+N7GYRJkuUNyEieCOGIdRwno9h7BByPMKBi5uRG50DgYICDoyqFn0ZraE+AStUQb4MQ==",
)
blob = blob_client.get_container_client("cc-images-nuernberg")


@app.get("/dashboard/{id}/{key}", response_class=HTMLResponse)
async def dashboard(id: str, key: str):
    try:
        project = projects.read_item(id, id)
        if key != project["key"]:
            raise ValueError("Invalid key")
    except:
        return "Invalid project and/or key."
    return catalog.render(
        "Layout",
        title=project["name"],
        project=project["id"],
        key=project["key"],
        date=datetime.date.today().strftime("%Y-%m-%d"),
    )


@app.get("/content/{id}/{key}", response_class=HTMLResponse)
async def content(id: str, key: str, date: str | None = None):
    if date is None:
        date = datetime.date.today().strftime("%Y-%m-%d")
    try:
        project = projects.read_item(id, id)
        if key != project["key"]:
            raise ValueError("Invalid key")
    except:
        return "Invalid project and/or key."
    db = fcn_db if id == "fcn" else kalkberg_db
    items = list(
        db.query_items(
            query=f"SELECT * FROM c WHERE STARTSWITH(c.timestamp, '{date}')",
            enable_cross_partition_query=True,
        )
    )
    if len(items) == 0:
        return catalog.render("Empty")
    df = prepare_data(items, date) if id == "fcn" else prepare_data2(items, date)
    chart = line_chart(df.drop("total", axis="columns"), project)
    capacity = get_capacity(project)
    create_map(df.iloc[-1].to_dict(), project)  # map gets saved as a HTML file
    heatmap = heatmap_chart()  # dummy function
    return catalog.render(
        project["name"].replace(" ", ""),
        title=project["name"],
        chart=chart,
        heatmap=heatmap,
        current=int(df["total"].to_list()[-1]),
        maximum=int(df["total"].max()),
        average=int(df["total"].mean()),
        minimum=int(df["total"].min()),
        capacity=capacity,
    )


@app.get("/utils/homography")
async def homography(
    tl_x: int,
    tl_y: int,
    tr_x: int,
    tr_y: int,
    br_x: int,
    br_y: int,
    bl_x: int,
    bl_y: int,
):
    src_points = np.array([[tl_x, tl_y], [tr_x, tr_y], [br_x, br_y], [bl_x, bl_y]])
    H = compute_homography(src_points, square_size=2.0, px_per_m=10)
    return {"homography": H.round(4).tolist()}

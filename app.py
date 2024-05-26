import os
import json
from dotenv import load_dotenv
from datetime import datetime as dt
from fastapi import FastAPI
from fastapi.responses import HTMLResponse
from fastapi.staticfiles import StaticFiles

import azure.storage.blob
from azure.cosmos import CosmosClient
from jinjax import Catalog

from viz import create_map, line_chart, heatmap_chart

# from perspective import compute_homography
from utils import get_capacity, prepare_data, prepare_data2, get_latest_entry

load_dotenv()

catalog = Catalog()
catalog.add_folder("components")
catalog.add_folder("dashboards")
app = FastAPI()

app.mount("/static", StaticFiles(directory="static"), name="static")

cosmos_client = CosmosClient.from_connection_string(
    os.environ["COSMOS_CONNECTION_STRING"]
)
cosmos_db = cosmos_client.get_database_client("crowd-counting")
fcn_db = cosmos_db.get_container_client("predictions-nuernberg")
kalkberg_db = cosmos_db.get_container_client("predictions-bad-segeberg")
projects = cosmos_db.get_container_client("projects")


blob_client = azure.storage.blob.BlobServiceClient(
    account_url=os.environ["STORAGE_URL"],
    credential=os.environ["STORAGE_CREDENTIAL"],
)
container_client = blob_client.get_container_client("cc-images-bad-segeberg")


@app.get("/", response_class=HTMLResponse)
async def login():
    return catalog.render("Login")


@app.get("/dashboard", response_class=HTMLResponse)
async def dashboard(id: str, key: str):
    date = dt.now().strftime("%Y-%m-%d")
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
        date=date,
    )


@app.get("/content", response_class=HTMLResponse)
async def content(id: str, key: str, date: str, time: str | None = None):
    # if date == dt.now().strftime("%Y-%m-%d") and time == "":
    #     return HTMLResponse("", 204)
    if time is None or time == "":
        time = "23:59:59"
    try:
        project = projects.read_item(id, id)
        if key != project["key"]:
            raise ValueError("Invalid key")
    except:
        return "Invalid project and/or key."
    db = fcn_db if id == "fcn" else kalkberg_db
    items = list(
        db.query_items(
            query=f"SELECT * FROM c WHERE STARTSWITH(c.timestamp, '{date}') AND c.timestamp < '{date}T{time}'",
            enable_cross_partition_query=True,
        )
    )
    if len(items) == 0:
        return catalog.render("Empty")
    df = prepare_data(items, date) if id == "fcn" else prepare_data2(items, date)
    chart = line_chart(df.drop("total", axis="columns"), project)
    capacity = get_capacity(project)
    create_map(df.iloc[-1].to_dict(), project)  # map gets saved as a HTML file
    # get the latest blobs from the container_client
    fname_right = get_latest_entry(items, "stage_right", "standard")
    fname_left = get_latest_entry(items, "stage_left", "standard")
    img_left = container_client.get_blob_client(f"{fname_left}.jpg").url
    img_right = container_client.get_blob_client(f"{fname_right}.jpg").url
    blob = container_client.get_blob_client(f"{fname_right}_transformed_density.json")
    heatmap = heatmap_chart(
        json.loads(blob.download_blob().content_as_text()), blob_name=fname_right
    )
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
        img_left=img_left,
        img_right=img_right,
    )


# @app.get("/utils/homography")
# async def homography(
#     tl_x: int,
#     tl_y: int,
#     tr_x: int,
#     tr_y: int,
#     br_x: int,
#     br_y: int,
#     bl_x: int,
#     bl_y: int,
# ):
#     src_points = np.array([[tl_x, tl_y], [tr_x, tr_y], [br_x, br_y], [bl_x, bl_y]])
#     H = compute_homography(src_points, square_size=2.0, px_per_m=10)
#     return {"homography": H.round(4).tolist()}

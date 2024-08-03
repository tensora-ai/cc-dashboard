import json
import os
from datetime import datetime as dt
from datetime import timedelta

from azure.cosmos import CosmosClient
from azure.storage.blob import BlobServiceClient
from dotenv import load_dotenv
from fastapi import FastAPI, Query
from fastapi.responses import HTMLResponse
from fastapi.staticfiles import StaticFiles
from jinjax import Catalog

from utils import (
    convert_to_array,
    filter_coords,
    get_latest_entry,
    merge_cam_crops,
    prep_data,
)
from viz import heatmap_chart, line_chart

MAX_ROWS = 1000

load_dotenv()

catalog = Catalog()
catalog.add_folder("components")
catalog.add_folder("dashboards")
app = FastAPI()

app.mount("/static", StaticFiles(directory="static"), name="static")

db = CosmosClient.from_connection_string(
    os.environ["COSMOS_CONNECTION_STRING"]
).get_database_client("tensora-count")
db_projects = db.get_container_client("projects")
db_predictions = db.get_container_client("predictions")

blob_client = BlobServiceClient.from_connection_string(
    os.environ["STORAGE_CONNECTION_STRING"]
)
blob_images = blob_client.get_container_client("images")
blob_predictions = blob_client.get_container_client("predictions")


@app.get("/", response_class=HTMLResponse)
async def login():
    return catalog.render("Login")


@app.get("/dashboard", response_class=HTMLResponse)
async def dashboard(
    id: str,
    key: str,
    area: str = "all",
    date: str = dt.now().strftime("%Y-%m-%d"),
    time: str = "",
):
    try:
        project = db_projects.read_item(id, id)
        if key != project["key"]:
            raise ValueError("Invalid key")
    except:
        return "Invalid project and/or key."

    return catalog.render("Layout", project=project, area=area, date=date, time=time)


@app.get("/content", response_class=HTMLResponse)
async def content(
    id: str,
    key: str,
    area: list[str] = Query(None),
    date: str = Query(...),
    time: str = Query(...),
):
    start = dt.now()
    if not time:
        time = "23:59:59"
    elif len(time.split(":")) == 2:
        time += ":00"
        # Combine date and time into a single datetime object
        original_datetime = dt.strptime(f"{date}T{time}", "%Y-%m-%dT%H:%M:%S")

        # Subtract 2 hours
        adjusted_datetime = original_datetime - timedelta(hours=2)

        # Format adjusted datetime back to date and time strings
        adjusted_date = adjusted_datetime.strftime("%Y-%m-%d")
        adjusted_time = adjusted_datetime.strftime("%H:%M:%S")
        time = adjusted_time
        date = adjusted_date
    try:
        project = db_projects.read_item(id, id)
        if key != project["key"]:
            raise ValueError("Invalid key")
    except:
        return "Invalid project and/or key."

    if not area:
        areas = list(project["areas"].keys())
    else:
        areas = area

    area2camera = {}
    for cam_name, cam_data in project["cameras"].items():
        for pos_name, pos_data in cam_data["position_settings"].items():
            for area_name, area_data in pos_data["area_metadata"].items():
                if area_name in area2camera:
                    area2camera[area_name].append(cam_name)
                else:
                    area2camera[area_name] = [cam_name]
    print(date)
    q = f"""
    SELECT * FROM c
    WHERE STARTSWITH(c.timestamp, '{date}')
    AND c.timestamp <= '{date}T{time}'
    AND c.project = '{project["id"]}'
    ORDER BY c.timestamp DESC
    OFFSET 0 LIMIT {MAX_ROWS}
    """

    items = list(db_predictions.query_items(q, partition_key=project["id"]))

    if len(items) == 0:
        return "No data available for the selected date and time."

    df = prep_data(items, areas)
    available_areas = set([k for item in items for k in item["counts"]])
    chart = line_chart(df.drop("total"), available_areas)

    images: dict[str, list[str]] = (
        {}
    )  # mapping areas to most recent prediction IDs for each camera
    densities: dict[str, str] = {}  # mapping areas to heatmap charts in HTML
    for area in areas:
        if area not in available_areas:
            continue
        a = project["areas"][area]["name"]
        images[a] = []
        merged_coords = []
        cam_crops = []
        for camera in area2camera[area]:
            id = get_latest_entry(items, camera, "standard")
            images[a].append(id)
            try:
                f = blob_predictions.download_blob(f"{id}_transformed_density.json")
                coords = json.loads(f.readall())
                pos_settings = project["cameras"][camera]["position_settings"]
                cam_crop = pos_settings["standard"]["area_metadata"][area][
                    "heatmap_crop"
                ]
                cam_crops.append(cam_crop)
                merged_coords += filter_coords(coords, cam_crop)
            except:
                print(f"{id}_transformed_density.json not found")
        area_crop = merge_cam_crops(cam_crops)
        img = convert_to_array(merged_coords, date, area_crop)
        densities[a] = heatmap_chart(img, area_crop)

    print(round((dt.now() - start).microseconds * 1e-6, 2), "seconds")

    return catalog.render(
        project["name"].replace(
            " ", ""
        ),  # Maps project name to name of the template file
        project=project,
        chart=chart,
        data=df,
        images=images,
        densities=densities,
    )

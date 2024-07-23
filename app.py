import os
import json
from dotenv import load_dotenv
from datetime import datetime as dt
from fastapi import FastAPI
from fastapi.responses import HTMLResponse
from fastapi.staticfiles import StaticFiles

from azure.storage.blob import BlobServiceClient
from azure.cosmos import CosmosClient
from jinjax import Catalog

from viz import line_chart, heatmap_chart
from utils import get_latest_entry, prep_data, filter_coords

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
async def dashboard(id: str, key: str, area: str = "all", date: str = dt.now().strftime("%Y-%m-%d"), time: str = ""):
    try:
        project = db_projects.read_item(id, id)
        if key != project["key"]:
            raise ValueError("Invalid key")
    except:
        return "Invalid project and/or key."
    
    return catalog.render(
        "Layout",
        project=project,
        area=area,
        date=date,
        time=time
    )

@app.get("/content", response_class=HTMLResponse)
async def content(id: str, key: str, area: str, date: str, time: str):
    start = dt.now()
    if not time:
        time = "23:59:59"
    try:
        project = db_projects.read_item(id, id)
        if key != project["key"]:
            raise ValueError("Invalid key")
    except:
        return "Invalid project and/or key."
    
    if not area or area == "all":
        areas = list(project["areas"].keys())
    else:
        areas = [area]

    area2camera = {}
    for cam_name, cam_data in project["cameras"].items():
        for pos_name, pos_data in cam_data["position_settings"].items():
            for area_name, area_data in pos_data["area_metadata"].items():
                if area_name in area2camera:
                    area2camera[area_name].append(cam_name)
                else:
                    area2camera[area_name] = [cam_name]
    
    q = f"""
    SELECT * FROM c
    WHERE STARTSWITH(c.timestamp, '{date}')
    AND c.timestamp <= '{date}T{time}'
    AND c.project = '{project["id"]}'
    ORDER BY c.timestamp
    """

    items = list(db_predictions.query_items(q, partition_key=project["id"]))

    if len(items) == 0:
        return "No data available for the selected date and time."

    df = prep_data(items, areas)
    chart = line_chart(df.drop("total"), project)

    # print(round((dt.now() - start).microseconds * 1e-6, 2), "seconds")

    images: dict[str, list[str]] = {} # mapping areas to most recent prediction IDs for each camera
    densities: dict[str, str] = {} # mapping areas to heatmap charts in HTML
    for area in areas:
        a = project["areas"][area]["name"]
        images[a] = []
        merged_coords = []
        for camera in area2camera[area]:
            id = get_latest_entry(items, camera, "standard")
            images[a].append(id)
            try:
                f = blob_predictions.download_blob(f"{id}_transformed_density.json")
                coords = json.loads(f.readall())
                merged_coords += filter_coords(coords, project["cameras"][camera]["position_settings"]["standard"]["area_metadata"][area]["heatmap_crop"])
            except:
                print(f"{id}_transformed_density.json not found")
        # densities[a] = heatmap_chart(coords)
        densities[a] = heatmap_chart(merged_coords)
        
    return catalog.render(
        project["name"].replace(" ", ""),
        project=project,
        chart=chart,
        data=df,
        images=images,
        densities=densities
    )

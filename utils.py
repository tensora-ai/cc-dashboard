import numpy as np
import polars as pl

def prep_data(items: list[dict], areas: list[str]):
    schema = {"timestamp": pl.String, "camera": pl.String, "counts": pl.Struct({k:pl.Int64 for k in areas})}
    df = pl.DataFrame(items, schema=schema).unnest("counts")
    df = df.fill_null(0)
    df = df.with_columns(pl.col("timestamp").cast(pl.Datetime).dt.truncate("1m"))
    df = df.group_by(["timestamp", "camera"]).mean()
    df = df.group_by(["timestamp"]).sum().drop("camera")
    df = df.sort("timestamp")
    df = df.fill_nan(0)
    df = df.with_columns([pl.col(x).ewm_mean(span=4, ignore_nulls=True).cast(pl.Int64) for x in areas])
    df = df.with_columns(pl.sum_horizontal(areas).alias("total"))
    return df


def get_capacity(project: dict):
    return sum(
        [
            project["areas"][k]["capacity"]
            for k in project["areas"]
            if project["areas"][k]["capacity"] > 0
        ]
    )


def get_latest_entry(items, camera: str, position: str):
    schema = {"id": pl.String, "timestamp": pl.String, "camera": pl.String, "position": pl.String}
    df = pl.DataFrame(items, schema=schema)
    df = df.filter((df["camera"] == camera) & (df["position"] == position))
    df = df.sort("timestamp")
    return df["id"].to_list()[-1]

def filter_coords(coords: list, crop: list[int]):
    coords = [x for x in coords if x[0] >= crop[0] and x[0] <= crop[2]]
    coords = [x for x in coords if x[1] >= crop[1] and x[1] <= crop[3]]
    return coords

def convert_to_array(items: list[list], crop: tuple | None = None):
    if crop:
        l, t, r, b = crop
    else:
        l = int(min(x[0] for x in items))
        t = int(min(x[1] for x in items))
        r = int(max(x[0] for x in items)) + 1
        b = int(max(x[1] for x in items)) + 1
    
    # Calculate the dimensions of the array
    width = (r - l) * 2
    height = (b - t) * 2
    
    # Create an empty array filled with zeros
    array = np.zeros((height, width))
    
    # Fill the array with intensity values
    for x, y, val in items:
        if l <= x < r and t <= y < b:  # Check if the point is within the crop area
            # Convert coordinates to array indices
            j = int((x - l) * 2)
            i = int((y - t) * 2)
            if 0 <= i < height and 0 <= j < width:
                array[height - i - 1, j] = round(val, 1)
    
    return array

def merge_cam_crops(cam_crops: list):
    arr = np.array(cam_crops)
    l = int(arr[:,0].min())
    t = int(arr[:,1].min())
    r = int(arr[:,2].max())
    b = int(arr[:,3].max())
    return l, t, r, b
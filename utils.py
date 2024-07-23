import polars as pl
from datetime import datetime

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
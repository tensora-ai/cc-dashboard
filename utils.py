import pandas as pd
from datetime import datetime


# def prepare_data2(items: list[dict], date: str):
#     date = datetime.strptime(date, "%Y-%m-%d").date()
#     df = pd.DataFrame(items)
#     df = df[["timestamp", "position", "count_standard_mask"]]
#     df["timestamp"] = pd.to_datetime(df["timestamp"])
#     df = df[df["timestamp"].dt.date == date]
#     df = df.sort_values(by="timestamp")
#     df = df.pivot(index="timestamp", columns="position", values="count_standard_mask")
#     df = df.ffill()
#     df = df.fillna(value=0)
#     df = df.resample("1T").ffill()
#     df = df.fillna(value=0)
#     df["total"] = df.sum(axis=1)
#     df.reset_index(inplace=True)
#     return df


def prepare_data(items: list[dict], date: str):
    date = datetime.strptime(date, "%Y-%m-%d").date()
    df = pd.DataFrame(items)
    df = df[["id", "timestamp", "position", "count_standard_mask"]]
    df["timestamp"] = pd.to_datetime(df["timestamp"])
    df = df[df["timestamp"].dt.date == date]
    df = df.sort_values(by="timestamp")
    df = df.pivot(index="timestamp", columns="position", values="count_standard_mask")
    df = df.ffill()
    df = df.fillna(value=0)
    df = df.resample("1T").ffill()
    df = df.fillna(value=0)
    df["total"] = df.sum(axis=1)
    df = df.sort_values(by="timestamp")
    for col in df.columns:
        df[col] = df[col].ewm(span=3, adjust=False).mean()
    return df


def prepare_data2(items: list[dict], date: str):
    date = datetime.strptime(date, "%Y-%m-%d").date()
    df = pd.DataFrame(items)
    df = df[["id", "timestamp", "camera_id", "count_standard_mask"]]
    df["camera_id"] = df["camera_id"].str.replace("stage_", "")
    df["timestamp"] = pd.to_datetime(df["timestamp"])
    df = df[df["timestamp"].dt.date == date]
    df = df.sort_values(by="timestamp")
    df = df.pivot(index="timestamp", columns="camera_id", values="count_standard_mask")
    df = df.ffill()
    df = df.fillna(value=0)
    df = df.resample("1T").ffill()
    df = df.fillna(value=0)
    df["total"] = df.sum(axis=1)
    df = df.sort_values(by="timestamp")
    for col in df.columns:
        df[col] = df[col].ewm(span=3, adjust=False).mean()
    return df

def prepare_data3(items: list[dict], date: str):
    date = datetime.strptime(date, "%Y-%m-%d").date()
    df = pd.DataFrame(items)
    df = df[["id", "timestamp", "camera_id", "count_standard_mask"]]
    # df["camera_id"] = df["camera_id"].str.replace("stage_", "")
    df["timestamp"] = pd.to_datetime(df["timestamp"])
    df["timestamp"] = df["timestamp"] + pd.Timedelta(hours=2)
    df = df[df["timestamp"].dt.date == date]
    df = df.sort_values(by="timestamp")
    df = df.pivot(index="timestamp", columns="camera_id", values="count_standard_mask")
    df = df.ffill()
    df = df.fillna(value=0)
    df = df.resample("1min").ffill()
    df = df.fillna(value=0)
    df["total"] = df.sum(axis=1)
    df = df.sort_values(by="timestamp")
    print(df.head())
    for col in df.columns:
        df[col] = df[col].ewm(span=3, adjust=False).mean()
    return df


def get_capacity(project: dict):
    return sum(
        [
            project["areas"][k]["capacity"]
            for k in project["areas"]
            if project["areas"][k]["capacity"] > 0
        ]
    )


def get_latest_entry(items, camera_id: str, position: str):
    df = pd.DataFrame(items)
    df = df[(df.camera_id == camera_id) & (df.position == position)]
    df = df.sort_values("timestamp")
    return df["id"].to_list()[-1]

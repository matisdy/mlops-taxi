"""Download the NYC TLC yellow taxi Parquet files of params.yaml into data/raw/ (spec section 4).
Usage: uv run python download.py
"""
from pathlib import Path

import requests
import yaml

CHUNK_SIZE = 1024 * 1024  # write 1 MiB at a time, never the whole file in memory


def download(url: str, path: Path) -> None:
    """Stream url into path through a .part file, renamed only once the download is complete."""
    part = path.with_name(path.name + ".part")
    try:
        # requests with a timeout (S3 p. 8; S5 p. 30); stream=True reads the body block by block
        with requests.get(url, stream=True, timeout=60) as response:
            response.raise_for_status()  # an HTTP error stops here: no error page saved as Parquet
            with open(part, "wb") as f:
                for chunk in response.iter_content(chunk_size=CHUNK_SIZE):
                    f.write(chunk)
        part.rename(path)  # a truncated file can never pass for a downloaded one
    finally:
        part.unlink(missing_ok=True)  # after an error, no .part left in data/raw for dvc add


if __name__ == "__main__":
    data = yaml.safe_load(open("params.yaml"))["data"]
    raw_dir = Path(data["raw_dir"])
    raw_dir.mkdir(parents=True, exist_ok=True)
    for month in data["months"]:
        path = raw_dir / f"yellow_tripdata_{month}.parquet"
        if path.exists():
            status = "already present"
        else:
            download(data["url"].format(month=month), path)
            status = "downloaded"
        print(f"{path}: {path.stat().st_size / 1e6:.1f} MB, {status}")

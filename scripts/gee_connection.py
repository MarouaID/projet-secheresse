"""
GEE connection utility.
Each teammate must fill in config/gee_config.yaml with their own GEE project ID.
"""

import ee
import yaml
from pathlib import Path


def _load_config() -> dict:
    config_path = Path(__file__).resolve().parents[1] / "config" / "gee_config.yaml"
    with open(config_path, "r") as f:
        return yaml.safe_load(f)["gee"]


def get_gee_project() -> str:
    cfg = _load_config()
    if cfg["project"] == "your-gee-project-id":
        raise ValueError("Please set your GEE project ID in config/gee_config.yaml")
    return cfg["project"]


def get_haouz_asset() -> str:
    cfg = _load_config()
    if cfg["haouz_asset"] == "projects/your-gee-project-id/assets/haouz_boundary":
        raise ValueError("Please set your haouz_asset path in config/gee_config.yaml")
    return cfg["haouz_asset"]


def connect() -> None:
    """Authenticate and initialize the GEE connection."""
    project = get_gee_project()
    try:
        ee.Initialize(project=project)
    except Exception:
        ee.Authenticate()
        ee.Initialize(project=project)


def test_connection() -> None:
    """Quick sanity check — prints available ERA5-Land bands."""
    connect()
    image = (
        ee.ImageCollection("ECMWF/ERA5_LAND/DAILY_AGGR")
        .filterDate("2020-01-01", "2020-01-02")
        .first()
    )
    print("Connexion réussie !")
    print("Bandes disponibles :", image.bandNames().getInfo())


if __name__ == "__main__":
    test_connection()

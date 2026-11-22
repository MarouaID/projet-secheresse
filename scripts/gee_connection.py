"""
GEE connection utility.
Each teammate must fill in config/gee_config.yaml with their own GEE project ID.
"""

import ee
import yaml
from pathlib import Path


def get_gee_project() -> str:
    config_path = Path(__file__).resolve().parents[1] / "config" / "gee_config.yaml"
    with open(config_path, "r") as f:
        config = yaml.safe_load(f)
    project = config["gee"]["project"]
    if project == "your-gee-project-id":
        raise ValueError(
            "Please set your GEE project ID in config/gee_config.yaml"
        )
    return project


def connect() -> None:
    """Authenticate and initialize the GEE connection."""
    project = get_gee_project()
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

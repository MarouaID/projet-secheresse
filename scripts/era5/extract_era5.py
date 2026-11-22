"""
ERA5-Land daily extraction for the Haouz plain.
Exports one CSV per year to Google Drive under DroughtProject_ERA5Land/.
Once done, download the CSVs manually into data/raw/era5/.

Usage:
    python scripts/era5/extract_era5.py --year 1981
    python scripts/era5/extract_era5.py --year 1981 --end_year 2025
"""

import argparse
import sys
from pathlib import Path

import ee

sys.path.append(str(Path(__file__).resolve().parents[2]))
from scripts.gee_connection import connect, get_haouz_asset

# ==========================================
# 4. SELECTION DES PARAMETRES
# ==========================================

BANDS = [
    "temperature_2m",
    "temperature_2m_max",
    "temperature_2m_min",
    "dewpoint_temperature_2m",
    "total_precipitation_sum",
    "potential_evaporation_sum",
    "u_component_of_wind_10m",
    "v_component_of_wind_10m",
    "surface_pressure",
    "volumetric_soil_water_layer_1",
    "volumetric_soil_water_layer_2",
    "volumetric_soil_water_layer_3",
    "volumetric_soil_water_layer_4",
    "surface_solar_radiation_downwards_sum",
]

OUTPUT_NAMES = [
    "T2M_K",
    "T2M_MAX_K",
    "T2M_MIN_K",
    "T2M_DEW_K",
    "TP_M",
    "PET_M",
    "U10",
    "V10",
    "PS_PA",
    "SWVL1",
    "SWVL2",
    "SWVL3",
    "SWVL4",
    "SSRD_J_M2",
]

SELECTORS = ["DATE"] + OUTPUT_NAMES


# ==========================================
# 5. VERIFIER LES BANDES DISPONIBLES
# ==========================================

def check_bands(era5: ee.ImageCollection) -> None:
    available = ee.Image(era5.first()).bandNames().getInfo()
    missing = [b for b in BANDS if b not in available]
    if missing:
        raise ValueError(f"Bandes indisponibles dans ERA5-Land : {missing}")
    print("Les 14 bandes sont disponibles.")


# ==========================================
# 6. EXTRACTION PAR ANNEE
# ==========================================

def export_year(year: int, geometry: ee.Geometry, era5: ee.ImageCollection) -> None:

    print(f"Preparation de {year}...")

    start = ee.Date.fromYMD(year, 1, 1)
    end = start.advance(1, "year")

    collection = era5.filterDate(start, end).select(BANDS, OUTPUT_NAMES)

    number_images = collection.size().getInfo()
    print("Images quotidiennes :", number_images)

    if number_images == 0:
        print("Aucune donnee disponible.")
        return

    projection = ee.Image(collection.first()).select(0).projection()
    image_list = collection.toList(number_images)

    def extract_image(image):
        image = ee.Image(image)
        date = ee.Date(image.get("system:time_start")).format("YYYY-MM-dd")
        samples = image.sample(
            region=geometry,
            projection=projection,
            geometries=True,
            dropNulls=True,
            tileScale=4,
        )

        def add_metadata(feature):
            coords = feature.geometry().coordinates()
            return feature.set({"DATE": date, "LON": coords.get(0), "LAT": coords.get(1)})

        return samples.map(add_metadata)

    daily_samples = ee.FeatureCollection(image_list.map(extract_image)).flatten()

    task = ee.batch.Export.table.toDrive(
        collection=daily_samples,
        description=f"ERA5Land_Haouz_{year}",
        folder="DroughtProject_ERA5Land",
        fileNamePrefix=f"era5land_haouz_{year}",
        fileFormat="CSV",
        selectors=["DATE", "LAT", "LON"] + OUTPUT_NAMES,
    )

    task.start()
    print(f"Export lance pour {year} — Task ID : {task.id}")


# ==========================================
# 7. POINT D'ENTREE
# ==========================================

def main():
    parser = argparse.ArgumentParser(description="Extract ERA5-Land data for the Haouz plain.")
    parser.add_argument("--year",     type=int, required=True, help="Start year (ex: 1981)")
    parser.add_argument("--end_year", type=int, default=None,  help="End year inclusive (ex: 2025). If omitted, only --year is exported.")
    args = parser.parse_args()

    connect()
    print("Connexion GEE reussie.")

    geometry = ee.FeatureCollection(get_haouz_asset()).geometry()
    era5 = ee.ImageCollection("ECMWF/ERA5_LAND/DAILY_AGGR")

    check_bands(era5)

    end_year = args.end_year if args.end_year else args.year
    for year in range(args.year, end_year + 1):
        export_year(year, geometry, era5)


if __name__ == "__main__":
    main()

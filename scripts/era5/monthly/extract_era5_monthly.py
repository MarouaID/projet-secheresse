"""
ERA5-Land monthly extraction for the Haouz plain (1981-2025).
Exports a single CSV to Google Drive: era5land_haouz_monthly_1981_2025.csv
Once done, download it into data/raw/era5/.

Aggregation rules:
    - SUM  : total_precipitation, potential_evaporation, surface_solar_radiation
    - MEAN : everything else (temperature, wind, pressure, soil water)

Usage:
    python scripts/era5/monthly/extract_era5_monthly.py
    python scripts/era5/monthly/extract_era5_monthly.py --start_year 1981 --end_year 2025
"""

import argparse
import sys
from pathlib import Path

import ee

sys.path.append(str(Path(__file__).resolve().parents[3]))
from scripts.gee_connection import connect, get_haouz_asset

# ==========================================
# PARAMETRES ET AGREGATION
# ==========================================

MEAN_BANDS = [
    "temperature_2m",
    "temperature_2m_max",
    "temperature_2m_min",
    "dewpoint_temperature_2m",
    "u_component_of_wind_10m",
    "v_component_of_wind_10m",
    "surface_pressure",
    "volumetric_soil_water_layer_1",
    "volumetric_soil_water_layer_2",
    "volumetric_soil_water_layer_3",
    "volumetric_soil_water_layer_4",
]

SUM_BANDS = [
    "total_precipitation_sum",
    "potential_evaporation_sum",
    "surface_solar_radiation_downwards_sum",
]

MEAN_NAMES = [
    "T2M_K",
    "T2M_MAX_K",
    "T2M_MIN_K",
    "T2M_DEW_K",
    "U10",
    "V10",
    "PS_PA",
    "SWVL1",
    "SWVL2",
    "SWVL3",
    "SWVL4",
]

SUM_NAMES = [
    "TP_M",
    "PET_M",
    "SSRD_J_M2",
]

ALL_BANDS   = MEAN_BANDS + SUM_BANDS
ALL_NAMES   = MEAN_NAMES + SUM_NAMES
SELECTORS   = ["YEAR", "MONTH"] + ALL_NAMES


# ==========================================
# CONSTRUCTION DE LA COLLECTION MENSUELLE
# ==========================================

def build_monthly_collection(
    era5: ee.ImageCollection,
    geometry: ee.Geometry,
    start_year: int,
    end_year: int,
) -> ee.FeatureCollection:

    months = ee.List.sequence(1, 12)
    years  = ee.List.sequence(start_year, end_year)

    def process_month(y_m):
        y_m   = ee.List(y_m)
        year  = ee.Number(y_m.get(0)).toInt()
        month = ee.Number(y_m.get(1)).toInt()

        start = ee.Date.fromYMD(year, month, 1)
        end   = start.advance(1, "month")

        monthly_mean = (
            era5.filterDate(start, end)
            .select(MEAN_BANDS, MEAN_NAMES)
            .mean()
        )

        monthly_sum = (
            era5.filterDate(start, end)
            .select(SUM_BANDS, SUM_NAMES)
            .sum()
        )

        image = monthly_mean.addBands(monthly_sum)

        stats = image.reduceRegion(
            reducer=ee.Reducer.mean(),
            geometry=geometry,
            scale=11132,
            maxPixels=1e9,
        )

        return ee.Feature(None, stats).set({"YEAR": year, "MONTH": month})

    year_month_pairs = years.map(lambda y: months.map(lambda m: ee.List([y, m]))).flatten()

    return ee.FeatureCollection(year_month_pairs.map(process_month))


# ==========================================
# EXPORT VERS DRIVE
# ==========================================

def export_monthly(start_year: int, end_year: int) -> None:

    connect()
    print("Connexion GEE reussie.")

    geometry = ee.FeatureCollection(get_haouz_asset()).geometry()
    era5     = ee.ImageCollection("ECMWF/ERA5_LAND/DAILY_AGGR")

    print(f"Construction de la collection mensuelle {start_year}-{end_year}...")

    monthly_fc = build_monthly_collection(era5, geometry, start_year, end_year)

    filename = f"era5land_haouz_monthly_{start_year}_{end_year}"

    task = ee.batch.Export.table.toDrive(
        collection=monthly_fc,
        description=filename,
        folder="DroughtProject_ERA5Land",
        fileNamePrefix=filename,
        fileFormat="CSV",
        selectors=SELECTORS,
    )

    task.start()
    print(f"Export lance — Task ID : {task.id}")
    print(f"Fichier : DroughtProject_ERA5Land/{filename}.csv")


# ==========================================
# POINT D'ENTREE
# ==========================================

def main():
    parser = argparse.ArgumentParser(
        description="Extract ERA5-Land monthly data for the Haouz plain."
    )
    parser.add_argument("--start_year", type=int, default=1981)
    parser.add_argument("--end_year",   type=int, default=2025)
    args = parser.parse_args()

    export_monthly(args.start_year, args.end_year)


if __name__ == "__main__":
    main()

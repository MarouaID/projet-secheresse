"""
ERA5-Land monthly dataset cleaning.

Conversions applied:
    - T2M_K, T2M_MAX_K, T2M_MIN_K, T2M_DEW_K : Kelvin  -> Celsius  (- 273.15)
    - TP_M                                     : meters  -> mm       (* 1000)
    - PET_M                                    : meters  -> mm, absolute value (* -1000)
    - SSRD_J_M2                                : J/m²    -> MJ/m²    (/ 1e6)
    - PS_PA                                    : Pa      -> hPa      (/ 100)
    - DATE column added                        : YYYY-MM-01 format

Output: data/processed/era5land_haouz_monthly_clean.csv

Usage:
    python scripts/era5/cleaning/clean_era5_monthly.py
"""

from pathlib import Path
import pandas as pd

RAW_PATH       = Path("data/raw/era5/era5land_haouz_monthly_1981_2025.csv")
PROCESSED_DIR  = Path("data/processed")
OUTPUT_PATH    = PROCESSED_DIR / "era5land_haouz_monthly_clean.csv"


def load(path: Path) -> pd.DataFrame:
    df = pd.read_csv(path)
    print(f"Loaded : {df.shape[0]} rows x {df.shape[1]} cols")
    return df


def convert_units(df: pd.DataFrame) -> pd.DataFrame:

    # Temperature : K -> °C
    for col in ["T2M_K", "T2M_MAX_K", "T2M_MIN_K", "T2M_DEW_K"]:
        df[col] = df[col] - 273.15

    # Precipitation : m -> mm
    df["TP_M"] = df["TP_M"] * 1000

    # Potential evaporation : m -> mm, ERA5 convention is negative (flip sign)
    df["PET_M"] = df["PET_M"] * -1000

    # Solar radiation : J/m² -> MJ/m²
    df["SSRD_J_M2"] = df["SSRD_J_M2"] / 1e6

    # Pressure : Pa -> hPa
    df["PS_PA"] = df["PS_PA"] / 100

    return df


def rename_columns(df: pd.DataFrame) -> pd.DataFrame:
    return df.rename(columns={
        "T2M_K"     : "T2M_C",
        "T2M_MAX_K" : "T2M_MAX_C",
        "T2M_MIN_K" : "T2M_MIN_C",
        "T2M_DEW_K" : "T2M_DEW_C",
        "TP_M"      : "TP_MM",
        "PET_M"     : "PET_MM",
        "SSRD_J_M2" : "SSRD_MJ_M2",
        "PS_PA"     : "PS_HPA",
    })


def add_date_column(df: pd.DataFrame) -> pd.DataFrame:
    df.insert(0, "DATE", pd.to_datetime(df[["YEAR", "MONTH"]].assign(DAY=1)))
    return df


def validate(df: pd.DataFrame) -> None:
    assert df.isnull().sum().sum() == 0,        "Null values found"
    assert df.duplicated(["YEAR","MONTH"]).sum() == 0, "Duplicate rows found"
    assert (df["TP_MM"] >= 0).all(),            "Negative precipitation found"
    assert (df["PET_MM"] >= 0).all(),           "Negative PET found"
    assert df["T2M_C"].between(-10, 50).all(),  "T2M out of plausible range"
    print("Validation passed.")


def main():
    df = load(RAW_PATH)
    df = convert_units(df)
    df = rename_columns(df)
    df = add_date_column(df)
    validate(df)

    PROCESSED_DIR.mkdir(parents=True, exist_ok=True)
    df.to_csv(OUTPUT_PATH, index=False)
    print(f"Saved  : {OUTPUT_PATH}")
    print(f"Shape  : {df.shape}")
    print(df.head(3).to_string())


if __name__ == "__main__":
    main()

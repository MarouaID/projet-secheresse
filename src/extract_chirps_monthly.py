"""
Extraction de la pluie MENSUELLE CHIRPS v3 pour une liste de points du Maroc.

Objectif
--------
Produire un tableau (CSV) avec une ligne par point et par mois, contenant le
cumul de pluie en millimetres. Ce tableau est la "colonne pluie" du dataset
commun de l'equipe (projet de detection de secheresse au Maroc).

Pourquoi le pas mensuel ?
-------------------------
CHIRPS est un produit construit au pas de 5 jours (pentade) et au mois. Les
valeurs journalieres sont seulement un decoupage de ces totaux, avec des
limites (fausses series de jours pluvieux, risque de fuite de donnees).
Le total mensuel est la valeur la plus solide, et c'est aussi le pas de temps
des indices de secheresse comme le SPI.

Methode
-------
Les pentades d'un mois s'additionnent au total mensuel de CHIRPS. On somme donc
les pentades de chaque mois (collection Earth Engine
"UCSB-CHC/CHIRPS/V3/PENTAD", en mm par pentade), puis on lit la valeur du pixel
a chaque point. Aucun fichier n'est telecharge : le calcul se fait en ligne et
on ne recupere que le petit tableau final.

Installation (dans le .venv du projet)
--------------------------------------
    pip install earthengine-api pandas
    earthengine authenticate        # une seule fois

Utilisation (depuis la racine du projet)
----------------------------------------
    python src/extract_chirps_monthly.py

Sortie
------
Fichier CSV (voir OUTPUT) avec les colonnes :
    point      : nom du point
    lon, lat   : coordonnees en degres decimaux (WGS84)
    date       : premier jour du mois (AAAA-MM-01)
    precip_mm  : cumul de pluie du mois, en mm

Limites a connaitre
-------------------
- La resolution de CHIRPS est d'environ 5,5 km (0,05 degre) : deux points a
  moins de 5 km tombent dans le meme pixel et auront la meme valeur.
- Si un point est sur un pixel sans donnee (par exemple en mer), la valeur
  est manquante (NaN).
- Ce script n'a pas ete execute par son auteur : verifier la premiere sortie.
"""
from pathlib import Path

import ee
import pandas as pd

# ----------------------------------------------------------------------------
# CONFIGURATION : seules ces lignes sont a modifier
# ----------------------------------------------------------------------------

# Identifiant du projet Google Cloud enregistre pour Earth Engine.
PROJECT = "projetmagma"

# Periode a extraire (annees completes uniquement).
START_YEAR = 1981
END_YEAR = 2025

# Points a extraire : {"nom": (longitude, latitude)}.
# ATTENTION : Earth Engine attend l'ordre (longitude, latitude).
# Ces 8 villes sont des points de TEST, a remplacer par la liste choisie
# par l'equipe.
POINTS = {
    "Rabat": (-6.84, 34.02),
    "Tanger": (-5.80, 35.76),
    "Fes": (-5.00, 34.03),
    "Oujda": (-1.91, 34.68),
    "Marrakech": (-7.98, 31.63),
    "Agadir": (-9.60, 30.43),
    "Ouarzazate": (-6.89, 30.92),
    "Laayoune": (-13.20, 27.15),
}

# Fichier de sortie (le dossier est cree s'il n'existe pas).
OUTPUT = "data/raw/chirps_monthly_morocco.csv"

# Taille d'un pixel CHIRPS en metres (valeur donnee par le catalogue Earth Engine).
PIXEL_SCALE_M = 5566


# ----------------------------------------------------------------------------
# FONCTIONS
# ----------------------------------------------------------------------------

def build_points(points: dict) -> ee.FeatureCollection:
    """Convertit le dictionnaire de points en collection Earth Engine.

    Parameters
    ----------
    points : dict
        Dictionnaire {nom: (longitude, latitude)}.

    Returns
    -------
    ee.FeatureCollection
        Une entite par point, avec les proprietes "point", "lon" et "lat".
        Ces proprietes sont recopiees dans les resultats, ce qui permet de
        retrouver le nom et les coordonnees de chaque ligne.
    """
    features = [
        ee.Feature(
            ee.Geometry.Point([lon, lat]),
            {"point": name, "lon": lon, "lat": lat},
        )
        for name, (lon, lat) in points.items()
    ]
    return ee.FeatureCollection(features)


def monthly_values(
    pentads: ee.ImageCollection,
    points: ee.FeatureCollection,
    year: int,
    month: int,
) -> ee.FeatureCollection:
    """Calcule le cumul de pluie d'un mois a chaque point.

    Parameters
    ----------
    pentads : ee.ImageCollection
        Collection CHIRPS par pentade (bande "precipitation", en mm/pentade).
    points : ee.FeatureCollection
        Points ou lire la valeur.
    year, month : int
        Annee et mois (1 a 12) a calculer.

    Returns
    -------
    ee.FeatureCollection
        Les points d'entree, avec en plus les proprietes "first" (le cumul en
        mm), "year" et "month". La propriete s'appelle "first" parce que c'est
        le nom donne par le reducteur ee.Reducer.first() ; elle est renommee
        plus tard dans to_dataframe().
    """
    start = ee.Date.fromYMD(year, month, 1)
    end = start.advance(1, "month")

    # Somme des pentades du mois : mm/pentade additionnes = mm/mois.
    monthly_img = pentads.filterDate(start, end).sum()

    # Lecture de la valeur du pixel a chaque point.
    values = monthly_img.reduceRegions(
        collection=points,
        reducer=ee.Reducer.first(),
        scale=PIXEL_SCALE_M,
    )
    return values.map(lambda f: f.set({"year": year, "month": month}))


def extract_year(
    pentads: ee.ImageCollection, points: ee.FeatureCollection, year: int
) -> list:
    """Extrait les 12 mois d'une annee en un seul appel au serveur.

    On regroupe les 12 mois avant d'appeler getInfo() : un appel par annee
    (45 appels au total) est beaucoup plus rapide qu'un appel par mois (540).

    Returns
    -------
    list of dict
        Une liste de dictionnaires, un par point et par mois.
    """
    collection = monthly_values(pentads, points, year, 1)
    for month in range(2, 13):
        collection = collection.merge(monthly_values(pentads, points, year, month))
    return [feature["properties"] for feature in collection.getInfo()["features"]]


def to_dataframe(rows: list) -> pd.DataFrame:
    """Met les resultats en forme : colonnes propres, dates, tri.

    Parameters
    ----------
    rows : list of dict
        Resultat brut renvoye par extract_year().

    Returns
    -------
    pandas.DataFrame
        Colonnes : point, lon, lat, date, precip_mm, triees par point et date.
    """
    df = pd.DataFrame(rows)

    # Le reducteur first() nomme la colonne "first" : on la renomme.
    df = df.rename(columns={"first": "precip_mm"})

    # Date = premier jour du mois, a partir des colonnes year et month.
    df["date"] = pd.to_datetime(df[["year", "month"]].assign(day=1))

    df = df[["point", "lon", "lat", "date", "precip_mm"]]
    return df.sort_values(["point", "date"]).reset_index(drop=True)


def main() -> None:
    """Point d'entree : extrait toutes les annees et sauvegarde le CSV."""
    # Connexion a Earth Engine (necessite d'avoir lance
    # "earthengine authenticate" au moins une fois).
    ee.Initialize(project=PROJECT)

    pentads = ee.ImageCollection("UCSB-CHC/CHIRPS/V3/PENTAD").select("precipitation")
    points = build_points(POINTS)

    rows = []
    for year in range(START_YEAR, END_YEAR + 1):
        rows.extend(extract_year(pentads, points, year))
        print(f"{year} termine")

    df = to_dataframe(rows)

    output_path = Path(OUTPUT)
    output_path.parent.mkdir(parents=True, exist_ok=True)
    df.to_csv(output_path, index=False)
    print(f"Fichier sauvegarde : {output_path} ({len(df)} lignes)")


if __name__ == "__main__":
    main()
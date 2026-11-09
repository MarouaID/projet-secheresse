# Projet sécheresse Maroc

Application qui **prévoit la sécheresse** au Maroc (3 types) et **conseille** les agriculteurs et éleveurs sur leurs besoins en eau.

## 1. Objectifs

1. **Prévoir la sécheresse** avec un indicateur par type :

| Type | Indicateur | Horizon |
| --- | --- | --- |
| Météorologique | SPI 3 | mois suivant |
| Agricole | SPEI 3 | mois suivant |
| Hydrologique | SPI 12 | dans 6 mois |

2. **Module Cultures** : besoin net en eau (Kc, pluie efficace), risque de perte de rendement (Ky), économie d'eau selon l'irrigation.
3. **Module Élevage** : besoin par jour, autonomie et stock d'eau à prévoir (vaches, chèvres, dindes, poules), ajustés à la température et à la sécheresse prévues.

## 2. Décisions de cadrage

| Sujet | Choix |
| --- | --- |
| Pas de temps | mensuel |
| Unité spatiale | **Région Marrakech-Safi uniquement** (extension aux autres régions = option) |
| Période | 1984 à aujourd'hui |
| Découpe temporelle | train jusqu'en 2015, validation 2016-2020, test dès 2021 (jamais au hasard) |
| Modèles | références (climatologie, persistance) + XGBoost/LightGBM |
| Cultures v1 | céréales, olivier, tomate (agrumes, maïs en option) |
| Animaux v1 | poules, vaches (chèvres, dindes = une ligne de plus dans le CSV) |
| Appli | Streamlit |

## 3. Plan général, étape par étape

### Étape 0 : Démarrage
- Cloner le dépôt, créer le `.venv`, installer `requirements.txt`.
- Valider ensemble ce README et les interfaces (section 6).
- Mettre en place la CI (GitHub Actions) et un test minimal.
- **Livrable** : tout le monde lance `python -m pytest` en local.

### Étape 1 : Collecte et préparation des données
- Télécharger NASA POWER (température, rayonnement, humidité, vent), CHIRPS (pluie) et l'indice NAO.
- Récupérer le polygone de la région Marrakech-Safi (limites officielles HCP ou OpenStreetMap, à vérifier).
- Agréger les pixels de la région par mois (moyenne), nettoyer (valeurs manquantes, unités), contrôler la cohérence.
- Commencer à remplir `cultures.csv` et `animaux.csv` avec leurs sources.
- **Livrable** : tableau mensuel 1984-2025 propre pour Marrakech-Safi.

### Étape 2 : Indicateurs de sécheresse
- Calculer SPI 3 et SPI 12 sur l'historique, calibrés sur la période d'entraînement seulement.
- Définir les classes de sécheresse et les règles début, aggravation, maintien, amélioration.
- Vérifier que les années sèches connues (2022, 2023) ressortent.
- **Livrable** : `marrakech_mois.parquet` avec `spi3` et `spi12`.

### Étape 3 : ETo et SPEI
- Calculer l'ETo (Penman-Monteith sur le passé, Hargreaves pour le futur), puis le SPEI 3.
- Gérer les mois à 0 mm (été sec) dans l'ajustement du SPI.
- **Livrable** : colonnes `eto` et `spei3` validées.

### Étape 4 : Modèles de prévision
- Construire le jeu de données ML (décalages de pluie et température, NAO décalée, mois, région).
- Modèles de référence : climatologie et persistance.
- Modèles XGBoost/LightGBM : température du mois suivant, pluie du mois suivant, somme des pluies des 6 mois suivants.
- Évaluer (MAE, RMSE) face aux références.
- **Livrable** : tableau de comparaison modèles vs références.

### Étape 5 : Prévision des indicateurs
- Reconstruire SPI 3, SPEI 3 et SPI 12 prévus (pluie prévue + mois déjà observés).
- Ajouter une indication d'incertitude.
- Évaluer sur les indicateurs (MAE sur le SPI/SPEI, F1 sur les classes).
- **Livrable** : `previsions.parquet`.

### Étape 6 : Modules Cultures et Élevage
- Finaliser `cultures.csv` (Kc, stades, Ky) et `animaux.csv`, avec la source de chaque ligne.
- Coder les fonctions : besoin net, déficit, risque de perte de rendement (pluvial), économie d'eau, besoin par jour, autonomie, stock à prévoir, alerte chaleur.
- Tester sur les exemples chiffrés (par exemple 10 ha, 52 mm : ~5 800 m³ en goutte-à-goutte).
- **Livrable** : fonctions testées dans `src/`.

### Étape 7 : Application
- Carte de la région Marrakech-Safi avec le niveau de sécheresse prévu (et courbes des indicateurs dans le temps).
- Choix du profil (agriculteur ou éleveur), saisie, résultats et conseils.
- Brancher l'appli sur les prévisions et les modules.
- **Livrable** : appli Streamlit fonctionnelle.

### Étape 8 : Finalisation
- Tests de bout en bout, correction des bugs.
- Rapport : méthode, résultats, limites (une seule région, peu de données de test, incertitude à 6 mois).
- Préparation de la démo.
- **Options si le temps le permet** : agrumes et maïs, validation par les barrages, NDVI, extension aux autres régions.

## 4. Structure du dépôt

```
projet-secheresse/
├── data/
│   ├── raw/          # données brutes (ignorées par Git)
│   ├── processed/    # tables propres
│   ├── cultures.csv  # Kc, stades, Ky, source
│   └── animaux.csv   # consommation par animal, source
├── src/              # code (ingestion, indicateurs, ml, calculs)
├── notebooks/        # exploration
├── tests/            # pytest
├── app/              # Streamlit
└── .github/workflows/ci.yml
```

## 5. Règles de travail

- Une branche par tâche, puis Pull Request relue par une autre personne.
- `git pull` avant de commencer, commits courts et clairs.
- Pas de gros fichiers dans Git.
- Chaque fonction de calcul a au moins un test.
- Chaque paramètre (Kc, Ky, litres par animal) cite sa source.
- Point de synchro court régulièrement.

## 6. Interfaces entre modules

Tant que le vrai fichier n'existe pas, on travaille avec un faux fichier au bon format.

- **`marrakech_mois.parquet`** : `date, pluie_mm, tmax, tmin, eto, nao, spi3, spei3, spi12`
- **`previsions.parquet`** : mêmes colonnes + `horizon` + colonnes d'incertitude
- **`cultures.csv`** : `culture, stade, kc, duree_jours, ky_saison, source`
- **`animaux.csv`** : `animal, variante, litres_par_jour, facteur_chaleur, source`

## 7. Installation

```bash
git clone https://github.com/MarouaID/projet-secheresse.git
cd projet-secheresse
python -m venv .venv
.venv\Scripts\activate            # Windows (Mac/Linux : source .venv/bin/activate)
python -m pip install -r requirements.txt
python -m pytest
```

## 8. Sources de données

CHIRPS (pluie), NASA POWER (température, rayonnement, humidité, vent), indice NAO (NOAA), frontières administratives (HCP ou OpenStreetMap, à vérifier), FAO Paper 56 (Kc, durée des stades), FAO Paper 66 (Ky). Optionnel : taux de remplissage des barrages, MODIS NDVI, ERA5-Land.

// ==========================================
// PLAINE DU HAOUZ — Délimitation automatique
// via MNT SRTM (élévation < 900m, pente < 4°)
//
// À exécuter dans l'éditeur de code GEE :
// https://code.earthengine.google.com/
//
// Avant de lancer : remplacer YOUR_GEE_PROJECT_ID
// par votre propre projet GEE dans la section 8.
// ==========================================


// ==========================================
// 1. CENTRE ET EMPRISE GEOGRAPHIQUE
// ==========================================

var marrakech = ee.Geometry.Point([-8.0, 31.63]);

var bbox = ee.Geometry.Rectangle([
  -9.3, 31.0,
  -7.0, 32.1
]);


// ==========================================
// 2. MODELE NUMERIQUE DE TERRAIN
// ==========================================

var dem = ee.Image('USGS/SRTMGL1_003')
  .select('elevation')
  .clip(bbox);

var slope = ee.Terrain.slope(dem);


// ==========================================
// 3. IDENTIFICATION DE LA PLAINE
// ==========================================

var plaine = dem.lt(900)
  .and(slope.lt(4))
  .rename('zone')
  .toByte();

var plaineLisse = plaine
  .focalMode(10, 'circle', 'pixels')
  .selfMask();


// ==========================================
// 4. CONVERSION EN POLYGONES
// ==========================================

var vecteurs = plaineLisse.reduceToVectors({
  geometry: bbox,
  scale: 120,
  geometryType: 'polygon',
  eightConnected: true,
  maxPixels: 1e10,
  bestEffort: false,
  tileScale: 4
});

var candidats = vecteurs.filterBounds(marrakech);

print('Nombre de polygones retenus:', candidats.size());

var haouz = candidats.geometry(100);


// ==========================================
// 5. LISSAGE ET LIMITES GEOGRAPHIQUES
// ==========================================

haouz = haouz
  .buffer(1000, 100)
  .buffer(-1000, 100);

var limites = ee.Geometry.Rectangle([
  -8.9, 31.0,
  -7.0, 31.75
]);

haouz = haouz
  .intersection(limites, 100)
  .simplify(200);


// ==========================================
// 6. AFFICHAGE ET VALIDATION
// ==========================================

Map.centerObject(haouz, 9);

Map.addLayer(haouz,   { color: 'red' },        'Plaine du Haouz', true, 0.4);
Map.addLayer(dem,     { min: 400, max: 1500 }, 'Elevation SRTM',  false);
Map.addLayer(slope,   { min: 0,   max: 20 },   'Pente',           false);

print('Surface du Haouz (km2):', haouz.area(100).divide(1e6));
print('Geometrie finale:', haouz);


// ==========================================
// 7. GEOMETRIE UTILISABLE POUR ERA5-LAND
// ==========================================

var geometry = haouz;


// ==========================================
// 8. EXPORTER LA GEOMETRIE VERS GEE ASSETS
//
// Remplacer YOUR_GEE_PROJECT_ID par votre projet
// ex: assetId: 'projects/drought-515513/assets/haouz_boundary'
// ==========================================

var haouzAsset = ee.FeatureCollection([
  ee.Feature(geometry).set({
    name: 'Haouz',
    method: 'SRTM elevation < 900m and slope < 4 degrees',
    type: 'approximate_study_area'
  })
]);

Export.table.toAsset({
  collection: haouzAsset,
  description: 'Haouz_Boundary',
  assetId: 'projects/YOUR_GEE_PROJECT_ID/assets/haouz_boundary'
});

print('Haouz geometry ready for export.');

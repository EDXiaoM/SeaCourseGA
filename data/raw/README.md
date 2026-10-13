# Dataset · Набор данных

Place the labelled dataset here as `merged.json` (GeoJSON FeatureCollection,
152 838 WGS-84 points of four classes, 116 MB). It is attached to the GitHub
release of this repository as `merged_json_v1_course.zip`:
<https://github.com/EDXiaoM/SeaCourseGA/releases/tag/v1.0>

Поместите размеченный набор данных сюда под именем `merged.json`. Он приложен
к релизу репозитория как `merged_json_v1_course.zip`.

Each point carries `latitude`, `longitude`, `class_code` (one of `OPEN_SEA`,
`COASTAL_SEA`, `NEAR_COAST`, `COASTLINE`) and `noaa_depth`; the application can
also open any other GeoJSON, CSV or JSON file with these columns
(menu *File → Open dataset…*).

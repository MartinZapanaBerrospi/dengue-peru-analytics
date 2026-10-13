"""Parámetros del proyecto: periodo, fuentes, rutas y reglas."""

from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
DATA = ROOT / "data"
RAW = DATA / "raw"
DOWNLOADS = RAW / "descarga"      # archivos bajados desde el navegador
STAGING = DATA / "staging"
CURATED = DATA / "curated"
REFERENCE = DATA / "reference"
SOURCES = ROOT / "docs" / "fuentes"
REPORTS = ROOT / "reports"
QUALITY = REPORTS / "calidad"
MANIFEST = RAW / "manifest.csv"
PORTAL_INVENTORY = REFERENCE / "inventario_portal.csv"

# Periodo de la vigilancia en el conjunto abierto (años completos) y desde cuándo hay población.
FIRST_YEAR = 2000
LAST_YEAR = 2024
POPULATION_FROM = 2013

PORTAL = "https://www.datosabiertos.gob.pe"
FILE_URL = PORTAL + "/sites/default/files/{name}"
DATASET_PAGES = {
    "dengue": PORTAL + "/dataset/vigilancia-epidemiol%C3%B3gica-de-dengue",
    "indicadores": PORTAL + "/dataset/indicadores-de-seguridad-ciudadana-y-tendencias-territoriales-mininter",
}
DOWNLOAD_URLS = {
    "dengue": FILE_URL.format(name="datos_abiertos_vigilancia_dengue_2000_2024.csv"),
    "indicadores": PORTAL + "/node/23663/dataset/download",
}
SALA_URL = "https://www.dge.gob.pe/portal/docs/vigilancia/sala/2026/SE33/dengue.pdf"

# Qué se registra: (clave, archivo bajado en data/raw/descarga/, ruta dentro del zip o None, nombre en el portal,
# destino). "ruta" es una lista cuando el archivo está dentro de un zip anidado.
SPEC = [
    ("dengue", "datos_abiertos_vigilancia_dengue_2000_2024.csv", None,
     "datos_abiertos_vigilancia_dengue_2000_2024.csv", RAW / "dengue.csv"),
    ("indicadores", "mininter_indicadores_2026-10-13.zip",
     ["DataSet_Ind_Plan_Acc_Segu_Ciud_Jul 2026.zip",
      "DataSet_Ind_Plan_Acc_Segu_Ciud_Jul 2026/DATASET_Ind_ Plan_Acc_Seg_Ciud_2009 a Jul 2026.csv"],
     "DataSet_Ind_Plan_Acc_Segu_Ciud_Jul 2026.zip", RAW / "indicadores.csv"),
]

# Archivos de referencia que se guardan en el repositorio (el sitio del CDC sí acepta descargas por script).
REFERENCE_FILES = [
    ("sala_cdc", "sala_dengue_SE33_2026.pdf", SALA_URL),
]

# Reglas
VALID_FORMS = ["DENGUE SIN SIGNOS DE ALARMA", "DENGUE CON SIGNOS DE ALARMA", "DENGUE GRAVE"]
MAX_AGE_YEARS = 110

"""Validaciones de exactitud: lo que el pipeline reconstruye frente a cifras oficiales.

V1  Casos por año del archivo frente a la tabla oficial de la sala situacional del CDC (2012–2024).
V2  Casos y formas clínicas de 2023 frente a la alerta epidemiológica AE-CDC N.° 006-2024.
V3  Población usada frente a la población implícita en la incidencia oficial de 2023.
V4  Población: departamentos y provincias frente al total nacional.

El script falla si una validación bloqueante no cuadra; las diferencias que no son errores
(cortes de datos distintos) se marcan como `info` y se explican en docs/02_calidad.md.

Uso:
    python -m src.validate
"""

import sys

import numpy as np
import pandas as pd

from src import config, parse

CASES_TOLERANCE_PCT = 0.05          # el archivo debe ser la serie vigente del CDC
FORM_SHARE_TOLERANCE_PCT = 3.0      # reparto por forma clínica de 2023 (cortes distintos)
POPULATION_TOLERANCE_PCT = 1.0
SUM_TOLERANCE_PCT = 0.01

# Alerta epidemiológica AE-CDC N.° 006-2024 (docs/fuentes/alerta_AE-CDC_006_2024_dengue.pdf), año 2023
ALERT_2023 = {"casos": 273684, "incidencia": 808.9, "sin signos": 242118, "con signos": 30512, "grave": 1054}

COLUMNS = ["validacion", "anio", "medida", "oficial", "calculado", "tolerancia_pct", "severidad", "detalle"]


def official_cases() -> pd.DataFrame:
    return pd.read_csv(config.REFERENCE / "cdc_sala_casos_fallecidos.csv")


def v1_casos_por_anio(dengue: pd.DataFrame) -> pd.DataFrame:
    official = official_cases().set_index("anio")["casos_cdc"]
    ours = dengue.groupby("anio").size()
    rows = [("V1", year, "casos de dengue", float(official[year]), float(ours[year]), CASES_TOLERANCE_PCT,
             "bloqueante", "tabla de casos, fallecidos y letalidad de la sala situacional, SE 33 de 2026")
            for year in range(2012, config.LAST_YEAR + 1)]
    return pd.DataFrame(rows, columns=COLUMNS)


def v2_alerta_2023(dengue: pd.DataFrame) -> pd.DataFrame:
    d = dengue[dengue["anio"] == 2023]
    total = len(d)
    shares = d["cie10"].value_counts()
    official_total = ALERT_2023["casos"]
    rows = [("V2-casos", 2023, "casos de dengue", float(official_total), float(total), None, "info",
             "la alerta es de principios de 2024; el CDC revisa la serie y el archivo coincide con la vigente")]
    for key, code in [("sin signos", "A97.0"), ("con signos", "A97.1"), ("grave", "A97.2")]:
        rows.append(("V2-forma", 2023, f"parte de casos {key} de alarma".replace("grave de alarma", "graves"),
                     100 * ALERT_2023[key] / official_total, 100 * shares[code] / total, FORM_SHARE_TOLERANCE_PCT,
                     "bloqueante", "reparto por forma clínica, en % de los casos del año"))
    return pd.DataFrame(rows, columns=COLUMNS)


def v3_poblacion_implicita(pop: dict) -> pd.DataFrame:
    implied = ALERT_2023["casos"] / ALERT_2023["incidencia"] * 1e5
    ours = float(pop["nacional"].set_index("anio").loc[2023, "poblacion"])
    return pd.DataFrame([("V3", 2023, "población nacional", implied, ours, POPULATION_TOLERANCE_PCT, "bloqueante",
                          "casos / incidencia oficial (808,9 por 100 mil) frente a la proyección del MININTER")],
                        columns=COLUMNS)


def v4_poblacion(pop: dict) -> pd.DataFrame:
    national = pop["nacional"].set_index("anio")["poblacion"]
    departments = pop["departamento"].groupby("anio")["poblacion"].sum()
    provinces = pop["provincia"].groupby("anio")["poblacion"].sum()
    rows = []
    for year in range(config.POPULATION_FROM, config.LAST_YEAR + 1):
        rows.append(("V4-departamentos", year, "población de los departamentos", float(national[year]),
                     float(departments[year]), SUM_TOLERANCE_PCT, "bloqueante", "suma de los departamentos"))
        # Hasta 2015 el conjunto trae solo parte de las provincias: la incidencia provincial empieza en 2016
        severity = "bloqueante" if year >= 2016 else "alerta"
        rows.append(("V4-provincias", year, "población de las provincias", float(national[year]),
                     float(provinces[year]), SUM_TOLERANCE_PCT, severity, "suma de las provincias"))
    return pd.DataFrame(rows, columns=COLUMNS)


def finish(table: pd.DataFrame) -> pd.DataFrame:
    table = table.copy()
    table["diferencia_pct"] = (100 * (table["calculado"] / table["oficial"] - 1)).round(3)
    within = table["diferencia_pct"].abs().le(table["tolerancia_pct"].fillna(np.inf))
    table["resultado"] = np.where(table["tolerancia_pct"].isna(), "info",
                                  np.where(within, "cumple", np.where(table["severidad"] == "alerta", "alerta", "falla")))
    return table


def compare_all(dengue: pd.DataFrame, pop: dict) -> pd.DataFrame:
    parts = [v1_casos_por_anio(dengue), v2_alerta_2023(dengue), v3_poblacion_implicita(pop), v4_poblacion(pop)]
    return finish(pd.concat(parts, ignore_index=True))


def main() -> int:
    if hasattr(sys.stdout, "reconfigure"):
        sys.stdout.reconfigure(encoding="utf-8")
    pop = parse.population(parse.read_indicadores())
    table = compare_all(parse.read_dengue(), pop)
    config.REPORTS.mkdir(parents=True, exist_ok=True)
    table.to_csv(config.REPORTS / "validaciones.csv", index=False)
    with pd.option_context("display.width", 200, "display.max_rows", None):
        print(table[["validacion", "anio", "oficial", "calculado", "diferencia_pct", "resultado"]].to_string(index=False))
    return 1 if (table["resultado"] == "falla").any() else 0


if __name__ == "__main__":
    sys.exit(main())

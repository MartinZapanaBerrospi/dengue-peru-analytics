"""Fase 3 — Transforma los casos: raw → staging → modelo en estrella (data/curated).

    raw       CSV del portal, un caso por fila (data/raw)
    staging   casos con tipos, claves territoriales y edad en años (data/staging/casos.parquet)
    curated   hechos y dimensiones que lee Power BI (data/curated/*.csv)

Ningún caso se excluye: lo que la Fase 2 marcó queda como marca o como grupo «sin edad válida». El
linaje (casos en cada paso) se escribe en reports/linaje.csv y el script falla si un paso pierde o
duplica un caso.

Uso:
    python -m src.transform
"""

import sys

import numpy as np
import pandas as pd

from src import config, parse

MIN_HISTORY_YEARS = 5            # años previos para el canal endémico
CHANNEL_FROM = config.FIRST_YEAR + MIN_HISTORY_YEARS
CHANNEL_PERCENTILE = 90          # sobre este percentil del histórico, la semana está fuera del canal
CHANNEL_MIN_CASES = 10         # una semana con menos casos no se marca, aunque supere el percentil
FORMS = [(1, "Sin signos de alarma", "A97.0", 0), (2, "Con signos de alarma", "A97.1", 1), (3, "Grave", "A97.2", 1)]
SMALL_WORDS = {"de", "del", "la", "las", "los", "y", "el", "e", "en"}
EDAD_ORDEN = [name for _, name in parse.AGE_GROUPS] + [parse.AGE_GROUP_UNKNOWN]


def proper(text: str) -> str:
    """'SAN JUAN DE LURIGANCHO' -> 'San Juan de Lurigancho'."""
    words = text.lower().split()
    return " ".join(w if i and w in SMALL_WORDS else w.capitalize() for i, w in enumerate(words))


# ---------------------------------------------------------------------------------------------
# Dimensiones
# ---------------------------------------------------------------------------------------------

def dim_departamento() -> pd.DataFrame:
    return pd.read_csv(config.REFERENCE / "departamentos.csv", dtype={"departamento_id": str})


def dim_provincia(cases: pd.DataFrame) -> pd.DataFrame:
    names = cases.groupby("provincia_id")["provincia"].agg(lambda s: s.value_counts().index[0])
    out = names.rename("provincia_fuente").reset_index()
    out["provincia"] = out["provincia_fuente"].map(proper)
    out["departamento_id"] = out["provincia_id"].str[:2]
    homonym = out["provincia"].duplicated(keep=False)
    deps = dim_departamento().set_index("departamento_id")["departamento"]
    out["provincia_unica"] = out["provincia"].where(~homonym, out["provincia"] + " (" + out["departamento_id"].map(deps) + ")")
    return out[["provincia_id", "provincia", "provincia_unica", "departamento_id"]].sort_values("provincia_id").reset_index(drop=True)


def dim_distrito(cases: pd.DataFrame, register: set) -> pd.DataFrame:
    names = cases.groupby("ubigeo")["distrito"].agg(lambda s: s.value_counts().index[0])
    out = names.rename("distrito_fuente").reset_index()
    out["distrito"] = out["distrito_fuente"].map(proper)
    out["provincia_id"] = out["ubigeo"].str[:4]
    out["departamento_id"] = out["ubigeo"].str[:2]
    provinces = dim_provincia(cases).set_index("provincia_id")["provincia"]
    out["provincia"] = out["provincia_id"].map(provinces)
    homonym = out["distrito"].duplicated(keep=False)
    out["distrito_unico"] = out["distrito"].where(~homonym, out["distrito"] + " (" + out["provincia"] + ")")
    out["distrito_en_padron"] = out["ubigeo"].isin(register).astype(int)         # problema 11
    cols = ["ubigeo", "distrito", "distrito_unico", "provincia_id", "departamento_id", "distrito_en_padron"]
    return out[cols].sort_values("ubigeo").reset_index(drop=True)


def dim_anio() -> pd.DataFrame:
    years = list(range(config.FIRST_YEAR, config.LAST_YEAR + 1))
    return pd.DataFrame({
        "anio": years,
        "decada": [f"{y // 10 * 10}s" for y in years],
        "forma_comparable": [int(y >= 2011) for y in years],                   # problema 4
        "con_poblacion": [int(y >= config.POPULATION_FROM) for y in years],
        "con_poblacion_provincial": [int(y >= 2016) for y in years],           # problema 9
    })


def dim_semana() -> pd.DataFrame:
    weeks = list(range(1, 54))
    return pd.DataFrame({"semana": weeks, "trimestre_epi": ["T" + str(min((w - 1) // 13 + 1, 4)) for w in weeks]})


def dim_forma_clinica() -> pd.DataFrame:
    return pd.DataFrame(FORMS, columns=["forma_clinica_id", "forma_clinica", "cie10", "alarma_o_grave"])


def dim_grupo_edad() -> pd.DataFrame:
    return pd.DataFrame({"grupo_edad_id": range(1, len(EDAD_ORDEN) + 1), "grupo_edad": EDAD_ORDEN})


def dim_sexo() -> pd.DataFrame:
    return pd.DataFrame({"sexo_id": ["F", "M"], "sexo": ["Mujer", "Hombre"]})


# ---------------------------------------------------------------------------------------------
# Hechos
# ---------------------------------------------------------------------------------------------

def fact_caso(cases: pd.DataFrame) -> pd.DataFrame:
    """Casos por año × semana × distrito × forma clínica × grupo de edad × sexo.

    `edad_suma` y `casos_con_edad` permiten calcular la edad promedio con DAX sin llevar un caso por fila.
    """
    form_id = dim_forma_clinica().set_index("cie10")["forma_clinica_id"]
    age_id = dim_grupo_edad().set_index("grupo_edad")["grupo_edad_id"]
    d = cases.assign(forma_clinica_id=cases["cie10"].map(form_id), grupo_edad_id=cases["grupo_edad"].map(age_id),
                     sexo_id=cases["sexo"], edad_valida=cases["edad_anios"].notna().astype(int),
                     edad_para_suma=cases["edad_anios"].fillna(0.0))
    keys = ["anio", "semana", "ubigeo", "forma_clinica_id", "grupo_edad_id", "sexo_id"]
    out = d.groupby(keys, as_index=False).agg(casos=("sexo", "size"), edad_suma=("edad_para_suma", "sum"),
                                              casos_con_edad=("edad_valida", "sum"))
    out["edad_suma"] = out["edad_suma"].round(3)
    return out.sort_values(keys).reset_index(drop=True)


def fact_poblacion_departamento(pop: dict) -> pd.DataFrame:
    out = pop["departamento"]
    out = out[out["anio"].between(config.POPULATION_FROM, config.LAST_YEAR)]
    return out[["departamento_id", "anio", "poblacion"]].astype({"poblacion": int}).sort_values(["departamento_id", "anio"]).reset_index(drop=True)


def fact_poblacion_provincia(pop: dict, provinces: pd.DataFrame) -> pd.DataFrame:
    out = pop["provincia"]
    out = out[out["anio"].between(2016, config.LAST_YEAR) & out["provincia_id"].isin(provinces["provincia_id"])]
    return out[["provincia_id", "anio", "poblacion"]].astype({"poblacion": int}).sort_values(["provincia_id", "anio"]).reset_index(drop=True)


def weeks_in_year(cases: pd.DataFrame) -> dict:
    """52 semanas, o 53 en los años donde el archivo trae casos en esa semana (problema 15)."""
    return {y: int(53 if (g == 53).any() else 52) for y, g in cases.groupby("anio")["semana"]}


def endemic_channel(counts: np.ndarray, years: list[int], weeks: int, percentiles: tuple) -> dict:
    """Canal endémico: para cada año desde CHANNEL_FROM y cada semana, los percentiles de los 5 años previos
    en la misma semana y las dos vecinas. `counts` es años × semanas (índice 0 = semana 1)."""
    out = {}
    for yi, year in enumerate(years):
        if year < CHANNEL_FROM:
            continue
        history = counts[yi - MIN_HISTORY_YEARS:yi]
        for w in range(weeks):
            window = history[:, max(w - 1, 0):min(w + 2, counts.shape[1])].ravel()
            out[(year, w + 1)] = np.percentile(window, percentiles)
    return out


def canal_arrays(cases: pd.DataFrame) -> tuple[list[int], dict]:
    years = list(range(config.FIRST_YEAR, config.LAST_YEAR + 1))
    weekly = cases.groupby(["departamento_id", "anio", "semana"]).size()
    return years, weekly


def fact_canal_endemico(cases: pd.DataFrame) -> pd.DataFrame:
    years, weekly = canal_arrays(cases)
    wy = weeks_in_year(cases)
    rows = []
    for dep in sorted(cases["departamento_id"].unique()):
        matrix = np.zeros((len(years), 53))
        if dep in weekly.index.get_level_values(0):
            for (y, w), n in weekly.loc[dep].items():
                matrix[years.index(y), w - 1] = n
        stats = endemic_channel(matrix, years, 53, (50, CHANNEL_PERCENTILE))
        for (year, week), (median, threshold) in stats.items():
            if week > wy[year]:
                continue
            n = int(matrix[years.index(year), week - 1])
            rows.append((dep, year, week, n, round(float(median), 2), round(float(threshold), 2),
                         int(n > threshold and n >= CHANNEL_MIN_CASES)))
    return pd.DataFrame(rows, columns=["departamento_id", "anio", "semana", "casos", "mediana_historica", "umbral",
                                       "sobre_canal"])


def fact_canal_nacional(cases: pd.DataFrame) -> pd.DataFrame:
    years = list(range(config.FIRST_YEAR, config.LAST_YEAR + 1))
    wy = weeks_in_year(cases)
    weekly = cases.groupby(["anio", "semana"]).size()
    matrix = np.zeros((len(years), 53))
    for (y, w), n in weekly.items():
        matrix[years.index(y), w - 1] = n
    stats = endemic_channel(matrix, years, 53, (25, 50, CHANNEL_PERCENTILE))
    rows = []
    for (year, week), (p25, p50, p75) in stats.items():
        if week > wy[year]:
            continue
        n = int(matrix[years.index(year), week - 1])
        rows.append((year, week, n, round(float(p25), 2), round(float(p50), 2), round(float(p75), 2), int(n > p75)))
    return pd.DataFrame(rows, columns=["anio", "semana", "casos", "p25", "mediana_historica", "umbral", "sobre_canal"])


# ---------------------------------------------------------------------------------------------
# Integridad y linaje
# ---------------------------------------------------------------------------------------------

KEYS = {
    "fact_caso": ["anio", "semana", "ubigeo", "forma_clinica_id", "grupo_edad_id", "sexo_id"],
    "fact_poblacion_departamento": ["departamento_id", "anio"],
    "fact_poblacion_provincia": ["provincia_id", "anio"],
    "fact_canal_endemico": ["departamento_id", "anio", "semana"],
    "fact_canal_nacional": ["anio", "semana"],
    "dim_distrito": ["ubigeo"], "dim_provincia": ["provincia_id"], "dim_departamento": ["departamento_id"],
    "dim_anio": ["anio"], "dim_semana": ["semana"], "dim_forma_clinica": ["forma_clinica_id"],
    "dim_grupo_edad": ["grupo_edad_id"], "dim_sexo": ["sexo_id"],
}
FOREIGN = [
    ("fact_caso", "anio", "dim_anio", "anio"), ("fact_caso", "semana", "dim_semana", "semana"),
    ("fact_caso", "ubigeo", "dim_distrito", "ubigeo"), ("fact_caso", "forma_clinica_id", "dim_forma_clinica", "forma_clinica_id"),
    ("fact_caso", "grupo_edad_id", "dim_grupo_edad", "grupo_edad_id"), ("fact_caso", "sexo_id", "dim_sexo", "sexo_id"),
    ("fact_poblacion_departamento", "departamento_id", "dim_departamento", "departamento_id"),
    ("fact_poblacion_departamento", "anio", "dim_anio", "anio"),
    ("fact_poblacion_provincia", "provincia_id", "dim_provincia", "provincia_id"),
    ("fact_poblacion_provincia", "anio", "dim_anio", "anio"),
    ("fact_canal_endemico", "departamento_id", "dim_departamento", "departamento_id"),
    ("fact_canal_endemico", "anio", "dim_anio", "anio"), ("fact_canal_endemico", "semana", "dim_semana", "semana"),
    ("fact_canal_nacional", "anio", "dim_anio", "anio"), ("fact_canal_nacional", "semana", "dim_semana", "semana"),
    ("dim_distrito", "provincia_id", "dim_provincia", "provincia_id"),
    ("dim_distrito", "departamento_id", "dim_departamento", "departamento_id"),
    ("dim_provincia", "departamento_id", "dim_departamento", "departamento_id"),
]


def check_integrity(tables: dict) -> list[str]:
    problems = []
    for name, key in KEYS.items():
        if tables[name].duplicated(key).any():
            problems.append(f"{name}: clave {key} repetida")
    for fact, fk, dim, key in FOREIGN:
        orphans = ~tables[fact][fk].isin(tables[dim][key])
        if orphans.any():
            problems.append(f"{fact}.{fk}: {int(orphans.sum())} filas sin {dim}")
    for name, table in tables.items():
        nulls = table.isna().sum()
        for col, n in nulls[nulls > 0].items():
            problems.append(f"{name}.{col}: {n} nulos")
    return problems


def lineage(raw_rows: int, staging: pd.DataFrame, fact: pd.DataFrame) -> pd.DataFrame:
    rows = [
        ("1. raw", "CSV del portal", raw_rows, raw_rows, 14, "Tal como se publica"),
        ("2. staging", "Casos con tipos, claves y edad en años", len(staging), len(staging), len(staging.columns),
         "Reglas de campo: 0 casos excluidos"),
        ("3. curated", "fact_caso (agregado)", len(fact), int(fact["casos"].sum()), len(fact.columns),
         "Un caso por fila pasa a semana × distrito × forma × edad × sexo: mismos casos"),
        ("3a. marca", "Casos sin edad válida", int((staging["grupo_edad"] == parse.AGE_GROUP_UNKNOWN).sum()),
         int((staging["grupo_edad"] == parse.AGE_GROUP_UNKNOWN).sum()), None, "Subconjunto, no exclusión"),
    ]
    return pd.DataFrame(rows, columns=["paso", "descripcion", "filas", "casos", "columnas", "nota"])


def main() -> int:
    if hasattr(sys.stdout, "reconfigure"):
        sys.stdout.reconfigure(encoding="utf-8")
    from src import quality
    raw_rows = len(quality.raw_frame())
    cases = parse.read_dengue()
    indicators = parse.read_indicadores()
    pop = parse.population(indicators)
    register = quality.district_register(indicators)

    config.STAGING.mkdir(parents=True, exist_ok=True)
    cases.to_parquet(config.STAGING / "casos.parquet", index=False)

    provinces = dim_provincia(cases)
    tables = {
        "fact_caso": fact_caso(cases),
        "fact_poblacion_departamento": fact_poblacion_departamento(pop),
        "fact_poblacion_provincia": fact_poblacion_provincia(pop, provinces),
        "fact_canal_endemico": fact_canal_endemico(cases),
        "fact_canal_nacional": fact_canal_nacional(cases),
        "dim_distrito": dim_distrito(cases, register),
        "dim_provincia": provinces,
        "dim_departamento": dim_departamento(),
        "dim_anio": dim_anio(),
        "dim_semana": dim_semana(),
        "dim_forma_clinica": dim_forma_clinica(),
        "dim_grupo_edad": dim_grupo_edad(),
        "dim_sexo": dim_sexo(),
    }
    problems = check_integrity(tables)
    trail = lineage(raw_rows, cases, tables["fact_caso"])
    base = trail.iloc[0]
    for row in trail.iloc[1:3].itertuples():
        if row.casos != base.casos:
            problems.append(f"Linaje: {row.paso} tiene {row.casos} casos; raw tiene {base.casos}")
    for p in problems:
        print(f"  ✗ {p}")
    if problems:
        return 1

    config.CURATED.mkdir(parents=True, exist_ok=True)
    for name, table in tables.items():
        table.to_csv(config.CURATED / f"{name}.csv", index=False, lineterminator="\n")
    config.REPORTS.mkdir(parents=True, exist_ok=True)
    trail.to_csv(config.REPORTS / "linaje.csv", index=False)

    print(trail[["paso", "filas", "casos"]].to_string(index=False))
    for name, table in tables.items():
        size = (config.CURATED / f"{name}.csv").stat().st_size / 1e6
        print(f"  {name}: {len(table):,} filas, {size:.2f} MB")
    return 0


if __name__ == "__main__":
    sys.exit(main())

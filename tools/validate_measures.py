"""Valida las medidas DAX del modelo contra el mismo cálculo hecho en Python.

Dos pasos, porque la consulta DAX se ejecuta en Power BI Desktop (con el MCP de modelado o con
tools/ejecutar_dax.ps1):

    python tools/validate_measures.py consulta            # escribe tools/validacion_medidas.dax
    (ejecutar esa consulta en Power BI y guardar el resultado como CSV)
    python tools/validate_measures.py comparar <csv_dax>  # compara y escribe reports/validacion_medidas.csv

La comparación cubre las medidas en el total y en cada año, departamento, provincia, forma clínica,
grupo de edad, sexo, semana, año × departamento y año × semana.
"""

import sys
from pathlib import Path

import numpy as np
import pandas as pd

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))

from src import config  # noqa: E402

QUERY_FILE = ROOT / "tools" / "validacion_medidas.dax"
OUT = config.REPORTS / "validacion_medidas.csv"
TOLERANCE = 1e-6          # diferencia relativa admitida (redondeo de punto flotante)

CASES = ["Casos", "Distritos con casos", "Provincias con casos", "Departamentos con casos", "Casos con edad válida",
         "Edad promedio", "% de mujeres", "Casos con signos de alarma o graves", "% con signos de alarma o graves",
         "Casos graves", "% graves", "Semana pico", "Casos en la semana pico"]
INCIDENCE = ["Población (habitantes-año)", "Casos con población", "Incidencia por 100 mil", "Incidencia nacional",
             "Veces la incidencia nacional"]
GLOBAL = CASES + INCIDENCE[:3] + ["Semanas sobre el canal", "Semanas evaluadas", "% de semanas sobre el canal",
                                  "Semanas del país sobre el canal", "Casos sin edad válida",
                                  "Casos en distritos fuera del padrón", "Fallecidos (CDC)", "Casos (CDC)", "Letalidad (CDC)"]
BY_YEAR = CASES + INCIDENCE[:4] + ["Casos año anterior", "Var. interanual", "Semanas sobre el canal", "Semanas evaluadas",
                                   "% de semanas sobre el canal", "Semanas del país sobre el canal", "Fallecidos (CDC)",
                                   "Casos (CDC)", "Letalidad (CDC)", "Casos sin edad válida"]
BY_DEPARTMENT = CASES + INCIDENCE + ["% de los casos del país", "Semanas sobre el canal", "Semanas evaluadas",
                                     "% de semanas sobre el canal"]
BY_YEAR_DEPARTMENT = ["Casos", "Distritos con casos", "Edad promedio", "% con signos de alarma o graves", "Población (habitantes-año)",
                      "Incidencia por 100 mil", "Semanas sobre el canal", "Semana pico"]
BY_PROVINCE = ["Casos", "Distritos con casos", "Población (habitantes-año)", "Casos con población", "Incidencia por 100 mil",
               "Edad promedio"]
BY_FORM = ["Casos", "Edad promedio", "% de mujeres"]
BY_AGE = ["Casos", "Participación del grupo de edad", "% con signos de alarma o graves", "% de mujeres"]
BY_SEX = ["Casos", "Edad promedio", "% con signos de alarma o graves"]
BY_WEEK = ["Casos", "Parte de los casos del año", "Casos con signos de alarma o graves"]
BY_YEAR_WEEK = ["Casos", "Parte de los casos del año", "Umbral del canal (país)", "Mediana histórica (país)"]
TEXTS = {"Corte de datos"}
ZERO_IF_EMPTY = {"Casos", "Distritos con casos", "Provincias con casos", "Departamentos con casos", "Casos con edad válida",
                 "Casos con signos de alarma o graves", "Casos graves", "Casos con población", "Semanas sobre el canal",
                 "Semanas evaluadas", "Semanas del país sobre el canal", "Casos sin edad válida",
                 "Casos en distritos fuera del padrón", "Fallecidos (CDC)", "Casos (CDC)"}
DEPT_ONLY_SKIP_CDC = True        # los fallecidos del CDC son nacionales: no se prueban por departamento


# ---------------------------------------------------------------------------------------------
# Python
# ---------------------------------------------------------------------------------------------

class Data:
    def __init__(self) -> None:
        read = lambda n: pd.read_csv(config.CURATED / f"{n}.csv", dtype={"ubigeo": str, "departamento_id": str,
                                                                          "provincia_id": str, "sexo_id": str})
        self.districts = read("dim_distrito")
        self.provinces = read("dim_provincia")
        self.departments = read("dim_departamento")
        self.forms = read("dim_forma_clinica")
        self.ages = read("dim_grupo_edad")
        self.sexes = read("dim_sexo")
        self.pop_dep = read("fact_poblacion_departamento")
        self.pop_prov = read("fact_poblacion_provincia")
        self.channel = read("fact_canal_endemico")
        self.channel_nat = read("fact_canal_nacional")
        self.cdc = read("fact_cdc_anual")
        fc = read("fact_caso").merge(self.districts[["ubigeo", "provincia_id", "departamento_id", "distrito_en_padron"]], on="ubigeo")
        fc = fc.merge(self.forms[["forma_clinica_id", "alarma_o_grave", "cie10"]], on="forma_clinica_id")
        self.cases = fc.merge(self.ages[["grupo_edad_id", "grupo_edad"]], on="grupo_edad_id")
        self.all_years = sorted(self.cases["anio"].unique())


def select(d: Data, years=None, deps=None, provs=None, forms=None, ages=None, sexes=None, weeks=None) -> pd.DataFrame:
    c = d.cases
    if years is not None:
        c = c[c["anio"].isin(years)]
    if deps is not None:
        c = c[c["departamento_id"].isin(deps)]
    if provs is not None:
        c = c[c["provincia_id"].isin(provs)]
    if forms is not None:
        c = c[c["forma_clinica_id"].isin(forms)]
    if ages is not None:
        c = c[c["grupo_edad_id"].isin(ages)]
    if sexes is not None:
        c = c[c["sexo_id"].isin(sexes)]
    if weeks is not None:
        c = c[c["semana"].isin(weeks)]
    return c


def population(d: Data, years, deps, provs) -> float:
    years = d.all_years if years is None else years
    if provs is not None:
        p = d.pop_prov[d.pop_prov["provincia_id"].isin(provs) & d.pop_prov["anio"].isin(years)]
    else:
        p = d.pop_dep[d.pop_dep["anio"].isin(years)]
        if deps is not None:
            p = p[p["departamento_id"].isin(deps)]
    return float(p["poblacion"].sum()) if len(p) else np.nan


def top_week(c: pd.DataFrame) -> tuple:
    if c.empty:
        return np.nan, np.nan
    by_week = c.groupby("semana")["casos"].sum()
    peak = by_week.max()
    return float(by_week[by_week == peak].index.max()), float(peak)


def measures(d: Data, names: list[str], years=None, deps=None, provs=None, forms=None, ages=None, sexes=None,
             weeks=None, share_base: dict | None = None) -> dict:
    c = select(d, years, deps, provs, forms, ages, sexes, weeks)
    total = float(c["casos"].sum()) if len(c) else np.nan
    n = lambda x: x if len(c) else np.nan
    years_set = d.all_years if years is None else list(years)
    first_pop = config.POPULATION_FROM if provs is None else 2016
    cases_with_pop = float(c.loc[c["anio"] >= first_pop, "casos"].sum()) if len(c) else np.nan
    cases_with_pop = cases_with_pop if (len(c) and cases_with_pop > 0) else (0.0 if len(c) else np.nan)
    pop = population(d, years_set, deps, provs)
    incidence = cases_with_pop / pop * 1e5 if pop == pop and pop > 0 and cases_with_pop == cases_with_pop else np.nan
    nat_cases = float(select(d, years, None, None, forms, ages, sexes, weeks).query("anio >= @config.POPULATION_FROM")["casos"].sum())
    nat_pop = population(d, years_set, None, None)
    national = nat_cases / nat_pop * 1e5 if nat_pop == nat_pop and nat_pop > 0 else np.nan
    with_age = float(c["casos_con_edad"].sum()) if len(c) else np.nan
    alarm = float(c.loc[c["alarma_o_grave"] == 1, "casos"].sum()) if len(c) else np.nan
    severe = float(c.loc[c["cie10"] == "A97.2", "casos"].sum()) if len(c) else np.nan
    peak_week, peak_cases = top_week(c)
    ch = d.channel[d.channel["anio"].isin(years_set)]
    if deps is not None:
        ch = ch[ch["departamento_id"].isin(deps)]
    nat = d.channel_nat[d.channel_nat["anio"].isin(years_set)]
    if weeks is not None:
        ch, nat = ch[ch["semana"].isin(weeks)], nat[nat["semana"].isin(weeks)]
    cdc = d.cdc[d.cdc["anio"].isin(years_set)]
    prev = select(d, [list(years)[0] - 1], deps, provs, forms, ages, sexes) if years is not None and len(list(years)) == 1 else None
    prev_total = float(prev["casos"].sum()) if prev is not None and len(prev) else np.nan
    out = {
        "Casos": total,
        "Distritos con casos": float(c["ubigeo"].nunique()) if len(c) else np.nan,
        "Provincias con casos": float(c["provincia_id"].nunique()) if len(c) else np.nan,
        "Departamentos con casos": float(c["departamento_id"].nunique()) if len(c) else np.nan,
        "Casos con edad válida": with_age,
        "Edad promedio": float(c["edad_suma"].sum() / with_age) if len(c) and with_age else np.nan,
        "% de mujeres": float(c.loc[c["sexo_id"] == "F", "casos"].sum() / total) if len(c) else np.nan,
        "Casos con signos de alarma o graves": alarm,
        "% con signos de alarma o graves": alarm / total if len(c) else np.nan,
        "Casos graves": severe,
        "% graves": severe / total if len(c) else np.nan,
        "Semana pico": peak_week,
        "Casos en la semana pico": peak_cases,
        "Población (habitantes-año)": pop,
        "Casos con población": cases_with_pop,
        "Incidencia por 100 mil": incidence,
        "Incidencia nacional": national,
        "Veces la incidencia nacional": incidence / national if incidence == incidence and national == national and national else np.nan,
        "Casos año anterior": prev_total,
        "Var. interanual": (total / prev_total - 1) if prev_total == prev_total and prev_total > 0 else np.nan,
        "% de los casos del país": total / float(select(d, years, None, None, forms, ages, sexes, weeks)["casos"].sum()) if len(c) else np.nan,
        "Semanas sobre el canal": float(ch["sobre_canal"].sum()) if len(ch) else np.nan,
        "Semanas evaluadas": float(len(ch)) if len(ch) else np.nan,
        "% de semanas sobre el canal": float(ch["sobre_canal"].sum() / len(ch)) if len(ch) else np.nan,
        "Semanas del país sobre el canal": float(nat["sobre_canal"].sum()) if len(nat) else np.nan,
        "Casos sin edad válida": float(c.loc[c["grupo_edad"] == "Sin edad válida", "casos"].sum()) if len(c) else np.nan,
        "Casos en distritos fuera del padrón": float(c.loc[c["distrito_en_padron"] == 0, "casos"].sum()) if len(c) else np.nan,
        "Fallecidos (CDC)": float(cdc["fallecidos_cdc"].sum()) if len(cdc) else np.nan,
        "Casos (CDC)": float(cdc["casos_cdc"].sum()) if len(cdc) else np.nan,
        "Letalidad (CDC)": float(cdc["fallecidos_cdc"].sum() / cdc["casos_cdc"].sum()) if len(cdc) else np.nan,
        "Participación del grupo de edad": np.nan,
        "Parte de los casos del año": np.nan,
    }
    for name in ZERO_IF_EMPTY:                       # sumas y conteos sin filas: DAX da 0 o BLANK, que se tratan como iguales
        if name in out and out[name] != out[name]:
            out[name] = 0.0
    if share_base is not None:
        if "age" in share_base:
            out["Participación del grupo de edad"] = total / share_base["age"] if len(c) else np.nan
        if "week" in share_base:
            out["Parte de los casos del año"] = total / share_base["week"] if len(c) else np.nan
    return {k: out[k] for k in names if k in out}


def expected() -> pd.DataFrame:
    d = Data()
    rows: list[tuple] = []

    def add(context, key, values):
        rows.extend((context, key, k, v) for k, v in values.items())

    add("global", "total", measures(d, GLOBAL))
    add("global", "total", {"Corte de datos": f"Casos notificados al CDC Perú hasta el año {config.LAST_YEAR}"})

    for year in d.all_years:
        add("anio", str(year), measures(d, BY_YEAR, years=[year]))

    dep_names = d.departments.set_index("departamento_id")["departamento"]
    for dep_id, name in dep_names.items():
        add("departamento", name, measures(d, BY_DEPARTMENT, deps=[dep_id]))
    present = d.cases.groupby(["anio", "departamento_id"]).size().index
    for year, dep_id in present:
        add("anio_departamento", f"{year}|{dep_names[dep_id]}", measures(d, BY_YEAR_DEPARTMENT, years=[year], deps=[dep_id]))

    for _, row in d.provinces.iterrows():
        add("provincia", row["provincia_unica"], measures(d, BY_PROVINCE, provs=[row["provincia_id"]]))

    for _, row in d.forms.iterrows():
        add("forma", row["forma_clinica"], measures(d, BY_FORM, forms=[row["forma_clinica_id"]]))
    total = float(d.cases["casos"].sum())
    for _, row in d.ages.iterrows():
        add("grupo_edad", row["grupo_edad"], measures(d, BY_AGE, ages=[row["grupo_edad_id"]], share_base={"age": total}))
    for _, row in d.sexes.iterrows():
        add("sexo", row["sexo"], measures(d, BY_SEX, sexes=[row["sexo_id"]]))
    for week in range(1, 54):
        add("semana", str(week), measures(d, BY_WEEK, weeks=[week], share_base={"week": total}))

    year_total = d.cases.groupby("anio")["casos"].sum()
    for _, r in d.channel_nat.iterrows():
        year, week = int(r["anio"]), int(r["semana"])
        values = measures(d, ["Casos", "Parte de los casos del año"], years=[year], weeks=[week],
                          share_base={"week": float(year_total[year])})
        values["Umbral del canal (país)"] = float(r["umbral"])
        values["Mediana histórica (país)"] = float(r["mediana_historica"])
        add("anio_semana", f"{year}|{week}", {k: values[k] for k in BY_YEAR_WEEK})
    return pd.DataFrame(rows, columns=["contexto", "clave", "medida", "python"])


# ---------------------------------------------------------------------------------------------
# DAX
# ---------------------------------------------------------------------------------------------

def dax_name(name: str) -> str:
    """Medida como texto: así se pueden mezclar cifras y textos en una sola tabla (UNION exige un solo tipo)."""
    return 'FORMAT ( [' + name.replace("]", "]]") + '], "General Number" )'


def selectcolumns(source: str, context: str, key: str, names: list[str]) -> list[str]:
    return [f'SELECTCOLUMNS ( {source}, "contexto", "{context}", "clave", {key}, "medida", "{m}", "valor", {dax_name(m)} )'
            for m in names]


def query() -> str:
    parts = []
    for m in GLOBAL + sorted(TEXTS):
        parts.append(f'ROW ( "contexto", "global", "clave", "total", "medida", "{m}", "valor", {dax_name(m)} )')
    parts += selectcolumns("VALUES ( dim_anio[anio] )", "anio", 'FORMAT ( dim_anio[anio], "0" )', BY_YEAR)
    parts += selectcolumns("VALUES ( dim_departamento[departamento] )", "departamento", "dim_departamento[departamento]", BY_DEPARTMENT)
    parts += selectcolumns("SUMMARIZE ( fact_caso, dim_anio[anio], dim_departamento[departamento] )", "anio_departamento",
                           'FORMAT ( dim_anio[anio], "0" ) & "|" & dim_departamento[departamento]', BY_YEAR_DEPARTMENT)
    parts += selectcolumns("VALUES ( dim_provincia[provincia_unica] )", "provincia", "dim_provincia[provincia_unica]", BY_PROVINCE)
    parts += selectcolumns("VALUES ( dim_forma_clinica[forma_clinica] )", "forma", "dim_forma_clinica[forma_clinica]", BY_FORM)
    parts += selectcolumns("VALUES ( dim_grupo_edad[grupo_edad] )", "grupo_edad", "dim_grupo_edad[grupo_edad]", BY_AGE)
    parts += selectcolumns("VALUES ( dim_sexo[sexo] )", "sexo", "dim_sexo[sexo]", BY_SEX)
    parts += selectcolumns("VALUES ( dim_semana[semana] )", "semana", 'FORMAT ( dim_semana[semana], "0" )', BY_WEEK)
    parts += selectcolumns("SUMMARIZE ( fact_canal_nacional, dim_anio[anio], dim_semana[semana] )", "anio_semana",
                           'FORMAT ( dim_anio[anio], "0" ) & "|" & FORMAT ( dim_semana[semana], "0" )', BY_YEAR_WEEK)
    return "EVALUATE\nUNION (\n    " + ",\n    ".join(parts) + "\n)\n"


def compare(dax_csv: Path) -> pd.DataFrame:
    dax = pd.read_csv(dax_csv, dtype=str)
    dax.columns = [c.strip("[]").split("[")[-1] for c in dax.columns]
    dax["dax"] = pd.to_numeric(dax["valor"].str.replace(",", ".", regex=False), errors="coerce")
    exp = expected()
    out = exp.merge(dax[["contexto", "clave", "medida", "dax", "valor"]], on=["contexto", "clave", "medida"], how="outer")
    numeric = ~out["medida"].isin(TEXTS)
    py = pd.to_numeric(out["python"].where(numeric), errors="coerce")
    # En DAX, una suma o un conteo sin filas devuelve BLANK; en Python, 0. Se tratan como iguales.
    dax_value = out["dax"].where(out["dax"].notna() | py.ne(0), 0.0)
    out["diferencia_relativa"] = (dax_value - py).abs() / py.abs().clip(lower=1e-9)
    both_blank = dax_value.isna() & py.isna()
    match = dax_value.notna() & py.notna() & (out["diferencia_relativa"] <= TOLERANCE)
    out["resultado"] = np.where(numeric, np.where(both_blank | match, "cumple", "falla"),
                                np.where(out["python"].astype(str) == out["valor"].astype(str), "cumple", "falla"))
    out["dax"] = out["dax"].where(numeric, np.nan)
    out["python"] = out["python"].astype(str).where(~numeric, py.astype(float).astype(str))
    return out.drop(columns="valor")


def main() -> int:
    if hasattr(sys.stdout, "reconfigure"):
        sys.stdout.reconfigure(encoding="utf-8")
    if len(sys.argv) >= 2 and sys.argv[1] == "consulta":
        QUERY_FILE.write_text(query(), encoding="utf-8")
        print(f"Consulta escrita en {QUERY_FILE.relative_to(ROOT)}")
        return 0
    if len(sys.argv) == 3 and sys.argv[1] == "comparar":
        result = compare(Path(sys.argv[2]))
        result.to_csv(OUT, index=False)
        failed = result[result["resultado"] != "cumple"]
        print(f"{len(result)} comparaciones; {len(failed)} fallan; diferencia relativa máxima "
              f"{result['diferencia_relativa'].max():.2e}")
        if len(failed):
            print(failed.head(40).to_string(index=False))
        return 1 if len(failed) else 0
    print(__doc__)
    return 2


if __name__ == "__main__":
    sys.exit(main())

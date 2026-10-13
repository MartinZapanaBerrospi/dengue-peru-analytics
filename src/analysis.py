"""Fase 5 — Responde las preguntas P1–P6 con cifras, desde data/curated y data/staging.

Escribe las tablas de soporte en reports/analisis/ y las cifras que citan el tablero y el README
en reports/analisis/cifras_clave.csv. Las definiciones son las del modelo de Power BI
(docs/04_modelado.md): la incidencia es suma de casos entre suma de población.

Uso:
    python -m src.analysis
"""

import sys

import numpy as np
import pandas as pd

from src import config

OUT = config.REPORTS / "analisis"
HIGH_YEAR_CASES = 50_000            # año de alta transmisión: más de 50 mil casos
LAST = config.LAST_YEAR
KEY: dict[str, tuple] = {}          # cifra -> (valor, descripción)


def key(name: str, value, description: str) -> None:
    KEY[name] = (value, description)


def load() -> dict:
    types = {c: str for c in ["ubigeo", "departamento_id", "provincia_id", "sexo_id"]}
    names = ["fact_caso", "fact_poblacion_departamento", "fact_poblacion_provincia", "fact_canal_endemico",
             "fact_canal_nacional", "fact_cdc_anual", "dim_distrito", "dim_provincia", "dim_departamento",
             "dim_forma_clinica", "dim_grupo_edad"]
    t = {n: pd.read_csv(config.CURATED / f"{n}.csv", dtype=types) for n in names}
    c = t["fact_caso"].merge(t["dim_distrito"][["ubigeo", "distrito_unico", "provincia_id", "departamento_id"]], on="ubigeo")
    c = c.merge(t["dim_departamento"][["departamento_id", "departamento", "zona"]], on="departamento_id")
    c = c.merge(t["dim_forma_clinica"][["forma_clinica_id", "forma_clinica", "alarma_o_grave"]], on="forma_clinica_id")
    c = c.merge(t["dim_grupo_edad"][["grupo_edad_id", "grupo_edad"]], on="grupo_edad_id")
    t["cases"] = c
    return t


def pct(a: float, b: float) -> float:
    return a / b - 1


def cum_week(weekly: pd.Series, share: float) -> int:
    """Primera semana en que se acumula `share` de los casos del año."""
    cum = weekly.sort_index().cumsum() / weekly.sum()
    return int(cum[cum >= share].index[0])


# ---------------------------------------------------------------------------------------------
# P1: evolución y epidemias
# ---------------------------------------------------------------------------------------------

def p1(t: dict) -> None:
    c = t["cases"]
    by_year = c.groupby("anio")["casos"].sum()
    pop = t["fact_poblacion_departamento"].groupby("anio")["poblacion"].sum()
    cdc = t["fact_cdc_anual"].set_index("anio")
    table = pd.DataFrame({"casos": by_year})
    table["poblacion"] = pop
    table["incidencia_por_100mil"] = table["casos"] / table["poblacion"] * 1e5
    table["variacion_anual"] = table["casos"].pct_change()
    table["fallecidos_cdc"] = cdc["fallecidos_cdc"]
    table["letalidad_cdc_pct"] = 100 * cdc["fallecidos_cdc"] / cdc["casos_cdc"]
    table["alta_transmision"] = (table["casos"] > HIGH_YEAR_CASES).astype(int)
    table.reset_index().to_csv(OUT / "p1_evolucion_anual.csv", index=False)

    key("casos_total", int(by_year.sum()), "Casos de dengue de 2000 a 2024")
    key("casos_2024", int(by_year[2024]), "Casos en 2024")
    key("casos_2023", int(by_year[2023]), "Casos en 2023")
    key("casos_2022", int(by_year[2022]), "Casos en 2022")
    key("casos_2017", int(by_year[2017]), "Casos en 2017, la mayor epidemia antes de 2023")
    key("casos_2018", int(by_year[2018]), "Casos en 2018")
    key("casos_2000", int(by_year[2000]), "Casos en 2000")
    key("veces_2023_vs_2022", by_year[2023] / by_year[2022], "Veces que 2023 multiplicó los casos de 2022")
    key("veces_2023_vs_2017", by_year[2023] / by_year[2017], "Veces que 2023 supera a la epidemia de 2017")
    key("var_2024_vs_2023", pct(by_year[2024], by_year[2023]), "Cambio de los casos de 2024 frente a 2023")
    key("anios_alta_transmision", ", ".join(str(y) for y in by_year[by_year > HIGH_YEAR_CASES].index),
        "Años con más de 50 mil casos")
    key("casos_2023_2024_pct", by_year[[2023, 2024]].sum() / by_year.sum(),
        "Parte de todos los casos de 25 años que cae en 2023 y 2024")
    key("incidencia_2023", table.loc[2023, "incidencia_por_100mil"], "Incidencia por 100 mil en 2023")
    key("incidencia_2024", table.loc[2024, "incidencia_por_100mil"], "Incidencia por 100 mil en 2024")
    key("incidencia_2017", table.loc[2017, "incidencia_por_100mil"], "Incidencia por 100 mil en 2017")
    key("incidencia_2018", table.loc[2018, "incidencia_por_100mil"], "Incidencia por 100 mil en 2018")
    key("incidencia_2013", table.loc[2013, "incidencia_por_100mil"], "Incidencia por 100 mil en 2013")
    key("fallecidos_2023", int(cdc.loc[2023, "fallecidos_cdc"]), "Fallecidos por dengue en 2023 (CDC)")
    key("fallecidos_2024", int(cdc.loc[2024, "fallecidos_cdc"]), "Fallecidos por dengue en 2024 (CDC)")
    key("fallecidos_2012_2024", int(cdc["fallecidos_cdc"].sum()), "Fallecidos por dengue de 2012 a 2024 (CDC)")
    key("letalidad_2023_pct", table.loc[2023, "letalidad_cdc_pct"], "Letalidad 2023 (CDC), en %")
    key("letalidad_2024_pct", table.loc[2024, "letalidad_cdc_pct"], "Letalidad 2024 (CDC), en %")
    key("letalidad_2018_pct", table.loc[2018, "letalidad_cdc_pct"], "Letalidad 2018 (CDC), en %")
    key("letalidad_max_anio", int(table["letalidad_cdc_pct"].idxmax()), "Año de mayor letalidad 2012–2024")
    key("casos_2025_cdc", 35852, "Casos de 2025 en la sala situacional del CDC (no están en el archivo abierto)")
    key("casos_2026_cdc", 46669, "Casos de 2026 hasta la semana 33 (no están en el archivo abierto)")


# ---------------------------------------------------------------------------------------------
# P2: temporada
# ---------------------------------------------------------------------------------------------

def p2(t: dict) -> None:
    c = t["cases"]
    weekly = c.groupby(["anio", "semana"])["casos"].sum()
    rows = []
    for year, w in weekly.groupby(level=0):
        s = w.droplevel(0)
        rows.append({"anio": year, "casos": int(s.sum()), "semana_pico": int(s.idxmax()), "casos_semana_pico": int(s.max()),
                     "semana_10pct": cum_week(s, 0.10), "semana_50pct": cum_week(s, 0.50), "semana_90pct": cum_week(s, 0.90),
                     "pct_primer_semestre": float(s[s.index <= 26].sum() / s.sum())})
    peak = pd.DataFrame(rows)
    peak["duracion_10_90"] = peak["semana_90pct"] - peak["semana_10pct"]
    peak.to_csv(OUT / "p2_temporada_anual.csv", index=False)
    p = peak.set_index("anio")

    # Perfil de las temporadas «normales»: los años de más de 10 mil casos, sin 2023 ni 2024
    base = [y for y in p.index if p.loc[y, "casos"] >= 10_000 and y not in (2023, 2024)]
    profile = (weekly.unstack(0)[base] / weekly.unstack(0)[base].sum()).mean(axis=1).rename("parte_del_anio")
    profile.reset_index().to_csv(OUT / "p2_perfil_semanal.csv", index=False)
    top = profile.sort_values(ascending=False)

    key("semana_pico_2017", int(p.loc[2017, "semana_pico"]), "Semana pico de 2017")
    key("semana_pico_2023", int(p.loc[2023, "semana_pico"]), "Semana pico de 2023")
    key("semana_pico_2024", int(p.loc[2024, "semana_pico"]), "Semana pico de 2024")
    key("casos_semana_pico_2023", int(p.loc[2023, "casos_semana_pico"]), "Casos en la semana pico de 2023")
    key("casos_semana_pico_2024", int(p.loc[2024, "casos_semana_pico"]), "Casos en la semana pico de 2024")
    key("semana_50pct_2023", int(p.loc[2023, "semana_50pct"]), "Semana en que 2023 acumula la mitad de sus casos")
    key("semana_50pct_2024", int(p.loc[2024, "semana_50pct"]), "Semana en que 2024 acumula la mitad de sus casos")
    key("adelanto_pico_2024", int(p.loc[2023, "semana_pico"] - p.loc[2024, "semana_pico"]), "Semanas que se adelantó el pico de 2024 frente a 2023")
    key("pct_primer_semestre_normal", float(profile[profile.index <= 26].sum()), "Parte de los casos que cae de la semana 1 a la 26, años normales")
    key("pct_primer_semestre_2023", float(p.loc[2023, "pct_primer_semestre"]), "Parte de los casos de 2023 que cae en el primer semestre")
    key("pct_primer_semestre_2024", float(p.loc[2024, "pct_primer_semestre"]), "Parte de los casos de 2024 que cae en el primer semestre")
    key("semana_pico_normal", int(top.index[0]), "Semana más alta del perfil de años normales")
    key("semanas_normales_n", len(base), "Años en el perfil de temporada normal")
    key("pct_semanas_10_a_22_normal", float(profile[(profile.index >= 10) & (profile.index <= 22)].sum()),
        "Parte de los casos que cae entre las semanas 10 y 22, años normales")
    key("pct_semanas_10_a_22_2023", float(weekly.loc[2023][(weekly.loc[2023].index >= 10) & (weekly.loc[2023].index <= 22)].sum() / p.loc[2023, "casos"]),
        "Parte de los casos de 2023 entre las semanas 10 y 22")

    # Pico por zona en 2023 y 2024
    zone = c.groupby(["zona", "anio", "semana"])["casos"].sum()
    zrows = []
    for (z, y), w in zone.groupby(level=[0, 1]):
        s = w.droplevel([0, 1])
        if y in (2017, 2023, 2024):
            zrows.append({"zona": z, "anio": y, "casos": int(s.sum()), "semana_pico": int(s.idxmax()), "semana_50pct": cum_week(s, 0.5)})
    pd.DataFrame(zrows).to_csv(OUT / "p2_pico_por_zona.csv", index=False)


# ---------------------------------------------------------------------------------------------
# P3: territorio
# ---------------------------------------------------------------------------------------------

def p3(t: dict) -> None:
    c = t["cases"]
    pop = t["fact_poblacion_departamento"]
    last = [2023, 2024]
    dep_cases = c[c["anio"].between(config.POPULATION_FROM, LAST)].groupby("departamento_id")["casos"].sum()
    dep_pop = pop.groupby("departamento_id")["poblacion"].sum()
    inc = pd.DataFrame({"casos_2013_2024": dep_cases, "habitantes_anio": dep_pop}).fillna(0)
    inc["incidencia_media_anual"] = inc["casos_2013_2024"] / inc["habitantes_anio"] * 1e5
    for y in [2017, 2023, 2024]:
        cy = c[c["anio"] == y].groupby("departamento_id")["casos"].sum()
        py = pop[pop["anio"] == y].set_index("departamento_id")["poblacion"]
        inc[f"casos_{y}"] = cy
        inc[f"incidencia_{y}"] = cy / py * 1e5
    inc = inc.fillna(0).join(t["dim_departamento"].set_index("departamento_id")[["departamento", "zona"]])
    national_2324 = c[c["anio"].isin(last)]["casos"].sum() / pop[pop["anio"].isin(last)]["poblacion"].sum() * 1e5
    inc["incidencia_2023_2024"] = inc.apply(
        lambda r: c[(c["anio"].isin(last)) & (c["departamento_id"] == r.name)]["casos"].sum()
        / pop[(pop["anio"].isin(last)) & (pop["departamento_id"] == r.name)]["poblacion"].sum() * 1e5, axis=1)
    inc["veces_nacional_2023_2024"] = inc["incidencia_2023_2024"] / national_2324
    inc = inc.sort_values("incidencia_2023_2024", ascending=False)
    inc.reset_index().to_csv(OUT / "p3_departamentos.csv", index=False)

    top = inc.iloc[0]
    key("dep_mayor_incidencia", top["departamento"], "Departamento con mayor incidencia en 2023–2024")
    key("dep_mayor_incidencia_valor", top["incidencia_2023_2024"], "Su incidencia anual media 2023–2024 por 100 mil")
    key("dep_mayor_incidencia_veces", top["veces_nacional_2023_2024"], "Veces la incidencia nacional")
    key("dep_2_incidencia", inc.iloc[1]["departamento"], "Segundo departamento por incidencia 2023–2024")
    key("dep_2_incidencia_valor", inc.iloc[1]["incidencia_2023_2024"], "Su incidencia anual media 2023–2024")
    key("dep_3_incidencia", inc.iloc[2]["departamento"], "Tercer departamento por incidencia 2023–2024")
    key("incidencia_nacional_2023_2024", national_2324, "Incidencia anual media nacional 2023–2024 por 100 mil")
    key("deps_con_casos_2023", int(c[c["anio"] == 2023]["departamento_id"].nunique()), "Departamentos con casos en 2023")
    key("deps_sobre_nacional", int((inc["veces_nacional_2023_2024"] > 1).sum()), "Departamentos con incidencia 2023–2024 sobre la nacional")

    # Concentración y expansión del mapa
    spread = c.groupby("anio").agg(casos=("casos", "sum"), departamentos=("departamento_id", "nunique"),
                                   provincias=("provincia_id", "nunique"), distritos=("ubigeo", "nunique"))
    top2 = c[c["departamento"].isin(["Piura", "Tumbes", "Loreto", "Lambayeque"])].groupby("anio")["casos"].sum()
    spread["pct_cuatro_deps"] = top2 / spread["casos"]
    lima = c[c["departamento"] == "Lima"].groupby("anio")["casos"].sum().reindex(spread.index).fillna(0)
    spread["pct_lima"] = lima / spread["casos"]
    piura = c[c["departamento"] == "Piura"].groupby("anio")["casos"].sum().reindex(spread.index).fillna(0)
    spread["pct_piura"] = piura / spread["casos"]
    spread.reset_index().to_csv(OUT / "p3_expansion.csv", index=False)
    key("distritos_2000", int(spread.loc[2000, "distritos"]), "Distritos con casos en 2000")
    key("distritos_2024", int(spread.loc[2024, "distritos"]), "Distritos con casos en 2024")
    key("distritos_2017", int(spread.loc[2017, "distritos"]), "Distritos con casos en 2017")
    key("deps_2000", int(spread.loc[2000, "departamentos"]), "Departamentos con casos en 2000")
    key("deps_2024", int(spread.loc[2024, "departamentos"]), "Departamentos con casos en 2024")
    key("provincias_2024", int(spread.loc[2024, "provincias"]), "Provincias con casos en 2024")
    key("pct_piura_2017", spread.loc[2017, "pct_piura"], "Parte de los casos de 2017 que fue de Piura")
    key("pct_piura_2023", spread.loc[2023, "pct_piura"], "Parte de los casos de 2023 que fue de Piura")
    key("pct_piura_2024", spread.loc[2024, "pct_piura"], "Parte de los casos de 2024 que fue de Piura")
    key("pct_lima_2023", spread.loc[2023, "pct_lima"], "Parte de los casos de 2023 que fue de Lima")
    key("pct_lima_2024", spread.loc[2024, "pct_lima"], "Parte de los casos de 2024 que fue de Lima")
    key("casos_lima_2024", int(lima[2024]), "Casos de Lima en 2024")
    key("casos_lima_2022", int(lima[2022]), "Casos de Lima en 2022")

    # Provincias y distritos
    pp = t["fact_poblacion_provincia"]
    prov = c[c["anio"].isin(last)].groupby("provincia_id")["casos"].sum().to_frame("casos_2023_2024")
    ppop = pp[pp["anio"].isin(last)].groupby("provincia_id")["poblacion"].sum()
    prov["incidencia_media_anual"] = prov["casos_2023_2024"] / ppop * 1e5
    prov = prov.join(t["dim_provincia"].set_index("provincia_id")[["provincia_unica", "departamento_id"]]).join(
        t["dim_departamento"].set_index("departamento_id")["departamento"], on="departamento_id")
    prov["poblacion_2024"] = pp[pp["anio"] == 2024].set_index("provincia_id")["poblacion"]
    big = prov[prov["poblacion_2024"] >= 20_000].sort_values("incidencia_media_anual", ascending=False)
    big.reset_index().to_csv(OUT / "p3_provincias_2023_2024.csv", index=False)
    key("provincia_mayor_incidencia", big.iloc[0]["provincia_unica"], "Provincia (20 mil hab. o más) con mayor incidencia 2023–2024")
    key("provincia_mayor_incidencia_valor", big.iloc[0]["incidencia_media_anual"], "Su incidencia anual media 2023–2024")
    key("provincia_mayor_incidencia_dep", big.iloc[0]["departamento"], "Su departamento")
    dist = c[c["anio"].isin(last)].groupby(["ubigeo", "distrito_unico", "departamento"])["casos"].sum().reset_index()
    dist = dist.sort_values("casos", ascending=False)
    dist.head(30).to_csv(OUT / "p3_distritos_mas_casos_2023_2024.csv", index=False)
    key("distrito_mas_casos", dist.iloc[0]["distrito_unico"], "Distrito con más casos en 2023–2024")
    key("distrito_mas_casos_valor", int(dist.iloc[0]["casos"]), "Sus casos en 2023–2024")
    key("distrito_mas_casos_dep", dist.iloc[0]["departamento"], "Su departamento")
    share10 = dist.head(10)["casos"].sum() / dist["casos"].sum()
    key("top10_distritos_pct", share10, "Parte de los casos de 2023–2024 en los 10 distritos con más")


# ---------------------------------------------------------------------------------------------
# P4: personas
# ---------------------------------------------------------------------------------------------

def p4(t: dict) -> None:
    c = t["cases"]
    staging = pd.read_parquet(config.STAGING / "casos.parquet", columns=["anio", "edad_anios", "sexo", "grupo_edad"])
    median = staging.groupby("anio")["edad_anios"].median().rename("mediana_edad")
    groups = c.pivot_table(index="anio", columns="grupo_edad", values="casos", aggfunc="sum", fill_value=0)
    groups = groups.div(groups.sum(axis=1), axis=0)
    table = groups.join(median)
    table["pct_mujeres"] = c[c["sexo_id"] == "F"].groupby("anio")["casos"].sum() / c.groupby("anio")["casos"].sum()
    table.reset_index().to_csv(OUT / "p4_edad_sexo_anual.csv", index=False)

    valid = staging[staging["edad_anios"].notna()]
    key("mediana_edad_total", float(valid["edad_anios"].median()), "Mediana de edad de todos los casos con edad válida")
    key("mediana_edad_2024", float(median[2024]), "Mediana de edad en 2024")
    key("mediana_edad_2012", float(median[2012]), "Mediana de edad en 2012")
    key("mediana_edad_2000", float(median[2000]), "Mediana de edad en 2000")
    key("pct_mujeres_total", float((staging["sexo"] == "F").mean()), "Parte de los casos que son mujeres")
    tot = c.groupby("grupo_edad")["casos"].sum()
    tot = tot / tot.sum()
    key("pct_adultez_total", float(tot["Adultez (30–59)"]), "Parte de los casos de 30 a 59 años")
    key("pct_juventud_total", float(tot["Juventud (18–29)"]), "Parte de los casos de 18 a 29 años")
    key("pct_ninez_total", float(tot["Niñez (1–11)"] + tot["Menor de 1 año"]), "Parte de los casos de menores de 12 años")
    key("pct_adulto_mayor_total", float(tot["Adulto mayor (60 o más)"]), "Parte de los casos de 60 años o más")
    key("pct_adultez_2000_2010", float(groups.loc[2000:2010, "Adultez (30–59)"].mean()), "Parte de 30 a 59 años, promedio 2000–2010")
    key("pct_adultez_2023_2024", float(groups.loc[2023:2024, "Adultez (30–59)"].mean()), "Parte de 30 a 59 años, promedio 2023–2024")
    key("pct_ninez_2000_2010", float((groups.loc[2000:2010, "Niñez (1–11)"] + groups.loc[2000:2010, "Menor de 1 año"]).mean()),
        "Parte de menores de 12 años, promedio 2000–2010")
    key("pct_ninez_2023_2024", float((groups.loc[2023:2024, "Niñez (1–11)"] + groups.loc[2023:2024, "Menor de 1 año"]).mean()),
        "Parte de menores de 12 años, promedio 2023–2024")
    key("pct_mujeres_2023_2024", float(table.loc[2023:2024, "pct_mujeres"].mean()), "Parte de mujeres, promedio 2023–2024")


# ---------------------------------------------------------------------------------------------
# P5: gravedad
# ---------------------------------------------------------------------------------------------

def p5(t: dict) -> None:
    c = t["cases"]
    comparable = c[c["anio"] >= 2011]
    by_year = comparable.groupby("anio").apply(
        lambda g: pd.Series({"casos": g["casos"].sum(),
                             "pct_alarma_o_grave": g.loc[g["alarma_o_grave"] == 1, "casos"].sum() / g["casos"].sum(),
                             "pct_graves": g.loc[g["forma_clinica"] == "Grave", "casos"].sum() / g["casos"].sum()}),
        include_groups=False)
    by_year.reset_index().to_csv(OUT / "p5_gravedad_anual.csv", index=False)
    by_age = comparable.groupby("grupo_edad").apply(
        lambda g: pd.Series({"casos": g["casos"].sum(), "pct_alarma_o_grave": g.loc[g["alarma_o_grave"] == 1, "casos"].sum() / g["casos"].sum(),
                             "pct_graves": g.loc[g["forma_clinica"] == "Grave", "casos"].sum() / g["casos"].sum()}), include_groups=False)
    by_age = by_age.reindex(t["dim_grupo_edad"]["grupo_edad"])
    by_age.reset_index().to_csv(OUT / "p5_gravedad_por_edad.csv", index=False)
    by_sex = comparable.groupby("sexo_id").apply(
        lambda g: g.loc[g["alarma_o_grave"] == 1, "casos"].sum() / g["casos"].sum(), include_groups=False)
    key("pct_alarma_2011_2024", float(comparable.loc[comparable["alarma_o_grave"] == 1, "casos"].sum() / comparable["casos"].sum()),
        "Parte de los casos con signos de alarma o graves, 2011–2024")
    key("pct_alarma_max", float(by_year["pct_alarma_o_grave"].max()), "Máxima parte anual de casos con signos de alarma o graves")
    key("pct_alarma_max_anio", int(by_year["pct_alarma_o_grave"].idxmax()), "Año de esa máxima")
    key("pct_alarma_2023", float(by_year.loc[2023, "pct_alarma_o_grave"]), "Parte con signos de alarma o graves en 2023")
    key("pct_alarma_2024", float(by_year.loc[2024, "pct_alarma_o_grave"]), "Parte con signos de alarma o graves en 2024")
    key("pct_alarma_2021", float(by_year.loc[2021, "pct_alarma_o_grave"]), "Parte con signos de alarma o graves en 2021")
    key("casos_alarma_graves_2023_2024", int(c[(c["anio"] >= 2023) & (c["alarma_o_grave"] == 1)]["casos"].sum()),
        "Casos con signos de alarma o graves en 2023–2024")
    key("pct_graves_2011_2024", float(comparable.loc[comparable["forma_clinica"] == "Grave", "casos"].sum() / comparable["casos"].sum()),
        "Parte de casos graves, 2011–2024")
    ages = by_age["pct_alarma_o_grave"].dropna()
    ages = ages[ages.index != "Sin edad válida"]
    key("grupo_mayor_alarma", ages.idxmax(), "Grupo de edad con mayor parte de casos con signos de alarma o graves")
    key("grupo_mayor_alarma_valor", float(ages.max()), "Esa parte")
    key("grupo_menor_alarma", ages.idxmin(), "Grupo de edad con menor parte")
    key("grupo_menor_alarma_valor", float(ages.min()), "Esa parte")
    key("pct_alarma_mujeres", float(by_sex["F"]), "Parte con signos de alarma o graves entre mujeres")
    key("pct_alarma_hombres", float(by_sex["M"]), "Parte con signos de alarma o graves entre hombres")
    pre = c[c["anio"] <= 2009]
    key("pct_graves_2000_2009", float(pre.loc[pre["forma_clinica"] == "Grave", "casos"].sum() / pre["casos"].sum()),
        "Parte de graves 2000–2009 (clasificación anterior, no comparable)")


# ---------------------------------------------------------------------------------------------
# P6: canal endémico
# ---------------------------------------------------------------------------------------------

def p6(t: dict) -> None:
    ch = t["fact_canal_endemico"].merge(t["dim_departamento"][["departamento_id", "departamento", "zona"]], on="departamento_id")
    nat = t["fact_canal_nacional"]
    by_year = ch.groupby("anio").agg(semanas_sobre_canal=("sobre_canal", "sum"), semanas_evaluadas=("sobre_canal", "size"))
    by_year["pct"] = by_year["semanas_sobre_canal"] / by_year["semanas_evaluadas"]
    by_year["semanas_pais_sobre_canal"] = nat.groupby("anio")["sobre_canal"].sum()
    first = nat[nat["sobre_canal"] == 1].groupby("anio")["semana"].min()
    by_year["primera_semana_pais_sobre_canal"] = first
    by_year.reset_index().to_csv(OUT / "p6_canal_anual.csv", index=False)

    dep = ch[ch["anio"].isin([2023, 2024])].groupby(["departamento", "zona"]).agg(
        semanas_sobre_canal=("sobre_canal", "sum"), semanas_evaluadas=("sobre_canal", "size")).reset_index()
    dep["pct"] = dep["semanas_sobre_canal"] / dep["semanas_evaluadas"]
    dep = dep.sort_values("semanas_sobre_canal", ascending=False)
    dep.to_csv(OUT / "p6_canal_departamentos_2023_2024.csv", index=False)

    n23 = nat[(nat["anio"] == 2023) & (nat["sobre_canal"] == 1)]
    n24 = nat[(nat["anio"] == 2024) & (nat["sobre_canal"] == 1)]
    key("semanas_pais_sobre_canal_2023", int(len(n23)), "Semanas de 2023 con los casos del país sobre el canal")
    key("semanas_pais_sobre_canal_2024", int(len(n24)), "Semanas de 2024 con los casos del país sobre el canal")
    key("semanas_pais_sobre_canal_2018", int(nat[(nat["anio"] == 2018) & (nat["sobre_canal"] == 1)].shape[0]), "Semanas de 2018 sobre el canal")
    key("primera_semana_sobre_canal_2023", int(n23["semana"].min()), "Primera semana de 2023 sobre el canal nacional")
    key("primera_semana_sobre_canal_2024", int(n24["semana"].min()), "Primera semana de 2024 sobre el canal nacional")
    key("pct_semanas_dep_sobre_canal_2023", float(by_year.loc[2023, "pct"]), "Parte de las semanas-departamento de 2023 sobre el canal")
    key("pct_semanas_dep_sobre_canal_2018", float(by_year.loc[2018, "pct"]), "Parte de las semanas-departamento de 2018 sobre el canal")
    key("dep_mas_semanas_sobre_canal", dep.iloc[0]["departamento"], "Departamento con más semanas sobre el canal en 2023–2024")
    key("dep_mas_semanas_sobre_canal_n", int(dep.iloc[0]["semanas_sobre_canal"]), "Sus semanas sobre el canal en 2023–2024")
    key("semanas_dep_sobre_canal_total", int(ch["sobre_canal"].sum()), "Semanas-departamento sobre el canal, 2005–2024")
    key("semanas_dep_evaluadas_total", int(len(ch)), "Semanas-departamento evaluadas, 2005–2024")
    # Aviso temprano: cuántas semanas antes del pico nacional el canal ya estaba sobrepasado
    peak23 = nat[nat["anio"] == 2023].sort_values("casos").iloc[-1]["semana"]
    peak24 = nat[nat["anio"] == 2024].sort_values("casos").iloc[-1]["semana"]
    key("semanas_aviso_2023", int(peak23 - n23["semana"].min()), "Semanas entre la primera semana sobre el canal y el pico, 2023")
    key("semanas_aviso_2024", int(peak24 - n24["semana"].min()), "Semanas entre la primera semana sobre el canal y el pico, 2024")


def main() -> int:
    if hasattr(sys.stdout, "reconfigure"):
        sys.stdout.reconfigure(encoding="utf-8")
    OUT.mkdir(parents=True, exist_ok=True)
    t = load()
    for step in (p1, p2, p3, p4, p5, p6):
        step(t)
    table = pd.DataFrame([(k, v[0], v[1]) for k, v in KEY.items()], columns=["cifra", "valor", "descripcion"])
    table.to_csv(OUT / "cifras_clave.csv", index=False)
    print(f"{len(table)} cifras clave y {len(list(OUT.glob('*.csv'))) - 1} tablas en {OUT.relative_to(config.ROOT)}")
    return 0


if __name__ == "__main__":
    sys.exit(main())

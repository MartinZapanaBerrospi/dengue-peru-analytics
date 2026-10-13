"""El modelo curado versionado y las reglas de la Fase 3."""

import numpy as np
import pandas as pd
import pytest

from src import config, parse, transform

TABLES = list(transform.KEYS)


@pytest.fixture(scope="module")
def t():
    types = {c: str for c in ["ubigeo", "departamento_id", "provincia_id", "sexo_id"]}
    return {name: pd.read_csv(config.CURATED / f"{name}.csv", dtype=types) for name in TABLES}


def test_las_claves_no_se_repiten_y_toda_clave_foranea_existe(t):
    assert transform.check_integrity(t) == []


def test_el_linaje_no_pierde_casos(t):
    trail = pd.read_csv(config.REPORTS / "linaje.csv")
    assert trail["casos"].iloc[:3].nunique() == 1 and trail["casos"].iloc[0] == 1_029_421
    assert t["fact_caso"]["casos"].sum() == 1_029_421
    assert trail["filas"].iloc[2] == len(t["fact_caso"]) == 332_850


def test_los_casos_por_anio_son_los_del_cdc(t):
    official = pd.read_csv(config.REFERENCE / "cdc_sala_casos_fallecidos.csv").set_index("anio")["casos_cdc"]
    ours = t["fact_caso"].groupby("anio")["casos"].sum()
    for year in range(2012, 2025):
        assert abs(ours[year] - official[year]) <= 1


def test_el_ubigeo_tiene_seis_digitos_y_el_padron_marca_los_distritos_nuevos(t):
    assert (t["dim_distrito"]["ubigeo"].str.len() == 6).all()
    new = t["dim_distrito"][t["dim_distrito"]["distrito_en_padron"] == 0]
    assert len(new) == 10 and "130112" in set(new["ubigeo"])
    assert t["fact_caso"].loc[t["fact_caso"]["ubigeo"].isin(new["ubigeo"]), "casos"].sum() == 1678


def test_la_edad_invalida_queda_sin_grupo_pero_cuenta(t):
    unknown_id = t["dim_grupo_edad"].set_index("grupo_edad").loc[parse.AGE_GROUP_UNKNOWN, "grupo_edad_id"]
    unknown = t["fact_caso"][t["fact_caso"]["grupo_edad_id"] == unknown_id]
    assert unknown["casos"].sum() == 14 and (unknown["casos_con_edad"] == 0).all() and (unknown["edad_suma"] == 0).all()


def test_las_formas_clinicas_mantienen_el_reparto_del_archivo(t):
    shares = t["fact_caso"].groupby("forma_clinica_id")["casos"].sum()
    assert shares.to_dict() == {1: 915_243, 2: 110_166, 3: 4_012}


def test_la_poblacion_departamental_suma_la_nacional_y_cubre_los_25_departamentos(t):
    pop = t["fact_poblacion_departamento"]
    assert pop["departamento_id"].nunique() == 25 and pop["anio"].min() == 2013 and pop["anio"].max() == 2024
    assert pop[(pop["anio"] == 2023)]["poblacion"].sum() == 33_725_844
    assert t["fact_poblacion_provincia"]["anio"].min() == 2016
    assert (t["dim_anio"].set_index("anio").loc[2016, "con_poblacion_provincial"] == 1)


def test_el_canal_endemico_usa_los_cinco_anios_previos_y_las_semanas_vecinas():
    years = list(range(2000, 2008))
    counts = np.zeros((len(years), 53))
    counts[:, 9] = [1, 2, 3, 4, 5, 6, 100, 200]          # semana 10 de cada año
    counts[:, 8] = 10                                      # semana 9 vecina
    counts[:, 10] = 0
    stats = transform.endemic_channel(counts, years, 53, (50, 75))
    assert min(year for year, _ in stats) == 2005         # hacen falta 5 años de historia
    median, threshold = stats[(2007, 10)]                  # historia: 2002–2006, semanas 9, 10 y 11
    window = np.concatenate([np.full(5, 10.0), counts[2:7, 9], np.zeros(5)])
    assert (median, threshold) == tuple(np.percentile(window, [50, 75]))


def test_una_semana_sobre_el_canal_necesita_un_minimo_de_casos(t):
    channel = t["fact_canal_endemico"]
    flagged = channel[channel["sobre_canal"] == 1]
    assert (flagged["casos"] >= transform.CHANNEL_MIN_CASES).all() and (flagged["casos"] >= flagged["umbral"] - 0.01).all()   # el umbral se guarda con 2 decimales
    assert channel["anio"].min() == 2005
    national = t["fact_canal_nacional"]
    assert national.loc[(national["anio"] == 2024) & (national["semana"] <= 12), "sobre_canal"].eq(1).all()


def test_la_semana_53_solo_existe_en_los_anios_que_la_traen(t):
    weeks = t["fact_canal_nacional"].groupby("anio")["semana"].max()
    assert weeks[2020] == 53 and weeks[2021] == 52 and weeks[2014] == 53

"""Reglas de campo de la Fase 2, probadas con recortes de los archivos reales (tests/fixtures)."""

from pathlib import Path

import numpy as np
import pandas as pd
import pytest

from src import parse, quality

FIXTURES = Path(__file__).parent / "fixtures"


@pytest.fixture(scope="module")
def cases():
    return parse.read_dengue(FIXTURES / "dengue_recorte.csv")


@pytest.fixture(scope="module")
def population():
    return parse.population(parse.read_indicadores(FIXTURES / "indicadores_recorte.csv"))


def test_el_ubigeo_se_lee_como_texto_de_seis_digitos(cases):
    assert cases["ubigeo"].str.fullmatch(r"\d{6}").all()
    assert (cases["departamento_id"] == cases["ubigeo"].str[:2]).all()
    assert (cases["provincia_id"] == cases["ubigeo"].str[:4]).all()
    assert (cases["ubigeo"].str.startswith("0")).any()          # el cero inicial sobrevive


def test_la_edad_imposible_se_marca_y_queda_sin_grupo(cases):
    absurd = cases[cases["edad_original"] == 71_963_641].iloc[0]
    assert absurd["edad_invalida"] and np.isnan(absurd["edad_anios"])
    assert absurd["grupo_edad"] == parse.AGE_GROUP_UNKNOWN
    assert cases["edad_invalida"].sum() == 2          # 71 963 641 y 814 años


def test_la_edad_en_meses_y_dias_se_pasa_a_años(cases):
    months = cases[(cases["tipo_edad"] == "M") & (cases["edad_original"] <= 11)]
    assert np.allclose(months["edad_anios"], months["edad_original"] / 12)
    assert (months["grupo_edad"] == "Menor de 1 año").all()
    days = cases[cases["tipo_edad"] == "D"]
    assert np.allclose(days["edad_anios"], days["edad_original"] / 365)


def test_los_grupos_de_edad_tienen_los_limites_del_curso_de_vida():
    ages = pd.Series([0.5, 1, 11.9, 12, 17.9, 18, 29.9, 30, 59.9, 60, 110.0, np.nan])
    got = parse.age_group(ages).tolist()
    assert got[:11] == ["Menor de 1 año", "Niñez (1–11)", "Niñez (1–11)", "Adolescencia (12–17)",
                        "Adolescencia (12–17)", "Juventud (18–29)", "Juventud (18–29)", "Adultez (30–59)",
                        "Adultez (30–59)", "Adulto mayor (60 o más)", "Adulto mayor (60 o más)"]
    assert got[11] == parse.AGE_GROUP_UNKNOWN


def test_la_forma_clinica_corresponde_al_cie10(cases):
    assert (cases["cie10"].map(parse.FORM_BY_CIE10) == cases["forma_clinica"]).all()
    assert set(cases["cie10"]) == {"A97.0", "A97.1", "A97.2"}


def test_los_casos_raros_del_archivo_real_estan_en_el_recorte(cases):
    assert (cases["localidad"] == "NULL").any()                 # «NULL» como texto
    assert (cases["diresa"] == "").any()
    assert (cases["semana"] == 53).any()
    assert ((cases["cie10"] == "A97.1") & (cases["anio"] == 2002)).any()
    assert (cases["ubigeo"] == "130112").any()                   # Alto Trujillo, distrito nuevo


def test_la_poblacion_toma_un_valor_por_territorio_y_anio(population):
    for level in ["departamento", "provincia"]:
        keys = [c for c in population[level].columns if c.endswith("_id")] + ["anio"]
        assert not population[level].duplicated(keys).any()


def test_lima_se_suma_en_un_solo_departamento(population):
    dep = population["departamento"]
    assert "15" in set(dep["departamento_id"]) and "1501" not in set(dep["departamento_id"])
    raw = parse.read_indicadores(FIXTURES / "indicadores_recorte.csv")
    lima = raw[(raw["ambito"] == 1) & raw["ubigeo_original"].astype(str).isin(["1501", "1599"])]
    expected = lima.groupby(["ubigeo_original", "anio"])["POBLACION_PROYECTADA"].first().groupby("anio").sum()
    got = dep[dep["departamento_id"] == "15"].set_index("anio")["poblacion"]
    assert got[2023] == expected[2023]


def test_los_departamentos_suman_la_poblacion_nacional(population):
    total = population["departamento"].groupby("anio")["poblacion"].sum()
    national = population["nacional"].set_index("anio")["poblacion"]
    assert (total == national.loc[total.index]).all()


def test_el_perfilado_reconoce_codigos_y_vacios(cases):
    raw = pd.read_csv(FIXTURES / "dengue_recorte.csv", sep=";", dtype=str, keep_default_na=False)
    profile = quality.profile_columns(raw).set_index("columna")
    assert profile.loc["ubigeo", "tipo_detectado"] == "código (texto)"
    assert profile.loc["diresa", "vacios"] >= 1
    assert profile.loc["edad", "maximo"] == 71_963_641


def test_los_atipicos_incluyen_las_edades_fuera_de_rango(cases):
    odd = quality.outliers(cases)
    assert odd.iloc[0]["edad_original"] == 71_963_641
    assert len(odd) >= 2

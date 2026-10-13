"""Los reportes versionados de la Fase 2 cumplen lo que dice la documentación."""

import pandas as pd
import pytest

from src import config


@pytest.fixture(scope="module")
def rules():
    return pd.read_csv(config.QUALITY / "reglas.csv")


@pytest.fixture(scope="module")
def checks():
    return pd.read_csv(config.REPORTS / "validaciones.csv")


def test_ninguna_regla_falla_y_hay_8_alertas(rules):
    assert len(rules) == 31
    assert not (rules["resultado"] == "falla").any()
    assert (rules["resultado"] == "alerta").sum() == 8
    assert set(rules["dimension"]) == {"Completitud", "Unicidad", "Validez", "Consistencia", "Exactitud", "Oportunidad"}


def test_v1_los_casos_por_anio_son_los_del_cdc(checks):
    v1 = checks[checks["validacion"] == "V1"]
    assert len(v1) == 13 and (v1["resultado"] == "cumple").all()
    assert (v1["diferencia_pct"].abs() <= 0.008).all()
    assert v1["calculado"].sum() == 28505 + 13091 + 17234 + 35816 + 25160 + 68290 + 4698 + 15287 + 47932 + 44791 + 63217 + 256641 + 271531


def test_el_archivo_coincide_con_la_serie_vigente_y_no_con_el_titular_de_la_alerta(checks):
    info = checks[checks["validacion"] == "V2-casos"].iloc[0]
    assert info["resultado"] == "info" and info["oficial"] == 273_684 and info["calculado"] == 256_641
    assert info["diferencia_pct"] == pytest.approx(-6.227, abs=0.001)


def test_v2_y_v3_cumplen(checks):
    for code in ["V2-forma", "V3"]:
        part = checks[checks["validacion"] == code]
        assert len(part) >= 1 and (part["resultado"] == "cumple").all()


def test_v4_la_poblacion_provincial_empieza_en_2016(checks):
    provinces = checks[checks["validacion"] == "V4-provincias"].set_index("anio")
    assert (provinces.loc[2013:2015, "resultado"] == "alerta").all()
    assert (provinces.loc[2016:, "resultado"] == "cumple").all()
    departments = checks[checks["validacion"] == "V4-departamentos"]
    assert len(departments) == 12 and (departments["resultado"] == "cumple").all()


def test_la_tabla_oficial_del_cdc_tiene_los_anios_de_la_sala():
    sala = pd.read_csv(config.REFERENCE / "cdc_sala_casos_fallecidos.csv")
    assert sala["anio"].tolist() == list(range(2012, 2027))
    assert sala.loc[sala["anio"] == 2023, ["casos_cdc", "fallecidos_cdc"]].iloc[0].tolist() == [256641, 444]


def test_la_clasificacion_con_signos_de_alarma_empieza_en_2010():
    table = pd.read_csv(config.QUALITY / "clasificacion.csv").set_index("anio")
    assert (table.loc[:2009, "Con signos de alarma"] <= 1).all()
    assert table.loc[2011, "Con signos de alarma"] > 3000

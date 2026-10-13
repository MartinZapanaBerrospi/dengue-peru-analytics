"""Las cifras del análisis (Fase 5) salen del modelo curado y coinciden con las del tablero."""

import pandas as pd
import pytest

from src import config

ANALYSIS = config.REPORTS / "analisis"


@pytest.fixture(scope="module")
def key():
    table = pd.read_csv(ANALYSIS / "cifras_clave.csv")
    return dict(zip(table["cifra"], table["valor"]))


def number(key, name):
    return float(key[name])


def test_las_cifras_clave_estan_completas(key):
    assert len(key) >= 100
    for name in ["casos_total", "incidencia_2023", "dep_mayor_incidencia", "semanas_pais_sobre_canal_2023", "pct_alarma_max"]:
        assert name in key


def test_los_casos_son_los_del_archivo_y_los_del_cdc(key):
    assert number(key, "casos_total") == 1_029_421
    sala = pd.read_csv(config.REFERENCE / "cdc_sala_casos_fallecidos.csv").set_index("anio")["casos_cdc"]
    assert number(key, "casos_2023") == sala[2023] and number(key, "casos_2024") == sala[2024]
    assert number(key, "veces_2023_vs_2022") == pytest.approx(256_641 / 63_217)


def test_la_incidencia_nacional_se_recalcula_con_la_poblacion_oficial(key):
    assert number(key, "incidencia_2023") == pytest.approx(256_641 / 33_725_844 * 1e5)
    assert number(key, "incidencia_2024") == pytest.approx(271_531 / 34_038_457 * 1e5)


def test_la_incidencia_por_departamento_coincide_con_la_medida_dax():
    dax = pd.read_csv(config.REPORTS / "validacion_medidas.csv")
    dax = dax[(dax["contexto"] == "anio_departamento") & (dax["medida"] == "Incidencia por 100 mil")]
    dax = dax.set_index("clave")["python"].astype(float)
    table = pd.read_csv(ANALYSIS / "p3_departamentos.csv").set_index("departamento")
    for dep in ["Tumbes", "Piura", "Ica", "Lima"]:
        assert table.loc[dep, "incidencia_2023"] == pytest.approx(dax[f"2023|{dep}"], rel=1e-9)
        assert table.loc[dep, "incidencia_2024"] == pytest.approx(dax[f"2024|{dep}"], rel=1e-9)


def test_el_pico_de_cada_anio_sale_de_la_curva_semanal(key):
    peak = pd.read_csv(ANALYSIS / "p2_temporada_anual.csv").set_index("anio")
    assert peak.loc[2023, "semana_pico"] == number(key, "semana_pico_2023") == 20
    assert peak.loc[2024, "casos_semana_pico"] == 21_628
    assert (peak["semana_10pct"] <= peak["semana_50pct"]).all() and (peak["semana_50pct"] <= peak["semana_90pct"]).all()


def test_la_gravedad_solo_se_compara_desde_2011():
    table = pd.read_csv(ANALYSIS / "p5_gravedad_anual.csv")
    assert table["anio"].min() == 2011
    assert table["pct_alarma_o_grave"].between(0, 0.3).all()


def test_el_canal_del_pais_en_2023_estuvo_sobrepasado_casi_todo_el_anio(key):
    assert number(key, "semanas_pais_sobre_canal_2023") == 47
    assert number(key, "primera_semana_sobre_canal_2023") == 1
    assert number(key, "semanas_pais_sobre_canal_2018") == 0


def test_las_tablas_de_soporte_existen():
    expected = {"p1_evolucion_anual", "p2_temporada_anual", "p2_perfil_semanal", "p3_departamentos", "p3_expansion",
                "p4_edad_sexo_anual", "p5_gravedad_anual", "p5_gravedad_por_edad", "p6_canal_anual"}
    assert expected <= {p.stem for p in ANALYSIS.glob("*.csv")}

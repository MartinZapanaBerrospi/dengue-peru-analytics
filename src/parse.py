"""Lectura de los archivos de datos abiertos y reglas de limpieza a nivel de campo.

Cada función resuelve un problema del catálogo de la Fase 2 (docs/02_calidad.md); el número del
problema va en el comentario. La Fase 2 las usa para medir la calidad y la Fase 3 para construir
el modelo, así que las dos fases aplican exactamente las mismas reglas.
"""

import numpy as np
import pandas as pd

from src import config

# Nombre en el archivo -> nombre en el proyecto
COLUMNS = {
    "departamento": "departamento", "provincia": "provincia", "distrito": "distrito", "localidad": "localidad",
    "enfermedad": "forma_clinica", "ano": "anio", "semana": "semana", "diagnostic": "cie10", "diresa": "diresa",
    "ubigeo": "ubigeo", "localcod": "localcod", "edad": "edad_original", "tipo_edad": "tipo_edad", "sexo": "sexo",
}
FORM_BY_CIE10 = {"A97.0": "DENGUE SIN SIGNOS DE ALARMA", "A97.1": "DENGUE CON SIGNOS DE ALARMA", "A97.2": "DENGUE GRAVE"}
FORM_SHORT = {
    "DENGUE SIN SIGNOS DE ALARMA": "Sin signos de alarma",
    "DENGUE CON SIGNOS DE ALARMA": "Con signos de alarma",
    "DENGUE GRAVE": "Grave",
}
# Cursos de vida del MINSA agrupados: (límite superior en años exclusivo, nombre)
AGE_GROUPS = [(1, "Menor de 1 año"), (12, "Niñez (1–11)"), (18, "Adolescencia (12–17)"), (30, "Juventud (18–29)"),
              (60, "Adultez (30–59)"), (200, "Adulto mayor (60 o más)")]
AGE_GROUP_UNKNOWN = "Sin edad válida"
EPIDEMIC_WEEKS_IN_2020 = 53


def read_dengue(path=None) -> pd.DataFrame:
    """Un caso por fila, con tipos, claves territoriales y edad en años (problemas 1 a 5)."""
    df = pd.read_csv(path or config.RAW / "dengue.csv", sep=";", dtype=str, keep_default_na=False)
    df = df.rename(columns=COLUMNS)
    for col in ["departamento", "provincia", "distrito", "localidad"]:
        df[col] = df[col].str.strip()
    df["anio"] = df["anio"].astype(int)
    df["semana"] = df["semana"].astype(int)
    df["edad_original"] = pd.to_numeric(df["edad_original"], errors="raise")
    df["departamento_id"] = df["ubigeo"].str[:2]
    df["provincia_id"] = df["ubigeo"].str[:4]
    return add_age(df)


def add_age(df: pd.DataFrame) -> pd.DataFrame:
    """Edad en años y su grupo.

    Problema 2: la edad viene en años, meses o días (`tipo_edad`) y a veces con valores imposibles
    (hasta 71 963 641 años). Una edad mayor al máximo se marca y queda sin grupo: el caso se cuenta
    en todo lo demás.
    """
    age = df["edad_original"].astype(float)
    years = np.select([df["tipo_edad"] == "A", df["tipo_edad"] == "M", df["tipo_edad"] == "D"],
                      [age, age / 12, age / 365], default=np.nan)
    df["edad_anios"] = years
    df["edad_invalida"] = ~(np.isfinite(years) & (years <= config.MAX_AGE_YEARS))
    df.loc[df["edad_invalida"], "edad_anios"] = np.nan
    df["grupo_edad"] = age_group(df["edad_anios"])
    return df


def age_group(years: pd.Series) -> pd.Series:
    out = pd.Series(AGE_GROUP_UNKNOWN, index=years.index, dtype="object")
    lower = 0.0
    for upper, name in AGE_GROUPS:
        out[(years >= lower) & (years < upper)] = name
        lower = upper
    return out


def read_indicadores(path=None) -> pd.DataFrame:
    df = pd.read_csv(path or config.RAW / "indicadores.csv", dtype={"UBIGEO_DASH": "string"})
    return df.rename(columns={"UBIGEO_DASH": "ubigeo_original", "ANIO": "anio", "AMBITO": "ambito",
                              "INDICADOR": "indicador", "FUENTE": "fuente"})


def population(indicators: pd.DataFrame) -> dict:
    """Población proyectada por territorio y año.

    Problema 7: cada indicador repite la población del territorio, así que sumarla directamente la
    inflaría. Se toma un valor por (ámbito, territorio, año).

    Departamento: los códigos son los de INEI sin cero inicial; Lima viene partida en 1501 (Lima
    Metropolitana) y 1599 (Región Lima) y aquí se suma, porque el dengue la trae como un solo departamento.
    Provincia: los 4 primeros dígitos del código de 6.
    """
    unique = (indicators.groupby(["ambito", "ubigeo_original", "anio"], as_index=False)
              ["POBLACION_PROYECTADA"].first().rename(columns={"POBLACION_PROYECTADA": "poblacion"}))
    national = unique[unique["ambito"] == 0][["anio", "poblacion"]].reset_index(drop=True)

    dep = unique[unique["ambito"] == 1].copy()
    dep["departamento_id"] = dep["ubigeo_original"].astype(str).str.zfill(2).where(
        ~dep["ubigeo_original"].astype(str).isin(["1501", "1599"]), "15")
    dep = dep.groupby(["departamento_id", "anio"], as_index=False)["poblacion"].sum()

    prov = unique[unique["ambito"] == 2].copy()
    prov["provincia_id"] = prov["ubigeo_original"].astype(str).str.zfill(6).str[:4]
    prov = prov.groupby(["provincia_id", "anio"], as_index=False)["poblacion"].sum()
    return {"nacional": national, "departamento": dep, "provincia": prov}

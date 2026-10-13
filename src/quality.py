"""Fase 2 — Perfilado, reglas de calidad en seis dimensiones y atípicos.

Escribe en reports/calidad/:
    perfilado_columnas.csv   tipo, vacíos, valores distintos, mínimo, máximo y más frecuentes de cada columna
    perfilado_anual.csv      casos, territorios, formas clínicas y problemas de edad por año
    reglas.csv               cada regla medible con su resultado, en las seis dimensiones
    atipicos.csv             casos con edad fuera de rango
    clasificacion.csv        aparición de cada forma clínica por año (cambio de definición)

Uso:
    python -m src.quality
"""

import sys

import numpy as np
import pandas as pd

from src import config, parse, validate

QUALITY = config.QUALITY
EMPTY_THRESHOLD_PCT = 1.0       # más de este % de vacíos en una columna que se usa marca alerta
CODE_COLUMNS = {"ubigeo", "diresa", "localcod"}   # códigos: se leen como texto para no perder el cero inicial
LAG_MONTHS_ALERT = 6            # rezago aceptable entre el cierre de los datos y su publicación


def raw_frame() -> pd.DataFrame:
    return pd.read_csv(config.RAW / "dengue.csv", sep=";", dtype=str, keep_default_na=False)


def profile_columns(raw: pd.DataFrame) -> pd.DataFrame:
    rows = []
    for col in raw.columns:
        s = raw[col]
        numeric = pd.to_numeric(s.where(s != ""), errors="coerce")
        is_numeric = numeric.notna().sum() == (s != "").sum() and (s != "").any() and col not in CODE_COLUMNS
        top = s[s != ""].value_counts().head(3)
        rows.append({
            "columna": col,
            "tipo_detectado": "numérico" if is_numeric else ("código (texto)" if col in CODE_COLUMNS else "texto"),
            "vacios": int((s == "").sum()),
            "pct_vacios": round(100 * (s == "").mean(), 3),
            "distintos": int(s.nunique()),
            "minimo": numeric.min() if is_numeric else s[s != ""].min(),
            "maximo": numeric.max() if is_numeric else s[s != ""].max(),
            "mas_frecuentes": "; ".join(f"{k} ({v})" for k, v in top.items()),
        })
    return pd.DataFrame(rows)


def profile_years(df: pd.DataFrame) -> pd.DataFrame:
    g = df.groupby("anio")
    out = g.agg(casos=("sexo", "size"), departamentos=("departamento_id", "nunique"), distritos=("ubigeo", "nunique"),
                semana_maxima=("semana", "max"), edad_invalida=("edad_invalida", "sum"))
    forms = df.pivot_table(index="anio", columns="cie10", values="sexo", aggfunc="size", fill_value=0)
    out["sin_signos"] = forms.get("A97.0", 0)
    out["con_signos"] = forms.get("A97.1", 0)
    out["graves"] = forms.get("A97.2", 0)
    out["pct_alarma_o_grave"] = (100 * (out["con_signos"] + out["graves"]) / out["casos"]).round(2)
    out["pct_mujeres"] = (100 * g["sexo"].apply(lambda s: (s == "F").mean())).round(1)
    out["mediana_edad"] = g["edad_anios"].median().round(1)
    return out.reset_index()


def classification_table(df: pd.DataFrame) -> pd.DataFrame:
    """Problema 3: «con signos de alarma» existe desde 2010. Antes la parte de graves no es comparable."""
    t = df.pivot_table(index="anio", columns="forma_clinica", values="sexo", aggfunc="size", fill_value=0)
    t = t.rename(columns=parse.FORM_SHORT)
    t["pct_con_signos"] = (100 * t["Con signos de alarma"] / t.sum(axis=1)).round(2)
    return t.reset_index()


def outliers(df: pd.DataFrame) -> pd.DataFrame:
    odd = df[df["edad_invalida"] | ((df["tipo_edad"] == "A") & (df["edad_original"] > 100))]
    out = odd[["anio", "semana", "departamento", "distrito", "tipo_edad", "edad_original", "forma_clinica", "sexo"]]
    return out.sort_values("edad_original", ascending=False).reset_index(drop=True)


def district_register(indicators: pd.DataFrame) -> set:
    """Distritos del padrón del MININTER (ámbito 3), con UBIGEO de 6 dígitos."""
    d = indicators[indicators["ambito"] == 3]["ubigeo_original"].astype("string").str.zfill(6)
    return set(d.dropna())


def run_rules(raw: pd.DataFrame, df: pd.DataFrame, register: set, checks: pd.DataFrame) -> pd.DataFrame:
    rules: list[dict] = []

    def rule(dimension, name, measured, ok, severity, detail):
        result = "cumple" if ok else ("alerta" if severity == "alerta" else "falla")
        rules.append({"dimension": dimension, "regla": name, "medido": measured, "resultado": result,
                      "severidad": severity, "detalle": detail})

    n = len(df)
    # Completitud
    essential = ["departamento", "provincia", "distrito", "enfermedad", "ano", "semana", "diagnostic", "ubigeo",
                 "edad", "tipo_edad", "sexo"]
    empty_essential = int((raw[essential] == "").sum().sum())
    rule("Completitud", "Los 11 campos esenciales no traen vacíos", empty_essential, empty_essential == 0,
         "bloqueante", "departamento, provincia, distrito, enfermedad, año, semana, CIE-10, UBIGEO, edad, tipo de edad y sexo")
    for col in ["diresa", "localidad", "localcod"]:
        # `localidad` usa además el texto «NULL» como vacío
        empty = int(((raw[col] == "") | (raw[col] == "NULL")).sum())
        pct = 100 * empty / n
        rule("Completitud", f"`{col}` con menos de {EMPTY_THRESHOLD_PCT:g} % de vacíos", empty,
             pct <= EMPTY_THRESHOLD_PCT, "alerta", f"{empty:,} vacíos ({pct:.2f} %)".replace(",", " "))
    years = set(df["anio"].unique())
    missing_years = sorted(set(range(config.FIRST_YEAR, config.LAST_YEAR + 1)) - years)
    rule("Completitud", "Hay casos en cada año de 2000 a 2024", len(missing_years), not missing_years, "bloqueante",
         f"años sin casos: {missing_years or 'ninguno'}")

    # Unicidad
    duplicated = int(raw.duplicated().sum())
    rule("Unicidad", "Filas idénticas (informativa: no hay identificador de caso)", duplicated, True, "info",
         f"{duplicated:,} filas ({100 * duplicated / n:.1f} %) repiten otra; no son duplicados: dos pacientes con la "
         "misma edad, sexo, lugar y semana producen la misma fila".replace(",", " "))
    names_per_ubigeo = df.groupby("ubigeo")["distrito"].nunique()
    rule("Unicidad", "Cada UBIGEO tiene un solo nombre de distrito", int((names_per_ubigeo > 1).sum()),
         (names_per_ubigeo > 1).sum() == 0, "bloqueante", f"{df['ubigeo'].nunique()} UBIGEO")
    parents = df.groupby("ubigeo")[["provincia", "departamento"]].nunique().max(axis=1)
    rule("Unicidad", "Cada UBIGEO tiene una sola provincia y un solo departamento", int((parents > 1).sum()),
         (parents > 1).sum() == 0, "bloqueante", "")

    # Validez
    rule("Validez", "Sexo es F o M", int((~df["sexo"].isin(["F", "M"])).sum()), df["sexo"].isin(["F", "M"]).all(),
         "bloqueante", "")
    rule("Validez", "Tipo de edad es A, M o D", int((~df["tipo_edad"].isin(["A", "M", "D"])).sum()),
         df["tipo_edad"].isin(["A", "M", "D"]).all(), "bloqueante", "")
    in_range = df["anio"].between(config.FIRST_YEAR, config.LAST_YEAR)
    rule("Validez", "Año entre 2000 y 2024", int((~in_range).sum()), in_range.all(), "bloqueante", "")
    week_ok = df["semana"].between(1, 53)
    rule("Validez", "Semana epidemiológica entre 1 y 53", int((~week_ok).sum()), week_ok.all(), "bloqueante", "")
    w53 = df[df["semana"] == 53]
    rule("Validez", "La semana 53 solo aparece en años con 53 semanas", len(w53), True, "info",
         f"{len(w53):,} casos en la semana 53, todos de {sorted(w53['anio'].unique().tolist())}".replace(",", " "))
    rule("Validez", "CIE-10 es A97.0, A97.1 o A97.2", int((~df["cie10"].isin(parse.FORM_BY_CIE10)).sum()),
         df["cie10"].isin(parse.FORM_BY_CIE10).all(), "bloqueante", "")
    well_formed = df["ubigeo"].str.fullmatch(r"\d{6}")
    rule("Validez", "UBIGEO de 6 dígitos numéricos", int((~well_formed).sum()), well_formed.all(), "bloqueante", "")
    in_register = df["ubigeo"].isin(register)
    missing = df.loc[~in_register, "ubigeo"].nunique()
    rule("Validez", "El UBIGEO existe en el padrón de distritos", int((~in_register).sum()), in_register.all(), "alerta",
         f"{missing} UBIGEO fuera del padrón (distritos creados desde 2021), {int((~in_register).sum()):,} casos".replace(",", " "))
    invalid_age = int(df["edad_invalida"].sum())
    rule("Validez", f"Edad de {config.MAX_AGE_YEARS} años o menos", invalid_age, invalid_age == 0, "alerta",
         f"{invalid_age} casos de {sorted(df.loc[df['edad_invalida'], 'anio'].unique().tolist())}, con hasta "
         f"{int(df['edad_original'].max()):,} años".replace(",", " "))
    baby = int(((df["tipo_edad"] == "A") & (df["edad_original"] == 0)).sum())
    rule("Validez", "Edad de 0 en años (se toma como menor de 1 año)", baby, True, "info", f"{baby} casos")

    # Consistencia
    expected_form = df["cie10"].map(parse.FORM_BY_CIE10)
    mismatch = int((expected_form != df["forma_clinica"]).sum())
    rule("Consistencia", "La forma clínica corresponde al CIE-10", mismatch, mismatch == 0, "bloqueante",
         "A97.0 sin signos, A97.1 con signos de alarma, A97.2 grave")
    dep_per_prefix = df.groupby("departamento_id")["departamento"].nunique()
    rule("Consistencia", "El nombre del departamento corresponde al prefijo del UBIGEO", int((dep_per_prefix > 1).sum()),
         (dep_per_prefix > 1).sum() == 0, "bloqueante", f"{df['departamento_id'].nunique()} prefijos")
    month_bad = int(((df["tipo_edad"] == "M") & (df["edad_original"] > 11)).sum())
    rule("Consistencia", "Edad en meses de 11 o menos (desde 12 meses es 1 año)", month_bad, month_bad == 0, "alerta",
         f"{month_bad} casos")
    day_bad = int(((df["tipo_edad"] == "D") & (df["edad_original"] > 30)).sum())
    rule("Consistencia", "Edad en días de 30 o menos", day_bad, day_bad == 0, "alerta", f"{day_bad} casos")
    early_alarm = df[(df["cie10"] == "A97.1") & (df["anio"] < 2010)]
    rule("Consistencia", "«Con signos de alarma» no aparece antes de 2010 (cambio de clasificación)", len(early_alarm),
         len(early_alarm) == 0, "alerta", f"{len(early_alarm)} caso(s) antes de 2010: {sorted(early_alarm['anio'].unique().tolist())}")

    # Exactitud (validaciones contra cifras oficiales)
    for code, label in [("V1", "V1: casos por año igual a la sala situacional del CDC (2012–2024)"),
                        ("V2-forma", "V2: reparto por forma clínica de 2023 igual al de la alerta del CDC"),
                        ("V3", "V3: población nacional igual a la implícita en la incidencia oficial"),
                        ("V4-departamentos", "V4: población de los departamentos suma la nacional")]:
        part = checks[checks["validacion"] == code]
        bad = int((part["resultado"] != "cumple").sum())
        rule("Exactitud", label, bad, bad == 0, "bloqueante",
             f"{len(part)} comparaciones; diferencia máxima {part['diferencia_pct'].abs().max():.3f} %")
    provinces = checks[checks["validacion"] == "V4-provincias"]
    rule("Exactitud", "V4: población de las provincias suma la nacional (desde 2016)",
         int((provinces[provinces["anio"] >= 2016]["resultado"] != "cumple").sum()),
         (provinces[provinces["anio"] >= 2016]["resultado"] == "cumple").all(), "bloqueante",
         "2013–2015 traen solo parte de las provincias")
    info = checks[checks["validacion"] == "V2-casos"].iloc[0]
    rule("Exactitud", "Casos de 2023 frente al titular de la alerta (informativa: corte distinto)",
         round(float(info["diferencia_pct"]), 3), True, "info",
         "el CDC revisa la serie: 273 684 en la alerta de 2024 y 256 641 en la sala vigente")

    # Oportunidad
    sala = pd.read_csv(config.REFERENCE / "cdc_sala_casos_fallecidos.csv")
    last_live = int(sala["anio"].max())
    behind = last_live - int(df["anio"].max())
    rule("Oportunidad", "El archivo llega al año más reciente que publica el CDC", behind, behind == 0, "alerta",
         f"el archivo llega a {int(df['anio'].max())}; la sala situacional ya muestra {last_live}")
    published = pd.Timestamp("2025-12-16")
    lag = (published.year - config.LAST_YEAR) * 12 + published.month - 12
    rule("Oportunidad", f"Rezago de publicación de {LAG_MONTHS_ALERT} meses o menos", lag, lag <= LAG_MONTHS_ALERT, "alerta",
         f"los datos terminan en diciembre de 2024 y se publicaron el {published.date()}: {lag} meses")
    return pd.DataFrame(rules)


def main() -> int:
    if hasattr(sys.stdout, "reconfigure"):
        sys.stdout.reconfigure(encoding="utf-8")
    QUALITY.mkdir(parents=True, exist_ok=True)
    raw = raw_frame()
    df = parse.read_dengue()
    indicators = parse.read_indicadores()
    checks = validate.compare_all(df, parse.population(indicators))

    profile_columns(raw).to_csv(QUALITY / "perfilado_columnas.csv", index=False)
    profile_years(df).to_csv(QUALITY / "perfilado_anual.csv", index=False)
    classification_table(df).to_csv(QUALITY / "clasificacion.csv", index=False)
    outliers(df).to_csv(QUALITY / "atipicos.csv", index=False)
    rules = run_rules(raw, df, district_register(indicators), checks)
    rules.to_csv(QUALITY / "reglas.csv", index=False)

    summary = rules.groupby(["dimension", "resultado"]).size().unstack(fill_value=0)
    print(summary.to_string())
    failed = rules[rules["resultado"] == "falla"]
    for r in failed.itertuples():
        print(f"  ✗ {r.regla}: {r.detalle}")
    return 1 if len(failed) else 0


if __name__ == "__main__":
    sys.exit(main())

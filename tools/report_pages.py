"""Páginas y visuales del informe de Power BI (PBIR), escritos por tools/build_report.py.

Lienzo de 1280 × 720 con márgenes de 24 px. Las cifras de los textos salen de
reports/analisis/cifras_clave.csv (Fase 5): el tablero no repite números escritos a mano.
"""

import csv
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
KEY = {r["cifra"]: r["valor"] for r in csv.DictReader(
    (ROOT / "reports" / "analisis" / "cifras_clave.csv").open(encoding="utf-8"))}

INK, MUTED, PANEL = "#1b1f24", "#4a5058", "#ffffff"
ACCENT = "#1f5f99"


# ---------------------------------------------------------------------------------------------
# Formato de cifras en español del Perú
# ---------------------------------------------------------------------------------------------

def num(value, decimals: int = 0) -> str:
    """1234567.8 -> '1 234 568' ; con decimales usa coma: 2,5."""
    text = f"{float(value):,.{decimals}f}"
    return text.replace(",", " ").replace(".", ",").replace("-", "−")


def pct(value, decimals: int = 1) -> str:
    return f"{num(float(value) * 100, decimals)} %"


def millions(value, decimals: int = 1) -> str:
    return f"S/ {num(float(value) / 1e6, decimals)} millones"


def k(name: str) -> str:
    return KEY[name]


def proper(name: str) -> str:
    """'SAN JUAN' -> 'San Juan' (artículos y preposiciones en minúscula)."""
    small = {"de", "del", "la", "las", "el", "los", "y", "e", "en", "para", "por", "a"}
    words = name.lower().split()
    return " ".join(w if i and w in small else w.capitalize() for i, w in enumerate(words))


# ---------------------------------------------------------------------------------------------
# Piezas PBIR
# ---------------------------------------------------------------------------------------------

def lit(value: str) -> dict:
    return {"expr": {"Literal": {"Value": value}}}


def text(value: str) -> dict:
    return lit("'" + value.replace("'", "''") + "'")


def color(hex_code: str) -> dict:
    return {"solid": {"color": lit(f"'{hex_code}'")}}


def measure(name: str, display: str | None = None) -> dict:
    p = {"field": {"Measure": {"Expression": {"SourceRef": {"Entity": "_Medidas"}}, "Property": name}},
         "queryRef": f"_Medidas.{name}", "nativeQueryRef": name}
    if display:
        p["displayName"] = display
    return p


def column(entity: str, prop: str, display: str | None = None, active: bool = False) -> dict:
    p = {"field": {"Column": {"Expression": {"SourceRef": {"Entity": entity}}, "Property": prop}},
         "queryRef": f"{entity}.{prop}", "nativeQueryRef": prop}
    if display:
        p["displayName"] = display
    if active:
        p["active"] = True
    return p


def sort_by(projection: dict, direction: str = "Descending") -> dict:
    return {"sort": [{"field": projection["field"], "direction": direction}]}


def container(title: str | None = None, background: bool = True) -> dict:
    objects = {
        "background": [{"properties": {"show": lit("true" if background else "false"),
                                       **({"color": color(PANEL), "transparency": lit("0D")} if background else {})}}],
        "border": [{"properties": {"show": lit("false")}}],
        "dropShadow": [{"properties": {"show": lit("false")}}],
        "subTitle": [{"properties": {"show": lit("false")}}],
        "title": [{"properties": {"show": lit("false")}}],
    }
    if title:
        objects["title"] = [{"properties": {
            "show": lit("true"), "text": text(title), "fontSize": lit("11D"),
            "fontColor": color(INK), "bold": lit("false"), "fontFamily": text("Segoe UI Semibold")}}]
    return objects


def position(x, y, w, h) -> dict:
    return {"x": x, "y": y, "z": 0, "height": h, "width": w, "tabOrder": 0}


def visual(name: str, pos: dict, body: dict) -> dict:
    return {
        "$schema": "https://developer.microsoft.com/json-schemas/fabric/item/report/definition/visualContainer/2.12.0/schema.json",
        "name": name, "position": pos, "visual": body,
    }


def textbox(name, x, y, w, h, paragraphs, background=False) -> dict:
    """paragraphs: lista de (texto, tamaño en pt, color, negrita)."""
    paras = []
    for content, size, hex_code, bold in paragraphs:
        paras.append({"textRuns": [{"value": content, "textStyle": {
            "fontFamily": "Segoe UI Semibold" if bold else "Segoe UI", "fontSize": f"{size}pt", "color": hex_code}}]})
    return visual(name, position(x, y, w, h), {
        "visualType": "textbox",
        "objects": {"general": [{"properties": {"paragraphs": paras}}]},
        "visualContainerObjects": container(background=background),
    })


def title(page_title: str, answer: str, width: int = 1016) -> dict:
    """Título (la pregunta) y subtítulo (la respuesta). Deja libre la esquina derecha para el segmentador."""
    return textbox("titulo", 24, 8, width, 72, [(page_title, 18, INK, True), (answer, 11, MUTED, False)])


def footer() -> dict:
    return textbox("fuente", 24, 690, 1232, 24, [(
        "Fuente: CDC Perú (MINSA), vigilancia epidemiológica de dengue, 2000–2024, y población proyectada del MININTER "
        "(datosabiertos.gob.pe). Un caso notificado no es una infección. Elaboración propia.", 8, MUTED, False)])


def reading(name, x, y, w, h, heading, bullets, extra_heading=None, extra=None) -> dict:
    paras = [(heading, 11, INK, True)] + [("• " + b, 10, INK, False) for b in bullets]
    if extra_heading:
        paras += [(extra_heading, 11, INK, True)] + [("• " + b, 10, INK, False) for b in extra]
    return textbox(name, x, y, w, h, paras, background=True)


def card(name, x, y, w, h, measure_name, label, value_size=22) -> dict:
    return visual(name, position(x, y, w, h), {
        "visualType": "card",
        "query": {"queryState": {"Values": {"projections": [measure(measure_name)]}}},
        "objects": {
            "labels": [{"properties": {"fontSize": lit(f"{value_size}D"), "color": color(ACCENT),
                                       "fontFamily": text("Segoe UI Semibold"), "labelDisplayUnits": lit("1D")}}],
            "categoryLabels": [{"properties": {"show": lit("false")}}],
        },
        "visualContainerObjects": {**container(), "title": [{"properties": {
            "show": lit("true"), "text": text(label), "fontSize": lit("10D"), "fontColor": color(MUTED),
            "bold": lit("false"), "fontFamily": text("Segoe UI")}}]},
    })


def axis_objects(categorical: bool = False, labels: bool = False, legend: bool = False, compact: bool = False) -> dict:
    objects = {
        "categoryAxis": [{"properties": {"showAxisTitle": lit("false"), "gridlineShow": lit("false"),
                                         "labelColor": color(MUTED), "fontSize": lit("8D" if compact else "9D"),
                                         **({"axisType": text("Categorical")} if categorical else {}),
                                         **({"innerPadding": lit("12D")} if compact else {})}}],
        # labelDisplayUnits 1 = sin abreviar: "3 135,8" y no "3,1 mil" (los montos ya están en millones)
        "valueAxis": [{"properties": {"showAxisTitle": lit("false"), "gridlineColor": color("#e9ecef"),
                                      "labelColor": color(MUTED), "fontSize": lit("9D"),
                                      "labelDisplayUnits": lit("1D"),
                                      **({"show": lit("false")} if compact else {})}}],
        "legend": [{"properties": {"show": lit("true" if legend else "false"), "position": text("Top"),
                                   "fontSize": lit("9D"), "labelColor": color(MUTED)}}],
    }
    if labels:
        objects["labels"] = [{"properties": {"show": lit("true"), "fontSize": lit("9D"), "color": color(INK),
                                             "labelDisplayUnits": lit("1D")}}]
    return objects


def chart(name, kind, x, y, w, h, chart_title, category, values, series=None, sort=None,
          categorical=False, labels=False, legend=False, compact=False) -> dict:
    state = {"Category": {"projections": [category]}, "Y": {"projections": values}}
    if series:
        state["Series"] = {"projections": [series]}
    query = {"queryState": state}
    if sort:
        query["sortDefinition"] = sort
    return visual(name, position(x, y, w, h), {
        "visualType": kind, "query": query,
        "objects": axis_objects(categorical, labels, legend, compact),
        "visualContainerObjects": container(chart_title),
    })


def table(name, x, y, w, h, table_title, projections, sort=None, widths=None) -> dict:
    """widths: ancho en píxeles de cada columna, en el orden de projections. Deben sumar menos que w."""
    query = {"queryState": {"Values": {"projections": projections}}}
    if sort:
        query["sortDefinition"] = sort
    objects = {
        "columnHeaders": [{"properties": {"fontSize": lit("9D"), "fontColor": color(INK), "wordWrap": lit("true")}}],
        "values": [{"properties": {"fontSize": lit("9D"), "wordWrap": lit("false")}}],
        "total": [{"properties": {"totals": lit("false")}}],
    }
    if widths:
        assert len(widths) == len(projections) and sum(widths) <= w - 40, name
        objects["columnWidth"] = [{"properties": {"value": lit(f"{width}D")}, "selector": {"metadata": p["queryRef"]}}
                                  for p, width in zip(projections, widths)]
    return visual(name, position(x, y, w, h), {
        "visualType": "tableEx", "query": query, "objects": objects,
        "visualContainerObjects": container(table_title),
    })


def slicer(name, x, y, w, h, entity, prop, header, order_prop=None, selected=None) -> dict:
    """selected: valor numérico que el segmentador trae elegido al abrir el informe (se guarda como filtro)."""
    query = {"queryState": {"Values": {"projections": [column(entity, prop, active=True)]}}}
    if order_prop:
        query["sortDefinition"] = sort_by(column(entity, order_prop), "Ascending")
    out = visual(name, position(x, y, w, h), {
        "visualType": "slicer", "query": query,
        "objects": {
            "data": [{"properties": {"mode": text("Dropdown")}}],
            "selection": [{"properties": {"strictSingleSelect": lit("false"), "singleSelect": lit("false")}}],
            "header": [{"properties": {"show": lit("true"), "text": text(header)}}],
        },
        "visualContainerObjects": container(background=False),
    })
    if selected is not None:
        # El segmentador guarda lo que trae elegido en objects.general[].properties.filter.
        out["visual"]["objects"]["general"] = [{"properties": {"filter": {"filter": {
            "Version": 2,
            "From": [{"Name": "t", "Entity": entity, "Type": 0}],
            "Where": [{"Condition": {"In": {
                "Expressions": [{"Column": {"Expression": {"SourceRef": {"Source": "t"}}, "Property": prop}}],
                "Values": [[{"Literal": {"Value": f"{v}L"}}] for v in ([selected] if isinstance(selected, int) else selected)]}}}],
        }}}}]
    return out


def matrix(name, x, y, w, h, matrix_title, rows, columns, values) -> dict:
    """Tabla cruzada: filas × columnas con una o más medidas."""
    return visual(name, position(x, y, w, h), {
        "visualType": "pivotTable",
        "query": {"queryState": {"Rows": {"projections": rows}, "Columns": {"projections": columns},
                                 "Values": {"projections": values}}},
        "objects": {
            "columnHeaders": [{"properties": {"fontSize": lit("9D"), "fontColor": color(INK)}}],
            "rowHeaders": [{"properties": {"fontSize": lit("9D"), "fontColor": color(INK)}}],
            "values": [{"properties": {"fontSize": lit("9D")}}],
            "subTotals": [{"properties": {"rowSubtotals": lit("false"), "columnSubtotals": lit("false")}}],
        },
        "visualContainerObjects": container(matrix_title),
    })


def year_slicer(x=1056, selected=None, header="Año (vacío = todos)", y=12) -> dict:
    return slicer("segmentador_anio", x, y, 200, 64, "dim_anio", "anio", header, selected=selected)


def with_filter(vis: dict, entity: str, prop: str, values: list, name: str = "filtro") -> dict:
    """Filtro fijo del visual: solo entran las filas cuya columna vale alguno de `values` (enteros)."""
    vis.setdefault("filterConfig", {"filters": []})["filters"].append({
        "name": name,
        "field": {"Column": {"Expression": {"SourceRef": {"Entity": entity}}, "Property": prop}},
        "type": "Categorical",
        "filter": {"Version": 2, "From": [{"Name": "t", "Entity": entity, "Type": 0}],
                   "Where": [{"Condition": {"In": {
                       "Expressions": [{"Column": {"Expression": {"SourceRef": {"Source": "t"}}, "Property": prop}}],
                       "Values": [[{"Literal": {"Value": f"{v}L"}}] for v in values]}}}]},
    })
    return vis


# ---------------------------------------------------------------------------------------------
# Páginas
# ---------------------------------------------------------------------------------------------

LAST_YEAR = 2024
CHECKS = sum(1 for _ in (ROOT / "reports" / "validacion_medidas.csv").open(encoding="utf-8")) - 1   # comparaciones de la Fase 4
HIGH_YEARS = [2017, 2022, 2023, 2024]          # años que el segmentador de la página Temporada abre comparando
CASOS = measure("Casos")
INC = measure("Incidencia por 100 mil", "Incidencia por 100 mil")


def f(name: str) -> float:
    return float(k(name))


def n(name: str, decimals: int = 0) -> str:
    return num(f(name), decimals)


def p(name: str, decimals: int = 1) -> str:
    return pct(f(name), decimals)


def p_abs(name: str, decimals: int = 1) -> str:
    return pct(abs(f(name)), decimals)


p1 = {"name": "p1_resumen", "displayName": "1. Resumen", "visuals": [
    title("Dengue en el Perú, 2000–2024",
          f"Resumen ejecutivo · {num(f('casos_total') / 1e6, 2)} millones de casos notificados al CDC Perú"),
    year_slicer(),
    card("kpi_casos", 24, 88, 232, 92, "Casos", "Casos notificados"),
    card("kpi_incidencia", 274, 88, 232, 92, "Incidencia por 100 mil", "Incidencia anual por 100 mil"),
    card("kpi_distritos", 524, 88, 232, 92, "Distritos con casos", "Distritos con casos"),
    card("kpi_pico", 774, 88, 232, 92, "Semana pico", "Semana epidemiológica pico"),
    card("kpi_alarma", 1024, 88, 232, 92, "% con signos de alarma o graves", "Con signos de alarma o graves"),
    chart("columnas_anio", "clusteredColumnChart", 24, 196, 808, 300, "Casos por año",
          column("dim_anio", "anio", "Año", active=True), [CASOS], categorical=True),
    chart("barras_zona", "clusteredBarChart", 848, 196, 408, 300, "Casos por zona de análisis",
          column("dim_departamento", "zona", "Zona", active=True), [CASOS], sort=sort_by(CASOS), labels=True),
    reading("lectura", 24, 512, 1232, 170, "Qué está pasando", [
        f"{p('casos_2023_2024_pct')} de los casos de 25 años cayeron en 2023 y 2024: {n('casos_2023')} y {n('casos_2024')}. Antes, el máximo había sido {n('casos_2017')} (2017).",
        f"Piura puso el {p('pct_piura_2017', 0)} de los casos de 2017; en 2024 Lima puso el {p('pct_lima_2024', 0)} ({n('casos_lima_2024')} casos). Los distritos con casos pasaron de "
        f"{n('distritos_2000')} a {n('distritos_2024')}.",
        f"Las temporadas empiezan alta: en 2023 y 2024 los casos del país superaron el canal endémico desde la semana 1, con {n('semanas_aviso_2023')} y {n('semanas_aviso_2024')} semanas de aviso antes del pico.",
    ], "Qué conviene hacer", [
        "Empezar el control vectorial antes de la semana 1 en las zonas que ya tuvieron epidemia, y vigilar las que se están sumando (Lima, Ica, Áncash).",
        f"Usar la incidencia y no el conteo para repartir recursos: {k('dep_mayor_incidencia')} y {k('dep_2_incidencia')} tienen la mayor incidencia (página 4).",
    ]),
    footer(),
]}

p2 = {"name": "p2_epidemias", "displayName": "2. Epidemias", "visuals": [
    title("¿Cómo evolucionaron los casos y qué años fueron epidemia?",
          f"Del valle de 2018 ({n('casos_2018')} casos) a {n('casos_2023')} en 2023 y {n('casos_2024')} en 2024: ya no son epidemias aisladas", width=1232),
    chart("linea_anio", "lineChart", 24, 88, 520, 260, "Casos por año",
          column("dim_anio", "anio", "Año", active=True), [CASOS]),
    with_filter(chart("columnas_incidencia", "clusteredColumnChart", 560, 88, 340, 260, "Incidencia por 100 mil (desde 2013)",
                      column("dim_anio", "anio", "Año", active=True), [INC], categorical=True, labels=True, compact=True),
                "dim_anio", "con_poblacion", [1], "filtro_incidencia"),
    with_filter(chart("columnas_fallecidos", "clusteredColumnChart", 916, 88, 340, 260, "Fallecidos por año (CDC)",
                      column("dim_anio", "anio", "Año", active=True), [measure("Fallecidos (CDC)", "Fallecidos")],
                      categorical=True, labels=True, compact=True),
                "dim_anio", "anio", list(range(2012, 2025)), "filtro_fallecidos"),
    table("tabla_anios", 24, 364, 808, 318, "Año por año", [
        column("dim_anio", "anio", "Año"),
        CASOS,
        measure("Var. interanual", "Var. vs año anterior"),
        INC,
        measure("Distritos con casos", "Distritos"),
        measure("Fallecidos (CDC)", "Fallecidos"),
        measure("Letalidad (CDC)", "Letalidad"),
    ], sort=sort_by(column("dim_anio", "anio"), "Descending"), widths=[70, 110, 130, 110, 90, 100, 90]),
    reading("lectura", 848, 364, 408, 318, "Lectura", [
        f"2023 multiplicó por {n('veces_2023_vs_2022', 1)} los casos de 2022 y fue {n('veces_2023_vs_2017', 1)} veces la epidemia de 2017.",
        f"Años de alta transmisión (más de 50 mil casos): {k('anios_alta_transmision')}.",
        f"Fallecidos 2012–2024: {n('fallecidos_2012_2024')}. La letalidad no subió con los casos: {n('letalidad_2023_pct', 2)} % en 2023 y {n('letalidad_2024_pct', 2)} % en 2024.",
        "Más casos pueden ser más infección, más pruebas o más notificación. 2025 y 2026 no están en el archivo abierto.",
    ]),
    footer(),
]}

p3 = {"name": "p3_temporada", "displayName": "3. Temporada", "interactions": [
        {"source": "segmentador_anio", "target": "tabla_pico", "type": "NoFilter"}],
      "visuals": [
    title("¿Cuándo se concentra el dengue?",
          f"La temporada normal llega a su pico hacia la semana {n('semana_pico_normal')}; 2023 fue tardía (semana {n('semana_pico_2023')}) y 2024 llegó seis semanas antes", width=1000),
    year_slicer(selected=HIGH_YEARS, header="Años a comparar"),
    chart("curva_semanal", "lineChart", 24, 88, 808, 300, "Casos por semana epidemiológica, año por año",
          column("dim_semana", "semana", "Semana", active=True), [CASOS], series=column("dim_anio", "anio", "Año"),
          legend=True),
    chart("parte_semanal", "lineChart", 848, 88, 408, 300, "Parte de los casos del año que cae en cada semana",
          column("dim_semana", "semana", "Semana", active=True),
          [measure("Parte de los casos del año", "% del año")], series=column("dim_anio", "anio", "Año"),
          legend=True),
    table("tabla_pico", 24, 404, 808, 278, "Semana pico de cada año", [
        column("dim_anio", "anio", "Año"),
        CASOS,
        measure("Semana pico"),
        measure("Casos en la semana pico", "Casos en esa semana"),
        measure("Semanas del país sobre el canal", "Semanas sobre el canal"),
    ], sort=sort_by(column("dim_anio", "anio"), "Descending"), widths=[70, 130, 120, 160, 170]),
    reading("lectura", 848, 404, 408, 278, "Lectura", [
        f"En una temporada normal el pico cae en la semana {n('semana_pico_normal')} y el {p('pct_primer_semestre_normal', 0)} de los casos queda en las semanas 1 a 26.",
        f"2023: pico en la semana {n('semana_pico_2023')} con {n('casos_semana_pico_2023')} casos. 2024: semana {n('semana_pico_2024')}, {n('adelanto_pico_2024')} semanas antes, con el {p('pct_primer_semestre_2024', 0)} de los casos en el primer semestre.",
        "Las zonas no coinciden: en 2024 la costa norte tuvo su pico en la semana 11 y la costa centro y sur en la 16.",
    ]),
    footer(),
]}

p4 = {"name": "p4_territorio", "displayName": "4. Territorio", "visuals": [
    title("¿Dónde se concentra por habitante?",
          f"{k('dep_mayor_incidencia')} ({n('dep_mayor_incidencia_veces', 1)} veces la incidencia nacional) y {k('dep_2_incidencia')} encabezan; Lima puso un tercio de los casos de 2024 pero su incidencia es la nacional",
          width=1000),
    year_slicer(selected=[2023, 2024], header="Años (abre en 2023–2024)"),
    chart("barras_departamento", "clusteredBarChart", 24, 88, 560, 594, "Casos por 100 mil habitantes al año, por departamento",
          column("dim_departamento", "departamento", "Departamento", active=True), [INC], sort=sort_by(INC), labels=True,
          compact=True),
    card("kpi_nacional", 600, 88, 208, 92, "Incidencia nacional", "Incidencia nacional"),
    card("kpi_casos", 824, 88, 208, 92, "Casos", "Casos"),
    card("kpi_deps", 1048, 88, 208, 92, "Departamentos con casos", "Departamentos con casos"),
    table("tabla_provincias", 600, 196, 656, 250, "Provincias con más casos (elija un departamento en el gráfico)", [
        column("dim_provincia", "provincia_unica", "Provincia"),
        column("dim_departamento", "departamento", "Departamento"),
        CASOS,
        measure("Población (habitantes-año)", "Habitantes-año"),
        INC,
    ], sort=sort_by(CASOS), widths=[160, 120, 90, 130, 110]),
    reading("lectura", 600, 462, 656, 220, "Lectura", [
        f"Solo {n('deps_sobre_nacional')} de 25 departamentos superan la incidencia nacional ({n('incidencia_nacional_2023_2024')} por 100 mil en 2023–2024).",
        f"El epicentro se movió: Piura puso el {p('pct_piura_2017', 0)} de los casos de 2017, el {p('pct_piura_2023', 0)} de 2023 y el {p('pct_piura_2024', 0)} de 2024; Lima pasó de {n('casos_lima_2022')} casos en 2022 a {n('casos_lima_2024')} en 2024.",
        f"El mapa se amplió: de {n('distritos_2000')} distritos con casos en 2000 a {n('distritos_2024')} en 2024.",
        "Los casos se asignan al lugar probable de infección; la incidencia provincial existe desde 2016 y la departamental, desde 2013.",
    ]),
    footer(),
]}

p5 = {"name": "p5_pacientes", "displayName": "5. Pacientes", "visuals": [
    title("¿A quién afecta y qué tan graves son los casos?",
          f"Afecta sobre todo a adultos de 30 a 59 años ({p('pct_adultez_total', 0)} de los casos); uno de cada ocho llega con signos de alarma o grave", width=1000),
    year_slicer(),
    chart("columnas_edad", "clusteredBarChart", 24, 88, 400, 280, "Casos por curso de vida",
          column("dim_grupo_edad", "grupo_edad", "Grupo de edad", active=True), [CASOS], labels=True),
    with_filter(with_filter(chart("barras_alarma_edad", "clusteredBarChart", 440, 88, 400, 280, "Con signos de alarma o graves, por edad (desde 2011)",
                      column("dim_grupo_edad", "grupo_edad", "Grupo de edad", active=True),
                      [measure("% con signos de alarma o graves", "% con signos de alarma o graves")], labels=True),
                "dim_anio", "forma_comparable", [1], "filtro_comparable"),
                "dim_grupo_edad", "grupo_edad_id", [1, 2, 3, 4, 5, 6], "filtro_con_edad"),
    chart("linea_alarma", "lineChart", 856, 88, 400, 280, "Con signos de alarma o graves, por año (desde 2011)",
          column("dim_anio", "anio", "Año", active=True),
          [measure("% con signos o graves (clasificación actual)", "% con signos de alarma o graves")], labels=True),
    chart("linea_edad", "lineChart", 24, 384, 400, 298, "Edad promedio por año",
          column("dim_anio", "anio", "Año", active=True), [measure("Edad promedio")]),
    chart("linea_mujeres", "lineChart", 440, 384, 400, 298, "Parte de mujeres por año",
          column("dim_anio", "anio", "Año", active=True), [measure("% de mujeres", "% de mujeres")]),
    reading("lectura", 856, 384, 400, 298, "Lectura", [
        f"Mediana de edad: {n('mediana_edad_total')} años; el {p('pct_mujeres_total', 0)} de los casos son mujeres.",
        f"Los menores de 1 año son los más graves ({p('grupo_mayor_alarma_valor', 0)} con signos de alarma o graves) y los adultos de 30 a 59, los menos ({p('grupo_menor_alarma_valor', 0)}).",
        f"La parte con signos de alarma o graves bajó de {p('pct_alarma_max', 0)} (2013) a {p('pct_alarma_2024', 0)} (2024). No hay población por edad ni sexo: no se calcula incidencia por grupo.",
    ]),
    footer(),
]}

p6 = {"name": "p6_brotes", "displayName": "6. Brotes", "visuals": [
    title("¿Qué semanas se salen del canal endémico?",
          f"En 2023 el país estuvo sobre el canal {n('semanas_pais_sobre_canal_2023')} semanas, desde la primera; en 2018, ninguna", width=1000),
    year_slicer(selected=LAST_YEAR, header="Año (elija uno)"),
    card("kpi_semanas_pais", 24, 88, 260, 92, "Semanas del país sobre el canal", "Semanas del país sobre el canal"),
    card("kpi_semanas_dep", 300, 88, 260, 92, "Semanas sobre el canal", "Semanas-depto. sobre el canal"),
    card("kpi_pct", 576, 88, 256, 92, "% de semanas sobre el canal", "% de semanas-depto."),
    chart("curva_canal", "lineChart", 24, 196, 808, 300, "Casos del país por semana frente al canal endémico",
          column("dim_semana", "semana", "Semana", active=True),
          [CASOS, measure("Umbral del canal (país)", "Umbral (percentil 90)"), measure("Mediana histórica (país)", "Mediana de los 5 años previos")],
          legend=True),
    table("tabla_canal", 848, 88, 408, 408, "Departamentos sobre el canal", [
        column("dim_departamento", "departamento", "Departamento"),
        measure("Semanas sobre el canal", "Semanas sobre el canal"),
        measure("% de semanas sobre el canal", "% de las semanas"),
    ], sort=sort_by(measure("Semanas sobre el canal")), widths=[150, 110, 100]),
    reading("lectura", 24, 512, 1232, 170, "Cómo leer esta página", [
        "El canal endémico compara cada semana con las mismas semanas de los 5 años anteriores: el umbral es el percentil 90 y se exigen al menos 10 casos.",
        f"2023: {n('semanas_pais_sobre_canal_2023')} semanas sobre el canal y la primera fue la semana {n('primera_semana_sobre_canal_2023')}, {n('semanas_aviso_2023')} semanas antes del pico. 2024: {n('semanas_pais_sobre_canal_2024')} semanas, {n('semanas_aviso_2024')} de aviso. "
        f"San Martín pasó {n('dep_mas_semanas_sobre_canal_n')} de 104 semanas sobre el canal en 2023–2024.",
        "Una semana sobre el canal es una señal para revisar, no un brote confirmado. Como el canal usa los 5 años previos, una epidemia sube el umbral de los 5 años siguientes.",
    ]),
    footer(),
]}

p7 = {"name": "p7_notas", "displayName": "7. Notas", "visuals": [
    title("Notas", "Definiciones, fuentes, validaciones y límites"),
    textbox("definiciones", 24, 88, 400, 440, [
        ("Definiciones", 11, INK, True),
        ("Caso: una notificación de dengue al sistema de vigilancia del CDC Perú (RENACE), con su lugar probable de infección. "
         "No es una infección confirmada.", 9, INK, False),
        ("Incidencia por 100 mil: casos entre población proyectada, por 100 000 habitantes y por año. Sobre varios años se suman "
         "casos y población antes de dividir.", 9, INK, False),
        ("Semana epidemiológica: semana de inicio de síntomas, del 1 al 52 o 53.", 9, INK, False),
        ("Signos de alarma o grave: formas clínicas más serias; la clasificación actual existe desde 2011.", 9, INK, False),
        ("Canal endémico: percentil 90 de los casos de la misma semana (y sus vecinas) de los 5 años previos, con al menos 10 casos.", 9, INK, False),
        ("Año de alta transmisión: más de 50 mil casos.", 9, INK, False),
        ("Zona de análisis: agrupación de departamentos del proyecto, no una región oficial.", 9, INK, False),
    ], background=True),
    textbox("fuentes", 440, 88, 400, 440, [
        ("Fuentes y validación", 11, INK, True),
        ("Datos: vigilancia epidemiológica de dengue 2000–2024 (CDC Perú, MINSA) y población proyectada del MININTER, en datosabiertos.gob.pe.", 9, INK, False),
        ("Los casos por año coinciden con la tabla oficial de la sala situacional del CDC en 2012–2024: 12 de 13 años idénticos y uno con 1 caso de diferencia.", 9, INK, False),
        ("El reparto por forma clínica de 2023 coincide con el de la alerta epidemiológica AE-CDC N.° 006-2024 (diferencia máxima 2,9 %), y la población "
         "con la implícita en la incidencia oficial (−0,3 %).", 9, INK, False),
        ("Calidad: 31 reglas en seis dimensiones, 16 problemas documentados y ningún caso excluido (1 029 421 en el archivo y en el modelo).", 9, INK, False),
        (f"Cada medida del tablero se comparó con el mismo cálculo en Python: {num(CHECKS)} comparaciones, diferencia máxima 4,9 × 10⁻¹⁵.", 9, INK, False),
        ("Detalle y código: github.com/MartinZapanaBerrospi/dengue-peru-analytics", 9, ACCENT, False),
    ], background=True),
    textbox("limites", 856, 88, 400, 440, [
        ("Límites", 11, INK, True),
        ("Un caso notificado no es una infección: más casos pueden ser más pruebas o más notificación.", 9, INK, False),
        ("El archivo termina en 2024. El CDC ya publica 2025 y 2026, pero esos datos no están abiertos.", 9, INK, False),
        ("No trae fallecidos (se usa la tabla oficial del CDC) ni distingue casos confirmados de probables.", 9, INK, False),
        ("Antes de 2011 la clasificación clínica era otra: la parte de casos graves no es comparable.", 9, INK, False),
        ("No hay población por edad ni sexo: no se calcula incidencia por grupo, y la edad y el sexo de los casos no miden riesgo.", 9, INK, False),
        ("Incidencia por departamento desde 2013 y por provincia desde 2016; 10 distritos creados desde 2021 no tienen población propia.", 9, INK, False),
        ("Las cifras oficiales se revisan: la alerta de 2024 daba 273 684 casos para 2023 y la sala vigente, 256 641.", 9, INK, False),
        ("Análisis descriptivo: dice qué pasó y cuánto, no por qué.", 9, INK, False),
    ], background=True),
    footer(),
]}

PAGES = [p1, p2, p3, p4, p5, p6, p7]

"""Páginas y visuales del informe de Power BI (PBIR), escritos por tools/build_report.py.

Lienzo de 1280 × 720 con márgenes de 24 px. Las cifras de los títulos salen de
reports/analisis/cifras_clave.csv (Fase 5): el tablero no repite números escritos a mano.

Estándar gerencial (el tablero se presenta en voz alta):
- el título de cada página es la conclusión, sin subtítulo; a lo sumo una línea «Acción: …»;
- las anotaciones van dentro del gráfico (visuales «nota_*», los únicos que pueden encimarse);
- tarjetas con dirección, color y comparación; detalle técnico en tooltips;
- tablas de 7 filas como máximo, con barras de datos;
- recorrido de 4 páginas; el detalle y «Sobre los datos» quedan ocultos y se llega con el botón ⓘ.
"""

import csv
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
KEY = {r["cifra"]: r["valor"] for r in csv.DictReader(
    (ROOT / "reports" / "analisis" / "cifras_clave.csv").open(encoding="utf-8"))}

INK, MUTED, PANEL = "#1b1f24", "#4a5058", "#ffffff"
ACCENT = "#1f5f99"
RED, GREY, LIGHT = "#b8433a", "#b8bec6", "#9db7d1"
NOTES_PAGE = "p7_notas"


# ---------------------------------------------------------------------------------------------
# Formato de cifras en español del Perú
# ---------------------------------------------------------------------------------------------

def num(value, decimals: int = 0) -> str:
    """1234567.8 -> '1 234 568' ; con decimales usa coma: 2,5."""
    text = f"{float(value):,.{decimals}f}"
    return text.replace(",", " ").replace(".", ",").replace("-", "−")


def pct(value, decimals: int = 1) -> str:
    return f"{num(float(value) * 100, decimals)} %"


def k(name: str) -> str:
    return KEY[name]


# ---------------------------------------------------------------------------------------------
# Piezas PBIR
# ---------------------------------------------------------------------------------------------

def lit(value: str) -> dict:
    return {"expr": {"Literal": {"Value": value}}}


def text(value: str) -> dict:
    return lit("'" + value.replace("'", "''") + "'")


def color(hex_code: str) -> dict:
    return {"solid": {"color": lit(f"'{hex_code}'")}}


def measure_color(name: str) -> dict:
    """Color que devuelve una medida (formato condicional por valor de campo)."""
    return {"solid": {"color": {"expr": {"Measure": {"Expression": {"SourceRef": {"Entity": "_Medidas"}}, "Property": name}}}}}


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


def title(conclusion: str, width: int = 840) -> dict:
    """El título es la conclusión de la página (una línea, unas 12 palabras). Sin subtítulo."""
    assert len(conclusion.split()) <= 13, conclusion
    return textbox("titulo", 24, 14, width, 44, [(conclusion, 18, INK, True)])


def action(content: str) -> dict:
    """La única línea de texto de la página: qué decidir."""
    return textbox("accion", 24, 652, 1232, 30, [("Acción: " + content, 11, ACCENT, True)])


def footer() -> dict:
    return textbox("fuente", 24, 690, 1232, 24, [(
        "Fuente: CDC Perú (MINSA), vigilancia epidemiológica de dengue, 2000–2024, y población proyectada del MININTER "
        "(datosabiertos.gob.pe). Un caso notificado no es una infección. Elaboración propia.", 8, MUTED, False)])


def note(name, x, y, w, h, content, hex_code=INK) -> dict:
    """Anotación fija dentro de un gráfico (fondo transparente). Cada línea de `content` es un párrafo."""
    lines = content.split("\n")
    return textbox(name, x, y, w, h, [(lines[0], 11, hex_code, True)] + [(line, 10, MUTED, False) for line in lines[1:]])


def note_measure(name, x, y, w, h, measure_name) -> dict:
    """Anotación dentro de un gráfico que cambia con el segmentador: una tarjeta transparente con una medida de texto."""
    return visual(name, position(x, y, w, h), {
        "visualType": "card",
        "query": {"queryState": {"Values": {"projections": [measure(measure_name)]}}},
        "objects": {
            "labels": [{"properties": {"fontSize": lit("11D"), "color": color(INK), "fontFamily": text("Segoe UI Semibold")}}],
            "categoryLabels": [{"properties": {"show": lit("false")}}],
        },
        "visualContainerObjects": container(background=False),
    })


def button(name, x, y, w, h, label, page: str | None) -> dict:
    """Botón de navegación: a una página (page) o atrás (page=None)."""
    link = ({"show": lit("true"), "type": text("PageNavigation"), "navigationSection": text(page)} if page
            else {"show": lit("true"), "type": text("Back")})
    return visual(name, position(x, y, w, h), {
        "visualType": "actionButton",
        "objects": {
            "icon": [{"properties": {"show": lit("false")}, "selector": {"id": "default"}}],
            "text": [{"properties": {"show": lit("true")}},
                     {"properties": {"text": text(label), "fontColor": color(ACCENT), "fontSize": lit("10D"),
                                     "fontFamily": text("Segoe UI Semibold"), "horizontalAlignment": text("center")},
                      "selector": {"id": "default"}}],
            "fill": [{"properties": {"show": lit("true"), "fillColor": color(PANEL), "transparency": lit("0D")},
                      "selector": {"id": "default"}}],
            "outline": [{"properties": {"show": lit("true"), "lineColor": color("#c9d3de"), "weight": lit("1D")},
                         "selector": {"id": "default"}}],
        },
        "visualContainerObjects": {**container(background=False), "visualLink": [{"properties": link}]},
        "drillFilterOtherVisuals": True,
    })


def info_button() -> dict:
    return button("boton_sobre_datos", 880, 20, 160, 32, "ⓘ  Sobre los datos", NOTES_PAGE)


def card(name, x, y, w, h, measure_name, label, value_size=22, value_color=None) -> dict:
    return visual(name, position(x, y, w, h), {
        "visualType": "card",
        "query": {"queryState": {"Values": {"projections": [measure(measure_name)]}}},
        "objects": {
            "labels": [{"properties": {"fontSize": lit(f"{value_size}D"), "color": value_color or color(INK),
                                       "fontFamily": text("Segoe UI Semibold"), "labelDisplayUnits": lit("1D")}}],
            "categoryLabels": [{"properties": {"show": lit("false")}}],
        },
        "visualContainerObjects": {**container(), "title": [{"properties": {
            "show": lit("true"), "text": text(label), "fontSize": lit("10D"), "fontColor": color(MUTED),
            "bold": lit("false"), "fontFamily": text("Segoe UI")}}]},
    })


def kpi(name, x, y, w, measure_name, label, comparison: str | None = None) -> list[dict]:
    """Tarjeta de KPI (72 px) y, debajo, su comparación con el año anterior en rojo (sube) o verde (baja)."""
    out = [card(name, x, y, w, 92, measure_name, label)]
    if comparison:
        out.append(visual(f"{name}_vs", position(x, y + 92, w, 44), {
            "visualType": "card",
            "query": {"queryState": {"Values": {"projections": [measure(f"Comparación {comparison}")]}}},
            "objects": {
                "labels": [{"properties": {"fontSize": lit("11D"), "color": measure_color(f"Color comparación {comparison}"),
                                           "fontFamily": text("Segoe UI Semibold")}}],
                "categoryLabels": [{"properties": {"show": lit("false")}}],
            },
            "visualContainerObjects": container(),
        }))
    return out


def axis_objects(categorical: bool = False, labels: bool = False, legend: bool = False, compact: bool = False,
                 value_axis: bool = True) -> dict:
    objects = {
        "categoryAxis": [{"properties": {"showAxisTitle": lit("false"), "gridlineShow": lit("false"),
                                         "labelColor": color(MUTED), "fontSize": lit("8D" if compact else "9D"),
                                         **({"axisType": text("Categorical")} if categorical else {}),
                                         **({"innerPadding": lit("12D")} if compact else {})}}],
        # labelDisplayUnits 1 = sin abreviar: "256 641" y no "257 mil"
        "valueAxis": [{"properties": {"showAxisTitle": lit("false"), "gridlineColor": color("#e9ecef"),
                                      "labelColor": color(MUTED), "fontSize": lit("9D"),
                                      "labelDisplayUnits": lit("1D"),
                                      **({"show": lit("false")} if compact or not value_axis else {})}}],
        "legend": [{"properties": {"show": lit("true" if legend else "false"), "position": text("Top"),
                                   "fontSize": lit("9D"), "labelColor": color(MUTED)}}],
    }
    if labels:
        objects["labels"] = [{"properties": {"show": lit("true"), "fontSize": lit("9D"), "color": color(INK),
                                             "labelDisplayUnits": lit("1D")}}]
    return objects


def chart(name, kind, x, y, w, h, chart_title, category, values, series=None, sort=None, tooltips=None,
          categorical=False, labels=False, legend=False, compact=False, value_axis=True, fill=None, colors=None) -> dict:
    """fill: medida que da el color de cada barra. colors: {queryRef de la medida o año: color} por serie."""
    state = {"Category": {"projections": [category]}, "Y": {"projections": values}}
    if series:
        state["Series"] = {"projections": [series]}
    if tooltips:
        state["Tooltips"] = {"projections": tooltips}
    query = {"queryState": state}
    if sort:
        query["sortDefinition"] = sort
    objects = axis_objects(categorical, labels, legend, compact, value_axis)
    if kind == "lineChart":
        objects["lineStyles"] = [{"properties": {"lineChartType": text("straight"), "strokeWidth": lit("2D")}}]
    if fill:
        objects["dataPoint"] = [{"properties": {"fill": measure_color(fill)},
                                 "selector": {"data": [{"dataViewWildcard": {"matchingOption": 1}}]}}]
    if colors:
        objects["dataPoint"] = [series_color(key, hex_code, series) for key, hex_code in colors.items()]
    return visual(name, position(x, y, w, h), {
        "visualType": kind, "query": query, "objects": objects,
        "visualContainerObjects": container(chart_title),
    })


def series_color(key, hex_code: str, series: dict | None) -> dict:
    """Color de una serie: por medida (queryRef) o por valor de la columna de series (un año)."""
    if isinstance(key, int):
        col = series["field"]["Column"]
        selector = {"data": [{"scopeId": {"Comparison": {
            "ComparisonKind": 0,
            "Left": {"Column": {"Expression": {"SourceRef": {"Entity": col["Expression"]["SourceRef"]["Entity"]}},
                                "Property": col["Property"]}},
            "Right": {"Literal": {"Value": f"{key}L"}}}}}]}
    else:
        selector = {"metadata": key}
    return {"properties": {"fill": color(hex_code)}, "selector": selector}


def combo(name, x, y, w, h, chart_title, category, columns, lines, colors, tooltips=None) -> dict:
    """Columnas apiladas + línea en el mismo eje (el eje secundario se oculta para que compartan escala)."""
    state = {"Category": {"projections": [category]}, "Y": {"projections": columns}, "Y2": {"projections": lines}}
    if tooltips:
        state["Tooltips"] = {"projections": tooltips}
    objects = axis_objects(legend=True)
    objects["valueAxis"][0]["properties"]["secShow"] = lit("false")
    objects["dataPoint"] = [series_color(key, hex_code, None) for key, hex_code in colors.items()]
    objects["lineStyles"] = [{"properties": {"strokeWidth": lit("2D"), "showMarker": lit("false"),
                                             "lineChartType": text("straight")}}]
    return visual(name, position(x, y, w, h), {
        "visualType": "lineStackedColumnComboChart", "query": {"queryState": state}, "objects": objects,
        "visualContainerObjects": container(chart_title),
    })


def table(name, x, y, w, h, table_title, projections, sort=None, widths=None, bars=None, font=10) -> dict:
    """widths: ancho en píxeles de cada columna. bars: {queryRef: medida de color} columnas con color condicional."""
    query = {"queryState": {"Values": {"projections": projections}}}
    if sort:
        query["sortDefinition"] = sort
    objects = {
        "columnHeaders": [{"properties": {"fontSize": lit(f"{font}D"), "fontColor": color(INK), "wordWrap": lit("true")}}],
        "values": [{"properties": {"fontSize": lit(f"{font}D"), "wordWrap": lit("false")}}],
        "total": [{"properties": {"totals": lit("false")}}],
    }
    if widths:
        assert len(widths) == len(projections) and sum(widths) <= w - 40, name
        objects["columnWidth"] = [{"properties": {"value": lit(f"{width}D")}, "selector": {"metadata": p["queryRef"]}}
                                  for p, width in zip(projections, widths)]
    for ref, color_measure in (bars or {}).items():
        # Formato condicional del color de letra (Desktop 2.159 no dibuja las barras de datos escritas a mano).
        objects["values"].append({"properties": {"fontColor": measure_color(color_measure)},
                                  "selector": {"data": [{"dataViewWildcard": {"matchingOption": 1}}], "metadata": ref}})
    return visual(name, position(x, y, w, h), {
        "visualType": "tableEx", "query": query, "objects": objects,
        "visualContainerObjects": container(table_title),
    })


def slicer(name, x, y, w, h, entity, prop, header, order_prop=None, selected=None, single=False) -> dict:
    """selected: valor numérico que el segmentador trae elegido al abrir el informe (se guarda como filtro)."""
    query = {"queryState": {"Values": {"projections": [column(entity, prop, active=True)]}}}
    if order_prop:
        query["sortDefinition"] = sort_by(column(entity, order_prop), "Ascending")
    out = visual(name, position(x, y, w, h), {
        "visualType": "slicer", "query": query,
        "objects": {
            "data": [{"properties": {"mode": text("Dropdown")}}],
            "selection": [{"properties": {"strictSingleSelect": lit("true" if single else "false"),
                                          "singleSelect": lit("true" if single else "false")}}],
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


def year_slicer(selected=None, header="Año", single=False) -> dict:
    return slicer("segmentador_anio", 1056, 8, 200, 56, "dim_anio", "anio", header, selected=selected, single=single)


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


def top_n(vis: dict, rank_measure: str, n: int = 7, name: str = "filtro_top") -> dict:
    """Solo las filas cuyo puesto (una medida RANKX) es n o menos: tablas de 7 filas."""
    vis.setdefault("filterConfig", {"filters": []})["filters"].append({
        "name": name,
        "field": {"Measure": {"Expression": {"SourceRef": {"Entity": "_Medidas"}}, "Property": rank_measure}},
        "type": "Advanced",
        "filter": {"Version": 2, "From": [{"Name": "m", "Entity": "_Medidas", "Type": 0}],
                   "Where": [{"Condition": {"Comparison": {
                       "ComparisonKind": 4,  # menor o igual
                       "Left": {"Measure": {"Expression": {"SourceRef": {"Source": "m"}}, "Property": rank_measure}},
                       "Right": {"Literal": {"Value": f"{n}L"}}}}}]},
        "howCreated": "User",
    })
    return vis


def no_filter(*targets: str) -> list[dict]:
    """El segmentador de año no filtra estos visuales (muestran siempre todo el periodo)."""
    return [{"source": "segmentador_anio", "target": t, "type": "NoFilter"} for t in targets]


# ---------------------------------------------------------------------------------------------
# Páginas
# ---------------------------------------------------------------------------------------------

LAST_YEAR = 2024
CHECKS = sum(1 for _ in (ROOT / "reports" / "validacion_medidas.csv").open(encoding="utf-8")) - 1   # comparaciones de la Fase 4
HIGH_YEARS = [2017, 2022, 2023, 2024]          # años que el segmentador de la página Temporada abre comparando
CASOS = measure("Casos")
INC = measure("Incidencia por 100 mil", "Incidencia por 100 mil")
ANIO = column("dim_anio", "anio", "Año", active=True)
SEMANA = column("dim_semana", "semana", "Semana", active=True)


def f(name: str) -> float:
    return float(k(name))


def n(name: str, decimals: int = 0) -> str:
    return num(f(name), decimals)


def p(name: str, decimals: int = 1) -> str:
    return pct(f(name), decimals)


# 1. Resumen: casos por año (2023 y 2024 resaltados) y por zona. Las tarjetas obedecen al año; los gráficos, no.
p1 = {"name": "p1_resumen", "displayName": "1. Resumen",
      "interactions": no_filter("columnas_anio", "barras_zona", "nota_2023_2024"),
      "visuals": [
    title(f"La mitad de los casos de 25 años cayó en 2023 y 2024"),
    info_button(),
    year_slicer(selected=LAST_YEAR, header="Año de las tarjetas", single=True),
    *kpi("kpi_casos", 24, 72, 296, "Casos", "Casos notificados", "casos"),
    *kpi("kpi_incidencia", 336, 72, 296, "Incidencia por 100 mil", "Incidencia anual por 100 mil habitantes", "incidencia"),
    *kpi("kpi_fallecidos", 648, 72, 296, "Fallecidos (CDC)", "Fallecidos (tabla oficial del CDC)", "fallecidos"),
    *kpi("kpi_distritos", 960, 72, 296, "Distritos con casos", "Distritos con casos", "distritos"),
    chart("columnas_anio", "clusteredColumnChart", 24, 224, 808, 416, "Casos por año, 2000–2024",
          ANIO, [CASOS], fill="Color año",
          tooltips=[measure("Var. interanual", "Var. vs año anterior"), INC, measure("Fallecidos (CDC)", "Fallecidos")]),
    note("nota_2023_2024", 120, 280, 420, 56,
         f"2023 y 2024: {p('casos_2023_2024_pct')} de los casos de 25 años\nAntes, el peor año fue 2017 ({n('casos_2017')})", ACCENT),
    chart("barras_zona", "clusteredBarChart", 848, 224, 408, 416, "Parte de los casos por zona, 2000–2024",
          column("dim_departamento", "zona", "Zona", active=True), [measure("% de los casos del país", "% de los casos")],
          sort=sort_by(measure("% de los casos del país")), labels=True, value_axis=False, tooltips=[CASOS]),
    action("ya no son epidemias aisladas: el control vectorial necesita presupuesto fijo cada año."),
    footer(),
]}

# 2. Alerta temprana (canal endémico): la página más gerencial, por eso va segunda.
p6 = {"name": "p6_brotes", "displayName": "2. Alerta temprana",
      "interactions": no_filter("columnas_semanas_anio"),
      "visuals": [
    title(f"En 2023 la alerta llegó {n('semanas_aviso_2023')} semanas antes del pico"),
    info_button(),
    year_slicer(selected=2023, header="Año (elija uno)", single=True),
    *kpi("kpi_aviso", 24, 72, 258, "Semanas de aviso", "Semanas de aviso antes del pico"),
    *kpi("kpi_semanas", 298, 72, 258, "Semanas del país sobre el canal", "Semanas sobre el umbral", "semanas"),
    *kpi("kpi_pico", 572, 72, 260, "Semana pico", "Semana pico"),
    combo("canal", 24, 224, 808, 416, "Casos del país por semana frente al umbral de epidemia", SEMANA,
          [measure("Casos hasta el umbral (país)", "Casos hasta el umbral"),
           measure("Exceso sobre el umbral (país)", "Casos sobre el umbral")],
          [measure("Umbral del canal (país)", "Umbral de epidemia")],
          {"_Medidas.Casos hasta el umbral (país)": LIGHT, "_Medidas.Exceso sobre el umbral (país)": RED,
           "_Medidas.Umbral del canal (país)": INK},
          tooltips=[CASOS, measure("Mediana histórica (país)", "Mediana de los 5 años previos")]),
    note_measure("nota_canal", 420, 300, 400, 40, "Nota del canal"),
    top_n(table("tabla_canal", 848, 72, 408, 300, "Departamentos con más semanas sobre el umbral", [
        column("dim_departamento", "departamento", "Departamento"),
        measure("Semanas sobre el canal", "Semanas sobre el umbral"),
        measure("% de semanas sobre el canal", "% de las semanas"),
    ], sort=sort_by(measure("Semanas sobre el canal")), widths=[130, 130, 100],
        bars={"_Medidas.% de semanas sobre el canal": "Color semanas sobre el umbral"}),
        "Puesto por semanas sobre el umbral"),
    with_filter(chart("columnas_semanas_anio", "clusteredColumnChart", 848, 388, 408, 252,
                      "Semanas del país sobre el umbral, por año", ANIO,
                      [measure("Semanas del país sobre el canal", "Semanas sobre el umbral")], fill="Color año",
                      labels=True, compact=True),
                "dim_anio", "anio", list(range(2010, LAST_YEAR + 1)), "filtro_anios"),
    action("activar el control vectorial apenas el país cruce el umbral, sin esperar el pico."),
    footer(),
]}

# 3. Temporada: forma de la curva (parte del año por semana) para comparar años de distinto tamaño.
p3 = {"name": "p3_temporada", "displayName": "3. Temporada", "visuals": [
    title("La temporada se adelanta: en 2024 el pico llegó seis semanas antes"),
    info_button(),
    year_slicer(selected=HIGH_YEARS, header="Años a comparar"),
    chart("curva_semanal", "lineChart", 24, 72, 860, 568, "Parte de los casos del año que cae en cada semana",
          SEMANA, [measure("Parte de los casos del año", "% del año")], series=column("dim_anio", "anio", "Año"),
          legend=True, tooltips=[CASOS],
          colors={2024: ACCENT, 2023: "#d9822b", 2022: GREY, 2017: "#6c757d"}),
    note("nota_pico_2024", 300, 130, 300, 30, f"2024: pico en la semana {n('semana_pico_2024')}", ACCENT),
    note("nota_pico_2023", 520, 190, 300, 30, f"2023: pico en la semana {n('semana_pico_2023')}", "#d9822b"),
    table("tabla_pico", 900, 72, 356, 260, "Semana pico de cada año", [
        column("dim_anio", "anio", "Año"),
        measure("Semana pico"),
        CASOS,
    ], sort=sort_by(column("dim_anio", "anio"), "Descending"), widths=[60, 100, 150]),
    note("nota_normal", 900, 348, 356, 56, f"Año normal: pico en la semana {n('semana_pico_normal')}", MUTED),
    action("empezar el control antes de la semana 1 en las zonas que ya tuvieron epidemia."),
    footer(),
]}

# 4. Territorio: incidencia, no conteo. Rojo = sobre la incidencia nacional.
p4 = {"name": "p4_territorio", "displayName": "4. Territorio", "visuals": [
    title(f"En 2023–2024, {k('dep_mayor_incidencia')} tuvo {n('dep_mayor_incidencia_veces', 1)} veces la incidencia nacional"),
    info_button(),
    year_slicer(selected=[2023, 2024], header="Años (abre en 2023–2024)"),
    chart("barras_departamento", "clusteredBarChart", 24, 72, 560, 568,
          "Incidencia anual por 100 mil habitantes (rojo: sobre la nacional)",
          column("dim_departamento", "departamento", "Departamento", active=True), [INC], sort=sort_by(INC), labels=True,
          compact=True, fill="Color incidencia",
          tooltips=[CASOS, measure("Veces la incidencia nacional", "Veces la nacional")]),
    card("kpi_nacional", 600, 72, 208, 92, "Incidencia nacional", "Incidencia nacional"),
    card("kpi_sobre", 824, 72, 208, 92, "Departamentos sobre la nacional", "Deptos. sobre la nacional",
         value_color=color(RED)),
    card("kpi_casos", 1048, 72, 208, 92, "Casos", "Casos"),
    top_n(table("tabla_provincias", 600, 180, 656, 300, "Las 7 provincias con más casos", [
        column("dim_provincia", "provincia_unica", "Provincia"),
        column("dim_departamento", "departamento", "Departamento"),
        CASOS,
        INC,
    ], sort=sort_by(CASOS), widths=[170, 130, 120, 150], bars={"_Medidas.Incidencia por 100 mil": "Color incidencia"}),
        "Puesto de la provincia por casos"),
    note("nota_lima", 600, 496, 656, 56,
         f"Lima puso el {p('pct_lima_2024', 0)} de los casos de 2024, pero su incidencia está por debajo de la nacional", MUTED),
    action("repartir personal e insumos por incidencia, no por número de casos."),
    footer(),
]}

# Páginas ocultas: detalle para responder preguntas. Se llega desde el panel de páginas o con ⓘ.
p2 = {"name": "p2_epidemias", "displayName": "Detalle: año por año", "hidden": True, "visuals": [
    title(f"La letalidad no subió con los casos: {n('letalidad_2024_pct', 2)} % en 2024", width=1000),
    info_button() | {"position": position(1096, 20, 160, 32)},
    with_filter(chart("columnas_incidencia", "clusteredColumnChart", 24, 72, 600, 270, "Incidencia por 100 mil (desde 2013)",
                      ANIO, [INC], categorical=True, labels=True, compact=True, fill="Color año"),
                "dim_anio", "con_poblacion", [1], "filtro_incidencia"),
    with_filter(chart("columnas_letalidad", "clusteredColumnChart", 640, 72, 616, 270, "Letalidad por año (CDC, desde 2012)",
                      ANIO, [measure("Letalidad (CDC)", "Letalidad")], categorical=True, labels=True, compact=True,
                      fill="Color año", tooltips=[measure("Fallecidos (CDC)", "Fallecidos")]),
                "dim_anio", "anio", list(range(2012, LAST_YEAR + 1)), "filtro_letalidad"),
    table("tabla_anios", 24, 358, 1232, 324, "Año por año", [
        column("dim_anio", "anio", "Año"),
        CASOS,
        measure("Var. interanual", "Var. vs año anterior"),
        INC,
        measure("Letalidad (CDC)", "Letalidad"),
    ], sort=sort_by(column("dim_anio", "anio"), "Descending"), widths=[90, 240, 200, 200, 160], font=9),
    footer(),
]}

p5 = {"name": "p5_pacientes", "displayName": "Detalle: pacientes", "hidden": True, "visuals": [
    title("Los menores de un año son los casos más graves"),
    info_button(),
    year_slicer(),
    chart("columnas_edad", "clusteredBarChart", 24, 72, 400, 610, "Casos por curso de vida",
          column("dim_grupo_edad", "grupo_edad", "Grupo de edad", active=True), [CASOS], labels=True, value_axis=False),
    with_filter(with_filter(chart("barras_alarma_edad", "clusteredBarChart", 440, 72, 400, 610,
                                  "Con signos de alarma o graves, por edad (desde 2011)",
                                  column("dim_grupo_edad", "grupo_edad", "Grupo de edad", active=True),
                                  [measure("% con signos de alarma o graves", "% con signos de alarma o graves")],
                                  labels=True, value_axis=False, tooltips=[CASOS]),
                            "dim_anio", "forma_comparable", [1], "filtro_comparable"),
                "dim_grupo_edad", "grupo_edad_id", [1, 2, 3, 4, 5, 6], "filtro_con_edad"),
    chart("linea_alarma", "lineChart", 856, 72, 400, 610, "Con signos de alarma o graves, por año (desde 2011)",
          ANIO, [measure("% con signos o graves (clasificación actual)", "% con signos de alarma o graves")], labels=True),
    footer(),
]}

# Sobre los datos: fuente, fecha de corte y tres advertencias. Las validaciones están en el README.
p7 = {"name": NOTES_PAGE, "displayName": "Sobre los datos", "hidden": True, "visuals": [
    title("Sobre los datos"),
    button("boton_volver", 1096, 20, 160, 32, "←  Volver", None),
    textbox("fuente_datos", 24, 88, 400, 200, [
        ("Fuente", 12, INK, True),
        ("Vigilancia epidemiológica de dengue del CDC Perú (MINSA) y población proyectada del MININTER, "
         "en datosabiertos.gob.pe.", 11, INK, False),
        ("Fallecidos: tabla oficial de la sala situacional del CDC.", 11, INK, False),
    ], background=True),
    textbox("corte", 440, 88, 400, 200, [
        ("Fecha de corte", 12, INK, True),
        (f"Casos de 2000 a {LAST_YEAR}: {n('casos_total')} notificaciones. El archivo abierto termina en {LAST_YEAR}; "
         "2025 y 2026 están en el CDC, pero no publicados como datos abiertos.", 11, INK, False),
        ("Los casos por año coinciden con la sala situacional del CDC en 12 de 13 años (2012–2024); el otro difiere en un caso.",
         11, INK, False),
    ], background=True),
    textbox("advertencias", 856, 88, 400, 200, [
        ("Tres advertencias", 12, INK, True),
        ("1. Un caso notificado no es una infección: más casos pueden ser más pruebas o más notificación.", 11, INK, False),
        ("2. Una semana sobre el umbral de epidemia es una señal para revisar, no un brote confirmado. "
         "El umbral es el percentil 90 de las mismas semanas de los 5 años previos.", 11, INK, False),
        ("3. La gravedad solo se compara desde 2011, cuando cambió la clasificación clínica.", 11, INK, False),
    ], background=True),
    textbox("detalle", 24, 304, 1232, 40, [
        ("Validaciones, método y código: github.com/MartinZapanaBerrospi/dengue-peru-analytics", 10, ACCENT, False)]),
    footer(),
]}

# Orden del recorrido (guion de presentación): resumen, alerta temprana, temporada, territorio; luego lo oculto.
PAGES = [p1, p6, p3, p4, p2, p5, p7]

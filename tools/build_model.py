"""Genera el modelo semántico de Power BI (TMDL) a partir de data/curated.

Escribe powerbi/dengue.SemanticModel/: tablas con su consulta de Power Query, relaciones y
medidas DAX. Los identificadores (lineageTag) se derivan del nombre de cada objeto, así que
regenerar el modelo produce exactamente los mismos archivos.

Las medidas están documentadas en docs/04_modelado.md y validadas contra Python en
tools/validate_measures.py.

Uso:
    python tools/build_model.py
"""

import re
import shutil
import sys
import uuid
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))

from src import config  # noqa: E402

NAME = "dengue"
LAST_YEAR = config.LAST_YEAR
MODEL = ROOT / "powerbi" / f"{NAME}.SemanticModel"
NS = uuid.UUID("c7a1d9e2-4b38-4f5d-a6c1-2e8f7b9d0a54")


def tag(*parts: str) -> str:
    return str(uuid.uuid5(NS, "/".join(parts)))


# ---------------------------------------------------------------------------------------------
# Tablas: (columna, tipo TMDL, opciones). El orden es el del CSV de data/curated.
# ---------------------------------------------------------------------------------------------

M_TYPES = {"string": "type text", "int64": "Int64.Type", "double": "type number", "dateTime": "type date"}

TABLES = {
    "dim_anio": {
        "description": "Año de la vigilancia, 2000 a 2024, con marcas de comparabilidad.",
        "columns": [
            ("anio", "int64", {"key": True, "format": "0", "description": "Año"}),
            ("decada", "string", {}),
            ("forma_comparable", "int64", {"hidden": True}),
            ("con_poblacion", "int64", {"hidden": True}),
            ("con_poblacion_provincial", "int64", {"hidden": True}),
        ],
    },
    "dim_semana": {
        "description": "Semana epidemiológica (1 a 53) y su trimestre. La 53 existe solo en algunos años.",
        "columns": [
            ("semana", "int64", {"key": True, "format": "0", "description": "Semana epidemiológica"}),
            ("trimestre_epi", "string", {}),
        ],
    },
    "dim_departamento": {
        "description": "Los 25 departamentos del país (Lima y Callao separados) y la zona de análisis del proyecto.",
        "columns": [
            ("departamento_id", "string", {"key": True, "hidden": True}),
            ("departamento", "string", {}),
            ("zona", "string", {"description": "Agrupación de departamentos del proyecto (no es una región oficial)"}),
        ],
    },
    "dim_provincia": {
        "description": "Las 124 provincias con casos. provincia_unica agrega el departamento si el nombre se repite.",
        "columns": [
            ("provincia_id", "string", {"key": True, "hidden": True}),
            ("provincia", "string", {}),
            ("provincia_unica", "string", {"description": "Nombre para mostrar; único en todo el modelo"}),
            ("departamento_id", "string", {"hidden": True}),
        ],
    },
    "dim_distrito": {
        "description": "Distrito de infección probable, por UBIGEO de 6 dígitos. distrito_unico agrega la provincia si el nombre se repite.",
        "columns": [
            ("ubigeo", "string", {"key": True}),
            ("distrito", "string", {}),
            ("distrito_unico", "string", {"description": "Nombre para mostrar; único en todo el modelo"}),
            ("provincia_id", "string", {"hidden": True}),
            ("departamento_id", "string", {"hidden": True}),
            ("distrito_en_padron", "int64", {"hidden": True}),
        ],
    },
    "dim_forma_clinica": {
        "description": "Forma clínica del caso: sin signos de alarma, con signos de alarma o grave.",
        "columns": [
            ("forma_clinica_id", "int64", {"key": True, "hidden": True}),
            ("forma_clinica", "string", {"sort_by": "forma_clinica_id"}),
            ("cie10", "string", {}),
            ("alarma_o_grave", "int64", {"hidden": True}),
        ],
    },
    "dim_grupo_edad": {
        "description": "Curso de vida del paciente; los casos con edad imposible quedan en «Sin edad válida».",
        "columns": [
            ("grupo_edad_id", "int64", {"key": True, "hidden": True}),
            ("grupo_edad", "string", {"sort_by": "grupo_edad_id"}),
        ],
    },
    "dim_sexo": {
        "description": "Sexo del paciente.",
        "columns": [
            ("sexo_id", "string", {"key": True, "hidden": True}),
            ("sexo", "string", {}),
        ],
    },
    "fact_caso": {
        "description": "Casos de dengue por año, semana, distrito, forma clínica, grupo de edad y sexo (2000–2024). "
                       "Solo hay fila si hubo al menos un caso.",
        "columns": [
            ("anio", "int64", {"hidden": True, "format": "0"}),
            ("semana", "int64", {"hidden": True, "format": "0"}),
            ("ubigeo", "string", {"hidden": True}),
            ("forma_clinica_id", "int64", {"hidden": True}),
            ("grupo_edad_id", "int64", {"hidden": True}),
            ("sexo_id", "string", {"hidden": True}),
            ("casos", "int64", {"hidden": True}),
            ("edad_suma", "double", {"hidden": True}),
            ("casos_con_edad", "int64", {"hidden": True}),
        ],
    },
    "fact_poblacion_departamento": {
        "description": "Población proyectada de los 25 departamentos, 2013–2024 (MININTER), con Lima sumada.",
        "columns": [
            ("departamento_id", "string", {"hidden": True}),
            ("anio", "int64", {"hidden": True, "format": "0"}),
            ("poblacion", "int64", {"hidden": True}),
        ],
    },
    "fact_poblacion_provincia": {
        "description": "Población proyectada de las provincias con casos, 2016–2024 (MININTER).",
        "columns": [
            ("provincia_id", "string", {"hidden": True}),
            ("anio", "int64", {"hidden": True, "format": "0"}),
            ("poblacion", "int64", {"hidden": True}),
        ],
    },
    "fact_canal_endemico": {
        "description": "Canal endémico por departamento y semana, 2005–2024: percentil 90 de los 5 años previos.",
        "columns": [
            ("departamento_id", "string", {"hidden": True}),
            ("anio", "int64", {"hidden": True, "format": "0"}),
            ("semana", "int64", {"hidden": True, "format": "0"}),
            ("casos", "int64", {"hidden": True}),
            ("mediana_historica", "double", {"hidden": True}),
            ("umbral", "double", {"hidden": True}),
            ("sobre_canal", "int64", {"hidden": True}),
        ],
    },
    "fact_canal_nacional": {
        "description": "Canal endémico del país por semana, 2005–2024: percentiles 25, 50 y 90 de los 5 años previos.",
        "columns": [
            ("anio", "int64", {"hidden": True, "format": "0"}),
            ("semana", "int64", {"hidden": True, "format": "0"}),
            ("casos", "int64", {"hidden": True}),
            ("p25", "double", {"hidden": True}),
            ("mediana_historica", "double", {"hidden": True}),
            ("umbral", "double", {"hidden": True}),
            ("sobre_canal", "int64", {"hidden": True}),
        ],
    },
    "fact_cdc_anual": {
        "description": "Casos y fallecidos oficiales del CDC por año, 2012–2024 (sala situacional). El archivo de casos no trae fallecidos.",
        "columns": [
            ("anio", "int64", {"hidden": True, "format": "0"}),
            ("casos_cdc", "int64", {"hidden": True}),
            ("fallecidos_cdc", "int64", {"hidden": True}),
        ],
    },
}

RELATIONSHIPS = [
    ("fact_caso", "anio", "dim_anio", "anio"),
    ("fact_caso", "semana", "dim_semana", "semana"),
    ("fact_caso", "ubigeo", "dim_distrito", "ubigeo"),
    ("fact_caso", "forma_clinica_id", "dim_forma_clinica", "forma_clinica_id"),
    ("fact_caso", "grupo_edad_id", "dim_grupo_edad", "grupo_edad_id"),
    ("fact_caso", "sexo_id", "dim_sexo", "sexo_id"),
    ("dim_distrito", "provincia_id", "dim_provincia", "provincia_id"),
    ("dim_provincia", "departamento_id", "dim_departamento", "departamento_id"),
    ("fact_poblacion_departamento", "departamento_id", "dim_departamento", "departamento_id"),
    ("fact_poblacion_departamento", "anio", "dim_anio", "anio"),
    ("fact_poblacion_provincia", "provincia_id", "dim_provincia", "provincia_id"),
    ("fact_poblacion_provincia", "anio", "dim_anio", "anio"),
    ("fact_canal_endemico", "departamento_id", "dim_departamento", "departamento_id"),
    ("fact_canal_endemico", "anio", "dim_anio", "anio"),
    ("fact_canal_endemico", "semana", "dim_semana", "semana"),
    ("fact_canal_nacional", "anio", "dim_anio", "anio"),
    ("fact_canal_nacional", "semana", "dim_semana", "semana"),
    ("fact_cdc_anual", "anio", "dim_anio", "anio"),
]

# ---------------------------------------------------------------------------------------------
# Medidas: (carpeta, nombre, expresión DAX, formato, descripción)
# ---------------------------------------------------------------------------------------------

# La población usa el nivel que se está viendo: distrito (sin población), provincia o departamento/país.
LEVEL_DISTRICT = "ISFILTERED ( dim_distrito[distrito_unico] )"
LEVEL_PROVINCE = "ISFILTERED ( dim_provincia[provincia_unica] )"

MEASURES = [
    # 1. Casos (P1, P4, P5)
    ("1. Casos", "Casos", "SUM ( fact_caso[casos] )", "#,##0",
     "Casos de dengue notificados al sistema de vigilancia, por lugar probable de infección."),
    ("1. Casos", "Casos año anterior",
     "VAR y = SELECTEDVALUE ( dim_anio[anio] )\nRETURN\n    IF ( NOT ISBLANK ( y ), CALCULATE ( [Casos], REMOVEFILTERS ( dim_anio ), dim_anio[anio] = y - 1 ) )",
     "#,##0", "Casos del año anterior al elegido. Solo con un año elegido."),
    ("1. Casos", "Var. interanual",
     "VAR antes = [Casos año anterior]\nRETURN\n    IF ( NOT ISBLANK ( antes ) && antes > 0, DIVIDE ( [Casos] - antes, antes ) )",
     "+0.0%;-0.0%;0.0%", "Variación de los casos frente al año anterior. Solo con un año elegido."),
    ("1. Casos", "% de los casos del país",
     "DIVIDE ( [Casos], CALCULATE ( [Casos], REMOVEFILTERS ( dim_departamento ), REMOVEFILTERS ( dim_provincia ), REMOVEFILTERS ( dim_distrito ) ) )",
     "0.0%", "Parte de los casos del país (con el mismo año, forma clínica, edad y sexo) que tiene el territorio."),
    ("1. Casos", "Distritos con casos", "DISTINCTCOUNT ( fact_caso[ubigeo] )", "#,##0",
     "Distritos distintos con al menos un caso."),
    ("1. Casos", "Provincias con casos",
     "COUNTROWS ( FILTER ( VALUES ( dim_provincia[provincia_id] ), [Casos] > 0 ) )", "#,##0",
     "Provincias con al menos un caso."),
    ("1. Casos", "Departamentos con casos",
     "COUNTROWS ( FILTER ( VALUES ( dim_departamento[departamento_id] ), [Casos] > 0 ) )", "#,##0",
     "Departamentos con al menos un caso."),
    ("1. Casos", "Casos con edad válida", "SUM ( fact_caso[casos_con_edad] )", "#,##0",
     "Casos con una edad válida (hasta 110 años); sirven para la edad promedio."),
    ("1. Casos", "Edad promedio", "DIVIDE ( SUM ( fact_caso[edad_suma] ), [Casos con edad válida] )", "0.0",
     "Edad promedio en años de los casos con edad válida."),
    ("1. Casos", "% de mujeres",
     "DIVIDE ( CALCULATE ( [Casos], dim_sexo[sexo_id] = \"F\" ), [Casos] )", "0.0%", "Parte de los casos que son mujeres."),
    ("1. Casos", "Participación del grupo de edad",
     "DIVIDE ( [Casos], CALCULATE ( [Casos], REMOVEFILTERS ( dim_grupo_edad ) ) )", "0.0%",
     "Parte de los casos que corresponde al grupo de edad dentro del contexto (año, territorio)."),

    # 2. Gravedad (P5)
    ("2. Gravedad", "Casos con signos de alarma o graves",
     "CALCULATE ( [Casos], dim_forma_clinica[alarma_o_grave] = 1 )", "#,##0",
     "Casos clasificados como dengue con signos de alarma o dengue grave."),
    ("2. Gravedad", "% con signos de alarma o graves",
     "DIVIDE ( [Casos con signos de alarma o graves], [Casos] )", "0.0%",
     "Parte de los casos con signos de alarma o graves. Solo comparable desde 2011: antes la clasificación era distinta."),
    ("2. Gravedad", "% con signos o graves (clasificación actual)",
     "IF ( SELECTEDVALUE ( dim_anio[forma_comparable] ) = 1, [% con signos de alarma o graves] )", "0.0%",
     "Igual que % con signos de alarma o graves, pero vacío en los años anteriores a 2011, cuando la clasificación clínica era distinta. Úselo por año."),
    ("2. Gravedad", "Casos graves", "CALCULATE ( [Casos], dim_forma_clinica[cie10] = \"A97.2\" )", "#,##0",
     "Casos de dengue grave."),
    ("2. Gravedad", "% graves", "DIVIDE ( [Casos graves], [Casos] )", "0.00%", "Parte de los casos que son graves."),
    ("2. Gravedad", "Fallecidos (CDC)", "SUM ( fact_cdc_anual[fallecidos_cdc] )", "#,##0",
     "Fallecidos por dengue según la tabla oficial del CDC (2012–2024). El archivo de casos no los trae."),
    ("2. Gravedad", "Casos (CDC)", "SUM ( fact_cdc_anual[casos_cdc] )", "#,##0", "Casos de la tabla oficial del CDC."),
    ("2. Gravedad", "Letalidad (CDC)", "DIVIDE ( [Fallecidos (CDC)], [Casos (CDC)] )", "0.00%",
     "Fallecidos entre casos, ambos de la tabla oficial del CDC."),

    # 3. Incidencia (P3)
    ("3. Incidencia", "Población (habitantes-año)",
     f"IF (\n    {LEVEL_DISTRICT},\n    BLANK (),\n    IF (\n        {LEVEL_PROVINCE},\n"
     "        SUM ( fact_poblacion_provincia[poblacion] ),\n        SUM ( fact_poblacion_departamento[poblacion] )\n    )\n)",
     "#,##0",
     "Población proyectada de los territorios elegidos, sumada sobre los años elegidos. Con un solo año es la población de ese año. "
     "Se calcula con el nivel que se muestra (provincia o departamento); un distrito no tiene población propia."),
    ("3. Incidencia", "Casos con población",
     f"IF (\n    {LEVEL_PROVINCE},\n    CALCULATE ( [Casos], dim_anio[con_poblacion_provincial] = 1 ),\n"
     "    CALCULATE ( [Casos], dim_anio[con_poblacion] = 1 )\n)",
     "#,##0", "Casos de los años que tienen población (desde 2013 por departamento y desde 2016 por provincia)."),
    ("3. Incidencia", "Incidencia por 100 mil",
     "VAR habitantes = [Población (habitantes-año)]\nRETURN\n    IF ( NOT ISBLANK ( habitantes ), DIVIDE ( [Casos con población], habitantes ) * 100000 )",
     "#,##0.0",
     "Casos por 100 mil habitantes en un año. Sobre varios años es el promedio anual ponderado por población (suma de casos entre suma de "
     "población), nunca un promedio de tasas. Con edad o sexo elegidos, es la tasa de esos casos sobre la población total."),
    ("3. Incidencia", "Incidencia nacional",
     "CALCULATE ( [Incidencia por 100 mil], REMOVEFILTERS ( dim_departamento ), REMOVEFILTERS ( dim_provincia ), REMOVEFILTERS ( dim_distrito ) )",
     "#,##0.0", "La misma incidencia para todo el país, con el mismo periodo, forma clínica, edad y sexo."),
    ("3. Incidencia", "Veces la incidencia nacional",
     "DIVIDE ( [Incidencia por 100 mil], [Incidencia nacional] )", "0.00",
     "Incidencia del territorio dividida por la nacional: 2 significa el doble."),

    # 4. Temporada (P2)
    ("4. Temporada", "Parte de los casos del año",
     "DIVIDE ( [Casos], CALCULATE ( [Casos], REMOVEFILTERS ( dim_semana ) ) )", "0.0%",
     "Parte de los casos del año (o periodo elegido) que cae en la semana."),
    ("4. Temporada", "Semana pico",
     "VAR t = ADDCOLUMNS ( VALUES ( dim_semana[semana] ), \"@c\", [Casos] )\nRETURN\n    IF ( NOT ISBLANK ( [Casos] ), MAXX ( TOPN ( 1, t, [@c], DESC ), dim_semana[semana] ) )",
     "0", "Semana epidemiológica con más casos en el contexto."),
    ("4. Temporada", "Casos en la semana pico",
     "VAR t = ADDCOLUMNS ( VALUES ( dim_semana[semana] ), \"@c\", [Casos] )\nRETURN\n    MAXX ( t, [@c] )",
     "#,##0", "Casos de la semana con más casos."),

    # 5. Canal endémico (P6)
    ("5. Canal endémico", "Semanas sobre el canal", "SUM ( fact_canal_endemico[sobre_canal] )", "#,##0",
     "Semanas de departamento con más casos que el percentil 90 de las mismas semanas de los 5 años previos (y al menos 10 casos)."),
    ("5. Canal endémico", "Semanas evaluadas", "COUNTROWS ( fact_canal_endemico )", "#,##0",
     "Semanas de departamento evaluadas contra su canal (desde 2005)."),
    ("5. Canal endémico", "% de semanas sobre el canal", "DIVIDE ( [Semanas sobre el canal], [Semanas evaluadas] )", "0.0%",
     "Parte de las semanas evaluadas que quedó sobre el canal."),
    ("5. Canal endémico", "Semanas del país sobre el canal", "SUM ( fact_canal_nacional[sobre_canal] )", "#,##0",
     "Semanas en que los casos del país superaron el percentil 90 del canal nacional."),
    ("5. Canal endémico", "Umbral del canal (país)", "AVERAGE ( fact_canal_nacional[umbral] )", "#,##0",
     "Percentil 90 de los casos del país en la misma semana de los 5 años previos. Úselo por semana y con un año elegido."),
    ("5. Canal endémico", "Mediana histórica (país)", "AVERAGE ( fact_canal_nacional[mediana_historica] )", "#,##0",
     "Mediana de los casos del país en la misma semana de los 5 años previos."),
    ("5. Canal endémico", "Umbral del canal (departamento)", "AVERAGE ( fact_canal_endemico[umbral] )", "#,##0.0",
     "Percentil 90 de los casos del departamento en la misma semana de los 5 años previos."),

    # 6. Calidad de datos (limitaciones)
    ("6. Calidad de datos", "Casos sin edad válida",
     "CALCULATE ( [Casos], dim_grupo_edad[grupo_edad] = \"Sin edad válida\" )", "#,##0",
     "Casos con edad imposible (más de 110 años), marcados en la Fase 2."),
    ("6. Calidad de datos", "Casos en distritos fuera del padrón",
     "CALCULATE ( [Casos], dim_distrito[distrito_en_padron] = 0 )", "#,##0",
     "Casos de distritos creados desde 2021 que el padrón de población no conoce: cuentan en la provincia, no tienen incidencia propia."),

    # 7. Textos para el tablero
    ("7. Textos", "Corte de datos",
     f"\"Casos notificados al CDC Perú hasta el año \" & CALCULATE ( MAX ( fact_caso[anio] ), REMOVEFILTERS () )",
     None, "Último año con datos."),
    ("7. Textos", "Fuente",
     "\"Fuente: CDC Perú (MINSA), vigilancia epidemiológica de dengue, y población proyectada del MININTER (datosabiertos.gob.pe). Elaboración propia.\"",
     None, "Pie de fuente para cada página."),
]


# ---------------------------------------------------------------------------------------------
# Escritura
# ---------------------------------------------------------------------------------------------

def indent(text: str, tabs: int) -> str:
    return "\n".join("\t" * tabs + line if line else "" for line in text.splitlines())


def quote(name: str) -> str:
    """Nombres con espacios, tildes o signos van entre comillas simples en TMDL."""
    if re.fullmatch(r"[A-Za-z_][A-Za-z0-9_]*", name):
        return name
    return "'" + name.replace("'", "''") + "'"


def table_tmdl(name: str, spec: dict) -> str:
    out = [f"/// {spec['description']}", f"table {name}", f"\tlineageTag: {tag('table', name)}"]
    if spec.get("data_category"):
        out.append(f"\tdataCategory: {spec['data_category']}")
    out.append("")
    m_types = []
    for col, dtype, opts in spec["columns"]:
        if opts.get("description"):
            out.append(f"\t/// {opts['description']}")
        if opts.get("expression"):            # columna calculada en DAX
            out.append(f"\tcolumn {col} =")
            out.append(indent(opts["expression"], 3))
        else:
            out.append(f"\tcolumn {col}")
        out.append(f"\t\tdataType: {dtype}")
        if opts.get("key"):
            out.append("\t\tisKey")
        if opts.get("hidden"):
            out.append("\t\tisHidden")
        if opts.get("format"):
            out.append(f"\t\tformatString: {opts['format']}")
        out.append(f"\t\tlineageTag: {tag('column', name, col)}")
        out.append("\t\tsummarizeBy: none")
        if not opts.get("expression"):
            out.append(f"\t\tsourceColumn: {col}")
        if opts.get("sort_by"):
            out.append(f"\t\tsortByColumn: {opts['sort_by']}")
        out.append("")
        out.append("\t\tannotation SummarizationSetBy = Automatic")
        out.append("")
        if not opts.get("expression"):
            m_types.append(f'{{"{col}", {M_TYPES[dtype]}}}')
    m = (
        "let\n"
        f'    Origen = Csv.Document(File.Contents(RutaDatos & "{name}.csv"), [Delimiter=",", Encoding=65001, QuoteStyle=QuoteStyle.Csv]),\n'
        "    Encabezados = Table.PromoteHeaders(Origen, [PromoteAllScalars=true]),\n"
        f'    Tipos = Table.TransformColumnTypes(Encabezados, {{{", ".join(m_types)}}}, "en-US")\n'
        "in\n"
        "    Tipos"
    )
    out.append(f"\tpartition {name} = m")
    out.append("\t\tmode: import")
    out.append("\t\tsource =")
    out.append(indent(m, 4))
    out.append("")
    out.append("\tannotation PBI_ResultType = Table")
    out.append("")
    return "\n".join(out)


def measures_tmdl() -> str:
    out = ["table _Medidas", f"\tlineageTag: {tag('table', '_Medidas')}", ""]
    for folder, name, expr, fmt, desc in MEASURES:
        out.append(f"\t/// {desc}")
        if "\n" in expr:
            out.append(f"\tmeasure {quote(name)} =")
            out.append(indent(expr, 3))
        else:
            out.append(f"\tmeasure {quote(name)} = {expr}")
        if fmt:
            out.append(f"\t\tformatString: {fmt}")
        out.append(f"\t\tdisplayFolder: {folder}")
        out.append(f"\t\tlineageTag: {tag('measure', name)}")
        out.append("")
    out += ["\tcolumn Columna", "\t\tdataType: string", "\t\tisHidden",
            f"\t\tlineageTag: {tag('column', '_Medidas', 'Columna')}", "\t\tsummarizeBy: none",
            "\t\tisNameInferred", "\t\tsourceColumn: [Columna]", "",
            "\t\tannotation SummarizationSetBy = Automatic", "",
            "\tpartition _Medidas = calculated", "\t\tmode: import",
            '\t\tsource = ROW ( "Columna", BLANK () )', ""]
    return "\n".join(out)


def write(path: Path, text: str) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(text, encoding="utf-8", newline="\n")


def main() -> None:
    definition = MODEL / "definition"
    if definition.exists():
        shutil.rmtree(definition)
    names = list(TABLES)

    write(MODEL / ".platform", (
        '{\n  "$schema": "https://developer.microsoft.com/json-schemas/fabric/gitIntegration/platformProperties/2.0.0/schema.json",\n'
        f'  "metadata": {{\n    "type": "SemanticModel",\n    "displayName": "{NAME}"\n  }},\n'
        f'  "config": {{\n    "version": "2.0",\n    "logicalId": "{tag("logical", "model")}"\n  }}\n}}\n'))
    write(MODEL / "definition.pbism", (
        '{\n  "$schema": "https://developer.microsoft.com/json-schemas/fabric/item/semanticModel/definitionProperties/1.0.0/schema.json",\n'
        '  "version": "4.2",\n  "settings": {}\n}\n'))
    write(definition / "database.tmdl", "database\n\tcompatibilityLevel: 1606\n\n")
    query_order = ", ".join(f'"{n}"' for n in ["RutaDatos", *names])
    write(definition / "model.tmdl", (
        "model Model\n\tculture: es-PE\n\tdefaultPowerBIDataSourceVersion: powerBI_V3\n"
        "\tdiscourageImplicitMeasures\n\tsourceQueryCulture: en-US\n\tdataAccessOptions\n"
        "\t\tlegacyRedirects\n\t\treturnErrorValuesAsNull\n\n"
        "annotation __PBI_TimeIntelligenceEnabled = 0\n\n"
        f"annotation PBI_QueryOrder = [{query_order}]\n\n"
        'annotation PBI_ProTooling = ["DevMode"]\n\n'
        + "".join(f"ref table {n}\n" for n in [*names, "_Medidas"]) + "\n"))
    curated = str(config.CURATED).replace("/", "\\") + "\\"
    write(definition / "expressions.tmdl", (
        "/// Carpeta data/curated del repositorio, con barra final. Cámbiala al clonar el proyecto en otra ruta.\n"
        f'expression RutaDatos = "{curated}" meta [IsParameterQuery=true, Type="Text", IsParameterQueryRequired=true]\n'
        f"\tlineageTag: {tag('expression', 'RutaDatos')}\n\n\tannotation PBI_ResultType = Text\n\n"))
    write(definition / "relationships.tmdl", "".join(
        f"relationship {tag('relationship', f, fc, t, tc)}\n\tfromColumn: {f}.{fc}\n\ttoColumn: {t}.{tc}\n\n"
        for f, fc, t, tc in RELATIONSHIPS))
    for name, spec in TABLES.items():
        write(definition / "tables" / f"{name}.tmdl", table_tmdl(name, spec))
    write(definition / "tables" / "_Medidas.tmdl", measures_tmdl())
    print(f"Modelo: {len(TABLES)} tablas, {len(RELATIONSHIPS)} relaciones, {len(MEASURES)} medidas -> "
          f"{MODEL}")


if __name__ == "__main__":
    main()

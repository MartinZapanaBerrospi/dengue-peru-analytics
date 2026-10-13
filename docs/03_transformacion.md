# Fase 3 — Transformación

> Estado: **cerrada** (2026-10-13)

## 1. Qué se hizo

`python -m src.transform` convierte el CSV del portal en un modelo en estrella que Power BI lee sin
ejecutar nada:

```
raw (data/raw)        →  staging (parquet)     →  curated (data/curated/*.csv)
1 029 421 casos          1 029 421 casos          1 029 421 casos
1 029 421 filas          1 029 421 filas          332 850 filas (agregado)
```

Ningún caso se excluye. Lo que la Fase 2 marcó queda como marca o como grupo «sin edad válida». El script
falla si un paso pierde o duplica un caso, si alguna clave se repite, si una clave foránea queda huérfana
o si una tabla trae nulos.

## 2. El modelo

| Tabla | Filas | Clave | Para qué sirve |
|---|---|---|---|
| `fact_caso` | 332 850 | año × semana × distrito × forma clínica × grupo de edad × sexo | Casos (`casos`), y `edad_suma` y `casos_con_edad` para la edad promedio |
| `fact_poblacion_departamento` | 300 | departamento × año | Población de los 25 departamentos, 2013–2024 |
| `fact_poblacion_provincia` | 1 116 | provincia × año | Población de las 124 provincias con casos, 2016–2024 |
| `fact_canal_endemico` | 24 012 | departamento × año × semana | Casos de la semana y su canal endémico, 2005–2024 |
| `fact_canal_nacional` | 1 044 | año × semana | Lo mismo para el país, con los percentiles 25, 50 y 90 |
| `dim_distrito` | 662 | `ubigeo` | Distrito, provincia, departamento y si está en el padrón |
| `dim_provincia` | 124 | `provincia_id` | Provincia y su departamento |
| `dim_departamento` | 25 | `departamento_id` | Nombre con tildes y zona de análisis |
| `dim_anio` | 25 | `anio` | Década y marcas de comparabilidad |
| `dim_semana` | 53 | `semana` | Semana epidemiológica y su trimestre |
| `dim_forma_clinica` | 3 | `forma_clinica_id` | Sin signos de alarma, con signos de alarma, grave |
| `dim_grupo_edad` | 7 | `grupo_edad_id` | Menor de 1 año, niñez, adolescencia, juventud, adultez, adulto mayor, sin edad válida |
| `dim_sexo` | 2 | `sexo_id` | Mujer, hombre |

**Por qué se agrega.** Un caso por fila serían 1 millón de filas y 108 MB. El tablero filtra por año, semana,
distrito, forma clínica, edad y sexo, así que el modelo agrega justo en ese grano: 332 850 filas y 10 MB, sin
perder ningún caso ni ningún filtro. Lo único que el agregado no permite es la **mediana** de edad (se
calcula en Python, en la Fase 5), y por eso lleva la suma de edades, que sí permite el promedio.

Los 25 departamentos están en `dim_departamento` aunque el dengue solo aparezca en 23: la incidencia
nacional necesita la población de todo el país.

## 3. Decisiones

| Tema | Decisión | Por qué |
|---|---|---|
| Caso sin identificador (problema 1) | No se eliminan filas idénticas | Son casos distintos; el agregado los suma |
| Edad imposible (2) | `grupo_edad` = «Sin edad válida» y no suma a la edad promedio | 14 casos; siguen contando en todo lo demás |
| Edad en meses o días (3) | Se pasa a años | La edad promedio y los grupos usan años |
| Clasificación clínica (4) | `dim_anio[forma_comparable]` = 1 desde 2011 | El tablero compara la parte de casos graves solo con ese filtro |
| Población repetida (7) | Un valor por territorio y año | Antes de unirla |
| Lima partida (8) | Se suman Lima Metropolitana y Región Lima | El dengue trae un solo departamento |
| Población provincial hasta 2015 (9) | `fact_poblacion_provincia` empieza en 2016 | Antes la suma de provincias no cuadra con la nacional |
| Distritos fuera del padrón (11) | `dim_distrito[distrito_en_padron]` = 0 | Cuentan en casos y en la incidencia de su provincia |
| Semana 53 (15) | La tienen los años donde el archivo trae casos en esa semana | 2003, 2008, 2009, 2014 y 2020 |
| Zona de análisis | Costa norte, Amazonía, Sierra y selva alta, Costa centro y sur | Agrupación de departamentos del proyecto ([`departamentos.csv`](../data/reference/departamentos.csv)); no es una región oficial del CDC |

### Canal endémico

El canal endémico es la herramienta de la epidemiología para saber si una semana es normal. Para cada
departamento y cada semana de 2005 a 2024:

1. Se toman los casos de **los cinco años anteriores**, en la misma semana y en la anterior y la siguiente
   (15 valores).
2. El **umbral** es el percentil 90 de esos valores; la **mediana histórica** es la mediana.
3. La semana queda **sobre el canal** si supera el umbral y tiene **al menos 10 casos**.

El mínimo evita marcar semanas de 2 o 3 casos en departamentos casi sin dengue. De 24 012 semanas-departamento,
3 415 (14,2 %) quedan sobre el canal. A nivel país, 2023 tiene 47 semanas sobre el canal y 2018 ninguna.

Como el historial son los cinco años previos, **la epidemia de un año eleva el umbral de los cinco
siguientes**. Es una propiedad del método: una semana normal después de una epidemia puede parecer baja.

## 4. Linaje

[`reports/linaje.csv`](../reports/linaje.csv):

| Paso | Filas | Casos | Nota |
|---|---|---|---|
| 1. raw | 1 029 421 | 1 029 421 | Tal como se publica |
| 2. staging | 1 029 421 | 1 029 421 | Con tipos, claves y edad en años; 0 casos excluidos |
| 3. curated | 332 850 | 1 029 421 | Agregado: mismos casos |
| 3a. marca | 14 | 14 | Casos sin edad válida; subconjunto, no exclusión |

Además, los casos por año del modelo coinciden con la tabla oficial del CDC (Fase 2, V1), y la suma de la
población departamental con la nacional.

## 5. Pruebas

[`tests/test_curated.py`](../tests/test_curated.py) (10 pruebas) comprueba claves únicas, claves foráneas,
linaje, casos por año contra el CDC, los 10 distritos nuevos (1 678 casos), la edad sin grupo, el reparto por
forma clínica, la población, el cálculo del canal endémico con un ejemplo hecho a mano y la semana 53. Se
ejecutan sobre los CSV versionados, así que pasan en GitHub Actions sin los archivos originales.

## 6. Lo que pasa a la Fase 4

- Relaciones: `fact_caso` → `dim_anio`, `dim_semana`, `dim_distrito`, `dim_forma_clinica`, `dim_grupo_edad`,
  `dim_sexo`; `dim_distrito` → `dim_provincia` → `dim_departamento`; las poblaciones → su territorio y
  `dim_anio`; los canales → `dim_departamento`, `dim_anio` y `dim_semana`.
- **Incidencia por 100 mil.** Como los casos y la población son anuales, no hace falta anualizar: casos del
  territorio entre su población del año, por 100 000. Por departamento desde 2013; por provincia desde 2016;
  nacional desde 2013.
- La incidencia se calcula con la población del **nivel que se está viendo** (departamento o provincia), con
  una medida que decide el nivel y devuelve vacío donde no hay población.
- Cada medida se valida contra el mismo cálculo en Python (Fase 4).

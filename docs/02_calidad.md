# Fase 2 — Calidad de los datos

> Estado: **cerrada** (2026-10-13). Los números de este documento salen de `python -m src.quality` y
> `python -m src.validate` y están en [`reports/`](../reports/).

## 1. Resumen

El archivo de dengue es **confiable en lo esencial** y su calidad tiene límites claros:

- **Cuadra con la cifra oficial.** Sus casos por año coinciden con la tabla vigente del CDC en los
  13 años que esa tabla publica (2012–2024): 12 idénticos y uno (2013) con 1 caso de diferencia en
  13 092. Ninguna de las 31 reglas falla de forma bloqueante: **23 cumplen y 8
  quedan en alerta**, todas explicadas abajo.
- **No hay un identificador de caso.** Hay 152 091 filas idénticas (14,8 %), que **no son duplicados**
  y no se eliminan.
- **La clasificación clínica cambió en 2010–2011.** Antes del cambio solo existen «sin signos» y
  «grave», así que la parte de casos graves de 2000–2010 no se puede comparar con la posterior.
- **El conjunto no llega a 2025** aunque el CDC ya publica 2025 y 2026.
- **La documentación del portal describe otro archivo:** habla de `tipo_dx` (confirmado o probable) y
  esa columna no existe.

## 2. Cómo se mide

Cada regla vive en [`src/quality.py`](../src/quality.py) y las reglas de campo en
[`src/parse.py`](../src/parse.py), que también usa la Fase 3: la limpieza que se mide es la que se aplica.
Una regla **bloqueante** hace fallar el script; una **alerta** se informa y se documenta; una **informativa**
solo describe.

| Dimensión | Reglas | Cumplen | Alertas |
|---|---|---|---|
| Completitud | 5 | 3 | 2 |
| Unicidad | 3 | 3 | 0 |
| Validez | 10 | 8 | 2 |
| Consistencia | 5 | 3 | 2 |
| Exactitud | 6 | 6 | 0 |
| Oportunidad | 2 | 0 | 2 |
| **Total** | **31** | **23** | **8** |

El detalle de cada regla, con su medida y su explicación, está en
[`reports/calidad/reglas.csv`](../reports/calidad/reglas.csv).

## 3. Perfilado

[`perfilado_columnas.csv`](../reports/calidad/perfilado_columnas.csv) describe cada columna: tipo, vacíos,
valores distintos, mínimo, máximo y más frecuentes. Lo que más importa:

| Columna | Vacíos | Distintos | Observación |
|---|---|---|---|
| `departamento`, `provincia`, `distrito`, `ubigeo` | 0 | 23, 124, 625 y 662 | El UBIGEO siempre trae 6 dígitos (se lee como texto para no perder el cero inicial) |
| `enfermedad`, `diagnostic` | 0 | 3 | Una forma clínica por código CIE-10 (A97.0, A97.1, A97.2) |
| `ano`, `semana` | 0 | 25 y 53 | Años 2000–2024; semana 53 en 2003, 2008, 2009, 2014 y 2020 |
| `edad`, `tipo_edad` | 0 | 123 y 3 | Edad en años (99,3 %), meses (0,6 %) o días (0,03 %) |
| `sexo` | 0 | 2 | 53,8 % mujeres |
| `diresa` | 23 | 33 | Código de la dirección de salud que notifica, no equivale al departamento |
| `localidad` | 53 909 y 68 689 «NULL» | 10 133 | Nombres mezclados con códigos; 11,9 % sin dato |
| `localcod` | 148 616 | 9 779 | 25 605 ceros; a veces trae un nombre |

**Por año.** [`perfilado_anual.csv`](../reports/calidad/perfilado_anual.csv) trae casos, departamentos y
distritos con casos, formas clínicas, edad inválida, % de mujeres y mediana de edad de cada año. Los
distritos con casos suben de 90 en 2000 a 561 en 2024, y los departamentos de 11 a 22.

## 4. Las seis dimensiones

- **Completitud.** Los 11 campos que usa el análisis no tienen vacíos. Las alertas son de columnas que
  no se usan: `localidad` (11,9 %) y `localcod` (14,4 %).
- **Unicidad.** Cada UBIGEO tiene un solo nombre de distrito, provincia y departamento. Las filas
  idénticas son informativas porque no hay con qué distinguir dos casos (problema 1).
- **Validez.** Sexo, tipo de edad, año, semana, CIE-10 y UBIGEO cumplen sus dominios. Alertas: 14 edades
  de más de 110 años y 10 UBIGEO que no están en el padrón de distritos (problemas 2 y 10).
- **Consistencia.** La forma clínica siempre corresponde a su CIE-10 y el departamento al prefijo del
  UBIGEO. Alertas: 14 casos con edad en meses mayor a 11 y un caso de «con signos de alarma» en 2002.
- **Exactitud.** Cinco validaciones contra cifras oficiales; todas cumplen (sección 5).
- **Oportunidad.** El archivo termina en 2024 y se publicó 12 meses después; el CDC ya muestra 2026.

## 5. Exactitud: validación contra cifras oficiales

[`reports/validaciones.csv`](../reports/validaciones.csv) tiene las 42 comparaciones.

### V1. Casos por año frente a la sala situacional del CDC

La [sala situacional del dengue](fuentes/sala_dengue_SE33_2026.pdf) (SE 33 de 2026, página 18) publica los
casos por año de 2012 a 2026. El archivo del portal coincide con esa serie:

| Año | CDC | Archivo | Diferencia |
|---|---|---|---|
| 2012 | 28 505 | 28 505 | 0 |
| 2013 | 13 092 | 13 091 | −1 |
| 2014 a 2022 | 17 234 a 63 217 | iguales | 0 |
| 2023 | 256 641 | 256 641 | 0 |
| 2024 | 271 531 | 271 531 | 0 |

Es la validación más fuerte del proyecto: el archivo **es** la serie del CDC, caso por caso en el total
anual. Eso no valida cada fila, pero sí que no se perdió ni se inventó nada en el camino.

### V2. Año 2023 frente a la alerta epidemiológica del CDC

La [alerta AE-CDC N.° 006-2024](fuentes/alerta_AE-CDC_006_2024_dengue.pdf) dice que en 2023 se
notificaron **273 684 casos**, 6,2 % más que los 256 641 del archivo. **No es un error del archivo:**
son cortes distintos de la misma serie. La alerta es de principios de 2024 y el CDC revisa las cifras; la
sala situacional vigente ya muestra 256 641. Se informa, no se bloquea.

Lo que sí se compara es el **reparto por forma clínica**, que no depende del corte:

| Forma clínica, 2023 | Alerta CDC | Archivo | Diferencia relativa |
|---|---|---|---|
| Sin signos de alarma | 88,47 % | 88,25 % | −0,2 % |
| Con signos de alarma | 11,15 % | 11,35 % | +1,8 % |
| Grave | 0,39 % | 0,40 % | +2,9 % |

### V3. Población frente a la incidencia oficial

La misma alerta da una incidencia nacional de 808,9 casos por 100 mil habitantes en 2023. Con 273 684
casos, la población implícita es de 33,83 millones. La proyección del MININTER para 2023 es de 33,73
millones: **−0,32 %**, dentro de la tolerancia de 1 %.

### V4. La población suma lo que debe

La población proyectada de los **departamentos suma exactamente la nacional** en los 12 años (2013–2024).
La de las **provincias suma la nacional desde 2016**; en 2013, 2014 y 2015 el conjunto trae solo una parte
de las provincias (68 %, 97 % y 99,7 %), así que la incidencia provincial empieza en 2016.

## 6. Catálogo de problemas

| # | Problema | Ejemplo real | Afecta | Decisión |
|---|---|---|---|---|
| 1 | **No hay identificador de caso** | 152 091 filas repiten otra en las 14 columnas | 14,8 % de las filas | Mantener: dos pacientes con la misma edad, sexo, lugar y semana dan la misma fila. Eliminarlas borraría casos reales |
| 2 | **Edades imposibles** | 71 963 641 años en Cura Mori, Piura, 2017; 41 964 604 en el mismo distrito | 14 casos (11 de 2017, 1 de 2022 y 2 de 2023) con más de 110 años; 28 más entre 100 y 110 | Marcar `edad_invalida` y dejar el caso **sin grupo de edad**; sigue contando en todo lo demás |
| 3 | **La edad viene en años, meses o días** | 6 377 casos en meses y 324 en días; 14 en meses con más de 11 | 0,65 % de las filas | Corregir: se convierte a años (meses ÷ 12, días ÷ 365) |
| 4 | **Cambió la clasificación clínica** | «Con signos de alarma»: 0 casos hasta 2009, 134 en 2010, 3 508 en 2011 | Años 2000–2010 | Marcar: la parte de casos graves o con signos de alarma solo se compara desde 2011 |
| 5 | **La documentación describe otro archivo** | La ficha menciona `tipo_dx` (confirmado, probable, sospechoso) y 13 variables; el CSV trae 14 columnas sin `tipo_dx` | Todo el conjunto | Documentar: no se puede separar confirmados de probables, y el diccionario del proyecto ([sección 8](#8-diccionario-de-datos)) describe lo que el archivo trae |
| 6 | **`localidad` y `localcod` están sucias** | «NULL» como texto (68 689), ceros, nombres en una columna de códigos | 11,9 % y 14,4 % de las filas | Excluir: no se usan; el lugar es el UBIGEO |
| 7 | **La población se repite por indicador** | Cada UBIGEO y año trae una fila por indicador con la misma población | Sumarla directamente la inflaría | Corregir: un valor por ámbito, territorio y año |
| 8 | **Lima está partida en dos en la población** | Lima Metropolitana (1501) y Región Lima (1599); el dengue trae un solo departamento, Lima (15) | Un departamento | Corregir: se suman |
| 9 | **La población provincial es incompleta hasta 2015** | La suma de provincias es el 68 % de la nacional en 2013 | Incidencia provincial 2013–2015 | Excluir: la incidencia provincial empieza en 2016 |
| 10 | **Salto en la población de 2016 a 2017** | La población nacional baja de 31,49 a 31,24 millones | Incidencia 2016 frente a 2017 | Documentar: es una revisión de las proyecciones del INEI, no una caída real |
| 11 | **Distritos que el padrón no conoce** | Alto Trujillo (130112): 1 164 casos en 2024; Kumpirushiato, Cielo Punco, Manitea y Unión Asháninka (Cusco) | 10 UBIGEO, 1 678 casos (0,16 %) | Mantener: son distritos creados desde 2021. Cuentan en casos y en la incidencia de su provincia, pero no tienen incidencia distrital |
| 12 | **Pocos casos fuera de la zona endémica** | Arequipa 28, Apurímac 11, Moquegua 1 en 25 años | 3 departamentos | Documentar: sus tasas no son interpretables |
| 13 | **El conjunto no llega a 2025** | El archivo termina en diciembre de 2024; la sala muestra 35 852 casos en 2025 y 46 669 en 2026 | Los análisis más recientes | Documentar: todo es hasta 2024 |
| 14 | **Las cifras oficiales se revisan** | 2023: 273 684 en la alerta de 2024 y 256 641 hoy | Comparaciones con titulares | Documentar: se valida contra una publicación de fecha fija y se cita su corte |
| 15 | **La semana 53 aparece en cinco años** | 1 903 casos en 2003, 2008, 2009, 2014 y 2020 | La curva semanal | Mantener: hay años de 53 semanas epidemiológicas |
| 16 | **`diresa` no equivale al departamento** | 23 vacíos; una Diresa agrupa varios territorios | 0,002 % | Excluir: el departamento sale del UBIGEO |

## 7. Atípicos

- **Edad.** Los 42 casos con más de 100 años están en
  [`atipicos.csv`](../reports/calidad/atipicos.csv). Los 14 de más de 110 años se marcan como inválidos;
  los otros 28 (entre 100 y 110) son posibles y se dejan. Once son de 2017 (diez de Piura y uno de Tumbes, en el
  año del Niño costero), lo que sugiere un error de digitación en una sola carga.
- **Años y semanas.** Los picos de 2017, 2023 y 2024 **no son atípicos: son epidemias** (2023 multiplica por
  4 los casos de 2022). Se compararon las 1 305 semanas con la mediana de sus 8 vecinas: solo una con 100 casos o más supera 2,5 veces a su entorno (la semana 24 de 2000, con 572 casos, en un año que cierra con 5 557) y se deja.
- **Años bajos.** 2018 (4 698 casos) es real: el CDC publica el mismo número.

## 8. Diccionario de datos

Primero lo que trae la fuente y luego el nombre que usa el proyecto.

| Columna del archivo | Nombre limpio | Tipo | Descripción | Ejemplo | Reglas |
|---|---|---|---|---|---|
| `departamento`, `provincia`, `distrito` | igual | texto | Lugar probable de infección, en mayúsculas y sin tildes | PIURA / PIURA / CASTILLA | Problema 11 (padrón) |
| `ubigeo` | `ubigeo` | texto de 6 dígitos | Código del distrito de infección | 200105 | Se lee como texto |
| — | `departamento_id`, `provincia_id` | texto | 2 y 4 primeros dígitos del UBIGEO | 20, 2001 | Une con la población |
| `enfermedad` | `forma_clinica` | texto | Sin signos de alarma, con signos de alarma o grave | DENGUE GRAVE | Problema 4 |
| `diagnostic` | `cie10` | texto | A97.0, A97.1 o A97.2 | A97.1 | Regla de consistencia |
| `ano`, `semana` | `anio`, `semana` | entero | Año y semana epidemiológica de inicio de síntomas | 2023, 20 | Semana 1 a 53 |
| `edad`, `tipo_edad` | `edad_original`, `tipo_edad` | entero, texto | Edad y su unidad (A años, M meses, D días) | 58, A | Problemas 2 y 3 |
| — | `edad_anios`, `edad_invalida`, `grupo_edad` | decimal, 0/1, texto | Edad en años, marca de más de 110 años y curso de vida | 26,0 | Problema 2 |
| `sexo` | `sexo` | texto | F o M | F | — |
| `diresa`, `localidad`, `localcod` | igual | texto | Dirección de salud y localidad | 31 | Problemas 6 y 16: no se usan |

## 9. Lo que pasa a la Fase 3

- Las reglas de campo (problemas 2, 3 y 4) se aplican con las mismas funciones de `src/parse.py`.
- **Agregar el caso** a semana × distrito × forma clínica × grupo de edad × sexo, sin perder ningún caso
  (linaje: 1 029 421 casos en el archivo y en el modelo).
- **Población:** un valor por territorio y año, con Lima sumada; incidencia departamental desde 2013 y
  provincial desde 2016.
- **Dimensión de territorio** con UBIGEO como clave, incluidos los 10 distritos que el padrón no conoce
  (sin población propia) y la región natural (costa, sierra, selva) como atributo de análisis.
- **Canal endémico** por departamento y semana, con los cinco años previos (Fase 5).
- **Marcas, no filtros:** `edad_invalida`, `distrito_sin_padron`, `forma_comparable` (desde 2011).

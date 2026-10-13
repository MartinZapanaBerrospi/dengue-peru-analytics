# Fase 5 — Análisis

> Estado: **cerrada** (2026-10-13). Datos de 2000 a 2024. Todas las cifras salen de
> `python -m src.analysis` y se guardan en [`reports/analisis/`](../reports/analisis/); el tablero las
> cita desde ahí.

## Cómo leer este documento

Cada respuesta trae su cifra, **qué dice**, **qué no dice** y la advertencia que hay que repetir en cualquier
presentación. Un caso notificado no es una infección: es lo que el sistema de vigilancia detectó y registró.
El análisis es descriptivo y no estima causas. La incidencia es casos por 100 mil habitantes en un año, con la
población proyectada del MININTER; se calcula desde 2013 por departamento.

## P1. ¿Cómo evolucionaron los casos y qué años fueron epidemia?

**El dengue pasó de epidemias aisladas a un nivel alto sostenido, y 2023 y 2024 concentran la mitad de los casos de 25 años.**

| Año | Casos | Incidencia por 100 mil | Fallecidos (CDC) | Letalidad (CDC) |
|---|---|---|---|---|
| 2012 | 28 505 | — | 42 | 0,15 % |
| 2013 | 13 091 | 43,0 | 18 | 0,14 % |
| 2014 | 17 234 | 55,9 | 34 | 0,20 % |
| 2015 | 35 816 | 115,0 | 52 | 0,15 % |
| 2016 | 25 160 | 79,9 | 45 | 0,18 % |
| 2017 | 68 290 | 218,6 | 89 | 0,13 % |
| 2018 | 4 698 | 14,9 | 18 | 0,38 % |
| 2019 | 15 287 | 47,6 | 37 | 0,24 % |
| 2020 | 47 932 | 146,9 | 86 | 0,18 % |
| 2021 | 44 791 | 135,6 | 43 | 0,10 % |
| 2022 | 63 217 | 189,3 | 86 | 0,14 % |
| 2023 | 256 641 | 761,0 | 444 | 0,17 % |
| 2024 | 271 531 | 797,7 | 261 | 0,10 % |

- **51,3 % de los 1 029 421 casos** de 2000 a 2024 cayeron en 2023 y 2024.
- **2023 multiplicó por 4,1 los casos de 2022** y fue 3,8 veces la epidemia de 2017.
  2024 la superó otra vez (271 531, +5,8 %).
- **Años de alta transmisión** (más de 50 mil casos): 2017, 2022, 2023, 2024. Antes de 2017 el máximo fue de 35 816 (2015).
- **2018 fue un valle real** (4 698 casos, 14,9 por 100 mil): el CDC publica el mismo número.
- Entre 2012 y 2024 el CDC registra **1 255 fallecidos**; 444 en 2023 y 261 en 2024. La
  letalidad de 2023 fue 0,17 % y la de 2024, 0,10 %: con muchos más casos, la proporción de fallecidos no subió.

**Qué no dice.** Que haya más infección que antes: más casos notificados pueden ser más pruebas y más notificación. Tampoco que
2025 siga igual: la sala situacional del CDC muestra solo 35 852 casos en 2025 y 46 669
hasta la semana 33 de 2026, pero esos años **no están en el archivo abierto** y se citan solo como contexto. La letalidad de 2018 (0,38 %) parece
alta por tener 18 fallecidos sobre 4 698 casos: con tan pocos casos, un fallecido más mueve mucho la proporción.

## P2. ¿Cuándo se concentra el dengue y cuánto se adelantó el pico?

**La temporada normal llega a su pico hacia la semana 16 (mediados de abril); 2023 fue tardía y 2024 llegó seis semanas antes que 2023.**

- En una temporada normal (15 años de más de 10 mil casos, sin 2023 ni 2024) el pico cae en la **semana 16**,
  y entre la semana 1 y la 26 se acumula el 69 % de los casos del año.
- **2023** llegó a su pico en la semana 20 con 19 269 casos en una semana, y recién acumuló la mitad de los casos de su
  año en la semana 22.
- **2024** tuvo su pico en la semana 14 (21 628 casos), **6 semanas antes** que 2023, y acumuló la mitad en la
  semana 14. El 94 % de sus casos cayó en el primer semestre.
- **2017** (El Niño costero) fue una epidemia corta y concentrada: pico en la semana 18 y solo 14 semanas entre el 10 % y el 90 % de los casos.

**Qué no dice.** Que la temporada sea igual en todo el país: en 2024 la costa norte llegó a su pico en la semana 11 y la costa centro y sur en la 16, mientras la
Amazonía lo tuvo en la 47. Años como 2008, 2012, 2019 y 2020 tuvieron su pico país en la segunda mitad del año. El pico de una zona pequeña es una cifra con mucho ruido.

## P3. ¿Dónde se concentra por habitante y cuánto se expandió el mapa?

Referencia: incidencia anual media de **2023 y 2024**, que es lo que más pesa. Incidencia nacional: **779** por 100 mil.

| Departamento | Casos 2023 | Casos 2024 | Incidencia anual media | Veces la nacional |
|---|---|---|---|---|
| Tumbes | 12 890 | 5 267 | 3 427 | 4,4 |
| Piura | 79 304 | 32 246 | 2 608 | 3,3 |
| Ica | 16 889 | 30 407 | 2 248 | 2,9 |
| La Libertad | 26 502 | 49 931 | 1 805 | 2,3 |
| Lambayeque | 31 460 | 9 305 | 1 503 | 1,9 |
| Áncash | 11 658 | 18 789 | 1 268 | 1,6 |
| San Martín | 6 890 | 10 870 | 944 | 1,2 |
| Ucayali | 8 174 | 740 | 704 | 0,9 |

- **Tumbes** tiene la mayor incidencia (3 427, 4,4 veces la nacional), seguido de Piura
  (2 608) e Ica. Solo 7 de 25 departamentos superan la incidencia nacional.
- **El epicentro se movió.** Piura puso el 65 % de los casos de 2017, el 31 % de los de 2023 y el 12 % de los de 2024.
- **Lima pasó de casi nada a un tercio del país.** Tuvo 938 casos en 2022, 30 735 en 2023 y 87 864 en 2024: el 32 % de los casos
  de ese año.
- **El mapa se amplió.** Los distritos con casos pasaron de 90 en 2000 a 329 en 2017 y 561 en 2024; los departamentos,
  de 11 a 22.
- Entre las provincias de 20 mil habitantes o más, **Huarmey** (Áncash) tiene la mayor incidencia 2023–2024: 4 976.
  El distrito con más casos es **Piura** (15 568); los 10 distritos con más reúnen el 24 % de los casos.

**Qué no dice.** Que los departamentos con menor incidencia estén a salvo: algunos no tienen dengue endémico y otros notifican poco. Los casos se
asignan al **lugar probable de infección** y no al de residencia, y la incidencia de Lima en 2024 (777 por 100 mil) es igual a la nacional (798) aunque puso un tercio de los casos: Lima pesa por su población, no por su incidencia.

## P4. ¿A quién afecta?

**A adultos en edad de trabajar, y un poco más a las mujeres.**

- **La mediana de edad es de 28 años** (de 21 en 2012 a 30 en 2024).
- Por curso de vida: **30 a 59 años, 38 %**; 18 a 29, 23 %; menores de 12, 16 %; 60 o más, 9 %.
- **La parte de adultos subió** de 36,5 % (2000–2010) a 39,5 % (2023–2024); la de niños se mantuvo cerca del 15 %.
- **53,8 % de los casos son mujeres** (54,3 % en 2023–2024).

**Qué no dice.** Que los adultos sean los más expuestos: la fuente **no trae población por edad ni por sexo**, así que no se calcula incidencia por grupo. Los
adultos pesan más en los casos también porque son más numerosos, y las mujeres pueden pesar más por consultar más. Tampoco dice a quién enferma más
gravemente (P5).

## P5. ¿Qué tan graves son los casos?

**Uno de cada ocho casos llega con signos de alarma o grave, y esa parte bajó en las epidemias recientes.**

- Entre 2011 y 2024, el **12,3 %** de los casos fue con signos de alarma o grave; los graves son el 0,39 %.
- La parte **bajó**: 27,1 % en 2013, 8,7 % en 2021, 11,7 % en 2023 y 9,9 % en 2024. En 2023 y 2024 hubo
  56 935 casos con signos de alarma o graves.
- **Los más pequeños son los más graves:** Menor de 1 año (17,9 %), frente a 11,0 % en Adultez (30–59).
  Las mujeres llegan con signos de alarma o graves más que los hombres (13,1 % y 11,5 %).

**Qué no dice.** Que el dengue sea hoy menos peligroso: en una epidemia enorme, la parte grave baja porque el denominador se llena de casos leves y de mejor
detección. Antes de 2011 la clasificación era otra (solo «sin signos» y «grave») y la parte de graves de 2000–2009 (0,45 %) **no es comparable**. Los
fallecidos no están en el archivo: salen de la tabla oficial del CDC.

## P6. ¿Qué semanas se salen del canal endémico?

**En 2023 el país estuvo sobre el canal 47 semanas, y el aviso estaba desde la primera.**

- El **canal endémico** compara cada semana con las mismas semanas de los cinco años anteriores (percentil 90, con al menos 10 casos).
- **2023:** los casos del país superaron el canal en **47 semanas** y la primera fue la semana 1,
  19 semanas antes del pico. **2024:** 18 semanas, también desde la semana 1 y 13 antes del pico. **2018:** ninguna.
- En 2023, el 44 % de las semanas de departamento estuvo sobre el canal; en 2018, el 0,3 %.

| Departamento | Semanas sobre el canal, 2023–2024 | Parte de las 104 semanas |
|---|---|---|
| San Martín | 80 de 104 | 77 % |
| Piura | 66 de 104 | 63 % |
| La Libertad | 64 de 104 | 62 % |
| Lima | 64 de 104 | 62 % |
| Lambayeque | 62 de 104 | 60 % |
| Ica | 58 de 104 | 56 % |

**Qué no dice.** Que una semana sobre el canal sea un brote confirmado: es una señal para revisar. Como el canal usa los cinco años previos, **una epidemia sube el umbral de los cinco años
siguientes**, y una semana normal después de una epidemia puede parecer baja. En 2023 y 2024 el canal ya estaba pasado en la semana 1: la temporada empezó alta.

## Lo que se pasa al tablero

Una página por pregunta, con la respuesta en el subtítulo y esta advertencia en la lectura. Las cifras de los textos se leen de `cifras_clave.csv`: ningún número
del tablero está escrito a mano.

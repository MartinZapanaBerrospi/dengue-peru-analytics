# Tablero de Power BI (PBIP)

> Fase 6 · Estado: **cerrada** (2026-10-13). **[Ver el tablero publicado](https://app.powerbi.com/view?r=eyJrIjoiNDRmNGU1YjctNTRjYi00MjM4LWI0MjYtYTRlY2I1NTljMDM5IiwidCI6IjFlYmE0NDNmLTIzZTUtNDUzNC05MGQxLTA5NzZhYWJlODZhYyIsImMiOjR9&pageName=p1_resumen)**

El informe se guarda como **Power BI Project**: el modelo en TMDL y el informe en PBIR (JSON), todo en
texto, revisable en GitHub sin abrir Power BI. **Ninguno de los dos se armó a mano.** Los generan dos
scripts, así que cada visual, medida y relación está en el historial de cambios:

```bash
python tools/build_model.py    # modelo: 14 tablas, 18 relaciones y 38 medidas DAX
python tools/build_report.py   # informe: 7 páginas, 57 visuales, tema propio
```

## Cómo abrirlo

1. Clona el repositorio. Los datos que lee el tablero (`data/curated/*.csv`) vienen incluidos: no hace
   falta ejecutar el pipeline.
2. Abre `dengue.pbip` con **Power BI Desktop** (se construyó con la versión 2.157; necesita soporte para
   el formato de informe PBIR).
3. Si clonaste en otra carpeta: *Inicio → Transformar datos → Editar parámetros* y cambia **`RutaDatos`**
   por la ruta de tu copia de `data/curated/`, con la barra final.
4. *Inicio → Actualizar*. El repositorio no guarda la caché de datos (`.pbi/cache.abf`), así que el primer
   refresco es obligatorio. Carga 332 850 filas de casos en segundos.

## Páginas

Cada página tiene el mismo esquema:
- **título:** la pregunta;
- **subtítulo:** la respuesta;
- **visuales:** la evidencia;
- **"Lectura":** qué significa para gerencia, con su advertencia;
- **pie:** la fuente.

Los textos toman sus cifras de [`reports/analisis/cifras_clave.csv`](../reports/analisis/cifras_clave.csv).
Ninguna cifra se escribió a mano, así que el tablero no puede contradecir al análisis.

| Página | Pregunta | Qué tiene |
|---|---|---|
| ![](../docs/img/01_resumen.png) **1. Resumen** | Resumen ejecutivo | 5 indicadores, casos por año y por zona, «qué está pasando» y «qué conviene hacer» |
| ![](../docs/img/02_epidemias.png) **2. Epidemias** (P1) | ¿Cómo evolucionaron los casos y qué años fueron epidemia? | Casos, incidencia y fallecidos por año, y una tabla año por año con variación y letalidad |
| ![](../docs/img/03_temporada.png) **3. Temporada** (P2) | ¿Cuándo se concentra el dengue? | Curva semanal de los años que se elijan (abre con 2017, 2022, 2023 y 2024) y semana pico de cada año |
| ![](../docs/img/04_territorio.png) **4. Territorio** (P3) | ¿Dónde se concentra por habitante? | Incidencia por departamento (abre en 2023–2024) y provincias con más casos |
| ![](../docs/img/05_pacientes.png) **5. Pacientes** (P4, P5) | ¿A quién afecta y qué tan graves son los casos? | Casos y gravedad por curso de vida, gravedad por año, edad promedio y parte de mujeres |
| ![](../docs/img/06_brotes.png) **6. Brotes** (P6) | ¿Qué semanas se salen del canal endémico? | Casos del país frente al umbral del canal y departamentos con más semanas sobre el canal |
| ![](../docs/img/07_notas.png) **7. Notas** | | Definiciones, fuentes, validación y límites |

**Segmentadores.** Año en el resumen, los pacientes, la temporada, el territorio y los brotes. Vacío significa
todo el periodo; *Temporada*, *Territorio* y *Brotes* abren con años elegidos.

## Decisiones de diseño

- **Una pregunta por página**, con la respuesta en el subtítulo. Un gerente entiende la página sin mirar los
  gráficos.
- **Incidencia con el denominador correcto.** La medida usa la población de la provincia o del departamento
  según lo que se muestre, cuenta solo los casos de los años que tienen población, y sobre varios años suma
  casos y población (nunca promedia tasas). Ver la [Fase 4](../docs/04_modelado.md#4-cómo-se-calcula-la-incidencia-por-100-mil).
- **La gravedad solo se compara desde 2011.** La clasificación clínica cambió: los gráficos de gravedad filtran
  los años anteriores, y una medida propia devuelve vacío antes de 2011.
- **Semanas y años en eje continuo.** Un eje de 53 categorías o de 25 años produce una barra de desplazamiento
  que esconde justo los años que más importan (2023 y 2024).
- **El canal endémico se explica en la propia página.** Una semana sobre el canal es una señal para revisar, no un
  brote confirmado; la página lo dice.
- **Números sin abreviar.** Power BI abrevia por defecto («256 mil»). Se desactivó en etiquetas, ejes y tarjetas.
- **Tema propio** ([`Dengue.json`](dengue.Report/StaticResources/RegisteredResources/Dengue.json)): un color de acento,
  fondo gris claro y tarjetas blancas, sin sombras ni bordes. Nada compite con los datos.

## Cómo se verificó

1. **Pruebas automáticas** ([`tests/test_powerbi.py`](../tests/test_powerbi.py)), en GitHub Actions:
   - ningún visual se sale del lienzo de 1280 × 720 ni se encima con otro;
   - cada medida y columna que usa un visual existe en el modelo;
   - cada página tiene título y pie;
   - los archivos versionados son exactamente los que producen los generadores.
2. **Medidas contra Python.** 9 702 comparaciones en Power BI Desktop, cero diferencias (ver la
   [Fase 4](../docs/04_modelado.md)).
3. **Revisión de cada captura a ojo** antes de cerrar la fase. Detectó lo que las pruebas no ven: gráficos con barra
   de desplazamiento que escondían 2023 y 2024, etiquetas de tarjeta de dos líneas que recortaban el valor, un grupo
   de edad con 14 casos que mostraba 21 % de gravedad y varias barras con decimales de más.

## Regenerar las capturas

```bash
powershell -File tools/refrescar.ps1 -Puerto <puerto de Desktop>      # el modelo recién abierto está vacío
powershell -ExecutionPolicy Bypass -File tools/capturas.ps1 -Salida <carpeta>
python tools/recortar_capturas.py <carpeta>
```

`capturas.ps1` cambia de página y captura la ventana de Power BI Desktop sin mover el mouse ni tomar el foco. Si
Desktop está minimizado, se restaura sin activarlo y se espera 20 s a que su árbol de accesibilidad aparezca.

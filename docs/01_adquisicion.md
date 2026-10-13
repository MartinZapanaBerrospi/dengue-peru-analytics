# Fase 1 — Adquisición

> Estado: **cerrada** (2026-10-13).

## Qué se descarga

| Fuente | Archivo que usa el proyecto | Tamaño | Destino |
|---|---|---|---|
| [Vigilancia epidemiológica de dengue](https://www.datosabiertos.gob.pe/dataset/vigilancia-epidemiol%C3%B3gica-de-dengue) (MINSA, CDC Perú) | `datos_abiertos_vigilancia_dengue_2000_2024.csv` | 108,6 MB | `data/raw/dengue.csv` |
| [Indicadores de seguridad ciudadana y tendencias territoriales](https://www.datosabiertos.gob.pe/dataset/indicadores-de-seguridad-ciudadana-y-tendencias-territoriales-mininter) (MININTER) | CSV `2009 a Jul 2026`, dentro de un zip anidado; solo se usa su población proyectada | 5,8 MB (9,8 MB comprimido) | `data/raw/indicadores.csv` |
| [Sala situacional del dengue, SE 33 de 2026](https://www.dge.gob.pe/portal/docs/vigilancia/sala/2026/SE33/dengue.pdf) (CDC Perú) | PDF de 108 páginas, para validar | 5,9 MB | [`docs/fuentes/`](fuentes/) |

El conjunto de indicadores del MININTER ya se usó en otro proyecto del portafolio. Aquí solo se toma
`POBLACION_PROYECTADA`, el denominador de la incidencia.

## Por qué la descarga se hace en el navegador

El portal de datos abiertos responde **418** a cualquier cliente que no sea un navegador (curl,
`requests`, `urllib`). Se comprobó el mismo día con el CSV de dengue. Es un control deliberado y **no
se intenta evadirlo**: no se cambian cabeceras ni se simula un navegador.

La salida es una descarga única y trazable. El CSV de dengue y el zip de indicadores se bajan una vez
desde el navegador y se dejan en `data/raw/descarga/`. A partir de ahí todo es automático y
verificable. En cambio, el sitio del CDC (`dge.gob.pe`) **sí acepta descargas por script**, así que
la sala situacional se baja con `curl` y se guarda en el repositorio.

## Cómo se ejecuta

1. Abrir en el navegador los enlaces de descarga:
   - `https://www.datosabiertos.gob.pe/sites/default/files/datos_abiertos_vigilancia_dengue_2000_2024.csv`
   - `https://www.datosabiertos.gob.pe/node/23663/dataset/download` (zip de indicadores)
2. Guardar ambos en `data/raw/descarga/` con los nombres que espera `src/config.py`
   (`datos_abiertos_vigilancia_dengue_2000_2024.csv` y `mininter_indicadores_*.zip`).
3. Ejecutar:

```bash
python -m src.extract              # copia, compara con el inventario y registra en el manifiesto
python -m src.extract --verificar  # solo comprueba que lo extraído no cambió
```

El script:

- **Copia cada archivo sin modificar un solo byte,** incluso el que está en un zip dentro de otro
  zip.
- **Lo compara con el inventario del portal** ([`inventario_portal.csv`](../data/reference/inventario_portal.csv)):
  el tamaño del archivo debe ser el que lista la página del conjunto. Una diferencia se marca como
  `distinto_al_inventario`.
- **Registra en el manifiesto** ([`data/raw/manifest.csv`](../data/raw/manifest.csv)) la URL, la
  fecha de publicación, el tamaño y el hash SHA-256. El manifiesto sí se versiona; los archivos
  originales no.
- **Es idempotente:** si un archivo no cambió, no lo reescribe ni toca el manifiesto.
- **Falla** si falta un archivo, si no está en el manifiesto o si su contenido ya no coincide con el
  hash registrado.

## Qué se encontró

| Archivo | Bytes | Estado | SHA-256 (primeros 12) |
|---|---|---|---|
| `dengue.csv` | 108 550 394 | `ok`: coincide con el tamaño que anuncia el portal | `35ec0840afa4` |
| `indicadores.csv` | 5 782 658 | `ok`: el zip anidado mide 9 845 996 bytes, igual que el inventario | `f1cc64f0cee9` |
| `sala_dengue_SE33_2026.pdf` | 5 933 151 | `ok`: descarga directa | `29fd86cb2cc8` |

- **El conjunto de dengue está fechado.** El archivo se publicó el 16 de diciembre de 2025 y la
  página dice «Fecha modificada: 2025-12-17». Cubre hasta diciembre de 2024: la fuente viva del CDC
  ya tiene 2025 y 2026 y el conjunto abierto no. Es una brecha de un año y medio entre lo que se
  publica en la sala situacional y lo que se abre como dato.
- **El portal no tiene control de versiones.** Si el CDC reemplaza el archivo, el mismo enlace
  entregará otro contenido. El manifiesto con hash lo detecta (`--verificar` falla) y obliga a
  repetir las validaciones.
- **La documentación del portal describe otro archivo.** La ficha habla de la columna `tipo_dx` y de 13
  variables; el CSV trae 14 columnas y no incluye `tipo_dx`. Se detalla en la Fase 2.

## Decisiones

- **No se versionan los archivos originales** (108 MB el de dengue): están en el manifiesto con su
  hash y el repositorio sirve el modelo curado, que es lo que lee Power BI.
- **La sala situacional se versiona.** Es la cifra oficial contra la que se valida y pesa 5,9 MB.
- **CI sin los archivos originales.** GitHub Actions ejecuta solo las pruebas, que usan recortes reales
  (`tests/fixtures/`) y los reportes y el modelo curado versionados.

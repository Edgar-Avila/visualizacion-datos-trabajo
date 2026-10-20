# Diccionario de datos: `_reporte_silver.json`

Este documento describe el archivo `preprocesamiento/silver/_reporte_silver.json`.

El archivo lo genera el notebook `02_silver.ipynb` al final de cada ejecución.

El archivo no contiene datos. Contiene el resultado de los controles de calidad.

## 1. Estructura general

El archivo es un objeto JSON. Tiene campos simples y dos campos agrupados.

- `fuentes_duplicadas` es una lista de objetos.
- `tarifas_finales` es un objeto de pares clave-valor.

Los conteos son **filas**, no clientes distintos. Esta distinción es importante porque `codigo_cliente` es un correlativo. Vea `preprocesamiento.md`, sección 6.4.

## 2. Convenciones

| Convención | Significado |
|---|---|
| Periodo | El mes de facturación. El formato es AAAAMM. Ejemplo: 202402. |
| Antes del dedup | El conteo se calcula sobre la unión de todos los periodos, sin quitar duplicados. |
| Final | El conteo se calcula sobre las tablas Parquet ya limpias y deduplicadas. |
| "pre-dedup" | Igual que "antes del dedup". |

## 3. Campos simples

| Campo | Tipo | Descripción | Valor actual |
|---|---|---|---|
| `filas_unidas_antes_dedup` | entero | Filas totales al unir todas las fuentes, antes del dedup. Incluye las dos granularidades. | 12.554.866 |
| `filas_clientes_finales` | entero | Filas del archivo `consumo_clientes.parquet` después del dedup. | 11.782.755 |
| `filas_agregado_finales` | entero | Filas del archivo `consumo_agregado.parquet` después del dedup. | 74.485 |
| `nulos_obligatorios` | entero | Filas con al menos un nulo en un campo obligatorio. | 0 |
| `negativos_finales` | entero | Filas con `consumo_kwh < 0` o `facturacion_soles < 0`, en las tablas finales. | 18.783 |
| `ubigeo_invalido` | entero | Filas con `ubigeo` nulo o sin el formato de 6 dígitos. | 0 |
| `duplicados_correlativo_periodo` | entero | Grupos (correlativo, periodo) con más de una fila, antes del dedup. En este dataset cada grupo tiene exactamente 2 copias. Por eso el valor también es el número de filas eliminadas. | 697.626 |
| `filas_rechazadas` | entero | Filas movidas a `_rechazados.parquet` por errores críticos. | 0 |
| `archivos_con_error` | lista de texto | Archivos que el notebook no pudo leer. | `[]` |
| `periodos_con_codigo_correlativo` | texto | Periodos donde el código es un correlativo denso 1..N, sobre el total de periodos por cliente. El formato es `detectados/total`. | `"34/34"` |
| `codigos_con_multiples_ubigeos` | entero | Códigos que aparecen con más de un ubigeo a lo largo del tiempo. | 261.109 |
| `filas_ubigeo_fuera_puno` | entero | Filas con un ubigeo que no empieza en `21` (Puno). | 66 |
| `ubigeos_con_multiples_provincias` | entero | Ubigeos que aparecen con más de una provincia. | 37 |
| `filas_geo_incoherente` | entero | Filas cuya combinación (departamento, provincia, distrito) no coincide con la combinación dominante de su ubigeo. | 112.269 |
| `fecha_alta_pre1950` | entero | Filas con `fecha_alta` anterior al 1 de enero de 1950. | 21.998 |
| `fecha_alta_1908_09_27` | entero | Filas con `fecha_alta` igual a 1908-09-27. | 20.690 |

## 4. Campo agrupado `fuentes_duplicadas`

Es una lista. Cada elemento describe un periodo con más de un archivo fuente.

| Campo | Tipo | Descripción | Ejemplo |
|---|---|---|---|
| `periodo` | entero | Periodo con más de un archivo fuente. Formato AAAAMM. | 202402 |
| `n_fuentes` | entero | Cantidad de archivos que contienen ese periodo. | 2 |
| `archivos` | texto | Nombres de los archivos, separados por coma. | `"ELPU_2024-02.zip, ELPU_2024-06.zip"` |
| `archivo_conservado` | texto | Archivo que el notebook conservó después del dedup. Es el archivo cuyo nombre coincide con el periodo. | `"ELPU_2024-02.zip"` |

Si la lista está vacía, no hay periodos con más de un archivo fuente.

## 5. Campo agrupado `tarifas_finales`

Es un objeto. Cada clave es una tarifa. Cada valor es el número de filas de esa tarifa en las tablas finales.

| Clave | Tipo del valor | Descripción |
|---|---|---|
| Nombre de la tarifa | entero | Filas con esa tarifa. |

Ejemplo del contenido actual:

| Tarifa | Filas |
|---|---|
| BT5B | 11.733.318 |
| BT5D | 68.363 |
| MT4 | 22.569 |
| BT6 | 11.348 |
| MT2 | 11.205 |
| MT3 | 7.412 |
| BT4 | 1.665 |
| BT3 | 666 |
| BT5A | 569 |
| BT2 | 125 |

## 6. Cómo interpretar los valores

### Campos donde cero es el resultado esperado

Estos campos deben valer `0` o `[]`:

- `nulos_obligatorios`
- `ubigeo_invalido`
- `filas_rechazadas`
- `archivos_con_error`

### Campos informativos

Estos campos describen características del dato. Un valor mayor que cero **no** es un error del notebook:

- `negativos_finales`: créditos o ajustes. Se conservan.
- `codigos_con_multiples_ubigeos`: prueba de que el código es un correlativo.
- `filas_ubigeo_fuera_puno`
- `ubigeos_con_multiples_provincias`
- `filas_geo_incoherente`
- `fecha_alta_pre1950`
- `fecha_alta_1908_09_27`

## 7. Relación con otros documentos

- El diccionario del conjunto de datos Parquet está en `preprocesamiento.md`, sección 6.3.
- La explicación de los hallazgos está en `preprocesamiento.md`, sección 7.
- El reporte se genera con el código de la última celda de `02_silver.ipynb`.

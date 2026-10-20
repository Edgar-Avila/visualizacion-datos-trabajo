# Preprocesamiento de datos de Electro Puno S.A.A.

Este documento usa un estilo técnico simplificado. Las reglas se basan en el
estándar ASD-STE100 y se adaptan al español. Las oraciones son cortas. Cada
oración tiene una idea. Los términos son siempre los mismos.

## 1. Objetivo

El objetivo es preparar los datos de consumo eléctrico para su análisis.

El proyecto tiene dos etapas:

1. La descarga de los archivos crudos.
2. La limpieza y la unión de los datos.

El resultado es un conjunto de datos limpio y consistente.

## 2. Términos

| Término | Significado |
|---|---|
| Suministro | Un cliente y su punto de conexión. También se llama "cliente". |
| Periodo | El mes de facturación. El formato es AAAAMM. Ejemplo: 202301. |
| Consumo | La energía eléctrica en kWh. |
| Facturación | El monto en soles (S/.). |
| Capa bronze | La carpeta con los archivos crudos, sin cambios. |
| Capa silver | La carpeta con los datos limpios y unidos. |
| Granularidad | El nivel de detalle de una fila. Vea la sección 6. |
| Correlativo | El número de fila dentro de un periodo. No identifica al suministro. |
| Parquet | Un formato de archivo comprimido para datos. |

## 3. Fuente de datos

Los datos vienen del portal Datos Abiertos del Perú. El nombre del portal es
`datosabiertos.gob.pe`.

El conjunto se llama "Consumo de energía eléctrica de los clientes de Electro
Puno S.A.A.".

Los datos cubren desde enero de 2023 hasta agosto de 2026.

## 4. Estructura de carpetas

La carpeta `preprocesamiento` tiene esta estructura:

```
preprocesamiento/
├── 01_descarga_bronze.ipynb    Descarga los archivos crudos.
├── 02_silver.ipynb             Limpia y une los datos.
├── bronze/                     Archivos crudos. No se editan.
├── silver/                     Datos limpios y unidos.
└── docs/                       Documentos del proyecto.
```

## 5. Paso 1: descarga de datos (capa bronze)

El notebook `01_descarga_bronze.ipynb` descarga los archivos.

El notebook hace estas tareas:

1. Crea la carpeta `bronze`.
2. Descarga 44 archivos de datos y 2 archivos de apoyo.
3. Guarda cada archivo con un nombre normalizado.
4. Crea el archivo `bronze/_manifest.csv` con la lista de las descargas.

El nombre normalizado usa el formato `ELPU_<AAAA-MM>.<ext>`. Ejemplo:
`ELPU_2023-01.csv`.

La descarga es repetible. Si un archivo ya existe, el notebook no lo descarga
otra vez.

El resultado son 46 archivos. El peso total es de 503 MB.

## 6. Paso 2: limpieza y unión (capa silver)

El notebook `02_silver.ipynb` limpia y une los datos.

El notebook procesa un archivo a la vez. Así el uso de memoria es bajo. El
notebook usa la herramienta DuckDB.

### 6.1 Problemas de los datos crudos

Los archivos crudos tienen estos problemas:

| Problema | Detalle |
|---|---|
| Varios esquemas | Se encontraron 3 esquemas con nombres de columna diferentes. Además hay 1 archivo en Excel y 1 archivo sin cabecera. |
| Codificación mixta | Las cabeceras usan cp1252. El cuerpo usa cp850 para la letra "eñe". Algunos archivos usan UTF-8. |
| Formato de Excel | El archivo de diciembre de 2024 tiene una fila vacía al inicio. |
| Dos granularidades | Los datos de 2026 tienen un detalle diferente. Vea la sección 6.4. |
| Código correlativo | El campo `codigo_cliente` es un correlativo por archivo. No identifica al suministro. Vea la sección 6.4. |
| Geografía incoherente | El `ubigeo` no siempre coincide con departamento, provincia y distrito. |
| Fechas centinela | Hay `fecha_alta` con valores imposibles. Ejemplo: 1908-09-27. |

### 6.2 Reglas de limpieza

El notebook aplica estas reglas:

1. Convierte todos los esquemas a un esquema canónico único.
2. Repara el texto con codificación mixta.
3. Establece las fechas en formato de fecha.
4. Rellena el código UBIGEO con ceros a la izquierda. El largo es de 6 dígitos.
5. Convierte el texto a mayúsculas. Borra los espacios al inicio y al final.
6. Convierte los números a números decimales.
7. Marca el periodo como un número entero.
8. Agrega la columna `source_file`. Esta columna guarda el archivo de origen.

### 6.3 Esquema canónico

Todas las filas tienen estas columnas:

| Columna | Tipo | Descripción |
|---|---|---|
| codigo_cliente | entero | Correlativo de fila en el periodo. No identifica al suministro entre meses. Vea la sección 6.4. |
| ubigeo | texto | Código de ubicación del INEI. Tiene 6 dígitos. |
| departamento | texto | Departamento del suministro. |
| provincia | texto | Provincia del suministro. |
| distrito | texto | Distrito del suministro. |
| fecha_alta | fecha | Fecha de instalación del suministro. |
| tarifa | texto | Tarifa del cliente. Ejemplo: BT5B. |
| periodo | entero | Mes de facturación. Formato AAAAMM. |
| consumo_kwh | decimal | Consumo de energía en kWh. |
| facturacion_soles | decimal | Monto facturado en soles. |
| estado_cliente | texto | Estado del suministro. Ejemplo: NORMAL. |
| fecha_corte | fecha | Fecha de generación del dato. |
| clientes | entero | Número de clientes en la fila. Vea la sección 6.4. |

### 6.4 Granularidad de los datos

Los datos tienen dos granularidades:

- Desde enero de 2023 hasta diciembre de 2025, una fila es un suministro. El
  campo `codigo_cliente` es un correlativo dentro del archivo. No sirve para
  seguir un suministro entre meses.
- Desde enero de 2026 hasta agosto de 2026, una fila es un grupo de
  suministros. El campo `clientes` tiene el número de suministros del grupo. El
  campo `codigo_cliente` también es un correlativo.

El `codigo_cliente` se repite con distinto significado. Por ejemplo, el código
`206371` aparece con 18 ubigeos diferentes. Por eso no se debe usar como clave
de cliente.

Por esta razón, el notebook guarda los dos grupos en archivos separados. No se
deben mezclar en una sola tabla.

### 6.5 Duplicados y errores

El notebook hace estas tareas:

1. Busca las filas con errores. Mueve estas filas al archivo
   `silver/_rechazados.parquet`.
2. Busca las filas duplicadas. El par (codigo_cliente, periodo) debe ser único.
3. Borra los duplicados. Conserva la fila del archivo cuyo nombre coincide con
   el periodo del dato.

## 7. Hallazgos de calidad

El análisis encontró estos puntos:

1. El portal publicó archivos duplicados. El archivo de junio de 2024 es una
   copia del archivo de febrero de 2024. El archivo de febrero de 2025 es una
   copia del archivo de junio de 2025.
2. Por el punto 1, no existe data real de junio de 2024 ni de febrero de 2025.
3. El notebook borró 697.626 filas duplicadas. Para el periodo 202506, conservó
   el archivo `ELPU_2025-06.zip`, que es el archivo correcto.
4. Hay 18.783 filas con valores negativos. Estos valores son créditos o ajustes.
   El notebook los conserva. No son errores de formato.
5. El campo `codigo_cliente` es un correlativo en los 34 periodos de 2023 a
   2025. Hay 261.109 códigos que aparecen con más de un ubigeo. No se debe usar
   para seguir un suministro en el tiempo.
6. Hay 66 filas con un ubigeo fuera de Puno. Ejemplo: `150101` y `150140` son
   ubigeos de Lima.
7. Hay 37 ubigeos con más de una provincia. Ejemplo: el ubigeo `210101` aparece
   con 12 provincias y 50 distritos.
8. Hay 112.269 filas con una geografía que no coincide con el ubigeo dominante.
9. Hay 21.998 filas con `fecha_alta` anterior a 1950. De estas, 20.690 tienen la
   fecha `1908-09-27`. Son fechas centinela.
10. El campo `estado_cliente` tiene el valor `NORMAL` en todas las filas. No
    aporta información.
11. Hay 110.198 filas con consumo mayor que cero y facturación igual a cero. La
    mayoría está en los meses 2023-02 a 2023-05.
12. Las tarifas `BT5A` y `BT5D` existen en los datos, pero no figuran en el
    diccionario del portal.
13. No hay valores nulos en los campos obligatorios.
14. No hay códigos UBIGEO inválidos (formato de 6 dígitos).
15. Todos los archivos se leyeron sin error.
16. La carpeta `silver` no tiene caracteres `¥`. El notebook reparó el texto de
    los distritos `NUÑOA` y `MUÑANI` del archivo de Excel de 2024-12.

## 8. Salidas

La carpeta `silver` tiene estos archivos:

| Archivo | Filas | Contenido |
|---|---|---|
| `consumo_clientes.parquet` | 11.782.755 | Serie de 2023-01 a 2025-12. Una fila por correlativo y periodo. |
| `consumo_agregado.parquet` | 74.485 | Serie de 2026-01 a 2026-08. Filas agregadas. |
| `resumen_mensual.parquet` | 42 | Totales por periodo. Une las dos granularidades. |
| `_rechazados.parquet` | 0 | Filas descartadas por los controles. |
| `_reporte_silver.json` | - | Reporte de los controles de calidad. |

El archivo `resumen_mensual.parquet` tiene estas columnas: `periodo`, `anio`,
`mes`, `granularidad`, `n_suministros`, `consumo_kwh_total`,
`facturacion_soles_total` y `consumo_kwh_promedio`.

## 9. Cómo ejecutar el proceso

Siga estos pasos en orden:

1. Abra el notebook `01_descarga_bronze.ipynb`.
2. Ejecute todas las celdas. Espere la descarga de los archivos.
3. Abra el notebook `02_silver.ipynb`.
4. Ejecute todas las celdas. Espere la limpieza y la unión.

Los dos notebooks usan el entorno de conda `visual`.

## 10. Notas técnicas

1. El entorno `visual` no tenía la librería `pyarrow`. Por eso el proyecto usa
   DuckDB para escribir los archivos Parquet.
2. El notebook `02_silver.ipynb` guarda los datos intermedios en la carpeta
   `silver/_parts`. Esta carpeta contiene un archivo por periodo.
3. El archivo `.gitignore` excluye las carpetas `bronze` y `silver`. Los datos
   se pueden generar otra vez con los dos notebooks.

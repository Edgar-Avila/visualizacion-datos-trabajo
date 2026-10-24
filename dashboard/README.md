# Dashboard de consumo eléctrico · Electro Puno S.A.A.

Aplicación local interactiva para explorar los datos del proyecto. Está construida con Python, Dash y Plotly. El código no modifica los notebooks ni los datos de preprocesamiento.

## Requisitos y ejecución

Desde la raíz del repositorio:

```powershell
python -m venv .venv
.venv\Scripts\Activate.ps1
python -m pip install -r dashboard\requirements.txt
python dashboard\app.py
```

Abra <http://127.0.0.1:8050>. La primera carga agrega las tablas con DuckDB y puede tardar un momento; las lecturas quedan cacheadas en memoria mientras corre el proceso. Se requieren los archivos `preprocesamiento/silver/consumo_clientes.parquet`, `consumo_agregado.parquet`, `resumen_mensual.parquet` y `analisis/peru_distrital_simple.geojson`. Si falta alguno, la página presenta el archivo que debe restaurarse.

## Vistas

- **Resumen:** indicadores, evolución y ranking provincial.
- **Evolución:** media móvil, comparación interanual y mapa de calor mes-año.
- **Mapa:** consumo, promedio por suministro-mes, suministros-mes o facturación por distrito. Al seleccionar un distrito, las demás vistas se actualizan.
- **Tarifas y perfiles:** comparación por tarifa y distribuciones de detalle individual.
- **Distribuciones:** histograma y relación consumo-facturación sobre una muestra reproducible de hasta 60.000 filas del periodo detallado.
- **Insights:** hallazgos de calidad y recomendaciones basadas en las limitaciones documentadas por el análisis.

Los filtros globales permiten elegir periodo, provincia, distrito y tarifa; se despliegan con el botón **+ FILTROS**. La tabla inferior se puede ordenar/filtrar y exportar como CSV agregado según los filtros.

## Decisiones sobre los datos

- `consumo_clientes.parquet` cubre 2023–2025 y tiene una fila por suministro-mes. El campo `codigo_cliente` se reinicia como correlativo; no se usa para seguir clientes.
- `consumo_agregado.parquet` cubre enero–agosto de 2026 y `clientes` indica el número de suministros representado por cada fila. El dashboard pondera los conteos con ese campo y no dibuja distribuciones individuales para 2026.
- El cruce inicial del mapa usa `ubigeo` con `properties.IDDIST`. Para UBIGEO sin geometría se intenta provincia+distrito, normalizados a mayúsculas sin tildes y con espacios consolidados. La nota del mapa muestra cuántos códigos aún no tienen polígono; los registros siguen disponibles en la tabla.
- El código UBIGEO se conserva para identificar el polígono cuando existe. La documentación de preprocesamiento advierte que algunos nombres contradicen al UBIGEO, por lo que el mapa puede reflejar problemas de calidad de origen.
- Los meses sin archivo (junio de 2024 y febrero de 2025) se representan como huecos, nunca como cero.
- Las distribuciones usan una muestra aleatoria determinista de la tabla de detalle. Son indicativas de forma y no sustituyen estadísticas exactas ni reflejan 2026.
- El notebook de perfiles calcula grupos con K-means durante su ejecución, pero el repositorio no contiene etiquetas de grupo persistidas. Esta app no inventa asignaciones: presenta las distribuciones y comparaciones por tarifa disponibles, y describe el alcance correcto de los perfiles suministro-mes/distrito.
- El resumen mensual mezcla detalle y agregado para comparaciones de totales. Los indicadores de número de suministros son conteos por periodo, no clientes únicos en varios meses.

## Estructura

`app.py` define la interfaz y callbacks; `data_loader.py` carga/agrega/cachea Parquet y GeoJSON; `calculos.py` centraliza filtros e indicadores; `assets/styles.css` contiene los estilos; `requirements.txt` lista dependencias.

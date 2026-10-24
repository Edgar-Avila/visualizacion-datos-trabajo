"""Carga, agregación y cacheo en memoria de los datos del proyecto."""
from functools import lru_cache
import json
import re
import unicodedata
from pathlib import Path

import duckdb
import pandas as pd

ROOT = Path(__file__).resolve().parents[1]
SILVER = ROOT / "preprocesamiento" / "silver"
GEO_PATH = ROOT / "analisis" / "peru_distrital_simple.geojson"


def normalizar(valor):
    texto = unicodedata.normalize("NFKD", str(valor or ""))
    texto = "".join(c for c in texto if not unicodedata.combining(c))
    return re.sub(r"\s+", " ", texto).strip().upper()


@lru_cache(maxsize=1)
def cargar_datos():
    """Lee los Parquet una vez y genera cubos compactos para las vistas."""
    faltan = [str(p) for p in [SILVER / "consumo_clientes.parquet",
                               SILVER / "consumo_agregado.parquet",
                               SILVER / "resumen_mensual.parquet", GEO_PATH] if not p.exists()]
    if faltan:
        raise FileNotFoundError("No se encontraron los archivos requeridos: " + ", ".join(faltan))
    cli = (SILVER / "consumo_clientes.parquet").as_posix()
    agr = (SILVER / "consumo_agregado.parquet").as_posix()
    con = duckdb.connect()
    # Se combinan conteos ponderados. No se interpreta codigo_cliente como ID.
    cubo = con.execute(f"""
        WITH todo AS (
          SELECT periodo, ubigeo, departamento, provincia, distrito, tarifa,
                 'detalle' granularidad, 1::BIGINT n,
                 consumo_kwh, facturacion_soles
          FROM read_parquet('{cli}')
          UNION ALL
          SELECT periodo, ubigeo, departamento, provincia, distrito, tarifa,
                 'agregado' granularidad, clientes::BIGINT n,
                 consumo_kwh, facturacion_soles
          FROM read_parquet('{agr}')
        )
        SELECT periodo, periodo//100 anio, periodo%100 mes, ubigeo,
               departamento, provincia, distrito, tarifa, granularidad,
               SUM(n)::BIGINT suministros, SUM(consumo_kwh) consumo_kwh,
               SUM(facturacion_soles) facturacion_soles,
               SUM(CASE WHEN consumo_kwh=0 THEN n ELSE 0 END)::BIGINT suministros_cero,
               COUNT(*) filas
        FROM todo GROUP BY ALL
    """).df()
    resumen = pd.read_parquet(SILVER / "resumen_mensual.parquet")
    # Muestra reproducible solo para visualizaciones de forma. El detalle individual no
    # se presenta para 2026 porque los Parquet de ese año ya vienen agregados.
    muestra = con.execute(f"""
      SELECT periodo, ubigeo, tarifa, provincia, consumo_kwh, facturacion_soles
      FROM read_parquet('{cli}') USING SAMPLE reservoir(60000 ROWS) REPEATABLE (37)
    """).df()
    con.close()
    muestra["ubigeo"] = muestra.ubigeo.astype(str).str.zfill(6)
    with GEO_PATH.open(encoding="utf-8") as f:
        geo = json.load(f)
    # Set an explicit GeoJSON feature id for Plotly's location lookup.
    for feature in geo.get("features", []):
        feature["id"] = str(feature.get("properties", {}).get("IDDIST", "")).zfill(6)
    geo_names = {}
    geo_labels = {}
    for feature in geo["features"]:
        p = feature.get("properties", {})
        code = str(p.get("IDDIST", "")).zfill(6)
        geo_names[(normalizar(p.get("NOMBPROV")), normalizar(p.get("NOMBDIST")))] = code
        geo_labels[code] = (str(p.get("NOMBPROV", "")).strip(), str(p.get("NOMBDIST", "")).strip())
    cubo["ubigeo"] = cubo.ubigeo.astype(str).str.zfill(6)
    cubo["periodo_txt"] = cubo.periodo.astype(str).str[:4] + "-" + cubo.periodo.astype(str).str[4:]
    cubo["geo_id"] = cubo.ubigeo
    geo_ids = {str(ft.get("properties", {}).get("IDDIST", "")).zfill(6) for ft in geo["features"]}
    # Fallback por nombres normalizados para los UBIGEO no presentes en el GeoJSON.
    cubo["geo_id"] = cubo.apply(
        lambda r: geo_names.get((normalizar(r.provincia), normalizar(r.distrito)), r.geo_id)
        if r.geo_id not in geo_ids
        else r.geo_id, axis=1)
    cubo["geo_provincia"] = cubo.geo_id.map(lambda code: geo_labels.get(code, (None, None))[0])
    cubo["geo_distrito"] = cubo.geo_id.map(lambda code: geo_labels.get(code, (None, None))[1])
    cubo["geo_provincia"] = cubo.geo_provincia.fillna(cubo.provincia)
    cubo["geo_distrito"] = cubo.geo_distrito.fillna(cubo.distrito)
    cubo["nombre_geo"] = cubo.geo_provincia.astype(str) + " · " + cubo.geo_distrito.astype(str)
    faltantes = sorted(set(cubo.loc[~cubo.geo_id.isin(geo_ids), "ubigeo"]))
    return {"cubo": cubo, "resumen": resumen, "muestra": muestra, "geo": geo,
            "ubigeos_sin_mapa": faltantes}


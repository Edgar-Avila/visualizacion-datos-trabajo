"""Funciones comunes de filtrado e indicadores para el dashboard."""
import pandas as pd


def filtrar(cubo, fechas=None, provincias=None, distritos=None, tarifas=None):
    d = cubo
    if fechas and all(fechas):
        d = d[d.periodo_txt.between(fechas[0][:7], fechas[1][:7])]
    if provincias:
        d = d[d.provincia.isin(provincias)]
    if distritos:
        d = d[d.nombre_geo.isin(distritos)]
    if tarifas:
        d = d[d.tarifa.isin(tarifas)]
    return d


def indicadores(d):
    if d.empty:
        return {"consumo": 0, "clientes": 0, "promedio": 0, "monto": 0, "provincia": "—", "distrito": "—"}
    consumo, clientes, monto = d.consumo_kwh.sum(), d.suministros.sum(), d.facturacion_soles.sum()
    loc = d.groupby("nombre_geo", observed=True).consumo_kwh.sum()
    prov = d.groupby("provincia", observed=True).consumo_kwh.sum()
    return {"consumo": consumo, "clientes": clientes, "promedio": consumo / clientes if clientes else 0,
            "monto": monto, "provincia": prov.idxmax() if len(prov) else "—",
            "distrito": loc.idxmax() if len(loc) else "—"}


def serie_mensual(d):
    return d.groupby(["periodo", "periodo_txt", "granularidad"], observed=True)[
        ["consumo_kwh", "facturacion_soles", "suministros"]].sum().reset_index().sort_values("periodo")


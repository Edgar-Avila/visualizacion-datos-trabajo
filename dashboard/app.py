"""Dashboard interactivo de consumo eléctrico de Electro Puno."""
from dash import Dash, Input, Output, State, dcc, html, dash_table, no_update
import dash_bootstrap_components as dbc
import pandas as pd
import plotly.express as px
import plotly.graph_objects as go
from plotly.subplots import make_subplots

from data_loader import cargar_datos
from calculos import filtrar, indicadores, serie_mensual

try:
    DATA = cargar_datos()
    CUBO, RESUMEN, MUESTRA, GEO = DATA["cubo"], DATA["resumen"], DATA["muestra"], DATA["geo"]
    LOAD_ERROR = None
except Exception as exc:  # Mensaje útil en pantalla si faltan datos/dependencias.
    CUBO = RESUMEN = MUESTRA = GEO = None
    LOAD_ERROR = str(exc)

COLORS = {"blue": "#176B87", "mint": "#64CCC5", "gold": "#F4B942", "ink": "#17313B"}
EMPTY = go.Figure().add_annotation(text="Sin datos para los filtros seleccionados", showarrow=False)


def layout_fig(fig, height=360):
    fig.update_layout(template="plotly_white", height=height, margin=dict(l=12, r=12, t=48, b=20),
                      font=dict(family="Inter, Segoe UI, sans-serif", color=COLORS["ink"]),
                      paper_bgcolor="rgba(0,0,0,0)", plot_bgcolor="rgba(0,0,0,0)")
    return fig


def money(x):
    return f"S/ {x:,.0f}"


def card(title, ident, unit=""):
    return dbc.Card(dbc.CardBody([html.Div(title, className="kpi-label"),
                                  html.Div(id=ident, className="kpi-value"),
                                  html.Div(unit, className="kpi-unit")]), className="kpi-card h-100")


def panel(title, graph):
    return dbc.Card(dbc.CardBody([html.H5(title, className="panel-title"), dcc.Graph(id=graph, config={"displayModeBar": False})]), className="panel-card")


if LOAD_ERROR:
    app = Dash(__name__)
    app.layout = dbc.Container([html.H2("No se pudo cargar el dashboard"), html.P(LOAD_ERROR)], className="py-5")
else:
    periodos = sorted(CUBO.periodo_txt.unique())
    provincias = sorted(CUBO.provincia.dropna().unique())
    tarifas = sorted(CUBO.tarifa.dropna().unique())
    app = Dash(__name__, external_stylesheets=[dbc.themes.BOOTSTRAP])
    app.title = "Energía Electro Puno · Dashboard"
    app.layout = dbc.Container([
        dcc.Store(id="distrito-mapa"), dcc.Download(id="download-csv"),
        dbc.Row([
            dbc.Col([html.Div([html.Div("ELECTRO PUNO · DATOS PARA DECIDIR", className="eyebrow"),
                              html.H1("Consumo eléctrico", className="hero-title"),
                              html.P("Una lectura integrada de consumo, cartera y facturación", className="hero-sub")])], md=8),
            dbc.Col(html.Div([html.Span("COBERTURA", className="coverage-label"), html.Strong("ENE 2023 — AGO 2026"),
                              html.Small("Jun-2024 y feb-2025 sin archivo")], className="coverage-box"), md=4)
        ], className="hero align-items-center g-3"),
        dbc.Row(dbc.Col(dbc.Button("+ FILTROS", id="toggle-filtros", n_clicks=0,
                                  outline=True, color="primary", className="filter-toggle"), width="auto"),
                className="mb-3"),
        dbc.Collapse(dbc.Card(dbc.CardBody([
            dbc.Row([
                dbc.Col([html.Label("Desde", className="filter-label"), dcc.Dropdown(periodos, periodos[0], id="desde", clearable=False)], md=2),
                dbc.Col([html.Label("Hasta", className="filter-label"), dcc.Dropdown(periodos, periodos[-1], id="hasta", clearable=False)], md=2),
                dbc.Col([html.Label("Provincia", className="filter-label"), dcc.Dropdown(provincias, id="provincia", multi=True, placeholder="Todas")], md=3),
                dbc.Col([html.Label("Distrito", className="filter-label"), dcc.Dropdown(id="distrito", multi=True, placeholder="Todos")], md=3),
                dbc.Col([html.Label("Tarifa", className="filter-label"), dcc.Dropdown(tarifas, id="tarifa", multi=True, placeholder="Todas")], md=2),
            ], className="g-2 align-items-end"),
            dbc.Row([dbc.Col(dbc.Button("Restablecer filtros", id="reset", outline=True, color="secondary", size="sm"), width="auto"),
                     dbc.Col(html.Span(id="filtro-status", className="filter-status"), className="align-self-center")], className="mt-3 g-2")
        ]), className="filter-card"), id="filtros-collapse", is_open=False, className="mb-4"),
        dbc.Row([
            dbc.Col(card("Consumo ttal", "kpi-consumo", "kWh")),
            dbc.Col(card("Suministros-mes", "kpi-clientes", "conteo ponderado")),
            dbc.Col(card("Consumo por suministro-mes", "kpi-promedio", "kWh")),
            dbc.Col(card("Facturación", "kpi-monto", "Soles · S/")),
            dbc.Col(card("Cambio vs. periodo previo", "kpi-cambio", "% consumo")),
        ], className="g-3 mb-4 row-cols-1 row-cols-sm-2 row-cols-lg-5"),
        dcc.Tabs(id="tabs", value="resumen", className="tabs", children=[
            dcc.Tab(label="Resumen", value="resumen", children=[dbc.Row([
                dbc.Col(panel("Evolución del consumo y la facturación", "serie-resumen"), md=8),
                dbc.Col(panel("Consumo por provincia", "provincia-chart"), md=4)], className="g-3 pt-3"),
                dbc.Row(dbc.Col(html.Div(id="resumen-insight", className="insight-strip")), className="mt-3")]),
            dcc.Tab(label="Evolución", value="evolucion", children=[dbc.Row([
                dbc.Col(panel("Tendencia mensual y media móvil de 3 meses", "serie-tiempo"), md=8),
                dbc.Col(panel("Variación interanual del consumo", "yoy-chart"), md=4)], className="g-3 pt-3"),
                dbc.Row(dbc.Col(panel("Estacionalidad · mes × año", "heatmap")), className="mt-3")]),
            dcc.Tab(label="Mapa", value="mapa", children=[dbc.Row([
                dbc.Col([dbc.Label("Métrica territorial"), dcc.Dropdown([{"label": x, "value": y} for x,y in [
                    ("Consumo total (kWh)","consumo_kwh"),("Consumo por suministro-mes", "promedio"),
                    ("Suministros-mes", "suministros"),("Facturación (S/)","facturacion_soles")]], "consumo_kwh", id="map-metric", clearable=False),
                    dcc.Graph(id="mapa-chart", config={"displayModeBar": False}),
                    html.Small("Haz clic en un distrito para filtrar todas las vistas.", className="muted")], md=8, className="panel-card p-3"),
                dbc.Col(panel("Distritos · mayor y menor consumo", "ranking-distritos"), md=4)], className="g-3 pt-3"),
                dbc.Row(dbc.Col(html.Div(id="mapa-nota", className="insight-strip")), className="mt-3")]),
            dcc.Tab(label="Tarifas y perfiles", value="tarifas", children=[dbc.Row([
                dbc.Col(panel("Consumo y facturación por tarifa", "tarifa-chart"), md=7),
                dbc.Col(panel("Perfiles de consumo individual · detalle 2023–2025", "perfil-chart"), md=5)], className="g-3 pt-3"),
                dbc.Row(dbc.Col(html.Div("El análisis del proyecto define perfiles de suministro-mes y distrito, pero no guarda etiquetas K-means en los Parquet. Esta vista compara distribuciones observadas por tarifa; no asigna grupos que no estén persistidos. codigo_cliente es un correlativo, así que no permite seguir clientes en el tiempo.", className="insight-strip")), className="mt-3")]),
            dcc.Tab(label="Distribuciones", value="distribuciones", children=[dbc.Row([
                dbc.Col(panel("Distribución del consumo individual (muestra reproducible)", "histograma"), md=7),
                dbc.Col(panel("Relación consumo–facturación", "scatter"), md=5)], className="g-3 pt-3"),
                dbc.Row(dbc.Col(panel("Correlación de variables principales · muestra", "correlacion")), className="g-3 mt-1"),
                dbc.Row(dbc.Col(html.Div(id="estadisticas", className="insight-strip")), className="mt-3")]),
            dcc.Tab(label="Insights", value="insights", children=[dbc.Row(dbc.Col(html.Div([
                html.H3("Hallazgos y decisiones"), html.P("Los indicadores responden a los filtros globales."), html.Div(id="insight-dinamico"),
                html.Hr(), html.Ul([
                    html.Li("La serie mensual tiene dos periodos ausentes: junio de 2024 y febrero de 2025. Trátalos como faltantes, no como consumo cero."),
                    html.Li("2026 contiene datos agrupados. Totales y suministros son comparables; distribuciones por cliente solo corresponden al detalle 2023–2025."),
                    html.Li("Los negativos se conservan como posibles créditos o ajustes. Conviene revisarlos por separado antes de atribuirlos a errores."),
                    html.Li("El campo estado_cliente es NORMAL en todas las filas y no segmenta la cartera."),
                    html.Li("Recomendación: solicitar un identificador persistente de suministro y corregir inconsistencias de UBIGEO/nombres en origen.")
                ])], className="insight-page p-4")), className="pt-3")]),
        ]),
        dbc.Row(dbc.Col([dash_table.DataTable(id="tabla", page_size=10, sort_action="native", filter_action="native",
                   style_table={"overflowX": "auto"}, style_cell={"fontFamily": "Segoe UI", "fontSize": 13, "padding": "9px", "textAlign": "left"},
                   style_header={"fontWeight": "700", "backgroundColor": "#eef5f5"}),
                   dbc.Button("Descargar datos agregados (CSV)", id="download-btn", color="primary", outline=True, className="mt-3")]), className="mt-4 mb-5"),
        html.Footer("Visualización de datos · UNAP · Fuente: Datos Abiertos del Perú / Electro Puno S.A.A.", className="footer")
    ], fluid=True, className="dashboard-shell")

    @app.callback(Output("filtros-collapse", "is_open"), Output("toggle-filtros", "children"),
                  Input("toggle-filtros", "n_clicks"), State("filtros-collapse", "is_open"),
                  prevent_initial_call=True)
    def toggle_filtros(_, is_open):
        abrir = not is_open
        return abrir, "- OCULTAR FILTROS" if abrir else "+ FILTROS"

    @app.callback(Output("distrito", "options"), Input("provincia", "value"))
    def opciones_distrito(provs):
        d = CUBO if not provs else CUBO[CUBO.geo_provincia.isin(provs)]
        choices = d[["geo_id", "nombre_geo"]].drop_duplicates().sort_values(["nombre_geo", "geo_id"])
        return [{"label": f"{r.nombre_geo} · {r.geo_id}", "value": r.geo_id} for r in choices.itertuples()]

    @app.callback(Output("desde", "value"), Output("hasta", "value"), Output("provincia", "value"),
                  Output("distrito", "value"), Output("tarifa", "value"), Output("distrito-mapa", "data"),
                  Input("reset", "n_clicks"), prevent_initial_call=True)
    def reset_filters(_):
        return periodos[0], periodos[-1], None, None, None, None

    @app.callback(Output("distrito-mapa", "data", allow_duplicate=True), Input("mapa-chart", "clickData"),
                  prevent_initial_call=True)
    def click_mapa(click):
        if not click or not click.get("points"): return None
        point = click["points"][0]
        loc = str(point.get("location") or ((point.get("customdata") or [""])[0]))
        rows = CUBO[CUBO.geo_id == loc]
        return loc if not rows.empty else None

    @app.callback(
        Output("kpi-consumo", "children"), Output("kpi-clientes", "children"), Output("kpi-promedio", "children"), Output("kpi-monto", "children"), Output("kpi-cambio", "children"),
        Output("filtro-status", "children"), Output("serie-resumen", "figure"), Output("provincia-chart", "figure"), Output("resumen-insight", "children"),
        Output("serie-tiempo", "figure"), Output("yoy-chart", "figure"), Output("heatmap", "figure"),
        Output("mapa-chart", "figure"), Output("ranking-distritos", "figure"), Output("mapa-nota", "children"),
        Output("tarifa-chart", "figure"), Output("perfil-chart", "figure"), Output("histograma", "figure"), Output("scatter", "figure"), Output("correlacion", "figure"),
        Output("estadisticas", "children"), Output("insight-dinamico", "children"),
        Output("tabla", "data"), Output("tabla", "columns"),
        Input("desde", "value"), Input("hasta", "value"), Input("provincia", "value"), Input("distrito", "value"), Input("tarifa", "value"),
        Input("distrito-mapa", "data"), Input("map-metric", "value"))
    def actualizar(desde, hasta, provs, dists, tars, clicked, metric):
        inicio, fin = sorted([desde, hasta]) if desde and hasta else (periodos[0], periodos[-1])
        d = CUBO[CUBO.periodo_txt.between(inicio, fin)]
        if provs: d = d[d.provincia.isin(provs)]
        seleccion_d = list(dists or [])
        if clicked and clicked not in seleccion_d: seleccion_d.append(clicked)
        if seleccion_d: d = d[d.geo_id.isin(seleccion_d)]
        if tars: d = d[d.tarifa.isin(tars)]
        if d.empty:
            return ("—", "—", "—", "—", "—", "Sin registros",
                    *[EMPTY for _ in range(7)], "No hay territorios en el filtro.",
                    *[EMPTY for _ in range(5)], "Sin datos.", "No hay registros con estos filtros.", [], [])
        k = indicadores(d); mensual = serie_mensual(d)
        totales_periodo = mensual.groupby("periodo_txt", as_index=False).consumo_kwh.sum().set_index("periodo_txt")
        cambio = "N/D"
        periodo_previo = (pd.Period(fin, freq="M") - 1).strftime("%Y-%m")
        if fin in totales_periodo.index and periodo_previo in totales_periodo.index:
            previo, actual = totales_periodo.loc[periodo_previo,"consumo_kwh"], totales_periodo.loc[fin,"consumo_kwh"]
            if previo != 0: cambio = f"{(actual / previo - 1) * 100:+.1f}%"
        base = mensual[mensual.granularidad.eq("detalle")]; agr = mensual[mensual.granularidad.eq("agregado")]
        fserie = go.Figure()
        for g, nombre, color in [(base,"Detalle",COLORS["blue"]),(agr,"Agregado",COLORS["gold"])]:
            if not g.empty:
                fserie.add_trace(go.Scatter(x=g.periodo_txt,y=g.consumo_kwh,name=f"Consumo · {nombre}",mode="lines+markers",line={"color":color}))
                fserie.add_trace(go.Scatter(x=g.periodo_txt,y=g.facturacion_soles,name=f"Facturación · {nombre}",mode="lines",yaxis="y2",line={"color":color,"dash":"dot"}))
        fserie.update_layout(title="Los meses faltantes aparecen como huecos", xaxis_title="Periodo", yaxis_title="Consumo (kWh)", yaxis2={"title":"Facturación (S/)","overlaying":"y","side":"right"}, legend={"orientation":"h","y":-0.25})
        prov = d.groupby("geo_provincia",as_index=False,observed=True).consumo_kwh.sum().nlargest(12,"consumo_kwh")
        fp = px.bar(prov,x="consumo_kwh",y="geo_provincia",orientation="h",labels={"consumo_kwh":"Consumo (kWh)","geo_provincia":"Provincia"},color_discrete_sequence=[COLORS["mint"]]).update_layout(yaxis={"categoryorder":"total ascending"})
        trend = mensual.groupby("periodo_txt",as_index=False).consumo_kwh.sum().sort_values("periodo_txt").set_index("periodo_txt")
        calendario = pd.period_range(inicio, fin, freq="M").astype(str)
        trend = trend.reindex(calendario)
        trend.index.name = "periodo_txt"
        trend = trend.reset_index()
        trend["media_3m"] = trend.consumo_kwh.rolling(3,min_periods=2).mean()
        ft = go.Figure([go.Scatter(x=trend.periodo_txt,y=trend.consumo_kwh,name="Consumo mensual",mode="lines+markers",line={"color":COLORS["blue"]}),go.Scatter(x=trend.periodo_txt,y=trend.media_3m,name="Media móvil 3 meses",line={"color":COLORS["gold"],"width":3})])
        cambios_mensuales = trend.consumo_kwh.pct_change(fill_method=None).dropna()
        if len(cambios_mensuales) >= 5:
            centro = cambios_mensuales.median()
            dispersion = 1.4826 * (cambios_mensuales - centro).abs().median()
            if dispersion > 0:
                idx_anomalias = cambios_mensuales[(cambios_mensuales-centro).abs() > 2.5*dispersion].index
                if len(idx_anomalias):
                    ft.add_trace(go.Scatter(x=trend.loc[idx_anomalias,"periodo_txt"],y=trend.loc[idx_anomalias,"consumo_kwh"],
                        mode="markers",name="Cambio inusual · MAD",marker={"color":"#d95d4f","size":10,"symbol":"diamond"}))
        ft.update_layout(xaxis_title="Periodo",yaxis_title="Consumo (kWh)")
        annual = trend.copy(); annual["anio"] = annual.periodo_txt.str[:4]; annual["mes"] = annual.periodo_txt.str[-2:].astype(int)
        annual["yoy"] = (annual.consumo_kwh / annual.consumo_kwh.shift(12) - 1) * 100
        fy = px.bar(annual,x="periodo_txt",y="yoy",labels={"periodo_txt":"Periodo","yoy":"Variación interanual (%)"},color_discrete_sequence=[COLORS["mint"]])
        mat = annual.pivot(index="anio",columns="mes",values="consumo_kwh").reindex(columns=range(1,13))
        fh = px.imshow(mat,aspect="auto",labels={"x":"Mes","y":"Año","color":"kWh"},color_continuous_scale="Teal")
        territory = d.groupby("geo_id",as_index=False,observed=True).agg(consumo_kwh=("consumo_kwh","sum"),facturacion_soles=("facturacion_soles","sum"),suministros=("suministros","sum"))
        labels = d.groupby("geo_id",as_index=False,observed=True).agg(nombre_geo=("nombre_geo","first"),provincia=("geo_provincia","first"))
        territory = territory.merge(labels,on="geo_id",how="left")
        territory["promedio"] = territory.consumo_kwh/territory.suministros.replace(0,pd.NA)
        mg = {"promedio":"promedio","consumo_kwh":"consumo_kwh","facturacion_soles":"facturacion_soles","suministros":"suministros"}.get(metric,"consumo_kwh")
        # Trazamos los anillos del GeoJSON directamente como polígonos geo. Así el
        # mapa no depende de un servicio externo de teselas ni de una clave remota.
        values = territory.set_index("geo_id")[mg].to_dict()
        lo, hi = territory[mg].min(), territory[mg].max()
        scale = px.colors.sequential.Tealgrn
        fm = go.Figure()
        for feature in GEO.get("features", []):
            props = feature.get("properties", {})
            code = str(feature.get("id", ""))
            if code not in values or pd.isna(values[code]):
                continue
            value = float(values[code])
            normalized = (value - lo) / (hi - lo) if hi > lo else .5
            fill = px.colors.sample_colorscale(scale, [normalized])[0]
            geom = feature.get("geometry", {})
            if not isinstance(geom, dict):
                continue
            polygons = [geom.get("coordinates", [])] if geom.get("type") == "Polygon" else geom.get("coordinates", [])
            label = territory.loc[territory.geo_id.eq(code), "nombre_geo"].iloc[0]
            for polygon in polygons:
                if not polygon:
                    continue
                ring = polygon[0]
                lon = [pt[0] for pt in ring]
                lat = [pt[1] for pt in ring]
                fm.add_trace(go.Scattergeo(lon=lon, lat=lat, mode="lines", fill="toself",
                    fillcolor=fill, line={"color":"white","width":.55}, name=label,
                    text=[f"{label}<br>{metric}: {value:,.2f}<br>UBIGEO: {code}"]*len(ring),
                    customdata=[[code]]*len(ring), hovertemplate="%{text}<extra></extra>", showlegend=False))
        fm.add_trace(go.Scattergeo(lon=[None,None],lat=[None,None],mode="markers",
            marker={"size":0,"color":[lo,hi],"cmin":lo,"cmax":hi,"colorscale":scale,"showscale":True,
                    "colorbar":{"title":metric,"thickness":14}},showlegend=False,hoverinfo="skip"))
        fm.update_geos(projection_type="mercator",showland=True,landcolor="#f2f6f5",
                       showcountries=True,countrycolor="#b8ccca",showcoastlines=True,coastlinecolor="#b8ccca",
                       center={"lon":-70.4,"lat":-15.2},projection_scale=120)
        fm.update_layout(height=540,margin={"l":0,"r":0,"t":20,"b":0},showlegend=False)
        extremos = pd.concat([territory.nlargest(8,"consumo_kwh").assign(grupo="Mayor consumo"),
                              territory.nsmallest(8,"consumo_kwh").assign(grupo="Menor consumo")]).drop_duplicates("geo_id")
        fr = px.bar(extremos.sort_values("consumo_kwh"),x="consumo_kwh",y="nombre_geo",orientation="h",color="grupo",
                    labels={"consumo_kwh":"Consumo (kWh)","nombre_geo":"Distrito","grupo":"Ranking"},
                    color_discrete_map={"Mayor consumo":COLORS["blue"],"Menor consumo":COLORS["gold"]}).update_layout(yaxis={"categoryorder":"total ascending"})
        bytar = d.groupby("tarifa",as_index=False,observed=True).agg(consumo_kwh=("consumo_kwh","sum"),facturacion_soles=("facturacion_soles","sum"),suministros=("suministros","sum"))
        fta = make_subplots(rows=1,cols=2,subplot_titles=("Consumo (kWh)","Facturación (S/)"),shared_yaxes=True)
        fta.add_trace(go.Bar(x=bytar.tarifa,y=bytar.consumo_kwh,name="Consumo",marker_color=COLORS["blue"]),row=1,col=1)
        fta.add_trace(go.Bar(x=bytar.tarifa,y=bytar.facturacion_soles,name="Facturación",marker_color=COLORS["gold"]),row=1,col=2)
        fta.update_layout(barmode="group",showlegend=False)
        sample = MUESTRA[MUESTRA.periodo.between(int(inicio.replace('-','')),int(fin.replace('-','')))]
        if tars: sample=sample[sample.tarifa.isin(tars)]
        if provs: sample=sample[sample.provincia.isin(provs)]
        if seleccion_d: sample=sample[sample.ubigeo.isin(seleccion_d)]
        sample=sample[sample.consumo_kwh>0]
        fprof=px.box(sample,x="tarifa",y="consumo_kwh",points=False,log_y=True,labels={"consumo_kwh":"Consumo (kWh, escala log)","tarifa":"Tarifa"},color_discrete_sequence=[COLORS["mint"]]) if not sample.empty else EMPTY
        fhist=px.histogram(sample,x="consumo_kwh",color="tarifa",nbins=45,log_x=True,labels={"consumo_kwh":"Consumo positivo (kWh, escala log)","count":"Observaciones de muestra"}) if not sample.empty else EMPTY
        sscatter=sample.sample(min(6000,len(sample)),random_state=7) if len(sample)>6000 else sample
        fsc=px.scatter(sscatter,x="consumo_kwh",y="facturacion_soles",color="tarifa",opacity=.5,log_x=True,labels={"consumo_kwh":"Consumo (kWh)","facturacion_soles":"Facturación (S/)"}) if not sscatter.empty else EMPTY
        correlacion = px.imshow(sample[["consumo_kwh","facturacion_soles"]].corr(),text_auto=".2f",zmin=-1,zmax=1,
            color_continuous_scale="RdBu_r",labels={"x":"Variable","y":"Variable","color":"Correlación"}) if len(sample)>1 else EMPTY
        stats = html.Div([html.Strong("Detalle 2023–2025 · muestra reproducible de hasta 60.000 filas. "),
                          f"n={len(sample):,}; mediana de consumo positivo={sample.consumo_kwh.median():,.2f} kWh; media={sample.consumo_kwh.mean():,.2f} kWh. Las distribuciones no incluyen 2026 agregado." if not sample.empty else "Sin datos individuales para esta selección."])
        msg = f"Mayor consumo del filtro: {k['distrito']} · {k['consumo']:,.0f} kWh. Provincia líder: {k['provincia']}."
        mapnote = f"Cruce por UBIGEO con fallback por provincia/distrito normalizados. UBIGEO sin polígono tras el fallback: {len(DATA['ubigeos_sin_mapa'])}."
        table = territory.sort_values("consumo_kwh",ascending=False).round(2)
        table = table.rename(columns={"geo_id":"UBIGEO","nombre_geo":"Distrito","provincia":"Provincia","consumo_kwh":"Consumo (kWh)","facturacion_soles":"Facturación (S/)","suministros":"Suministros-mes","promedio":"kWh/suministro-mes"})
        return (f"{k['consumo']:,.0f}",f"{k['clientes']:,.0f}",f"{k['promedio']:,.2f}",money(k['monto']),cambio,
                f"{len(d):,} celdas territorio × periodo × tarifa", layout_fig(fserie),layout_fig(fp),msg,layout_fig(ft),layout_fig(fy),layout_fig(fh),fm,layout_fig(fr),mapnote,
                layout_fig(fta),layout_fig(fprof),layout_fig(fhist),layout_fig(fsc),layout_fig(correlacion),stats,msg,table.to_dict("records"),[{"name":c,"id":c} for c in table.columns])

    @app.callback(Output("download-csv", "data"), Input("download-btn", "n_clicks"), State("desde", "value"), State("hasta", "value"), State("provincia", "value"), State("distrito", "value"), State("tarifa", "value"), prevent_initial_call=True)
    def descargar(_, desde, hasta, provs, dists, tars):
        inicio, fin = sorted([desde, hasta]); d=CUBO[CUBO.periodo_txt.between(inicio,fin)]
        if provs: d=d[d.provincia.isin(provs)]
        if dists: d=d[d.geo_id.isin(dists)]
        if tars: d=d[d.tarifa.isin(tars)]
        out=d.groupby(["periodo_txt","ubigeo","provincia","distrito","tarifa"],as_index=False,observed=True)[["suministros","consumo_kwh","facturacion_soles"]].sum()
        return dcc.send_data_frame(out.to_csv,"consumo_filtrado.csv",index=False,encoding="utf-8-sig")


if __name__ == "__main__":
    app.run(debug=False, host="127.0.0.1", port=8050)

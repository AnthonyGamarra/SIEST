from dash import html, dcc, register_page, Input, Output, callback

layout = html.Div([
    dcc.Location(id="ate-topicos-url", refresh=False),
    html.H4("Página de prueba de redirección"),
    html.Div(id="ate-topicos-msg", style={"marginTop": "8px", "color": "#0064AF", "fontSize": "16px"})
])

register_page(
    __name__,
    path_template="/dashboard_eme_prioridad_1/<codcas>",
    name="dashboard_eme_prioridad_1",
    layout=layout
)

@callback(
    Output("ate-topicos-msg", "children"),
    Input("ate-topicos-url", "pathname"),
    Input("ate-topicos-url", "search"),
)
def mostrar_prueba(pathname, search):
    codcas = pathname.rstrip("/").split("/")[-1] if pathname else "N/A"
    periodo = None
    if search:
        parts = dict(p.split("=", 1) for p in search.lstrip("?").split("&") if "=" in p)
        periodo = parts.get("periodo")
    return f"Redirección OK -> centro: {codcas}, periodo: {periodo or 'N/A'}"

def stat_card(title, data, width=3, height=2):
    return {
        "id": title.lower().replace(" ", "_"),
        "title": title,
        "width": width,
        "height": height,
        "type": "stats",
        "data": [{"label": part[0], "value": part[1]} for part in data]
    }

def graph_card(title, series, xAxis=[{"type": "time"}], yAxis=[{"type": "value"}], width=6, height=2):
    return {
        "id": title.lower().replace(" ", "_"),
        "title": title,
        "width": width,
        "height": height,
        "type": 'graph',
        "options": {
            'legend': {
                'selectedMode': True,
                'textStyle': {
                    'color': '#fff'
                },
            },
            "xAxis": xAxis,
            "yAxis": yAxis,
            "series": series,
        }
    }

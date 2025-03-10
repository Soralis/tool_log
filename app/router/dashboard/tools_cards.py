def stat_card(title, data, width=3, height=2):
    return {
        "id": title.lower().replace(" ", "_"),
        "title": title,
        "width": width,
        "height": height,
        "type": "stats",
        "data": [{"label": part[0], "value": part[1]} for part in data]
    }

def graph_card(title, data, graph_type="line", width=6, height=4):
    return {
        "id": title.lower().replace(" ", "_"),
        "title": title,
        "width": width,
        "height": height,
        "type": graph_type,
        "data": [
            {
                    "label": "Tool Life",
                    "data": data,
                    "borderColor": "rgb(75, 192, 192)",
                    "backgroundColor": "rgba(75, 192, 192, 0.5)",
                    "tension": 0.1,
                    "fill": True
                }
            ]
        }
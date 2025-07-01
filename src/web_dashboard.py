from fastapi import FastAPI, Request
from fastapi.responses import HTMLResponse
from jinja2 import Template
import aiosqlite
import os
import plotly.graph_objs as go

DATABASE_PATH = os.path.join(os.path.dirname(__file__), 'database', 'sounds_database.db')

app = FastAPI()

HTML_TEMPLATE = """
<!DOCTYPE html>
<html>
<head>
    <title>Статистика пользователей</title>
    <style>
        body { font-family: Arial, sans-serif; margin: 40px; }
        table { border-collapse: collapse; width: 60%; }
        th, td { border: 1px solid #ccc; padding: 8px; text-align: left; }
        th { background: #eee; }
    </style>
</head>
<body>
    <h2>Топ пользователей по запросам</h2>
    <table>
        <tr><th>#</th><th>User ID</th><th>Username</th><th>Requests</th><th>Last Request</th></tr>
        {% for row in stats %}
        <tr>
            <td>{{ loop.index }}</td>
            <td>{{ row[0] }}</td>
            <td>{{ row[1] or '' }}</td>
            <td>{{ row[2] }}</td>
            <td>{{ row[3] }}</td>
        </tr>
        {% endfor %}
    </table>
    {{ plotly_html|safe }}
</body>
</html>
"""


async def get_stats():
    async with aiosqlite.connect(DATABASE_PATH) as conn:
        cursor = await conn.execute(
            """
            SELECT user_id, username, requests_count, last_request
            FROM user_stats
            ORDER BY requests_count DESC, last_request DESC LIMIT 20
            """
        )
        return await cursor.fetchall()


def make_plotly_bar(stats):
    usernames = [row[1] if row[1] else str(row[0]) for row in stats]
    counts = [row[2] for row in stats]
    fig = go.Figure([go.Bar(x=usernames, y=counts)])
    fig.update_layout(title="Топ пользователей по запросам", xaxis_title="Пользователь", yaxis_title="Запросов")
    return fig.to_html(full_html=False, include_plotlyjs='cdn')


@app.get("/dashboard", response_class=HTMLResponse)
async def dashboard(request: Request):
    stats = await get_stats()
    plotly_html = make_plotly_bar(stats) if stats else ""
    template = Template(HTML_TEMPLATE)
    return template.render(stats=stats, plotly_html=plotly_html)

import markdown
from fastapi.templating import Jinja2Templates
from pathlib import Path

BASE_DIR = Path(__file__).parent / "templates"
templates = Jinja2Templates(directory=str(BASE_DIR))

# Register markdown filter: {{ content | markdown | safe }}
def md(text):
    return markdown.markdown(text, extensions=['fenced_code', 'tables'])
templates.env.filters["markdown"] = md

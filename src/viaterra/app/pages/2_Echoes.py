from viaterra.app.auth import require_owner
from viaterra.app.components.echoes_page import render_echoes

require_owner()
render_echoes()
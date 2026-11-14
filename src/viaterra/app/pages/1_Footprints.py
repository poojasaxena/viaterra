from viaterra.app.auth import require_owner
from viaterra.app.components.footprints_page import render_footprints

require_owner()
render_footprints()
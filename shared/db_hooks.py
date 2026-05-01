from shared.db import init_all, get_pool
from flask import g

def register_db_hooks(app):
    """Register DB initialization and teardown for a Flask app."""
    with app.app_context():
        init_all()

    @app.teardown_appcontext
    def close_db(exception):
        conn = g.pop("db_conn", None)
        if conn is not None:
            try:
                get_pool().putconn(conn)
            except Exception:
                pass

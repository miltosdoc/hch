"""Shared auth middleware for all HCH apps."""
import re, os
from functools import wraps
from flask import request, jsonify, session, g
from psycopg2 import pool
from psycopg2.extras import RealDictCursor
from werkzeug.security import check_password_hash

# Direct DB access for API key validation (no Flask context needed)
_API_POOL = None

def _get_api_pool():
    global _API_POOL
    if _API_POOL is None:
        _API_POOL = pool.ThreadedConnectionPool(1, 10, os.environ.get("DATABASE_URL", "postgresql://hch_user:hch_secure@db:5432/hch"))
    return _API_POOL

def validate_api_key(token):
    """Validate an API key token. Returns user dict or None."""
    try:
        conn = _get_api_pool().getconn()
        cur = conn.cursor(cursor_factory=RealDictCursor)
        # Fetch all active keys and check each hash
        cur.execute("""SELECT ak.*, u.username, u.is_admin 
                       FROM api_keys ak JOIN hch_users u ON ak.user_id = u.id 
                       WHERE ak.is_active AND u.is_active""")
        rows = cur.fetchall()
        for r in rows:
            if check_password_hash(r["key_hash"], token):
                cur.execute("UPDATE api_keys SET last_used = NOW() WHERE id = %s", (r["id"],))
                conn.commit()
                cur.close()
                _get_api_pool().putconn(conn)
                return {"id": r["user_id"], "username": r["username"], "is_admin": r["is_admin"]}
        cur.close()
        _get_api_pool().putconn(conn)
    except Exception as e:
        pass  # Log in production
    return None

def require_auth(f):
    """Decorator that requires either session auth or API key auth."""
    @wraps(f)
    def decorated_function(*args, **kwargs):
        # Check for API key in Authorization header
        auth_header = request.headers.get("Authorization", "")
        if auth_header.startswith("Bearer "):
            token = auth_header[7:]
            user = validate_api_key(token)
            if user:
                g.user = user
                g.auth_method = "api_key"
                return f(*args, **kwargs)
            return jsonify({"status": "error", "code": "unauthorized", "message": "Invalid API key"}), 401
        
        # Fall back to session auth (Flask-Login)
        from flask_login import current_user
        if not current_user.is_authenticated:
            if request.path.startswith("/api/"):
                return jsonify({"status": "error", "code": "unauthorized", "message": "Authentication required"}), 401
            from flask import redirect, url_for
            return redirect(url_for("login"))
        
        g.user = {"id": current_user.id, "username": current_user.username, "is_admin": current_user.is_admin}
        g.auth_method = "session"
        return f(*args, **kwargs)
    return decorated_function

def require_admin(f):
    """Decorator that requires admin privileges."""
    @wraps(f)
    @require_auth
    def decorated_function(*args, **kwargs):
        if not g.user.get("is_admin"):
            if request.path.startswith("/api/"):
                return jsonify({"status": "error", "code": "forbidden", "message": "Admin access required"}), 403
            from flask import flash, redirect, url_for
            flash("Behörighet saknas")
            return redirect(url_for("dashboard"))
        return f(*args, **kwargs)
    return decorated_function

def api_response(data, status=200):
    """Helper for consistent API responses."""
    return jsonify({"status": "ok", "data": data}), status

def api_error(code, message, status=400):
    """Helper for consistent API error responses."""
    return jsonify({"status": "error", "code": code, "message": message}), status

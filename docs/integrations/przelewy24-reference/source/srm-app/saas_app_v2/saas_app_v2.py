import reflex as rx
from starlette.requests import Request
from starlette.responses import JSONResponse
from .state import State
from .pages.dashboard import index

from .pages.mass_redirects import mass_redirects_page

from .product_state import ProductRedirectState
from .category_search_state import CategorySearchRedirectState
from .file_upload_state import FileUploadRedirectState

import sys
import os
sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), "..", "backend")))
import auth_manager
import db_manager

app = rx.App(
    stylesheets=[
        "https://fonts.googleapis.com/css2?family=Montserrat:wght@400;700;900&display=swap",
        "/styles.css",
    ],
)

app.add_page(
    index,
    route="/",
    title="Manager Przekierowań | Masowe 301",
    on_load=[
        State.check_login,
        State.clear_manual_data,
        CategorySearchRedirectState.clear_category_search_data,
        FileUploadRedirectState.clear_file_upload_data
    ]
)

app.add_page(mass_redirects_page, route="/mass", title="Manager Przekierowań | Masowe Przekierowania", on_load=State.check_login)

import secrets
from google.oauth2 import id_token
from google.auth.transport import requests as google_requests

GOOGLE_CLIENT_ID = "278936147990-it0126st7srntrhql53sq0ldu6ro9nsn.apps.googleusercontent.com"

async def google_verify(request: Request):
    data = await request.json()
    token = data.get('credential')

    if not token:
        return JSONResponse({"success": False, "error": "Google Credential required"}, status_code=400)

    try:
        idinfo = id_token.verify_oauth2_token(token, google_requests.Request(), GOOGLE_CLIENT_ID)
        email = idinfo['email']

        conn = db_manager.get_db_connection()
        cursor = conn.cursor()
        cursor.execute("SELECT * FROM users WHERE email = ?", (email,))
        user = cursor.fetchone()

        if not user:
            role = 'admin' if email == 'stas@admin.com' else 'client'
            temp_pw = secrets.token_hex(16)
            auth_manager.register_user(email, temp_pw, role=role)
            cursor.execute("SELECT * FROM users WHERE email = ?", (email,))
            user = cursor.fetchone()
            cursor.execute("INSERT INTO clients (user_id, shop_url, gsc_property_url) VALUES (?, ?, ?)",
                           (user['id'], 'https://pending.shoper.pl', 'https://pending.gsc.url'))
            conn.commit()

        import jwt, datetime
        jwt_token = jwt.encode({
            'user_id': user['id'],
            'email': user['email'],
            'role': user['role'],
            'exp': datetime.datetime.utcnow() + datetime.timedelta(hours=24)
        }, auth_manager.SECRET_KEY, algorithm="HS256")

        cursor.execute("SELECT id FROM clients WHERE user_id = ?", (user['id'],))
        client_row = cursor.fetchone()
        client_id = client_row['id'] if client_row else None
        conn.close()

        return JSONResponse({
            "success": True,
            "token": jwt_token,
            "role": user['role'],
            "email": user['email'],
            "client_id": client_id
        })
    except Exception as e:
        return JSONResponse({"success": False, "error": str(e)}, status_code=400)

async def login_api(request: Request):
    data = await request.json()
    email = data.get('email')
    password = data.get('password')

    success, token_or_msg, user = auth_manager.authenticate_user(email, password)
    if success:
        conn = db_manager.get_db_connection()
        cursor = conn.cursor()
        cursor.execute("SELECT id FROM clients WHERE user_id = ?", (user['id'],))
        client_row = cursor.fetchone()
        client_id = client_row['id'] if client_row else None
        conn.close()

        return JSONResponse({
            "success": True,
            "token": token_or_msg,
            "role": user['role'],
            "email": user['email'],
            "client_id": client_id
        })
    return JSONResponse({"success": False, "error": token_or_msg}, status_code=401)

async def register_api(request: Request):
    data = await request.json()
    email = data.get('email')
    password = data.get('password')
    shop_url = data.get('shop_url') or 'https://pending.shoper.pl'
    property_url = data.get('property_url') or 'https://pending.gsc.url'

    if not all([email, password]):
        return JSONResponse({"success": False, "error": "All fields required"}, status_code=400)

    success, msg = auth_manager.register_user(email, password)
    if not success:
        return JSONResponse({"success": False, "error": msg}, status_code=400)

    conn = db_manager.get_db_connection()
    cursor = conn.cursor()
    cursor.execute("SELECT id FROM users WHERE email = ?", (email,))
    user_id = cursor.fetchone()['id']
    try:
        cursor.execute('''
        INSERT INTO clients (user_id, shop_url, gsc_property_url)
        VALUES (?, ?, ?)
        ''', (user_id, shop_url, property_url))
        conn.commit()
        return JSONResponse({"success": True, "message": "Account and shop registered successfully."})
    except Exception as e:
        return JSONResponse({"success": False, "error": str(e)}, status_code=400)
    finally:
        conn.close()

app._api.add_route("/api/auth/google-verify", google_verify, methods=["POST"])
app._api.add_route("/api/auth/login", login_api, methods=["POST"])
app._api.add_route("/api/auth/register", register_api, methods=["POST"])

# ─── Webhook Przelewy24 ─────────────────────────────────────────

async def payment_webhook(request: Request):
    """Webhook od P24 – weryfikuj i ustaw is_paid."""
    data = await request.json()
    session_id = data.get("sessionId", "")
    order_id   = data.get("orderId", 0)
    amount     = data.get("amount", 0)

    if not session_id or not order_id:
        return JSONResponse({"success": False}, status_code=400)

    verified = p24_manager.verify_transaction(session_id, order_id, amount)
    if verified:
        conn = db_manager.get_db_connection()
        cursor = conn.cursor()
        try:
            cursor.execute(
                "UPDATE payments SET status = 'completed' WHERE details = ?",
                (session_id,)
            )
            conn.commit()
        except Exception:
            pass
        finally:
            conn.close()
        return JSONResponse({"data": True, "responseCode": 0})
    return JSONResponse({"success": False, "error": "Verification failed"}, status_code=400)

app._api.add_route("/api/payment/status", payment_webhook, methods=["POST"])

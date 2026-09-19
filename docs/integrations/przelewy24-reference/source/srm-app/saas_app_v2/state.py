import reflex as rx
import sys
import os
import asyncio
import time
import io
import contextlib
import requests
import rxconfig

# Add backend to sys.path
backend_path = os.path.abspath(os.path.join(os.path.dirname(rxconfig.__file__), "backend"))
if backend_path not in sys.path:
    sys.path.append(backend_path)

# Add current dir to sys.path for local imports
current_dir = os.path.dirname(os.path.abspath(__file__))
if current_dir not in sys.path:
    sys.path.append(current_dir)

try:
    import shoper_core
    import gsc_auto_pilot
    import shoper_manual_logic
    import db_manager
except ImportError as e:
    print(f"❌ Backend Import Error: {e}")

class State(rx.State):
    """The app state."""
    # --- Shoper API Connection (isolated per session) ---
    shop_url: str = ""
    token: str = ""  # Shoper OAuth Bearer token

    @rx.var
    def is_authenticated(self) -> bool:
        return bool(self.login_token)

    # --- Identity & Session ---
    # Active identity (isolated per tab) - prevents "session hijack" across tabs
    email: str = ""
    login_token: str = ""

    # Persisted strings (LocalStorage) - only for auto-login / remembering user
    persisted_email: str = rx.LocalStorage(name="email")
    persisted_token: str = rx.LocalStorage(name="token")

    async def check_login(self):
        """Standard page entry logic (on_load)."""
        import asyncio
        await asyncio.sleep(0.3)  # Wait for LocalStorage to hydrate

        # 0. Auto-login from Shoper AppStore (one-time token in URL)
        from urllib.parse import urlparse, parse_qs
        raw_path = self.router.page.raw_path or ""
        parsed_qs = parse_qs(urlparse(raw_path).query)
        auto_token = parsed_qs.get("auto_token", [""])[0]
        if auto_token and not self.login_token:
            try:
                resp = await asyncio.to_thread(
                    requests.post,
                    "https://booster-engine.pl/api/srm-auth.php?action=auto_login",
                    json={"auto_token": auto_token},
                    timeout=5
                )
                if resp.status_code == 200:
                    data = resp.json()
                    if data.get("success"):
                        self.login_token = data["token"]
                        self.email = data["email"]
                        self.persisted_token = data["token"]
                        self.persisted_email = data["email"]
                        self.shop_url = data.get("shop_url", "")
                        self.token = data.get("access_token", "")  # OAuth token = ready Bearer
                        self.is_app_active = True
                        self.is_appstore_user = True
                        print(f"AUTO-LOGIN OK: {data['email']} → {self.shop_url}")
                        return  # Skip all other checks — user is authenticated
            except Exception as e:
                print(f"Auto-login failed: {e}")

        # 1. Sync active identity from persisted if opening a fresh tab (e.g. F5 or link)
        if not self.login_token and self.persisted_token:
            self.login_token = self.persisted_token
            self.email = self.persisted_email

        # 2. Safety check: if no identity found — SaaS users come via auto_token from Shoper panel
        if not self.login_token:
            return

        # 3. Load saved Shoper API data from remote Hostinger server
        if self.email and self.login_token and not self.shop_url:
            try:
                resp = await asyncio.to_thread(
                    requests.post,
                    "https://booster-engine.pl/api/srm-auth.php?action=get_api_data",
                    json={"token": self.login_token},
                    timeout=5
                )
                if resp.status_code == 200:
                    data = resp.json()
                    if data.get("success") and data.get("data"):
                        row = data["data"]
                        self.shop_url = row.get("shop_url") or ""
                        # Set to empty if it's the pending placeholder
                        if self.shop_url == "https://pending.shoper.pl":
                            self.shop_url = ""

                        # OAuth access_token from srm_shops
                        self.token = row.get("access_token") or ""
                        if self.token:
                            self.is_appstore_user = True

                        # Check Shoper AppStore subscription status (bypass if admin)
                        app_status = row.get("app_status", "inactive")
                        role = row.get("role", "client")
                        self.is_app_active = (app_status == "active") or (role == "admin")
            except Exception as e:
                print(f"Failed to load remote API data: {e}")

        # Load is_paid from payments table (if you still need it, though it's unlocked now)
        if self.email:
            try:
                conn = db_manager.get_db_connection()
                cursor = conn.cursor()
                cursor.execute(
                    "SELECT COUNT(*) as cnt FROM payments p JOIN clients c ON p.client_id = c.id JOIN users u ON c.user_id = u.id WHERE u.email = ? AND p.status = 'completed'",
                    (self.email,)
                )
                row = cursor.fetchone()
                conn.close()
                self.is_paid = (row['cnt'] > 0) if row else False
            except Exception:
                pass


    is_paid: bool = False
    is_app_active: bool = True  # Shoper AppStore subscription status
    is_appstore_user: bool = False  # True if user came through Shoper AppStore auto-login
    selected_plan: str = "yearly"
    payment_error: str = ""

    logs: list[str] = []
    processing: bool = False
    processed_count: int = 0 # Added processed_count to state

    @rx.var
    def is_shoper_connected(self) -> bool:
        return bool(self.token)

    urls_to_process: str = ""
    results: list[dict] = []

    # Manual Redirects State
    manual_search_query: str = ""
    manual_search_results: list[dict] = []
    manual_category_id: str = ""
    manual_is_searching: bool = False
    manual_is_redirecting: bool = False
    manual_search_results_visible: bool = False

    # Mass Redirects State
    textarea_content: str = ""
    is_analyzing: bool = False
    is_redirecting: bool = False

    current_page: str = "Produkt ➡️ Produkt" # Default page

    def set_page(self, page: str):
        self.current_page = page

    def clear_manual_data(self):
        """Очистить результаты ручного поиска (Reset on Load)."""
        self.manual_search_query = ""
        self.manual_search_results = []
        self.manual_category_id = ""
        self.manual_search_results_visible = False
        # self.logs = []  <-- НЕ ТРОГАЕМ (согласно требованию)

    def select_plan(self, plan: str):
        """Wybierz plan subskrypcji."""
        self.selected_plan = plan

    def create_payment(self):
        """Utwórz transakcję P24 i przekieruj na stronę płatności."""
        self.payment_error = ""
        try:
            import uuid
            import p24_manager

            amount = p24_manager.PLAN_YEARLY_BRUTTO if self.selected_plan == "yearly" else p24_manager.PLAN_MONTHLY_BRUTTO
            description = "Manager Przekierowań – subskrypcja roczna" if self.selected_plan == "yearly" else "Manager Przekierowań – subskrypcja miesięczna"
            session_id = str(uuid.uuid4())

            result = p24_manager.create_transaction(
                email=self.email,
                amount=amount,
                description=description,
                session_id=session_id,
                return_url="http://localhost:8001/payment-success",
                status_url="http://localhost:8005/api/payment/status"
            )

            if result["success"]:
                try:
                    conn = db_manager.get_db_connection()
                    cursor = conn.cursor()
                    cursor.execute(
                        "INSERT INTO payments (client_id, amount, currency, status, details) SELECT c.id, ?, 'PLN', 'pending', ? FROM clients c JOIN users u ON c.user_id = u.id WHERE u.email = ?",
                        (amount, session_id, self.email)
                    )
                    conn.commit()
                    conn.close()
                except Exception:
                    pass
                return rx.redirect(result["redirect_url"], external=True)
            else:
                self.payment_error = result.get("error", "Błąd płatności")
        except Exception as e:
            self.payment_error = str(e)


    async def run_process(self):
        """Run batch processing with real-time logs."""
        if not self.is_authenticated:
            yield rx.window_alert("Please authenticate first.")
            return



        if not self.urls_to_process:
            yield rx.window_alert("No URLs provided.")
            return

        self.processing = True
        self.logs = ["🚀 Initiating real-time engine..."]
        yield

        # Split URLs
        urls = [u.strip() for u in self.urls_to_process.split('\n') if u.strip()]

        # Wrapper to capture prints
        class LogWriter(io.StringIO):
            def __init__(self, state):
                super().__init__()
                self.state = state
            def write(self, s):
                if s.strip():
                    self.state.logs.append(s.strip())
                return super().write(s)

        log_capture = LogWriter(self)

        try:
            with contextlib.redirect_stdout(log_capture):
                # Call real processing logic
                res = gsc_auto_pilot.process_error_urls(
                    shop_url=self.shop_url,
                    urls=urls,
                    fallback_category_id=0, # Default for now
                    dry_run=False,
                    shoper_creds={
                        'token': self.token
                    },
                    skip_semantic=True # Mass mode by default
                )

            if res.get("success"):
                self.logs.append(f"🏁 Finished! Redirected: {res.get('successful_redirects')}")
                # Update total processed (mock update for UI)
                self.processed_count += res.get('successful_redirects', 0)
            else:
                self.logs.append(f"❌ Error: {res.get('error')}")

        except Exception as e:
            self.logs.append(f"⚠️ Runtime Error: {str(e)}")

        self.processing = False
        yield

    def handle_search_keydown(self, key: str):
        if key == "Enter":
            return State.manual_search

    def handle_redirect_keydown(self, key: str):
        if key == "Enter":
            return State.manual_run_redirects

    async def manual_search(self):
        """Search products using logic from shoper_manual_logic."""
        if not self.manual_search_query:
            yield rx.window_alert("Wpisz nazwę продукта.")
            return

        self.manual_is_searching = True
        self.manual_search_results = []
        self.manual_search_results_visible = False
        yield

        try:
            with contextlib.suppress(SystemExit):
                token = self.token
                if token:
                    results = shoper_manual_logic.search_products(self.shop_url, token, self.manual_search_query)
                    self.manual_search_results = results
                    self.manual_search_results_visible = True
                    if not results:
                        yield rx.window_alert("Nic nie znaleziono!")
                else:
                    yield rx.window_alert("Błąd autoryzacji w skrypcie (sprawdź SHOP_URL, login i hasło w skrypcie).")
        except Exception as e:
            yield rx.window_alert(f"Błąd wyszukiwania: {str(e)}")

        self.manual_is_searching = False
        yield

    async def manual_run_redirects(self):
        """Create redirects for all found products."""
        if not self.manual_category_id:
            yield rx.window_alert("Podaj ID kategorii docelowej.")
            return

        if not self.manual_search_results:
            yield rx.window_alert("Brak produktów do przekierowania.")
            return

        self.manual_is_redirecting = True
        self.logs = [f"⏳ Rozpoczynamy tworzenie {len(self.manual_search_results)} przekierowań..."]
        yield

        token = self.token
        cat_id = shoper_manual_logic.extract_category_id(self.manual_category_id)

        if not cat_id:
            self.manual_is_redirecting = False
            yield rx.window_alert("Nieprawidłowe ID kategorii.")
            return

        success_count = 0
        for p in self.manual_search_results:
            success, msg = shoper_manual_logic.create_redirect(self.shop_url, token, p["route"], cat_id)
            if success:
                self.logs.append(f"✅ Przekierowanie: [{p['id']}] {p['name']}")
                success_count += 1
            else:
                self.logs.append(f"❌ Błąd [{p['id']}]: {msg}")

            self.processed_count += 1
            yield
            await asyncio.sleep(0.5)

        self.logs.append(f"🎉 Zakończono! Sukces: {success_count} z {len(self.manual_search_results)}")
        self.manual_is_redirecting = False
        yield rx.window_alert(f"Zakończono! Utworzono {success_count} przekierowań.")

    def run_analysis(self):
        """Stub for mass CSV analysis - to be implemented."""
        return rx.window_alert("Analiza masowa - wkrótce dostępna.")

    async def run_mass_redirects(self):
        """Stub for mass redirect execution - to be implemented."""
        if not self.textarea_content.strip():
            yield rx.window_alert("Wklej adresy URL do pola tekstowego.")
            return
        yield rx.window_alert("Masowe przekierowania - wkrótce dostępne.")


    def toggle_subscription(self):
        self.is_paid = not self.is_paid

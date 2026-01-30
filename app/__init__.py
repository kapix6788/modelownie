from flask import Flask
from flask_sqlalchemy import SQLAlchemy
from flask_login import LoginManager

# Inicjalizacja rozszerzeń (bez przypisanej aplikacji)
db = SQLAlchemy()
login_manager = LoginManager()


def create_app():
    """
    Fabryka aplikacji Flask.
    Inicjalizuje konfigurację, bazę danych, system logowania i rejestruje trasy.
    """
    app = Flask(__name__)

    # Konfiguracja aplikacji
    app.config['SECRET_KEY'] = 'bardzo_tajny_klucz_do_sesji'
    app.config['SQLALCHEMY_DATABASE_URI'] = 'sqlite:///warsztat.db'
    app.config['SQLALCHEMY_TRACK_MODIFICATIONS'] = False

    # Inicjalizacja rozszerzeń z aplikacją
    db.init_app(app)
    login_manager.init_app(app)

    # Przekierowanie do logowania, gdy użytkownik nie jest zalogowany
    # 'main.login' oznacza funkcję login() w Blueprincie 'main'
    login_manager.login_view = 'main.login'
    login_manager.login_message = "Zaloguj się, aby uzyskać dostęp."
    login_manager.login_message_category = "info"

    # Import modeli (konieczny, aby SQLAlchemy wiedziało co stworzyć)
    from .models import User

    @login_manager.user_loader
    def load_user(user_id):
        return User.query.get(int(user_id))

    # Rejestracja Blueprinta (naszych tras)
    from . import routes
    app.register_blueprint(routes.bp)

    # Tworzenie bazy danych (jeśli nie istnieje)
    with app.app_context():
        db.create_all()

    return app
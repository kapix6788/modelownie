import pytest
from app import create_app, db
from app.models import User, Vehicle, Part, Service
from app.routes import validate_nip
from werkzeug.security import generate_password_hash, check_password_hash


#KONFIGURACJA
@pytest.fixture
def app():
    app = create_app()
    app.config.update({
        "TESTING": True,
        "SQLALCHEMY_DATABASE_URI": "sqlite:///:memory:",
        "WTF_CSRF_ENABLED": False
    })

    with app.app_context():
        db.create_all()
        yield app
        db.session.remove()
        db.drop_all()


#KLASY TESTOWE
class TestUserModel:
    def test_password_hashing_security(self, app):
        plain_password = "SecretPassword123"
        hashed = generate_password_hash(plain_password)

        user = User(
            first_name="Jan",
            last_name="Testowy",
            email="jan@test.pl",
            role="client",
            password=hashed
        )
        db.session.add(user)
        db.session.commit()

        fetched_user = User.query.filter_by(email="jan@test.pl").first()

        assert fetched_user.password != plain_password, "Hasło nie może być zapisane jawnym tekstem"
        assert check_password_hash(fetched_user.password, plain_password) is True, "Hasz powinien pasować do hasła"
        assert check_password_hash(fetched_user.password, "ZleHaslo") is False, "Złe hasło nie powinno pasować"


class TestPartModel:
    def test_stock_management_logic(self, app):
        part = Part(name="Filtr", price=50.0, stock_quantity=10)
        db.session.add(part)
        db.session.commit()

        part.stock_quantity -= 3
        db.session.commit()

        updated_part = Part.query.first()
        assert updated_part.stock_quantity == 7, "Stan magazynowy powinien zmaleć o 3"

    def test_negative_stock_behavior(self, app):
        part = Part(name="Śruba", price=1.0, stock_quantity=5)
        db.session.add(part)
        db.session.commit()

        part.stock_quantity -= 10
        db.session.commit()

        assert part.stock_quantity == -5, "System powinien poprawnie obliczyć ujemny stan"


class TestVehicleModel:
    def test_vehicle_owner_relationship_memory(self):
        car = Vehicle(
            make="Fiat",
            model="Panda",
            registration_number="K1 TEST",
            owner_id=999
        )

        assert car.owner_id == 999
        assert car.make == "Fiat"

    def test_registration_uniqueness_constraint(self, app):
        owner = User(first_name="A", last_name="B", email="a@b.pl", role="client", password="x")
        db.session.add(owner)
        db.session.commit()

        car1 = Vehicle(make="Opel", model="Astra", registration_number="DW12345", owner_id=owner.id)
        db.session.add(car1)
        db.session.commit()
        car2 = Vehicle(make="Ford", model="Focus", registration_number="DW12345", owner_id=owner.id)
        db.session.add(car2)

        with pytest.raises(Exception):
            db.session.commit()


class TestServiceModel:
    def test_service_initialization(self):
        service = Service(name="Wymiana opon", base_price=120.50)
        assert service.name == "Wymiana opon"
        assert service.base_price == 120.50
        assert isinstance(service.base_price, float), "Cena powinna być typu float"

class TestValidators:
    def test_nip_validation_algorithm(self):
        assert validate_nip('123-456-32-18') is True, "Poprawny NIP z myślnikami powinien przejść"
        assert validate_nip('1234567890') is False, "NIP ze złą sumą kontrolną powinien odpaść"
        assert validate_nip('Abcdefghij') is False, "NIP z literami powinien odpaść"
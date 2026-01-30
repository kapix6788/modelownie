from behave import given, when, then
from app import create_app, db
from app.models import User
from werkzeug.security import generate_password_hash

@given('Użytkownik jest na stronie logowania')
def step_impl(context):
    context.app = create_app()
    context.app.config['SQLALCHEMY_DATABASE_URI'] = 'sqlite:///:memory:'
    context.app.config['TESTING'] = True
    context.app.config['WTF_CSRF_ENABLED'] = False

    context.app_context = context.app.app_context()
    context.app_context.push()

    db.create_all()
    context.client = context.app.test_client()

    user = User(
        first_name="Jan",
        last_name="Testowy",
        email="klient@test.pl",
        role="client",
        password=generate_password_hash("tajne")
    )
    db.session.add(user)
    db.session.commit()

@when('Wpisuje email "{email}" i hasło "{password}"')
def step_impl(context, email, password):
    context.form_data = {
        'email': email,
        'password': password
    }

@when('Klika przycisk zaloguj')
def step_impl(context):
    if not hasattr(context, 'form_data'):
        raise Exception("Brak danych logowania!")

    context.response = context.client.post('/login', data=context.form_data, follow_redirects=True)


@then('Zostaje przekierowany do panelu klienta')
def step_impl(context):
    assert context.response.status_code == 200
    page_content = context.response.data.decode('utf-8')

    if 'Panel Klienta' not in page_content and 'Witaj' not in page_content and 'Wyloguj' not in page_content:
        context.app_context.pop()
        assert False, "Nie znaleziono panelu klienta po zalogowaniu!"

    db.session.remove()
    db.drop_all()
    context.app_context.pop()
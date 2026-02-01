from datetime import datetime
from flask import Blueprint, render_template, redirect, url_for, flash, request, make_response
from flask_login import login_user, logout_user, login_required, current_user
from werkzeug.security import generate_password_hash, check_password_hash
from fpdf import FPDF
from sqlalchemy.exc import IntegrityError
from .models import User, Vehicle, RepairOrder, db, Service, Part, RepairPart


bp = Blueprint('main', __name__)

def validate_nip(nip_str):
    if not nip_str: return False
    nip = nip_str.replace('-', '').strip()
    if len(nip) != 10 or not nip.isdigit():
        return False
    weights = [6, 5, 7, 2, 3, 4, 5, 6, 7]
    checksum = sum(int(nip[i]) * weights[i] for i in range(9))
    return (checksum % 11) == int(nip[9])

@bp.route('/')
def index():
    return redirect(url_for('main.login'))


@bp.route('/login', methods=['GET', 'POST'])
def login():
    if request.method == 'POST':
        email = request.form.get('email')
        password = request.form.get('password')
        user = User.query.filter_by(email=email).first()

        if user and check_password_hash(user.password, password):
            login_user(user)
            return redirect(url_for('main.dashboard'))
        else:
            flash('Błędne dane logowania.')
    return render_template('login.html')


@bp.route('/register', methods=['GET', 'POST'])
def register():
    if request.method == 'POST':
        email = request.form.get('email')
        password = request.form.get('password')
        first_name = request.form.get('first_name')
        last_name = request.form.get('last_name')
        role = request.form.get('role')
        phone_number = request.form.get('phone_number')
        nip = request.form.get('nip')

        if len(password) < 4:
            flash('Hasło musi mieć co najmniej 4 znaki', 'error')
            return redirect(url_for('main.register'))

        if phone_number:
            clean_phone = phone_number.replace('-', '').replace(' ', '')

            if not clean_phone.isdigit():
                flash('Numer telefonu może zawierać tylko cyfry', 'error')
                return redirect(url_for('main.register'))

            if not (9 <= len(clean_phone) <= 9):
                flash('Numer telefonu musi mieć 9', 'error')
                return redirect(url_for('main.register'))
            phone_number = clean_phone

        if nip:
            clean_nip = nip.replace('-', '').strip()
            if not validate_nip(clean_nip):
                flash('Podano nieprawidłowy numer NIP!', 'error')
                return redirect(url_for('main.register'))
            nip = clean_nip

        if User.query.filter_by(email=email).first():
            flash('Taki email już istnieje w bazie.', 'error')
            return redirect(url_for('main.register'))

        hashed_password = generate_password_hash(password)
        new_user = User(
            email=email, password=hashed_password,
            first_name=first_name, last_name=last_name, role=role,
            phone_number=phone_number, nip=nip
        )
        db.session.add(new_user)
        db.session.commit()
        flash('Konto założone! Zaloguj się.')
        return redirect(url_for('main.login'))
    return render_template('register.html')


@bp.route('/logout')
@login_required
def logout():
    logout_user()
    return redirect(url_for('main.login'))


@bp.route('/dashboard')
@login_required
def dashboard():
    if current_user.role == 'client':
        return redirect(url_for('main.client_panel'))
    elif current_user.role == 'mechanic':
        return redirect(url_for('main.mechanic_panel'))
    elif current_user.role == 'reception':
        return redirect(url_for('main.reception_panel'))
    elif current_user.role == 'owner':
        return redirect(url_for('main.owner_panel'))
    else:
        return "Nieznana rola użytkownika", 403

#KLIENT

@bp.route('/panel/client')
@login_required
def client_panel():
    if current_user.role != 'client': return redirect(url_for('main.dashboard'))
    return render_template('client_panel.html', vehicles=current_user.vehicles, user=current_user)


@bp.route('/client/add_vehicle', methods=['POST'])
@login_required
def client_add_vehicle():
    if current_user.role != 'client': return "Brak uprawnień", 403

    make = request.form.get('make')
    model = request.form.get('model')
    registration_number = request.form.get('registration_number')
    vin = request.form.get('vin')

    if vin:
        clean_vin = vin.replace(' ', '').replace('-', '').upper()

        if len(clean_vin) > 0:
            if len(clean_vin) != 17:
                flash('Numer VIN musi mieć dokładnie 17 znaków!', 'error')
                return redirect(url_for('main.client_panel'))

            if not clean_vin.isalnum():
                flash('VIN może zawierać tylko cyfry i litery (bez znaków specjalnych)!', 'error')
                return redirect(url_for('main.client_panel'))
            vin = clean_vin
        else:
            vin = None

    if Vehicle.query.filter_by(registration_number=registration_number).first():
        flash('Pojazd o takiej rejestracji już istnieje w systemie.', 'error')
        return redirect(url_for('main.client_panel'))

    if vin and Vehicle.query.filter_by(vin=vin).first():
        flash('Pojazd o takim numerze VIN już istnieje w systemie.', 'error')
        return redirect(url_for('main.client_panel'))
    new_car = Vehicle(
        make=make,
        model=model,
        vin=vin,
        registration_number=registration_number,
        owner_id=current_user.id
    )
    db.session.add(new_car)
    db.session.commit()

    flash(f'Pojazd {make} {model} został dodany!')
    return redirect(url_for('main.client_panel'))


@bp.route('/client/delete_vehicle/<int:vehicle_id>', methods=['POST'])
@login_required
def client_delete_vehicle(vehicle_id):
    if current_user.role != 'client': return "Brak uprawnień", 403

    vehicle = Vehicle.query.filter_by(id=vehicle_id, owner_id=current_user.id).first_or_404()

    try:
        db.session.delete(vehicle)
        db.session.commit()
        flash('Pojazd został usunięty z Twojej listy.')
    except IntegrityError:
        db.session.rollback()
        flash('BŁĄD: Nie można usunąć pojazdu, który posiada aktywne zlecenia lub historię napraw!', 'error')

    return redirect(url_for('main.client_panel'))


@bp.route('/client/check_status', methods=['POST'])
@login_required
def client_check_status():
    if current_user.role != 'client': return "Brak uprawnień", 403
    order_id = request.form.get('order_id')
    if not order_id:
        flash('Podaj numer zlecenia.', 'warning')
        return redirect(url_for('main.client_panel'))

    repair = RepairOrder.query.filter_by(id=order_id).first()
    if repair and repair.vehicle.owner_id == current_user.id:
        status_color = "success" if repair.status == 'Gotowe' else "warning" if repair.status == 'Czeka na części' else "info"
        flash(f'Zlecenie #{repair.id} - Aktualny status: {repair.status}', status_color)
    else:
        flash(f'Nie znaleziono zlecenia o numerze #{order_id} na Twoim koncie.', 'error')
    return redirect(url_for('main.client_panel'))


@bp.route('/book_appointment', methods=['GET', 'POST'])
@login_required
def book_appointment():
    if current_user.role != 'client': return "Brak uprawnień", 403

    if request.method == 'POST':
        vehicle_id = request.form.get('vehicle_id')
        service_id = request.form.get('service_id')
        date_str = request.form.get('date')
        time_str = request.form.get('time')
        # 1. Odbieramy notatki klienta
        client_notes = request.form.get('client_notes')

        if not all([vehicle_id, service_id, date_str, time_str]):
            flash('Wypełnij wszystkie wymagane pola!', 'error')
            return redirect(url_for('main.book_appointment'))

        try:
            full_date = datetime.strptime(f"{date_str} {time_str}", "%Y-%m-%d %H:%M")

            final_description = "Rezerwacja Online"
            if client_notes and client_notes.strip():
                final_description += f": {client_notes}"
            else:
                final_description += ": Wybrana usługa z listy."

            new_order = RepairOrder(
                vehicle_id=vehicle_id,
                description=final_description,
                status="Zgłoszone",
                start_date=full_date
            )

            selected_service = Service.query.get(service_id)
            if selected_service:
                new_order.services.append(selected_service)

            db.session.add(new_order)
            db.session.commit()
            flash(f'Zarezerwowano wizytę na {date_str} {time_str}.')
            return redirect(url_for('main.client_panel'))
        except ValueError:
            flash('Nieprawidłowy format daty.', 'error')
    return render_template('book_appointment.html', vehicles=current_user.vehicles, services=Service.query.all())


@bp.route('/history')
@login_required
def client_history():
    my_repairs = RepairOrder.query.join(Vehicle).filter(
        Vehicle.owner_id == current_user.id, RepairOrder.status == 'Gotowe'
    ).order_by(RepairOrder.end_date.desc()).all()
    return render_template('repair_history.html', repairs=my_repairs)


@bp.route('/history/<int:repair_id>')
@login_required
def repair_details(repair_id):
    repair = RepairOrder.query.get_or_404(repair_id)
    if repair.vehicle.owner_id != current_user.id:
        flash('Nie masz dostępu do tego zlecenia.')
        return redirect(url_for('main.client_history'))

    parts_cost = sum(item.part.price * item.quantity for item in repair.used_parts)
    services_cost = sum(s.base_price for s in repair.services)
    return render_template('repair_details.html', repair=repair, parts_cost=parts_cost, services_cost=services_cost,
                           total_cost=parts_cost + services_cost)


@bp.route('/history/<int:repair_id>/invoice')
@login_required
def download_invoice(repair_id):
    repair = RepairOrder.query.get_or_404(repair_id)
    if current_user.role not in ['reception', 'owner'] and repair.vehicle.owner_id != current_user.id:
        return "Brak dostępu", 403

    parts_cost = sum(item.part.price * item.quantity for item in repair.used_parts)
    services_cost = sum(s.base_price for s in repair.services)
    total_cost = parts_cost + services_cost
    real_client = repair.vehicle.owner

    pdf = FPDF()
    pdf.add_page()
    pdf.set_font("Arial", 'B', 16)
    pdf.cell(40, 10, f"Faktura nr: {repair.id}/2026")
    pdf.ln(20)

    pdf.set_font("Arial", '', 12)
    pdf.cell(0, 10, f"Klient: {real_client.first_name} {real_client.last_name}", 0, 1)
    if real_client.nip:
        pdf.cell(w=0, h=10, txt=f"NIP: {real_client.nip}", border=0, ln=1)
    pdf.cell(0, 10, f"Pojazd: {repair.vehicle.make} {repair.vehicle.model} ({repair.vehicle.registration_number})", 0,
             1)
    pdf.cell(0, 10, f"Data naprawy: {repair.start_date.strftime('%Y-%m-%d')}", 0, 1)
    pdf.ln(10)

    pdf.set_font("Arial", 'B', 12)
    pdf.cell(0, 10, "Uslugi:", 0, 1)
    pdf.set_font("Arial", '', 12)
    for service in repair.services:
        pdf.cell(140, 10, service.name, 1)
        pdf.cell(50, 10, f"{service.base_price:.2f} PLN", 1, 1, 'R')

    if repair.used_parts:
        pdf.ln(5)
        pdf.set_font("Arial", 'B', 12)
        pdf.cell(0, 10, "Czesci:", 0, 1)
        pdf.set_font("Arial", '', 12)
        for item in repair.used_parts:
            pdf.cell(140, 10, f"{item.part.name} (x{item.quantity})", 1)
            pdf.cell(50, 10, f"{item.part.price * item.quantity:.2f} PLN", 1, 1, 'R')

    pdf.ln(10)
    pdf.set_font("Arial", 'B', 14)
    pdf.cell(140, 10, "RAZEM DO ZAPLATY:", 0)
    pdf.cell(50, 10, f"{total_cost:.2f} PLN", 0, 1, 'R')

    response = make_response(pdf.output(dest='S').encode('latin-1', 'replace'))
    response.headers['Content-Type'] = 'application/pdf'
    response.headers['Content-Disposition'] = f'attachment; filename=faktura_{repair.id}.pdf'
    return response

#RECEPCJA

@bp.route('/panel/reception')
@login_required
def reception_panel():
    if current_user.role != 'reception': return redirect(url_for('main.dashboard'))
    return render_template('reception_panel.html',
                           repairs=RepairOrder.query.order_by(RepairOrder.start_date.desc()).all(),
                           mechanics=User.query.filter_by(role='mechanic').all(),
                           services=Service.query.all(),
                           user=current_user)


@bp.route('/reception/create_order', methods=['GET', 'POST'])
@login_required
def reception_create_order():
    if current_user.role != 'reception': return redirect(url_for('main.dashboard'))

    if request.method == 'POST':
        vehicle_id = request.form.get('vehicle_id')
        service_id = request.form.get('service_id')
        mechanic_id = request.form.get('mechanic_id')
        description = request.form.get('description')
        date_str = request.form.get('date')
        time_str = request.form.get('time')

        if vehicle_id and service_id:
            start_date_obj = datetime.strptime(f"{date_str} {time_str}", '%Y-%m-%d %H:%M')
            new_repair = RepairOrder(
                description=description, status='Zgłoszone',
                start_date=start_date_obj, vehicle_id=vehicle_id
            )
            if mechanic_id:
                new_repair.mechanic_id = mechanic_id
                new_repair.status = 'Przyjęte do realizacji'

            new_repair.services.append(Service.query.get(service_id))
            db.session.add(new_repair)
            db.session.commit()
            flash(f'Zapisano zlecenie #{new_repair.id}.')
            return redirect(url_for('main.reception_panel'))

    return render_template('reception_create_order.html',
                           vehicles=Vehicle.query.all(), services=Service.query.all(),
                           mechanics=User.query.filter_by(role='mechanic').all(),
                           clients=User.query.filter_by(role='client').all(),
                           now=datetime.now())


@bp.route('/reception/quick_add_vehicle', methods=['POST'])
@login_required
def quick_add_vehicle():
    if current_user.role != 'reception': return "Brak uprawnień", 403

    registration_number = request.form.get('registration_number')
    if Vehicle.query.filter_by(registration_number=registration_number).first():
        flash('Auto o takiej rejestracji już istnieje!', 'error')
    else:
        new_car = Vehicle(
            make=request.form.get('make'), model=request.form.get('model'),
            registration_number=registration_number, vin=request.form.get('vin'),
            owner_id=request.form.get('owner_id')
        )
        db.session.add(new_car)
        db.session.commit()
        flash(f'Dodano pojazd: {new_car.make} {new_car.model}')
    return redirect(url_for('main.reception_create_order'))


@bp.route('/assign_mechanic/<int:repair_id>', methods=['POST'])
@login_required
def assign_mechanic(repair_id):
    if current_user.role != 'reception': return redirect(url_for('main.dashboard'))
    repair = RepairOrder.query.get_or_404(repair_id)
    mechanic_id = request.form.get('mechanic_id')

    if mechanic_id:
        repair.mechanic_id = mechanic_id
        repair.status = 'Przyjęte do realizacji'
        db.session.commit()
        flash(f'Przypisano mechanika do zlecenia #{repair.id}.')
    return redirect(url_for('main.reception_panel'))


@bp.route('/appointment/delete/<int:repair_id>', methods=['POST'])
@login_required
def delete_appointment(repair_id):
    if current_user.role != 'reception': return "Brak uprawnień", 403
    db.session.delete(RepairOrder.query.get_or_404(repair_id))
    db.session.commit()
    flash('Rezerwacja została usunięta.')
    return redirect(url_for('main.reception_panel'))


@bp.route('/repair/edit/<int:repair_id>', methods=['POST'])
@login_required
def edit_repair(repair_id):
    if current_user.role != 'reception': return "Brak uprawnień", 403
    repair = RepairOrder.query.get_or_404(repair_id)

    new_date = request.form.get('date')
    new_time = request.form.get('time')
    new_status = request.form.get('status')
    description = request.form.get('description')
    mechanic_id = request.form.get('mechanic_id')
    service_id = request.form.get('service_id')

    if new_date and new_time:
        repair.start_date = datetime.strptime(f"{new_date} {new_time}", '%Y-%m-%d %H:%M')

    if new_status:
        repair.status = new_status
        if new_status == 'Gotowe': repair.end_date = datetime.now()

    if description: repair.description = description

    if mechanic_id:
        repair.mechanic_id = mechanic_id
        if repair.status == 'Zgłoszone': repair.status = 'Przyjęte do realizacji'
    elif mechanic_id == "":
        repair.mechanic_id = None

    if service_id:
        new_service = Service.query.get(service_id)
        if repair.services:
            repair.services[0] = new_service
        else:
            repair.services.append(new_service)

    db.session.commit()
    flash(f'Zaktualizowano dane zlecenia #{repair.id}.')
    return redirect(url_for('main.reception_panel'))



#MECHANIK


@bp.route('/panel/mechanic')
@login_required
def mechanic_panel():
    if current_user.role != 'mechanic': return redirect(url_for('main.dashboard'))
    return render_template('mechanic_panel.html', tasks=current_user.repairs_assigned, parts=Part.query.all(),
                           user=current_user)


@bp.route('/mechanic/update_order/<int:repair_id>', methods=['POST'])
@login_required
def mechanic_update_order(repair_id):
    if current_user.role != 'mechanic': return "Brak uprawnień", 403
    repair = RepairOrder.query.get_or_404(repair_id)
    new_status = request.form.get('status')
    notes = request.form.get('mechanic_notes')

    if new_status:
        repair.status = new_status
        if new_status == 'Gotowe': repair.end_date = datetime.now()
    if notes:
        repair.mechanic_notes = notes

    db.session.commit()
    flash(f'Zaktualizowano zlecenie #{repair.id}.')
    return redirect(url_for('main.mechanic_panel'))


@bp.route('/report_missing_part/<int:repair_id>', methods=['POST'])
@login_required
def report_missing_part(repair_id):
    if current_user.role != 'mechanic': return "Brak uprawnień", 403
    repair = RepairOrder.query.get_or_404(repair_id)
    part = Part.query.get_or_404(request.form.get('part_id'))

    repair.status = 'Czeka na części'
    new_note = f"[{datetime.now().strftime('%Y-%m-%d %H:%M')}] ZAPOTRZEBOWANIE: Brak części '{part.name}'."
    repair.mechanic_notes = (repair.mechanic_notes + "\n" + new_note) if repair.mechanic_notes else new_note

    db.session.commit()
    flash(f'Zgłoszono brak: {part.name}.')
    return redirect(url_for('main.mechanic_panel'))


@bp.route('/add_part/<int:repair_id>', methods=['POST'])
@login_required
def add_part(repair_id):
    if current_user.role != 'mechanic': return "Brak uprawnień", 403
    repair = RepairOrder.query.get_or_404(repair_id)
    part = Part.query.get(request.form.get('part_id'))
    quantity = int(request.form.get('quantity'))

    if part and part.stock_quantity >= quantity:
        part.stock_quantity -= quantity
        db.session.add(RepairPart(repair_id=repair.id, part_id=part.id, quantity=quantity))
        db.session.commit()
        flash(f'Dodano {part.name} (x{quantity}).')
    else:
        flash('Brak części w magazynie!', 'error')
    return redirect(url_for('main.mechanic_panel'))


@bp.route('/complete_repair/<int:repair_id>', methods=['POST'])
@login_required
def complete_repair(repair_id):
    if current_user.role not in ['mechanic', 'owner']: return "Brak uprawnień", 403
    repair = RepairOrder.query.get_or_404(repair_id)
    repair.status = 'Gotowe'
    repair.end_date = datetime.now()
    db.session.commit()
    flash(f'Zlecenie #{repair.id} zakończone!')
    return redirect(url_for('main.mechanic_panel'))



#WŁAŚCICIEL

@bp.route('/panel/owner')
@login_required
def owner_panel():
    if current_user.role != 'owner': return redirect(url_for('main.dashboard'))

    all_finished = RepairOrder.query.filter_by(status='Gotowe').all()
    total_income = 0
    for repair in all_finished:
        for s in repair.services: total_income += s.base_price
        for p in repair.used_parts: total_income += (p.part.price * p.quantity)

    return render_template('owner_panel.html',
                           employees=User.query.filter(User.role.in_(['mechanic', 'reception'])).all(),
                           services=Service.query.all(),
                           total_income=total_income,
                           active_count=RepairOrder.query.filter(RepairOrder.status != 'Gotowe').count(),
                           finished_count=len(all_finished))


@bp.route('/owner/add_employee', methods=['POST'])
@login_required
def add_employee():
    if current_user.role != 'owner': return "Brak dostępu", 403
    email = request.form.get('email')
    if User.query.filter_by(email=email).first():
        flash('Taki email już istnieje!', 'error')
    else:
        hashed_pw = generate_password_hash(request.form.get('password'))
        new_emp = User(
            email=email, password=hashed_pw,
            first_name=request.form.get('first_name'),
            last_name=request.form.get('last_name'),
            role=request.form.get('role')
        )
        db.session.add(new_emp)
        db.session.commit()
        flash(f'Dodano pracownika: {new_emp.first_name}')
    return redirect(url_for('main.owner_panel'))


@bp.route('/owner/delete_employee/<int:user_id>', methods=['POST'])
@login_required
def delete_employee(user_id):
    if current_user.role != 'owner': return "Brak dostępu", 403
    user = User.query.get_or_404(user_id)
    if user.role == 'owner':
        flash('Nie możesz usunąć samego siebie!', 'error')
    else:
        db.session.delete(user)
        db.session.commit()
        flash('Usunięto pracownika.')
    return redirect(url_for('main.owner_panel'))


@bp.route('/owner/add_service', methods=['POST'])
@login_required
def add_service():
    if current_user.role != 'owner': return "Brak dostępu", 403
    db.session.add(Service(name=request.form.get('name'), base_price=float(request.form.get('price'))))
    db.session.commit()
    flash('Dodano usługę.')
    return redirect(url_for('main.owner_panel'))


@bp.route('/owner/edit_service/<int:service_id>', methods=['POST'])
@login_required
def edit_service(service_id):
    if current_user.role != 'owner': return "Brak dostępu", 403
    service = Service.query.get_or_404(service_id)
    service.name = request.form.get('name')
    service.base_price = float(request.form.get('price'))
    db.session.commit()
    flash('Zaktualizowano cennik.')
    return redirect(url_for('main.owner_panel'))


@bp.route('/owner/delete_service/<int:service_id>', methods=['POST'])
@login_required
def delete_service(service_id):
    if current_user.role != 'owner': return "Brak dostępu", 403
    db.session.delete(Service.query.get_or_404(service_id))
    db.session.commit()
    flash('Usunięto usługę.')
    return redirect(url_for('main.owner_panel'))


@bp.route('/owner/report_pdf')
@login_required
def owner_download_report():
    if current_user.role != 'owner': return "Brak dostępu", 403

    all_finished = RepairOrder.query.filter_by(status='Gotowe').all()
    total_income = 0
    parts_cost = 0
    for repair in all_finished:
        for s in repair.services: total_income += s.base_price
        for p in repair.used_parts:
            cost = p.part.price * p.quantity
            total_income += cost
            parts_cost += cost
    income_services = total_income - parts_cost
    current_date = datetime.now().strftime('%Y-%m-%d')

    pdf = FPDF()
    pdf.add_page()
    pdf.set_font("Arial", 'B', 16)
    pdf.cell(0, 10, f"RAPORT FINANSOWY: {current_date}", ln=1, align='C')
    pdf.ln(10)

    pdf.set_font("Arial", '', 12)
    pdf.cell(0, 10, "Podsumowanie okresu:", ln=1)
    pdf.set_font("Arial", 'B', 12)
    pdf.cell(0, 10, f"PRZYCHOD: {total_income:.2f} PLN", ln=1)
    pdf.set_font("Arial", '', 12)
    pdf.cell(0, 10, f" - Czesci: {parts_cost:.2f} PLN", ln=1)
    pdf.cell(0, 10, f" - Uslugi: {income_services:.2f} PLN", ln=1)
    pdf.ln(10)

    pdf.set_fill_color(200, 220, 255)
    pdf.set_font("Arial", 'B', 10)
    pdf.cell(20, 10, "ID", 1, 0, 'C', True)
    pdf.cell(30, 10, "Data", 1, 0, 'C', True)
    pdf.cell(90, 10, "Pojazd", 1, 0, 'C', True)
    pdf.cell(50, 10, "Kwota", 1, 1, 'C', True)

    pdf.set_font("Arial", '', 10)
    for repair in all_finished:
        order_total = sum(s.base_price for s in repair.services) + sum(
            p.part.price * p.quantity for p in repair.used_parts)
        pdf.cell(20, 10, str(repair.id), 1)
        pdf.cell(30, 10, repair.start_date.strftime('%Y-%m-%d'), 1)
        pdf.cell(90, 10, f"{repair.vehicle.make} {repair.vehicle.model}", 1)
        pdf.cell(50, 10, f"{order_total:.2f}", 1, 1)

    response = make_response(pdf.output(dest='S').encode('latin-1', 'replace'))
    response.headers['Content-Type'] = 'application/pdf'
    response.headers['Content-Disposition'] = f'attachment; filename=Raport_{current_date}.pdf'
    return response


@bp.route('/init_services')
def init_services():
    if not Service.query.first():
        db.session.add_all([
            Service(name="Wymiana oleju i filtrów", base_price=250.0),
            Service(name="Przegląd okresowy", base_price=150.0),
            Service(name="Wymiana opon", base_price=100.0),
            Service(name="Diagnostyka komputerowa", base_price=50.0),
            Service(name="Naprawa układu hamulcowego", base_price=400.0)
        ])
        db.session.commit()
        return "Usługi dodane!"
    return "Usługi już istnieją."


@bp.route('/init_parts')
def init_parts():
    if not Part.query.first():
        db.session.add_all([
            Part(name="Filtr Oleju", code="F-OIL", price=45.0, stock_quantity=20),
            Part(name="Olej 5W30 (1L)", code="OIL", price=60.0, stock_quantity=100),
            Part(name="Klocki Hamulcowe", code="BRK", price=180.0, stock_quantity=10),
            Part(name="Tarcza Hamulcowa", code="DSK", price=220.0, stock_quantity=8)
        ])
        db.session.commit()
        return "Magazyn zatowarowany!"
    return "Części już istnieją."
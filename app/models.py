from . import db
from flask_login import UserMixin
from sqlalchemy.sql import func

repair_services = db.Table('repair_services',
                           db.Column('repair_id', db.Integer, db.ForeignKey('repair_order.id'), primary_key=True),
                           db.Column('service_id', db.Integer, db.ForeignKey('service.id'), primary_key=True)
                           )

# UŻYTKOWNICY
class User(db.Model, UserMixin):

    id = db.Column(db.Integer, primary_key=True)
    email = db.Column(db.String(150), unique=True, nullable=False)
    password = db.Column(db.String(150), nullable=False)
    first_name = db.Column(db.String(150), nullable=False)
    last_name = db.Column(db.String(150), nullable=False)
    role = db.Column(db.String(20), nullable=False)

    phone_number = db.Column(db.String(20))
    nip = db.Column(db.String(15))

    specialization = db.Column(db.String(100), nullable=True)

    vehicles = db.relationship('Vehicle', backref='owner', lazy=True)
    repairs_assigned = db.relationship('RepairOrder', backref='mechanic', lazy=True)

# POJAZDY I ZLECENIA
class Vehicle(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    make = db.Column(db.String(50), nullable=False)
    model = db.Column(db.String(50), nullable=False)
    vin = db.Column(db.String(17), unique=True)
    registration_number = db.Column(db.String(20), unique=True, nullable=False)

    owner_id = db.Column(db.Integer, db.ForeignKey('user.id'), nullable=False)
    repairs = db.relationship('RepairOrder', backref='vehicle', lazy=True)

class RepairOrder(db.Model):

    id = db.Column(db.Integer, primary_key=True)
    description = db.Column(db.Text, nullable=False)
    mechanic_notes = db.Column(db.Text)
    status = db.Column(db.String(50), default='Zgłoszone')

    start_date = db.Column(db.DateTime(timezone=True), default=func.now())
    end_date = db.Column(db.DateTime(timezone=True))

    vehicle_id = db.Column(db.Integer, db.ForeignKey('vehicle.id'), nullable=False)
    mechanic_id = db.Column(db.Integer, db.ForeignKey('user.id'), nullable=True)

    used_parts = db.relationship('RepairPart', backref='repair', lazy=True)
    services = db.relationship('Service', secondary=repair_services, lazy='subquery',
                               backref=db.backref('repairs', lazy=True))

# MAGAZYN I USŁUGI
class Part(db.Model):

    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(100), nullable=False)
    code = db.Column(db.String(50), unique=True)
    price = db.Column(db.Float, nullable=False)
    stock_quantity = db.Column(db.Integer, default=0)

class RepairPart(db.Model):

    id = db.Column(db.Integer, primary_key=True)
    repair_id = db.Column(db.Integer, db.ForeignKey('repair_order.id'), nullable=False)
    part_id = db.Column(db.Integer, db.ForeignKey('part.id'), nullable=False)
    quantity = db.Column(db.Integer, nullable=False, default=1)
    part = db.relationship('Part')

class Service(db.Model):

    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(100), nullable=False)
    base_price = db.Column(db.Float, nullable=False)
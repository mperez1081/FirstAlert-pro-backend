from src.models.user import db
from datetime import datetime
import json

class Incident(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    incident_type = db.Column(db.String(100), nullable=False)
    location = db.Column(db.String(200), nullable=False)
    address = db.Column(db.String(300), nullable=False)
    priority = db.Column(db.Integer, nullable=False)  # 1=High, 2=Medium, 3=Low
    units_requested = db.Column(db.Integer, nullable=False)
    pertinent_details = db.Column(db.Text)
    created_by = db.Column(db.String(50), nullable=False)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    status = db.Column(db.String(20), default='active')  # active, cleared
    timeline = db.Column(db.Text)  # JSON string of timeline events
    responding_units = db.Column(db.Text)  # JSON string of responding units

    def __repr__(self):
        return f'<Incident {self.id}: {self.incident_type}>'

    def to_dict(self):
        return {
            'id': self.id,
            'incident_type': self.incident_type,
            'location': self.location,
            'address': self.address,
            'priority': self.priority,
            'units_requested': self.units_requested,
            'pertinent_details': self.pertinent_details,
            'created_by': self.created_by,
            'created_at': self.created_at.isoformat() if self.created_at else None,
            'status': self.status,
            'timeline': json.loads(self.timeline) if self.timeline else [],
            'responding_units': json.loads(self.responding_units) if self.responding_units else []
        }

    def set_timeline(self, timeline_data):
        self.timeline = json.dumps(timeline_data)

    def set_responding_units(self, units_data):
        self.responding_units = json.dumps(units_data)

class CallType(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(100), unique=True, nullable=False)
    default_priority = db.Column(db.Integer, nullable=False)
    created_by = db.Column(db.String(50), nullable=False)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)

    def __repr__(self):
        return f'<CallType {self.name}>'

    def to_dict(self):
        return {
            'id': self.id,
            'name': self.name,
            'default_priority': self.default_priority,
            'created_by': self.created_by,
            'created_at': self.created_at.isoformat() if self.created_at else None
        }

class Unit(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    unit_id = db.Column(db.String(20), unique=True, nullable=False)  # FM-1, DISPATCH-1, ADMIN
    unit_name = db.Column(db.String(100), nullable=False)  # Fire Marshal 1, Dispatch 1, System Administrator
    unit_type = db.Column(db.String(20), nullable=False)  # fire_marshal, dispatch, admin
    password_hash = db.Column(db.String(128))
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    last_login = db.Column(db.DateTime)

    def __repr__(self):
        return f'<Unit {self.unit_id}: {self.unit_name}>'

    def to_dict(self):
        return {
            'id': self.id,
            'unit_id': self.unit_id,
            'unit_name': self.unit_name,
            'unit_type': self.unit_type,
            'created_at': self.created_at.isoformat() if self.created_at else None,
            'last_login': self.last_login.isoformat() if self.last_login else None
        }


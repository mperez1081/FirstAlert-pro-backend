import os
import sys
# DON'T CHANGE THIS !!!
sys.path.insert(0, os.path.dirname(os.path.dirname(__file__)))

from flask import Flask, send_from_directory
from flask_cors import CORS
from flask_socketio import SocketIO
from src.models.user import db
from src.models.incident import Incident, CallType, Unit
from src.routes.user import user_bp
from src.routes.incidents import incidents_bp
from src.routes.auth import auth_bp
from src.socketio_events import register_socketio_events

app = Flask(__name__, static_folder=os.path.join(os.path.dirname(__file__), 'static'))
app.config['SECRET_KEY'] = 'asdf#FGSgvasgf$5$WGT'

# Enable CORS for all routes
CORS(app, origins="*")

# Initialize Socket.IO
socketio = SocketIO(app, cors_allowed_origins="*", logger=True, engineio_logger=True)

# Register Socket.IO events
register_socketio_events(socketio)

# Register blueprints
app.register_blueprint(user_bp, url_prefix='/api')
app.register_blueprint(incidents_bp, url_prefix='/api')
app.register_blueprint(auth_bp, url_prefix='/api')

# Database configuration
app.config['SQLALCHEMY_DATABASE_URI'] = f"sqlite:///{os.path.join(os.path.dirname(__file__), 'database', 'app.db')}"
app.config['SQLALCHEMY_TRACK_MODIFICATIONS'] = False
db.init_app(app)

def initialize_default_data():
    """Initialize default units and call types"""
    
    # Create default call types
    default_call_types = [
        {'name': 'Structure Fire', 'default_priority': 1},
        {'name': 'Traffic Collision', 'default_priority': 2},
        {'name': 'Medical Emergency', 'default_priority': 1},
        {'name': 'Assault', 'default_priority': 2},
        {'name': 'Hazmat', 'default_priority': 1}
    ]
    
    for call_type_data in default_call_types:
        existing = CallType.query.filter_by(name=call_type_data['name']).first()
        if not existing:
            call_type = CallType(
                name=call_type_data['name'],
                default_priority=call_type_data['default_priority'],
                created_by='SYSTEM'
            )
            db.session.add(call_type)
    
    # Create default units
    # Fire Marshal Units (FM-1 to FM-25)
    for i in range(1, 26):
        unit_id = f'FM-{i}'
        existing = Unit.query.filter_by(unit_id=unit_id).first()
        if not existing:
            unit = Unit(
                unit_id=unit_id,
                unit_name=f'Fire Marshal {i}',
                unit_type='fire_marshal'
            )
            db.session.add(unit)
    
    # Dispatch Units (DISPATCH-1 to DISPATCH-5)
    for i in range(1, 6):
        unit_id = f'DISPATCH-{i}'
        existing = Unit.query.filter_by(unit_id=unit_id).first()
        if not existing:
            unit = Unit(
                unit_id=unit_id,
                unit_name=f'Dispatch {i}',
                unit_type='dispatch'
            )
            db.session.add(unit)
    
    # Admin Unit
    admin_unit = Unit.query.filter_by(unit_id='ADMIN').first()
    if not admin_unit:
        admin_unit = Unit(
            unit_id='ADMIN',
            unit_name='System Administrator',
            unit_type='admin'
        )
        db.session.add(admin_unit)
    
    db.session.commit()

with app.app_context():
    db.create_all()
    initialize_default_data()

# Socket.IO event handlers
@socketio.on('connect')
def handle_connect():
    print('Client connected')

@socketio.on('disconnect')
def handle_disconnect():
    print('Client disconnected')

@socketio.on('join_room')
def handle_join_room(data):
    """Join a room for real-time updates"""
    from flask_socketio import join_room
    room = data.get('room', 'general')
    join_room(room)
    print(f'Client joined room: {room}')

@socketio.on('incident_update')
def handle_incident_update(data):
    """Broadcast incident updates to all clients"""
    from flask_socketio import emit
    emit('incident_updated', data, broadcast=True)

@app.route('/', defaults={'path': ''})
@app.route('/<path:path>')
def serve(path):
    static_folder_path = app.static_folder
    if static_folder_path is None:
            return "Static folder not configured", 404

    if path != "" and os.path.exists(os.path.join(static_folder_path, path)):
        return send_from_directory(static_folder_path, path)
    else:
        index_path = os.path.join(static_folder_path, 'index.html')
        if os.path.exists(index_path):
            return send_from_directory(static_folder_path, 'index.html')
        else:
            return "index.html not found", 404


if __name__ == '__main__':
    socketio.run(app, host='0.0.0.0', port=5000, debug=True)


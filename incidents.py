from flask import Blueprint, request, jsonify, current_app
from flask_socketio import SocketIO
from src.models.incident import db, Incident, CallType
from src.middleware.auth import token_required, dispatch_or_admin_required, admin_required
from datetime import datetime
import json

incidents_bp = Blueprint('incidents', __name__)

def get_socketio():
    """Get the SocketIO instance from the current app"""
    return current_app.extensions.get('socketio')

@incidents_bp.route('/incidents', methods=['GET'])
@token_required
def get_incidents(current_user):
    """Get all active incidents"""
    try:
        incidents = Incident.query.filter_by(status='active').all()
        return jsonify([incident.to_dict() for incident in incidents])
    except Exception as e:
        return jsonify({'error': str(e)}), 500

@incidents_bp.route('/incidents', methods=['POST'])
@dispatch_or_admin_required
def create_incident(current_user):
    """Create a new incident (dispatch or admin only)"""
    try:
        data = request.get_json()
        
        incident = Incident(
            incident_type=data['incident_type'],
            location=data['location'],
            address=data['address'],
            priority=data['priority'],
            units_requested=data['units_requested'],
            pertinent_details=data.get('pertinent_details', ''),
            created_by=current_user['unit_id']
        )
        
        # Initialize empty timeline and responding units
        incident.set_timeline([])
        incident.set_responding_units([])
        
        db.session.add(incident)
        db.session.commit()
        
        # Emit real-time update
        socketio = get_socketio()
        if socketio:
            incident_data = incident.to_dict()
            socketio.emit('incident_created', incident_data, room='general')
            
            # Send push notifications to Fire Marshal units
            notification_data = {
                'type': 'new_incident',
                'title': 'New Emergency Call',
                'message': f'{incident.incident_type} at {incident.location}',
                'incident_id': incident.id,
                'priority': incident.priority
            }
            
            for i in range(1, 26):
                socketio.emit('push_notification', notification_data, room=f'user_FM-{i}')
        
        return jsonify(incident.to_dict()), 201
    except Exception as e:
        db.session.rollback()
        return jsonify({'error': str(e)}), 500

@incidents_bp.route('/incidents/<int:incident_id>', methods=['GET'])
def get_incident(incident_id):
    """Get a specific incident"""
    try:
        incident = Incident.query.get_or_404(incident_id)
        return jsonify(incident.to_dict())
    except Exception as e:
        return jsonify({'error': str(e)}), 500

@incidents_bp.route('/incidents/<int:incident_id>', methods=['PUT'])
def update_incident(incident_id):
    """Update an incident"""
    try:
        incident = Incident.query.get_or_404(incident_id)
        data = request.get_json()
        
        # Update fields if provided
        if 'incident_type' in data:
            incident.incident_type = data['incident_type']
        if 'location' in data:
            incident.location = data['location']
        if 'address' in data:
            incident.address = data['address']
        if 'priority' in data:
            incident.priority = data['priority']
        if 'units_requested' in data:
            incident.units_requested = data['units_requested']
        if 'pertinent_details' in data:
            incident.pertinent_details = data['pertinent_details']
        if 'status' in data:
            incident.status = data['status']
        
        db.session.commit()
        return jsonify(incident.to_dict())
    except Exception as e:
        db.session.rollback()
        return jsonify({'error': str(e)}), 500

@incidents_bp.route('/incidents/<int:incident_id>', methods=['DELETE'])
def delete_incident(incident_id):
    """Delete/Clear an incident"""
    try:
        incident = Incident.query.get_or_404(incident_id)
        incident.status = 'cleared'
        db.session.commit()
        return jsonify({'message': 'Incident cleared successfully'})
    except Exception as e:
        db.session.rollback()
        return jsonify({'error': str(e)}), 500

@incidents_bp.route('/incidents/<int:incident_id>/timeline', methods=['POST'])
def add_timeline_entry(incident_id):
    """Add entry to incident timeline"""
    try:
        incident = Incident.query.get_or_404(incident_id)
        data = request.get_json()
        
        # Get current timeline
        timeline = json.loads(incident.timeline) if incident.timeline else []
        
        # Add new entry
        new_entry = {
            'id': len(timeline) + 1,
            'timestamp': datetime.utcnow().isoformat(),
            'type': data['type'],  # note, photo, resource_request, status_update
            'content': data['content'],
            'user': data['user']
        }
        
        timeline.append(new_entry)
        incident.set_timeline(timeline)
        
        db.session.commit()
        return jsonify(incident.to_dict())
    except Exception as e:
        db.session.rollback()
        return jsonify({'error': str(e)}), 500

@incidents_bp.route('/incidents/<int:incident_id>/respond', methods=['POST'])
def respond_to_incident(incident_id):
    """Add responding unit to incident"""
    try:
        incident = Incident.query.get_or_404(incident_id)
        data = request.get_json()
        
        # Get current responding units
        responding_units = json.loads(incident.responding_units) if incident.responding_units else []
        
        # Add new responding unit
        new_unit = {
            'user_id': data['user_id'],
            'unit_number': data['unit_number'],
            'status': 'responding',
            'responded_at': datetime.utcnow().isoformat(),
            'on_scene_at': None,
            'cleared_at': None
        }
        
        # Check if unit already responding
        existing_unit = next((unit for unit in responding_units if unit['user_id'] == data['user_id']), None)
        if existing_unit:
            return jsonify({'error': 'Unit already responding to this incident'}), 400
        
        responding_units.append(new_unit)
        incident.set_responding_units(responding_units)
        
        # Add timeline entry
        timeline = json.loads(incident.timeline) if incident.timeline else []
        timeline.append({
            'id': len(timeline) + 1,
            'timestamp': datetime.utcnow().isoformat(),
            'type': 'status_update',
            'content': f'{data["user_id"]} ({data["unit_number"]}) responding to call',
            'user': data['user_id']
        })
        incident.set_timeline(timeline)
        
        db.session.commit()
        return jsonify(incident.to_dict())
    except Exception as e:
        db.session.rollback()
        return jsonify({'error': str(e)}), 500

@incidents_bp.route('/incidents/<int:incident_id>/status', methods=['PATCH'])
def update_unit_status(incident_id):
    """Update unit status (on scene, clear)"""
    try:
        incident = Incident.query.get_or_404(incident_id)
        data = request.get_json()
        
        # Get current responding units
        responding_units = json.loads(incident.responding_units) if incident.responding_units else []
        
        # Find and update unit status
        unit_found = False
        for unit in responding_units:
            if unit['user_id'] == data['user_id']:
                unit_found = True
                if data['status'] == 'on_scene':
                    unit['status'] = 'on_scene'
                    unit['on_scene_at'] = datetime.utcnow().isoformat()
                elif data['status'] == 'clear':
                    unit['status'] = 'clear'
                    unit['cleared_at'] = datetime.utcnow().isoformat()
                break
        
        if not unit_found:
            return jsonify({'error': 'Unit not found in responding units'}), 404
        
        incident.set_responding_units(responding_units)
        
        # Add timeline entry
        timeline = json.loads(incident.timeline) if incident.timeline else []
        status_text = 'on scene' if data['status'] == 'on_scene' else 'cleared from call'
        timeline.append({
            'id': len(timeline) + 1,
            'timestamp': datetime.utcnow().isoformat(),
            'type': 'status_update',
            'content': f'{data["user_id"]} marked {status_text}',
            'user': data['user_id']
        })
        incident.set_timeline(timeline)
        
        db.session.commit()
        return jsonify(incident.to_dict())
    except Exception as e:
        db.session.rollback()
        return jsonify({'error': str(e)}), 500

@incidents_bp.route('/call-types', methods=['GET'])
def get_call_types():
    """Get all call types"""
    try:
        call_types = CallType.query.all()
        return jsonify([call_type.to_dict() for call_type in call_types])
    except Exception as e:
        return jsonify({'error': str(e)}), 500

@incidents_bp.route('/call-types', methods=['POST'])
def create_call_type():
    """Create a new call type (admin only)"""
    try:
        data = request.get_json()
        
        call_type = CallType(
            name=data['name'],
            default_priority=data['default_priority'],
            created_by=data['created_by']
        )
        
        db.session.add(call_type)
        db.session.commit()
        
        return jsonify(call_type.to_dict()), 201
    except Exception as e:
        db.session.rollback()
        return jsonify({'error': str(e)}), 500

@incidents_bp.route('/call-types/<int:call_type_id>', methods=['DELETE'])
def delete_call_type(call_type_id):
    """Delete a call type (admin only)"""
    try:
        call_type = CallType.query.get_or_404(call_type_id)
        db.session.delete(call_type)
        db.session.commit()
        return jsonify({'message': 'Call type deleted successfully'})
    except Exception as e:
        db.session.rollback()
        return jsonify({'error': str(e)}), 500


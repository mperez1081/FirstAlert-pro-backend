from flask_socketio import emit, join_room, leave_room
from src.models.incident import db, Incident
import json

def register_socketio_events(socketio):
    """Register all Socket.IO event handlers"""
    
    @socketio.on('connect')
    def handle_connect():
        print('Client connected')
        emit('connected', {'message': 'Connected to FirstAlert Pro server'})
    
    @socketio.on('disconnect')
    def handle_disconnect():
        print('Client disconnected')
    
    @socketio.on('join_user_room')
    def handle_join_user_room(data):
        """Join user-specific room for targeted notifications"""
        user_id = data.get('user_id')
        if user_id:
            join_room(f'user_{user_id}')
            print(f'User {user_id} joined their room')
    
    @socketio.on('join_general_room')
    def handle_join_general_room():
        """Join general room for broadcast notifications"""
        join_room('general')
        print('Client joined general room')
    
    @socketio.on('leave_user_room')
    def handle_leave_user_room(data):
        """Leave user-specific room"""
        user_id = data.get('user_id')
        if user_id:
            leave_room(f'user_{user_id}')
            print(f'User {user_id} left their room')
    
    @socketio.on('incident_created')
    def handle_incident_created(data):
        """Broadcast new incident to all users"""
        print(f'Broadcasting new incident: {data.get("incident_id")}')
        emit('new_incident', data, room='general')
        
        # Send push notification to all Fire Marshal units
        fire_marshal_notification = {
            'type': 'new_incident',
            'title': 'New Emergency Call',
            'message': f'{data.get("incident_type")} at {data.get("location")}',
            'incident_id': data.get('incident_id'),
            'priority': data.get('priority')
        }
        
        # Emit to all Fire Marshal users (FM-1 through FM-25)
        for i in range(1, 26):
            emit('push_notification', fire_marshal_notification, room=f'user_FM-{i}')
    
    @socketio.on('incident_updated')
    def handle_incident_updated(data):
        """Broadcast incident updates to all users"""
        print(f'Broadcasting incident update: {data.get("incident_id")}')
        emit('incident_update', data, room='general')
    
    @socketio.on('unit_responded')
    def handle_unit_responded(data):
        """Broadcast unit response to incident"""
        print(f'Unit {data.get("user_id")} responded to incident {data.get("incident_id")}')
        
        # Notify all users about the response
        response_notification = {
            'type': 'unit_response',
            'message': f'{data.get("user_id")} ({data.get("unit_number")}) responding to call',
            'incident_id': data.get('incident_id'),
            'user_id': data.get('user_id'),
            'unit_number': data.get('unit_number')
        }
        
        emit('unit_response', response_notification, room='general')
        
        # Send specific notification to dispatch units
        dispatch_notification = {
            'type': 'unit_response',
            'title': 'Unit Response',
            'message': f'{data.get("user_id")} responding to {data.get("incident_type")}',
            'incident_id': data.get('incident_id')
        }
        
        for i in range(1, 6):
            emit('push_notification', dispatch_notification, room=f'user_DISPATCH-{i}')
    
    @socketio.on('status_updated')
    def handle_status_updated(data):
        """Broadcast status updates (on scene, clear)"""
        print(f'Status update: {data.get("user_id")} - {data.get("status")}')
        
        status_text = {
            'on_scene': 'on scene',
            'clear': 'cleared from call'
        }.get(data.get('status'), data.get('status'))
        
        status_notification = {
            'type': 'status_update',
            'message': f'{data.get("user_id")} marked {status_text}',
            'incident_id': data.get('incident_id'),
            'user_id': data.get('user_id'),
            'status': data.get('status')
        }
        
        emit('status_update', status_notification, room='general')
    
    @socketio.on('timeline_updated')
    def handle_timeline_updated(data):
        """Broadcast timeline updates (notes, photos, resource requests)"""
        print(f'Timeline update for incident {data.get("incident_id")}')
        
        timeline_notification = {
            'type': 'timeline_update',
            'incident_id': data.get('incident_id'),
            'entry': data.get('entry'),
            'user_id': data.get('user_id')
        }
        
        emit('timeline_update', timeline_notification, room='general')
        
        # If it's a resource request, notify dispatch
        if data.get('entry', {}).get('type') == 'resource_request':
            resource_notification = {
                'type': 'resource_request',
                'title': 'Resource Request',
                'message': f'{data.get("user_id")} requested {data.get("entry", {}).get("content")}',
                'incident_id': data.get('incident_id')
            }
            
            for i in range(1, 6):
                emit('push_notification', resource_notification, room=f'user_DISPATCH-{i}')
    
    @socketio.on('call_type_updated')
    def handle_call_type_updated(data):
        """Broadcast call type changes (admin only)"""
        print(f'Call type updated by admin: {data.get("action")}')
        
        call_type_notification = {
            'type': 'call_type_update',
            'action': data.get('action'),  # 'added' or 'removed'
            'call_type': data.get('call_type'),
            'admin_user': data.get('admin_user')
        }
        
        emit('call_type_update', call_type_notification, room='general')
    
    @socketio.on('unit_name_updated')
    def handle_unit_name_updated(data):
        """Broadcast unit name changes (admin only)"""
        print(f'Unit name updated by admin: {data.get("unit_id")}')
        
        unit_update_notification = {
            'type': 'unit_name_update',
            'unit_id': data.get('unit_id'),
            'new_name': data.get('new_name'),
            'admin_user': data.get('admin_user')
        }
        
        emit('unit_name_update', unit_update_notification, room='general')
    
    @socketio.on('request_incident_sync')
    def handle_request_incident_sync():
        """Send current incidents to requesting client"""
        try:
            incidents = Incident.query.filter_by(status='active').all()
            incidents_data = [incident.to_dict() for incident in incidents]
            emit('incident_sync', {'incidents': incidents_data})
        except Exception as e:
            emit('error', {'message': f'Failed to sync incidents: {str(e)}'})
    
    @socketio.on('ping')
    def handle_ping():
        """Handle ping for connection testing"""
        emit('pong', {'timestamp': str(datetime.utcnow())})

def broadcast_incident_update(socketio, incident_data, event_type='incident_update'):
    """Helper function to broadcast incident updates"""
    socketio.emit(event_type, incident_data, room='general')

def send_push_notification(socketio, user_id, notification_data):
    """Helper function to send push notification to specific user"""
    socketio.emit('push_notification', notification_data, room=f'user_{user_id}')


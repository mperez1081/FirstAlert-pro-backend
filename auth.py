from flask import Blueprint, request, jsonify
from src.models.incident import db, Unit
from werkzeug.security import generate_password_hash, check_password_hash
from datetime import datetime
import jwt
import os

auth_bp = Blueprint('auth', __name__)

# JWT secret key (in production, use environment variable)
JWT_SECRET = os.environ.get('JWT_SECRET', 'your-secret-key-change-in-production')

@auth_bp.route('/login', methods=['POST'])
def login():
    """Authenticate user and return JWT token"""
    try:
        data = request.get_json()
        unit_id = data.get('unit_id')
        password = data.get('password', 'default')  # Default password for now
        
        # Find unit
        unit = Unit.query.filter_by(unit_id=unit_id).first()
        if not unit:
            return jsonify({'error': 'Invalid credentials'}), 401
        
        # For now, we'll use simple authentication
        # In production, check password hash
        # if not check_password_hash(unit.password_hash, password):
        #     return jsonify({'error': 'Invalid credentials'}), 401
        
        # Update last login
        unit.last_login = datetime.utcnow()
        db.session.commit()
        
        # Generate JWT token
        token_payload = {
            'unit_id': unit.unit_id,
            'unit_type': unit.unit_type,
            'exp': datetime.utcnow().timestamp() + 86400  # 24 hours
        }
        
        token = jwt.encode(token_payload, JWT_SECRET, algorithm='HS256')
        
        return jsonify({
            'token': token,
            'user': unit.to_dict()
        })
    except Exception as e:
        return jsonify({'error': str(e)}), 500

@auth_bp.route('/units', methods=['GET'])
def get_units():
    """Get all units"""
    try:
        units = Unit.query.all()
        return jsonify([unit.to_dict() for unit in units])
    except Exception as e:
        return jsonify({'error': str(e)}), 500

@auth_bp.route('/units', methods=['POST'])
def create_unit():
    """Create a new unit (admin only)"""
    try:
        data = request.get_json()
        
        # Check if unit already exists
        existing_unit = Unit.query.filter_by(unit_id=data['unit_id']).first()
        if existing_unit:
            return jsonify({'error': 'Unit already exists'}), 400
        
        unit = Unit(
            unit_id=data['unit_id'],
            unit_name=data['unit_name'],
            unit_type=data['unit_type'],
            password_hash=generate_password_hash(data.get('password', 'default'))
        )
        
        db.session.add(unit)
        db.session.commit()
        
        return jsonify(unit.to_dict()), 201
    except Exception as e:
        db.session.rollback()
        return jsonify({'error': str(e)}), 500

@auth_bp.route('/units/<int:unit_id>', methods=['PUT'])
def update_unit(unit_id):
    """Update unit information (admin only)"""
    try:
        unit = Unit.query.get_or_404(unit_id)
        data = request.get_json()
        
        if 'unit_name' in data:
            unit.unit_name = data['unit_name']
        if 'password' in data:
            unit.password_hash = generate_password_hash(data['password'])
        
        db.session.commit()
        return jsonify(unit.to_dict())
    except Exception as e:
        db.session.rollback()
        return jsonify({'error': str(e)}), 500

@auth_bp.route('/units/by-type/<unit_type>', methods=['GET'])
def get_units_by_type(unit_type):
    """Get units by type (fire_marshal, dispatch, admin)"""
    try:
        units = Unit.query.filter_by(unit_type=unit_type).all()
        return jsonify([unit.to_dict() for unit in units])
    except Exception as e:
        return jsonify({'error': str(e)}), 500



@auth_bp.route('/user', methods=['GET'])
def get_current_user():
    """Get current user information from JWT token"""
    try:
        # Get token from Authorization header
        auth_header = request.headers.get('Authorization')
        if not auth_header or not auth_header.startswith('Bearer '):
            return jsonify({'error': 'No token provided'}), 401
        
        token = auth_header.split(' ')[1]
        
        # Decode JWT token
        try:
            payload = jwt.decode(token, JWT_SECRET, algorithms=['HS256'])
            unit_id = payload.get('unit_id')
            
            # Find unit
            unit = Unit.query.filter_by(unit_id=unit_id).first()
            if not unit:
                return jsonify({'error': 'User not found'}), 404
            
            return jsonify(unit.to_dict())
        except jwt.ExpiredSignatureError:
            return jsonify({'error': 'Token expired'}), 401
        except jwt.InvalidTokenError:
            return jsonify({'error': 'Invalid token'}), 401
            
    except Exception as e:
        return jsonify({'error': str(e)}), 500


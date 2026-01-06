"""
Personnel Routes - API endpoints for user management and authentication
"""
from flask import Blueprint, request, jsonify
from flasgger import swag_from
from services.personnel_service import personnel_service
from services.face_service import face_service

personnel_bp = Blueprint('personnel', __name__, url_prefix='/api/personnel')


@personnel_bp.route('/register', methods=['POST'])
def register():
    """
    Register new personnel
    ---
    tags:
      - Personnel
    consumes:
      - application/json
    parameters:
      - in: body
        name: body
        required: true
        schema:
          type: object
          required:
            - user_id
            - name
            - password
          properties:
            user_id:
              type: string
              description: Unique user identifier
              example: "kopral_budi"
            name:
              type: string
              description: Full name
              example: "Budi Santoso"
            password:
              type: string
              description: User password
              example: "password123"
            role:
              type: string
              description: User role
              example: "User"
              default: "User"
            permissions:
              type: object
              description: Permission settings
              example:
                use_gun: true
                query: false
                approval: false
                system_management: false
    responses:
      200:
        description: Registration successful
        schema:
          type: object
          properties:
            success:
              type: boolean
            message:
              type: string
            user:
              type: object
      400:
        description: Registration failed
    """
    data = request.get_json()
    
    if not data:
        return jsonify({'success': False, 'error': 'No data provided'}), 400
    
    user_id = data.get('user_id')
    name = data.get('name')
    password = data.get('password')
    role = data.get('role', 'User')
    permissions = data.get('permissions')
    
    if not all([user_id, name, password]):
        return jsonify({
            'success': False, 
            'error': 'user_id, name, and password are required'
        }), 400
    
    result = personnel_service.register(
        user_id=user_id,
        name=name,
        password=password,
        role=role,
        permissions=permissions
    )
    
    status_code = 200 if result['success'] else 400
    return jsonify(result), status_code


@personnel_bp.route('/login', methods=['POST'])
def login():
    """
    Login with user_id and password
    ---
    tags:
      - Personnel
    consumes:
      - application/json
    parameters:
      - in: body
        name: body
        required: true
        schema:
          type: object
          required:
            - user_id
            - password
          properties:
            user_id:
              type: string
              description: User identifier
              example: "kopral_budi"
            password:
              type: string
              description: User password
              example: "password123"
    responses:
      200:
        description: Login successful
        schema:
          type: object
          properties:
            success:
              type: boolean
            message:
              type: string
            user:
              type: object
      401:
        description: Login failed
    """
    data = request.get_json()
    
    if not data:
        return jsonify({'success': False, 'error': 'No data provided'}), 400
    
    user_id = data.get('user_id')
    password = data.get('password')
    
    if not all([user_id, password]):
        return jsonify({
            'success': False, 
            'error': 'user_id and password are required'
        }), 400
    
    result = personnel_service.login(user_id=user_id, password=password)
    
    status_code = 200 if result['success'] else 401
    return jsonify(result), status_code


@personnel_bp.route('/list', methods=['GET'])
def list_personnel():
    """
    List all registered personnel
    ---
    tags:
      - Personnel
    responses:
      200:
        description: List of personnel
        schema:
          type: object
          properties:
            success:
              type: boolean
            count:
              type: integer
            personnel:
              type: array
              items:
                type: object
    """
    personnel = personnel_service.list_all()
    return jsonify({
        'success': True,
        'count': len(personnel),
        'personnel': personnel
    })


@personnel_bp.route('/<user_id>', methods=['GET'])
def get_personnel(user_id):
    """
    Get personnel by user_id
    ---
    tags:
      - Personnel
    parameters:
      - in: path
        name: user_id
        type: string
        required: true
        description: User identifier
    responses:
      200:
        description: Personnel data
      404:
        description: User not found
    """
    personnel = personnel_service.get_by_user_id(user_id)
    
    if personnel:
        return jsonify({'success': True, 'user': personnel})
    else:
        return jsonify({'success': False, 'error': 'User not found'}), 404


@personnel_bp.route('/<user_id>', methods=['PUT'])
def update_personnel(user_id):
    """
    Update personnel data
    ---
    tags:
      - Personnel
    parameters:
      - in: path
        name: user_id
        type: string
        required: true
      - in: body
        name: body
        schema:
          type: object
          properties:
            name:
              type: string
            role:
              type: string
            password:
              type: string
            permissions:
              type: object
    responses:
      200:
        description: Update successful
      400:
        description: Update failed
    """
    data = request.get_json()
    
    if not data:
        return jsonify({'success': False, 'error': 'No data provided'}), 400
    
    result = personnel_service.update(user_id, **data)
    
    status_code = 200 if result['success'] else 400
    return jsonify(result), status_code


@personnel_bp.route('/<user_id>', methods=['DELETE'])
def delete_personnel(user_id):
    """
    Delete personnel by user_id
    ---
    tags:
      - Personnel
    parameters:
      - in: path
        name: user_id
        type: string
        required: true
    responses:
      200:
        description: Delete successful
      404:
        description: User not found
    """
    # Also delete associated face
    face_service.delete_face_by_user_id(user_id)
    
    result = personnel_service.delete(user_id)
    
    status_code = 200 if result['success'] else 404
    return jsonify(result), status_code


@personnel_bp.route('/register-with-face', methods=['POST'])
def register_with_face():
    """
    Register personnel with face in one request
    ---
    tags:
      - Personnel
    consumes:
      - application/json
    parameters:
      - in: body
        name: body
        required: true
        schema:
          type: object
          required:
            - user_id
            - name
            - password
            - image
          properties:
            user_id:
              type: string
              example: "kopral_budi"
            name:
              type: string
              example: "Budi Santoso"
            password:
              type: string
              example: "password123"
            image:
              type: string
              description: Base64 encoded face image
            role:
              type: string
              default: "User"
            permissions:
              type: object
    responses:
      200:
        description: Registration successful with face
      400:
        description: Registration failed
    """
    data = request.get_json()
    
    if not data:
        return jsonify({'success': False, 'error': 'No data provided'}), 400
    
    user_id = data.get('user_id')
    name = data.get('name')
    password = data.get('password')
    image = data.get('image')
    role = data.get('role', 'User')
    permissions = data.get('permissions')
    
    if not all([user_id, name, password, image]):
        return jsonify({
            'success': False, 
            'error': 'user_id, name, password, and image are required'
        }), 400
    
    # 1. Register personnel
    personnel_result = personnel_service.register(
        user_id=user_id,
        name=name,
        password=password,
        role=role,
        permissions=permissions
    )
    
    if not personnel_result['success']:
        return jsonify(personnel_result), 400
    
    # 2. Register face
    face_result = face_service.register_face(
        base64_image=image,
        user_id=user_id,
        name=name
    )
    
    if face_result['success']:
        # Mark face as registered
        personnel_service.update(user_id, has_face=True)
    
    return jsonify({
        'success': True,
        'message': 'Personnel registered with face',
        'user': personnel_result['user'],
        'face': face_result
    })

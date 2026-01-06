"""
WSS Face Recognition Backend - Main Application

Flask server dengan Swagger documentation untuk face recognition.
"""
import os
from flask import Flask, jsonify
from flask_cors import CORS
from flasgger import Swagger

from config import get_config
from models.database import db, init_db
from routes.face_routes import face_bp
from routes.personnel_routes import personnel_bp

def create_app():
    """Create and configure Flask application"""
    
    # Initialize Flask
    app = Flask(__name__)
    
    # Load configuration
    config = get_config()
    app.config.from_object(config)
    
    # Ensure upload folder exists
    os.makedirs(app.config.get('UPLOAD_FOLDER', 'uploads'), exist_ok=True)
    
    # Initialize CORS
    CORS(app, origins=app.config.get('CORS_ORIGINS', '*'))
    
    # Initialize Database
    app.config['SQLALCHEMY_DATABASE_URI'] = config.DATABASE_URL
    app.config['SQLALCHEMY_TRACK_MODIFICATIONS'] = False
    db.init_app(app)
    
    # Initialize Swagger
    swagger_config = {
        "headers": [],
        "specs": [
            {
                "endpoint": 'apispec',
                "route": '/apispec.json',
                "rule_filter": lambda rule: True,
                "model_filter": lambda tag: True,
            }
        ],
        "static_url_path": "/flasgger_static",
        "swagger_ui": True,
        "specs_route": "/swagger"
    }
    
    swagger_template = {
        "swagger": "2.0",
        "info": {
            "title": "WSS Face Recognition API",
            "description": """
## API untuk Face Recognition

Backend ini menyediakan:
- **Registrasi Wajah**: Simpan face encoding ke database
- **Verifikasi Wajah**: Cocokkan wajah dengan database
- **Manajemen Wajah**: List dan hapus wajah

### Cara Kerja
1. Client kirim gambar (base64)
2. Backend extract face encoding menggunakan dlib
3. Encoding disimpan/dicocokkan dengan database PostgreSQL
            """,
            "version": "1.0.0",
            "contact": {
                "name": "WSS Team",
                "email": "ametsuramet@gmail.com"
            }
        },
        "host": "localhost:5000",
        "basePath": "/api",
        "schemes": ["http", "https"],
        "tags": [
            {
                "name": "Personnel",
                "description": "User management and authentication"
            },
            {
                "name": "Face",
                "description": "Face recognition operations"
            },
            {
                "name": "Health",
                "description": "Health check"
            }
        ]
    }
    
    Swagger(app, config=swagger_config, template=swagger_template)
    
    # Register blueprints
    app.register_blueprint(face_bp, url_prefix='/api/face')
    app.register_blueprint(personnel_bp)
    
    # Health check route
    @app.route('/api/health', methods=['GET'])
    def health_check():
        """
        Health Check
        ---
        tags:
          - Health
        responses:
          200:
            description: Server is healthy
            schema:
              type: object
              properties:
                status:
                  type: string
                  example: healthy
                message:
                  type: string
                  example: WSS Face Recognition Backend is running
        """
        return jsonify({
            'status': 'healthy',
            'message': 'WSS Face Recognition Backend is running'
        })
    
    # Root route
    @app.route('/', methods=['GET'])
    def index():
        return jsonify({
            'name': 'WSS Face Recognition Backend',
            'version': '1.0.0',
            'swagger': '/swagger',
            'health': '/api/health'
        })
    
    # Create tables
    with app.app_context():
        init_db()
    
    return app


if __name__ == '__main__':
    app = create_app()
    config = get_config()
    
    print(f"""
╔══════════════════════════════════════════════════════════╗
║       WSS Face Recognition Backend                       ║
╠══════════════════════════════════════════════════════════╣
║  Server:  http://{config.HOST}:{config.PORT}                          ║
║  Swagger: http://{config.HOST}:{config.PORT}/swagger                  ║
║  Health:  http://{config.HOST}:{config.PORT}/api/health               ║
╚══════════════════════════════════════════════════════════╝
    """)
    
    app.run(
        host=config.HOST,
        port=config.PORT,
        debug=config.DEBUG
    )

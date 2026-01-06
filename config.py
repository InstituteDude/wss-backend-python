"""
Configuration for WSS Face Recognition Backend
"""
import os
from dotenv import load_dotenv

load_dotenv()

class Config:
    """Base configuration"""
    
    # Flask
    SECRET_KEY = os.getenv('SECRET_KEY', 'wss-face-recognition-secret-key-2024')
    DEBUG = os.getenv('DEBUG', 'True').lower() == 'true'
    
    # Server
    HOST = os.getenv('HOST', '0.0.0.0')
    PORT = int(os.getenv('PORT', 5000))
    
    # Database (PostgreSQL)
    DATABASE_URL = os.getenv(
        'DATABASE_URL', 
        'postgresql://postgres:postgres@localhost:5432/wss_face_recognition'
    )
    
    # Face Recognition Settings
    FACE_RECOGNITION_TOLERANCE = float(os.getenv('FACE_TOLERANCE', 0.6))
    # Lower = more strict, Higher = more lenient
    # Default 0.6 is good balance
    
    # Upload settings
    UPLOAD_FOLDER = os.path.join(os.path.dirname(__file__), 'uploads')
    MAX_CONTENT_LENGTH = 16 * 1024 * 1024  # 16MB max file size
    ALLOWED_EXTENSIONS = {'png', 'jpg', 'jpeg', 'gif'}
    
    # CORS
    CORS_ORIGINS = os.getenv('CORS_ORIGINS', '*')
    
    # Go Backend Integration (Main Backend)
    # Python forwards face encodings to Go for storage/verification
    GO_BACKEND_URL = os.getenv('GO_BACKEND_URL', 'http://localhost:9876')
    GO_API_KEY = os.getenv('GO_API_KEY', '')  # For /api/biometrics/verify endpoint


class DevelopmentConfig(Config):
    """Development configuration"""
    DEBUG = True


class ProductionConfig(Config):
    """Production configuration"""
    DEBUG = False


# Export config based on environment
config = {
    'development': DevelopmentConfig,
    'production': ProductionConfig,
    'default': DevelopmentConfig
}

def get_config():
    """Get configuration based on environment"""
    env = os.getenv('FLASK_ENV', 'development')
    return config.get(env, config['default'])

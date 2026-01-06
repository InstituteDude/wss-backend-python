"""
Personnel Model - User management with password hashing
"""
from datetime import datetime
from werkzeug.security import generate_password_hash, check_password_hash
from models.database import db
import json


class Personnel(db.Model):
    """Model for storing personnel/user data"""
    __tablename__ = 'personnel'
    
    id = db.Column(db.Integer, primary_key=True)
    user_id = db.Column(db.String(100), unique=True, nullable=False, index=True)
    name = db.Column(db.String(255), nullable=False)
    password_hash = db.Column(db.String(255), nullable=False)
    role = db.Column(db.String(50), default='User')
    permissions = db.Column(db.Text, nullable=True)  # JSON string
    has_face = db.Column(db.Boolean, default=False)
    has_fingerprint = db.Column(db.Boolean, default=False)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    updated_at = db.Column(db.DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)
    
    def set_password(self, password: str):
        """Hash and store password"""
        self.password_hash = generate_password_hash(password)
    
    def check_password(self, password: str) -> bool:
        """Verify password against hash"""
        return check_password_hash(self.password_hash, password)
    
    def set_permissions(self, permissions: dict):
        """Store permissions as JSON"""
        self.permissions = json.dumps(permissions)
    
    def get_permissions(self) -> dict:
        """Get permissions as dict"""
        if self.permissions:
            return json.loads(self.permissions)
        return {
            'use_gun': True,
            'query': False,
            'approval': False,
            'system_management': False
        }
    
    def to_dict(self) -> dict:
        """Convert to dictionary (without password)"""
        return {
            'id': self.id,
            'user_id': self.user_id,
            'name': self.name,
            'role': self.role,
            'permissions': self.get_permissions(),
            'has_face': self.has_face,
            'has_fingerprint': self.has_fingerprint,
            'created_at': self.created_at.isoformat() if self.created_at else None,
            'updated_at': self.updated_at.isoformat() if self.updated_at else None,
        }
    
    def __repr__(self):
        return f'<Personnel {self.user_id}: {self.name}>'

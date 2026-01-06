"""
Database Models untuk Face Recognition

Menyimpan face encodings di PostgreSQL.
Face encoding adalah array 128 angka yang merepresentasikan wajah.
"""
from flask_sqlalchemy import SQLAlchemy
from datetime import datetime
import json
import numpy as np

db = SQLAlchemy()


class FaceEncoding(db.Model):
    """
    Model untuk menyimpan face encoding
    
    Setiap wajah direpresentasikan sebagai array 128 float numbers.
    Array ini disimpan sebagai JSON string di database.
    """
    __tablename__ = 'face_encodings'
    
    id = db.Column(db.Integer, primary_key=True)
    
    # User identification
    user_id = db.Column(db.String(100), nullable=False, index=True)
    name = db.Column(db.String(255), nullable=False)
    
    # Face encoding (128 numbers stored as JSON)
    encoding = db.Column(db.Text, nullable=False)
    
    # Metadata
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    updated_at = db.Column(db.DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)
    
    # Optional: store original image path
    image_path = db.Column(db.String(500), nullable=True)
    
    def __repr__(self):
        return f'<FaceEncoding {self.user_id}: {self.name}>'
    
    def set_encoding(self, encoding_array):
        """
        Set face encoding dari numpy array
        
        Args:
            encoding_array: numpy array of 128 floats
        """
        if isinstance(encoding_array, np.ndarray):
            self.encoding = json.dumps(encoding_array.tolist())
        else:
            self.encoding = json.dumps(list(encoding_array))
    
    def get_encoding(self):
        """
        Get face encoding sebagai numpy array
        
        Returns:
            numpy array of 128 floats
        """
        return np.array(json.loads(self.encoding))
    
    def to_dict(self):
        """Convert to dictionary for API response"""
        return {
            'id': self.id,
            'user_id': self.user_id,
            'name': self.name,
            'created_at': self.created_at.isoformat() if self.created_at else None,
            'updated_at': self.updated_at.isoformat() if self.updated_at else None
        }


def init_db():
    """Initialize database tables"""
    db.create_all()
    print("[Database] Tables created successfully!")

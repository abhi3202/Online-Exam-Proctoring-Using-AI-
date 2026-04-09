from sqlalchemy import Column, Integer, String, Boolean, DateTime, Text, ForeignKey
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy.orm import relationship
from datetime import datetime

Base = declarative_base()

class User(Base):
    __tablename__ = 'users'

    id = Column(Integer, primary_key=True)
    name = Column(String(100), nullable=False)
    email = Column(String(100), unique=True, nullable=False)
    password = Column(String(255), nullable=False)
    role = Column(String(20), default='student')

    labels = relationship("Label", back_populates="labeler")

class Label(Base):
    __tablename__ = 'labels'

    id = Column(Integer, primary_key=True)
    session_dir = Column(String(255), nullable=False, index=True)
    violation_timestamp = Column(String(50), nullable=False, index=True)
    violation_type = Column(String(100), nullable=False)
    human_true = Column(Boolean, nullable=False)
    confidence = Column(String(10))
    notes = Column(Text)
    labeled_at = Column(DateTime, default=datetime.utcnow)
    labeler_id = Column(Integer, ForeignKey('users.id'))
    
    labeler = relationship("User", back_populates="labels")

print("Models defined: User, Label")


from sqlalchemy import Column, Integer, String, DateTime, Numeric, ForeignKey, Enum
from sqlalchemy.orm import relationship
from datetime import datetime
from database import Base
import enum

class ShiftStatus(str, enum.Enum):
    OPEN = "OPEN"
    CLOSED = "CLOSED"

class Merchant(Base):
    __tablename__ = "merchants"
    id = Column(Integer, primary_key=True, index=True)
    name = Column(String(255), nullable=False)
    
    shifts = relationship("Shift", back_populates="merchant")

class User(Base):
    __tablename__ = "users"
    id = Column(Integer, primary_key=True, index=True)
    username = Column(String(50), unique=True, index=True)

class MerchantUser(Base):
    __tablename__ = "merchant_users"
    id = Column(Integer, primary_key=True, index=True)
    merchant_id = Column(Integer, ForeignKey("merchants.id"))
    user_id = Column(Integer, ForeignKey("users.id"))
    role = Column(String(50)) # CASHIER, REVIEWER, OWNER

class Shift(Base):
    __tablename__ = "shifts"
    id = Column(Integer, primary_key=True, index=True)
    merchant_id = Column(Integer, ForeignKey("merchants.id"))
    shift_code = Column(String(50), unique=True, nullable=False)
    target_revenue = Column(Numeric(18, 2), default=0) # P1-01: Chỉ tiêu tham khảo
    status = Column(Enum(ShiftStatus), default=ShiftStatus.OPEN)
    opened_at = Column(DateTime, default=datetime.utcnow)
    closed_at = Column(DateTime, nullable=True)

    merchant = relationship("Merchant", back_populates="shifts")
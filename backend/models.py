from sqlalchemy import Column, Integer, String, Unicode, DateTime, Numeric, ForeignKey, Boolean, Enum
from sqlalchemy.orm import relationship
from datetime import datetime
from database import Base
import enum


class ShiftStatus(str, enum.Enum):
    DRAFT = 'DRAFT'
    OPEN = 'OPEN'
    CLOSED = 'CLOSED'
    CANCELLED = 'CANCELLED'


class OrderStatus(str, enum.Enum):
    DRAFT = 'DRAFT'
    CONFIRMED_ORDER = 'CONFIRMED_ORDER'
    UNDER_REVIEW = 'UNDER_REVIEW'
    CANCELLED_ORDER = 'CANCELLED_ORDER'


class PaymentStatus(str, enum.Enum):
    UNPAID = 'UNPAID'
    PARTIALLY_PAID = 'PARTIALLY_PAID'
    PAID = 'PAID'


class PaymentRequestStatus(str, enum.Enum):
    ACTIVE = 'ACTIVE'
    FULFILLED = 'FULFILLED'
    EXPIRED = 'EXPIRED'
    REVOKED = 'REVOKED'


class MatchStatus(str, enum.Enum):
    UNMATCHED = 'UNMATCHED'
    PARTIALLY_ALLOCATED = 'PARTIALLY_ALLOCATED'
    FULLY_ALLOCATED = 'FULLY_ALLOCATED'
    REJECTED_TX = 'REJECTED_TX'


class EntryType(str, enum.Enum):
    ALLOCATION = 'ALLOCATION'
    REVERSAL = 'REVERSAL'


class AllocationMode(str, enum.Enum):
    AUTO = 'AUTO'
    MANUAL = 'MANUAL'
    REVERSAL = 'REVERSAL'


class DecisionType(str, enum.Enum):
    APPROVE_MANUAL_MATCH = 'APPROVE_MANUAL_MATCH'
    REVERSE_ALLOCATION = 'REVERSE_ALLOCATION'
    REQUEST_INFO = 'REQUEST_INFO'
    REJECT_TX = 'REJECT_TX'
    OVERPAYMENT_RESOLUTION = 'OVERPAYMENT_RESOLUTION'


class User(Base):
    __tablename__ = "users"
    id = Column(Integer, primary_key=True, index=True)
    full_name = Column(Unicode(100), nullable=False)
    email = Column(String(100), unique=True, nullable=False)
    password_hash = Column(String(255), nullable=False)
    webauthn_credential_id = Column(Unicode(255), nullable=True)
    webauthn_public_key = Column(Unicode, nullable=True)
    current_challenge = Column(Unicode(255), nullable=True)
    created_at = Column(DateTime, default=datetime.utcnow)


class Merchant(Base):
    __tablename__ = "merchants"
    id = Column(Integer, primary_key=True, index=True)
    merchant_code = Column(String(30), unique=True, nullable=False)
    name = Column(Unicode(150), nullable=False)
    bank_bin = Column(String(20), nullable=False)
    account_no = Column(String(50), nullable=False)
    webhook_secret = Column(String(100), nullable=False)
    created_at = Column(DateTime, default=datetime.utcnow)


class MerchantUser(Base):
    __tablename__ = "merchant_users"
    id = Column(Integer, primary_key=True, index=True)
    user_id = Column(Integer, ForeignKey("users.id"))
    merchant_id = Column(Integer, ForeignKey("merchants.id"))
    role = Column(String(20), nullable=False)
    is_active = Column(Boolean, default=True)


class Shift(Base):
    __tablename__ = "shifts"
    id = Column(Integer, primary_key=True, index=True)
    merchant_id = Column(Integer, ForeignKey("merchants.id"))
    name = Column(Unicode(100), nullable=False)
    target_revenue = Column(Numeric(18, 2), nullable=False)
    start_time = Column(DateTime, nullable=False)
    end_time = Column(DateTime, nullable=False)
    closed_at = Column(DateTime, nullable=True)
    status = Column(Enum(ShiftStatus), default=ShiftStatus.OPEN)


class Order(Base):
    __tablename__ = "orders"
    id = Column(Integer, primary_key=True, index=True)
    shift_id = Column(Integer, ForeignKey("shifts.id"))
    created_by = Column(Integer, ForeignKey("users.id"))
    order_code = Column(String(30), unique=True, nullable=False, index=True)
    total_amount = Column(Numeric(18, 2), nullable=False)
    customer_note = Column(Unicode(255), nullable=True)
    order_status = Column(Enum(OrderStatus), default=OrderStatus.CONFIRMED_ORDER)
    payment_status = Column(Enum(PaymentStatus), default=PaymentStatus.UNPAID)
    created_at = Column(DateTime, default=datetime.utcnow)


class PaymentRequest(Base):
    __tablename__ = "payment_requests"
    id = Column(Integer, primary_key=True, index=True)
    order_id = Column(Integer, ForeignKey("orders.id"))
    request_code = Column(String(40), unique=True, nullable=False)
    expected_amount = Column(Numeric(18, 2), nullable=False)
    qr_url = Column(Unicode(500), nullable=False)
    status = Column(Enum(PaymentRequestStatus), default=PaymentRequestStatus.ACTIVE)
    expires_at = Column(DateTime, nullable=False)
    created_at = Column(DateTime, default=datetime.utcnow)


class BankTransaction(Base):
    __tablename__ = "bank_transactions"
    id = Column(Integer, primary_key=True, index=True)
    merchant_id = Column(Integer, ForeignKey("merchants.id"))
    reference_code = Column(String(50), unique=True, nullable=False, index=True)
    amount = Column(Numeric(18, 2), nullable=False)
    allocated_amount = Column(Numeric(18, 2), default=0)
    unallocated_amount = Column(Numeric(18, 2), nullable=False)
    transfer_content = Column(Unicode(255), nullable=False)
    sender_account = Column(String(50), nullable=True)
    match_status = Column(Enum(MatchStatus), default=MatchStatus.UNMATCHED)
    created_at = Column(DateTime, default=datetime.utcnow)


class PaymentAllocation(Base):
    __tablename__ = "payment_allocations"
    id = Column(Integer, primary_key=True, index=True)
    bank_transaction_id = Column(Integer, ForeignKey("bank_transactions.id"))
    payment_request_id = Column(Integer, ForeignKey("payment_requests.id"))
    order_id = Column(Integer, ForeignKey("orders.id"))
    entry_type = Column(Enum(EntryType), nullable=False)
    allocated_amount = Column(Numeric(18, 2), nullable=False)
    reversal_of_id = Column(Integer, ForeignKey("payment_allocations.id"), nullable=True)
    allocation_mode = Column(Enum(AllocationMode), default=AllocationMode.AUTO)
    prev_hash = Column(String(64), nullable=False)
    record_hash = Column(String(64), nullable=False)
    created_at = Column(DateTime, default=datetime.utcnow)


class Decision(Base):
    __tablename__ = "decisions"
    id = Column(Integer, primary_key=True, index=True)
    order_id = Column(Integer, ForeignKey("orders.id"), nullable=True)
    bank_transaction_id = Column(Integer, ForeignKey("bank_transactions.id"), nullable=True)
    reviewer_id = Column(Integer, ForeignKey("users.id"))
    decision_type = Column(Enum(DecisionType), nullable=False)
    reason = Column(Unicode(500), nullable=False)
    challenge_used = Column(Unicode(255), nullable=True)
    assertion_signature = Column(Unicode, nullable=True)
    biometric_verified = Column(Boolean, default=False)
    review_date = Column(DateTime, default=datetime.utcnow)

class ShiftAudit(Base):
    __tablename__ = "shift_audits"
    id = Column(Integer, primary_key=True, index=True)
    shift_id = Column(Integer, ForeignKey("shifts.id"), nullable=False, unique=True)
    merchant_id = Column(Integer, ForeignKey("merchants.id"), nullable=False)
    closed_by = Column(Integer, ForeignKey("users.id"), nullable=True)
    total_orders = Column(Integer, default=0)
    total_revenue = Column(Numeric(18, 2), default=0)
    total_allocations = Column(Integer, default=0)
    merkle_root = Column(String(64), nullable=False)
    first_record_hash = Column(String(64), nullable=True)
    last_record_hash = Column(String(64), nullable=True)
    audit_signature = Column(Unicode(500), nullable=True)
    created_at = Column(DateTime, default=datetime.utcnow)

with open("backend/models.py", "r", encoding="utf-8") as f:
    content = f.read()

shift_audit_code = """

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
"""

if "class ShiftAudit" not in content:
    content += shift_audit_code
    with open("backend/models.py", "w", encoding="utf-8") as f:
        f.write(content)
    print("SUCCESS: ShiftAudit added to backend/models.py")
else:
    print("ShiftAudit already present")

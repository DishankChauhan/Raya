from flask_sqlalchemy import SQLAlchemy
from datetime import datetime
import uuid
import json

db = SQLAlchemy()

class Customer(db.Model):
    __tablename__ = 'customers'
    
    id = db.Column(db.String(36), primary_key=True, default=lambda: str(uuid.uuid4()))
    name = db.Column(db.String(100), nullable=False)
    email = db.Column(db.String(100), unique=True, nullable=False)
    phone = db.Column(db.String(30))
    address = db.Column(db.Text)
    date_of_birth = db.Column(db.Date)
    account_number = db.Column(db.String(20), unique=True, nullable=False)
    account_type = db.Column(db.String(20), default='checking')
    balance = db.Column(db.Numeric(15, 2), default=0.00)
    risk_score = db.Column(db.Integer, default=1)  # 1-5 scale
    is_sanctioned = db.Column(db.Boolean, default=False)
    country_code = db.Column(db.String(3))
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    
    # Relationships
    transactions_sent = db.relationship('Transaction', foreign_keys='Transaction.sender_id', backref='sender')
    transactions_received = db.relationship('Transaction', foreign_keys='Transaction.receiver_id', backref='receiver')

class Transaction(db.Model):
    __tablename__ = 'transactions'
    
    id = db.Column(db.String(36), primary_key=True, default=lambda: str(uuid.uuid4()))
    sender_id = db.Column(db.String(36), db.ForeignKey('customers.id'), nullable=False)
    receiver_id = db.Column(db.String(36), db.ForeignKey('customers.id'), nullable=True)
    
    transaction_type = db.Column(db.String(20), nullable=False)  # transfer, withdrawal, deposit, payment
    amount = db.Column(db.Numeric(15, 2), nullable=False)
    currency = db.Column(db.String(3), default='USD')
    
    # Additional fields for AML analysis
    description = db.Column(db.Text)
    channel = db.Column(db.String(20))  # online, atm, branch, mobile
    counterparty_name = db.Column(db.String(100))
    counterparty_account = db.Column(db.String(20))
    counterparty_country = db.Column(db.String(3))
    
    # Metadata
    transaction_date = db.Column(db.DateTime, default=datetime.utcnow)
    reference_number = db.Column(db.String(50), unique=True)
    status = db.Column(db.String(20), default='completed')
    
    # Geolocation data
    ip_address = db.Column(db.String(45))
    location_lat = db.Column(db.Float)
    location_lng = db.Column(db.Float)
    
    created_at = db.Column(db.DateTime, default=datetime.utcnow)

class FlaggedTransaction(db.Model):
    __tablename__ = 'flagged_transactions'
    
    id = db.Column(db.String(36), primary_key=True, default=lambda: str(uuid.uuid4()))
    transaction_id = db.Column(db.String(36), db.ForeignKey('transactions.id'), nullable=False)
    
    # Rule that triggered the flag
    rule_name = db.Column(db.String(100), nullable=False)
    rule_description = db.Column(db.Text)
    risk_level = db.Column(db.String(10))  # low, medium, high, critical
    risk_score = db.Column(db.Integer)  # 1-100
    
    # Flag metadata
    flagged_at = db.Column(db.DateTime, default=datetime.utcnow)
    flagged_by = db.Column(db.String(50), default='system')
    
    # Investigation status
    status = db.Column(db.String(20), default='pending')  # pending, investigating, cleared, escalated
    assigned_to = db.Column(db.String(100))
    notes = db.Column(db.Text)
    
    # AI/LLM analysis results (Phase 2)
    llm_risk_level = db.Column(db.String(10))  # High, Medium, Low
    llm_explanation = db.Column(db.Text)  # LLM-generated explanation
    llm_suggested_action = db.Column(db.String(50))  # escalate, monitor, ignore
    llm_confidence_score = db.Column(db.Float)  # 0.0-1.0
    llm_analyzed_at = db.Column(db.DateTime)
    llm_model_used = db.Column(db.String(50))  # e.g., "gpt-4"
    
    # Relationships
    transaction = db.relationship('Transaction', backref='flags')

# OFAC Sanctioned entities (simplified for demo)
class SanctionedEntity(db.Model):
    __tablename__ = 'sanctioned_entities'
    
    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(200), nullable=False)
    entity_type = db.Column(db.String(50))  # individual, organization, country
    country_code = db.Column(db.String(3))
    sanctions_program = db.Column(db.String(100))
    effective_date = db.Column(db.Date)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)

# New: LLM Audit Log for transparency and compliance
class LLMAuditLog(db.Model):
    __tablename__ = 'llm_audit_logs'
    
    id = db.Column(db.String(36), primary_key=True, default=lambda: str(uuid.uuid4()))
    transaction_id = db.Column(db.String(36), db.ForeignKey('transactions.id'), nullable=False)
    flagged_transaction_id = db.Column(db.String(36), db.ForeignKey('flagged_transactions.id'), nullable=True)
    
    # Request details
    prompt_sent = db.Column(db.Text, nullable=False)
    model_used = db.Column(db.String(50), nullable=False)
    temperature = db.Column(db.Float, default=0.0)
    max_tokens = db.Column(db.Integer, default=1000)
    
    # Response details
    response_received = db.Column(db.Text)
    tokens_used = db.Column(db.Integer)
    response_time_ms = db.Column(db.Integer)
    
    # Status and metadata
    status = db.Column(db.String(20))  # success, error, timeout
    error_message = db.Column(db.Text)
    cost_estimate = db.Column(db.Float)  # in USD
    
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    
    # Relationships
    transaction = db.relationship('Transaction', backref='llm_logs')
    flagged_transaction = db.relationship('FlaggedTransaction', backref='llm_audit_logs') 
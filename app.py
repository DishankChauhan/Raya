from flask import Flask, request, jsonify, render_template
from flask_sqlalchemy import SQLAlchemy
from flask_migrate import Migrate
from config import config
from models import db, Customer, Transaction, FlaggedTransaction, SanctionedEntity
from data_generator import DataGenerator
from aml_rules import AMLRuleEngine
import os
from datetime import datetime, timedelta

def create_app(config_name=None):
    app = Flask(__name__)
    
    # Configuration
    config_name = config_name or os.getenv('FLASK_ENV', 'development')
    app.config.from_object(config[config_name])
    
    # Initialize extensions
    db.init_app(app)
    migrate = Migrate(app, db)
    
    # Initialize rule engine
    rule_engine = AMLRuleEngine()
    
    @app.route('/')
    def index():
        return jsonify({
            'message': 'Raya - AI-Powered Suspicious Transaction Detection',
            'version': '1.0.0',
            'description': 'Advanced AML monitoring system with intelligent rule-based detection',
            'endpoints': {
                'flagged_transactions': '/api/flagged',
                'run_rules': '/api/run-rules',
                'seed_data': '/api/seed',
                'transactions': '/api/transactions',
                'customers': '/api/customers',
                'statistics': '/api/stats',
                'available_rules': '/api/rules'
            }
        })
    
    @app.route('/api/flagged', methods=['GET'])
    def get_flagged_transactions():
        """Get all flagged transactions with filtering options"""
        
        # Query parameters
        risk_level = request.args.get('risk_level')
        rule_name = request.args.get('rule_name')
        status = request.args.get('status', 'pending')
        limit = request.args.get('limit', 100, type=int)
        offset = request.args.get('offset', 0, type=int)
        
        # Build query
        query = db.session.query(FlaggedTransaction, Transaction, Customer).join(
            Transaction, FlaggedTransaction.transaction_id == Transaction.id
        ).join(
            Customer, Transaction.sender_id == Customer.id
        )
        
        # Apply filters
        if risk_level:
            query = query.filter(FlaggedTransaction.risk_level == risk_level)
        if rule_name:
            query = query.filter(FlaggedTransaction.rule_name == rule_name)
        if status:
            query = query.filter(FlaggedTransaction.status == status)
        
        # Apply pagination
        results = query.order_by(FlaggedTransaction.flagged_at.desc()).offset(offset).limit(limit).all()
        
        flagged_transactions = []
        for flag, transaction, customer in results:
            flagged_transactions.append({
                'flag_id': str(flag.id),
                'transaction_id': str(transaction.id),
                'rule_name': flag.rule_name,
                'rule_description': flag.rule_description,
                'risk_level': flag.risk_level,
                'risk_score': flag.risk_score,
                'status': flag.status,
                'flagged_at': flag.flagged_at.isoformat(),
                'transaction': {
                    'amount': float(transaction.amount),
                    'currency': transaction.currency,
                    'type': transaction.transaction_type,
                    'date': transaction.transaction_date.isoformat(),
                    'reference': transaction.reference_number,
                    'counterparty_name': transaction.counterparty_name,
                    'counterparty_country': transaction.counterparty_country,
                    'channel': transaction.channel
                },
                'customer': {
                    'name': customer.name,
                    'account_number': customer.account_number,
                    'country_code': customer.country_code,
                    'risk_score': customer.risk_score
                }
            })
        
        return jsonify({
            'flagged_transactions': flagged_transactions,
            'total_results': len(flagged_transactions),
            'filters_applied': {
                'risk_level': risk_level,
                'rule_name': rule_name,
                'status': status
            }
        })
    
    @app.route('/api/run-rules', methods=['POST'])
    def run_aml_rules():
        """Run AML rules on transactions"""
        
        data = request.get_json() or {}
        transaction_id = data.get('transaction_id')
        
        try:
            flagged_count = rule_engine.run_all_rules(transaction_id)
            
            return jsonify({
                'success': True,
                'message': f'AML rules executed successfully',
                'flagged_transactions': flagged_count,
                'timestamp': datetime.utcnow().isoformat()
            })
        
        except Exception as e:
            return jsonify({
                'success': False,
                'error': str(e)
            }), 500
    
    @app.route('/api/init-db', methods=['POST'])
    def init_database():
        """Initialize database tables"""
        try:
            db.create_all()
            return jsonify({
                'success': True,
                'message': 'Database tables created successfully'
            })
        except Exception as e:
            return jsonify({
                'success': False,
                'error': str(e)
            }), 500
    
    @app.route('/api/seed', methods=['POST'])
    def seed_database():
        """Seed database with sample data"""
        
        data = request.get_json() or {}
        customers_count = data.get('customers', 1000)
        transactions_count = data.get('transactions', 10000)
        
        try:
            generator = DataGenerator()
            customers, transactions = generator.seed_database(customers_count, transactions_count)
            
            return jsonify({
                'success': True,
                'message': 'Database seeded successfully',
                'customers_created': len(customers),
                'transactions_created': len(transactions)
            })
        
        except Exception as e:
            return jsonify({
                'success': False,
                'error': str(e)
            }), 500
    
    @app.route('/api/transactions', methods=['GET'])
    def get_transactions():
        """Get transactions with filtering"""
        
        limit = request.args.get('limit', 50, type=int)
        offset = request.args.get('offset', 0, type=int)
        transaction_type = request.args.get('type')
        min_amount = request.args.get('min_amount', type=float)
        max_amount = request.args.get('max_amount', type=float)
        
        query = db.session.query(Transaction, Customer).join(
            Customer, Transaction.sender_id == Customer.id
        )
        
        if transaction_type:
            query = query.filter(Transaction.transaction_type == transaction_type)
        if min_amount:
            query = query.filter(Transaction.amount >= min_amount)
        if max_amount:
            query = query.filter(Transaction.amount <= max_amount)
        
        results = query.order_by(Transaction.transaction_date.desc()).offset(offset).limit(limit).all()
        
        transactions = []
        for transaction, customer in results:
            transactions.append({
                'id': str(transaction.id),
                'amount': float(transaction.amount),
                'currency': transaction.currency,
                'type': transaction.transaction_type,
                'date': transaction.transaction_date.isoformat(),
                'reference': transaction.reference_number,
                'counterparty_name': transaction.counterparty_name,
                'counterparty_country': transaction.counterparty_country,
                'channel': transaction.channel,
                'status': transaction.status,
                'customer_name': customer.name,
                'customer_account': customer.account_number
            })
        
        return jsonify({
            'transactions': transactions,
            'total_results': len(transactions)
        })
    
    @app.route('/api/customers', methods=['GET'])
    def get_customers():
        """Get customers with filtering"""
        
        limit = request.args.get('limit', 50, type=int)
        offset = request.args.get('offset', 0, type=int)
        risk_score = request.args.get('risk_score', type=int)
        country_code = request.args.get('country_code')
        
        query = Customer.query
        
        if risk_score:
            query = query.filter(Customer.risk_score >= risk_score)
        if country_code:
            query = query.filter(Customer.country_code == country_code)
        
        customers = query.offset(offset).limit(limit).all()
        
        customer_list = []
        for customer in customers:
            customer_list.append({
                'id': str(customer.id),
                'name': customer.name,
                'email': customer.email,
                'account_number': customer.account_number,
                'account_type': customer.account_type,
                'balance': float(customer.balance),
                'risk_score': customer.risk_score,
                'country_code': customer.country_code,
                'is_sanctioned': customer.is_sanctioned,
                'created_at': customer.created_at.isoformat()
            })
        
        return jsonify({
            'customers': customer_list,
            'total_results': len(customer_list)
        })
    
    @app.route('/api/stats', methods=['GET'])
    def get_statistics():
        """Get AML system statistics"""
        
        # Basic counts
        total_customers = Customer.query.count()
        total_transactions = Transaction.query.count()
        total_flagged = FlaggedTransaction.query.count()
        
        # Risk level breakdown
        flagged_summary = rule_engine.get_flagged_summary()
        
        # Recent activity (last 7 days)
        week_ago = datetime.utcnow() - timedelta(days=7)
        recent_transactions = Transaction.query.filter(
            Transaction.transaction_date >= week_ago
        ).count()
        recent_flagged = FlaggedTransaction.query.filter(
            FlaggedTransaction.flagged_at >= week_ago
        ).count()
        
        # Top rules triggered
        top_rules = db.session.query(
            FlaggedTransaction.rule_name,
            db.func.count(FlaggedTransaction.id).label('count')
        ).group_by(FlaggedTransaction.rule_name).order_by(db.text('count DESC')).limit(5).all()
        
        return jsonify({
            'overview': {
                'total_customers': total_customers,
                'total_transactions': total_transactions,
                'total_flagged': total_flagged,
                'flag_rate': round((total_flagged / total_transactions * 100) if total_transactions > 0 else 0, 2)
            },
            'risk_levels': flagged_summary,
            'recent_activity': {
                'transactions_last_7_days': recent_transactions,
                'flagged_last_7_days': recent_flagged
            },
            'top_triggered_rules': [{'rule': rule, 'count': count} for rule, count in top_rules]
        })
    
    @app.route('/api/rules', methods=['GET'])
    def get_available_rules():
        """Get list of available AML rules"""
        
        rules_info = [
            {
                'name': 'LARGE_CASH_WITHDRAWAL',
                'description': 'Flags cash withdrawals over $10,000',
                'risk_level': 'high',
                'category': 'cash_transaction'
            },
            {
                'name': 'MULTIPLE_HIGH_VALUE_SAME_DAY',
                'description': 'Flags multiple high-value transactions on the same day',
                'risk_level': 'medium',
                'category': 'transaction_pattern'
            },
            {
                'name': 'SANCTIONED_COUNTRY_TRANSFER',
                'description': 'Flags transfers to sanctioned countries',
                'risk_level': 'critical',
                'category': 'sanctions'
            },
            {
                'name': 'OFAC_SANCTIONED_ENTITY',
                'description': 'Flags transactions with OFAC sanctioned entities',
                'risk_level': 'critical',
                'category': 'sanctions'
            },
            {
                'name': 'STRUCTURING_PATTERN',
                'description': 'Flags potential structuring patterns',
                'risk_level': 'high',
                'category': 'structuring'
            },
            {
                'name': 'HIGH_VELOCITY',
                'description': 'Flags high transaction velocity',
                'risk_level': 'medium',
                'category': 'velocity'
            },
            {
                'name': 'HIGH_RISK_CUSTOMER',
                'description': 'Flags transactions from high-risk customers',
                'risk_level': 'medium',
                'category': 'customer_risk'
            }
        ]
        
        return jsonify({
            'available_rules': rules_info,
            'total_rules': len(rules_info)
        })
    
    return app

# Create the app
app = create_app()

if __name__ == '__main__':
    with app.app_context():
        db.create_all()
    app.run(host='0.0.0.0', port=5000, debug=True) 
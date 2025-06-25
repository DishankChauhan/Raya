from flask import Flask, request, jsonify, render_template
from flask_sqlalchemy import SQLAlchemy
from flask_migrate import Migrate
from config import config
from models import db, Customer, Transaction, FlaggedTransaction, SanctionedEntity, LLMAuditLog
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
    
    # Initialize rule engine with LLM capability
    enable_llm = bool(app.config.get('OPENAI_API_KEY'))
    rule_engine = AMLRuleEngine(enable_llm=enable_llm)
    
    # Initialize LLM classifier if available
    llm_classifier = None
    if enable_llm:
        try:
            from llm_classifier import LLMRiskClassifier
            llm_classifier = LLMRiskClassifier()
        except ImportError:
            enable_llm = False
    
    @app.route('/')
    def index():
        return jsonify({
            'message': 'Raya - AI-Powered Suspicious Transaction Detection',
            'version': '2.0.0',
            'description': 'Advanced AML monitoring system with intelligent rule-based detection and LLM analysis',
            'phase': 'Phase 2 - LLM Enhanced',
            'llm_enabled': enable_llm,
            'endpoints': {
                'flagged_transactions': '/api/flagged',
                'run_rules': '/api/run-rules',
                'seed_data': '/api/seed',
                'transactions': '/api/transactions',
                'customers': '/api/customers',
                'statistics': '/api/stats',
                'available_rules': '/api/rules',
                'llm_analysis': '/api/llm/analyze',
                'transaction_explanation': '/api/transaction/<transaction_id>/explanation',
                'llm_audit_logs': '/api/llm/audit'
            }
        })
    
    @app.route('/dashboard')
    def dashboard():
        """Serve the analyst review dashboard"""
        page = request.args.get('page', 1, type=int)
        per_page = 50
        
        # Base query to get flagged transactions
        query = db.session.query(FlaggedTransaction).options(
            db.joinedload(FlaggedTransaction.transaction).joinedload(Transaction.sender)
        ).order_by(FlaggedTransaction.flagged_at.desc())
        
        # Paginate the results
        pagination = query.paginate(page=page, per_page=per_page, error_out=False)
        flags = pagination.items

        # We need to structure the data for the template
        flagged_transactions_data = []
        for flag in flags:
            transaction_data = {
                'flag_id': str(flag.id),
                'rule_name': flag.rule_name,
                'risk_level': flag.risk_level,
                'risk_score': flag.risk_score,
                'status': flag.status,
                'flagged_at': flag.flagged_at.strftime('%Y-%m-%d %H:%M:%S'),
                'analyst_verdict': flag.analyst_verdict,
                'analyst_notes': flag.analyst_notes,
                'analyst_reviewed_at': flag.analyst_reviewed_at.strftime('%Y-%m-%d %H:%M:%S') if flag.analyst_reviewed_at else 'N/A',
                'analyst_reviewed_by': flag.analyst_reviewed_by or 'N/A',
                'transaction': {
                    'amount': float(flag.transaction.amount),
                    'currency': flag.transaction.currency,
                    'counterparty_name': flag.transaction.counterparty_name,
                    'counterparty_country': flag.transaction.counterparty_country,
                },
                'customer': {
                    'name': flag.transaction.sender.name,
                    'account_number': flag.transaction.sender.account_number,
                }
            }
            if flag.llm_analyzed_at:
                transaction_data['llm_analysis'] = {
                    'risk_level': flag.llm_risk_level,
                    'explanation': flag.llm_explanation,
                    'suggested_action': flag.llm_suggested_action,
                    'confidence_score': flag.llm_confidence_score,
                }
            flagged_transactions_data.append(transaction_data)

        return render_template(
            'dashboard.html', 
            flags=flagged_transactions_data,
            pagination=pagination
        )

    @app.route('/api/flagged/<flag_id>/review', methods=['POST'])
    def review_flagged_transaction(flag_id):
        """Endpoint for analysts to submit their review"""
        data = request.get_json()
        if not data:
            return jsonify({'success': False, 'error': 'Invalid request'}), 400

        verdict = data.get('verdict')
        notes = data.get('notes')
        analyst = data.get('analyst')

        flag = FlaggedTransaction.query.get(flag_id)
        if not flag:
            return jsonify({'success': False, 'error': 'Flagged transaction not found'}), 404

        try:
            flag.analyst_verdict = verdict
            flag.analyst_notes = notes
            flag.analyst_reviewed_by = analyst
            flag.analyst_reviewed_at = datetime.utcnow()
            flag.status = 'reviewed' # Update status
            
            db.session.commit()
            
            return jsonify({'success': True, 'message': 'Review submitted successfully'})
        except Exception as e:
            db.session.rollback()
            return jsonify({'success': False, 'error': str(e)}), 500

    @app.route('/api/flagged', methods=['GET'])
    def get_flagged_transactions():
        """Get all flagged transactions with filtering options and LLM analysis"""
        
        # Query parameters
        risk_level = request.args.get('risk_level')
        llm_risk_level = request.args.get('llm_risk_level')
        rule_name = request.args.get('rule_name')
        status = request.args.get('status', 'pending')
        limit = request.args.get('limit', 100, type=int)
        offset = request.args.get('offset', 0, type=int)
        include_llm = request.args.get('include_llm', 'true').lower() == 'true'
        
        # Build query
        query = db.session.query(FlaggedTransaction, Transaction, Customer).join(
            Transaction, FlaggedTransaction.transaction_id == Transaction.id
        ).join(
            Customer, Transaction.sender_id == Customer.id
        )
        
        # Apply filters
        if risk_level:
            query = query.filter(FlaggedTransaction.risk_level == risk_level)
        if llm_risk_level:
            query = query.filter(FlaggedTransaction.llm_risk_level == llm_risk_level)
        if rule_name:
            query = query.filter(FlaggedTransaction.rule_name == rule_name)
        if status:
            query = query.filter(FlaggedTransaction.status == status)
        
        # Apply pagination
        results = query.order_by(FlaggedTransaction.flagged_at.desc()).offset(offset).limit(limit).all()
        
        flagged_transactions = []
        for flag, transaction, customer in results:
            transaction_data = {
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
            }
            
            # Include LLM analysis if requested and available
            if include_llm and flag.llm_analyzed_at:
                transaction_data['llm_analysis'] = {
                    'risk_level': flag.llm_risk_level,
                    'explanation': flag.llm_explanation,
                    'suggested_action': flag.llm_suggested_action,
                    'confidence_score': flag.llm_confidence_score,
                    'analyzed_at': flag.llm_analyzed_at.isoformat(),
                    'model_used': flag.llm_model_used
                }
            
            flagged_transactions.append(transaction_data)
        
        return jsonify({
            'flagged_transactions': flagged_transactions,
            'total_results': len(flagged_transactions),
            'filters_applied': {
                'risk_level': risk_level,
                'llm_risk_level': llm_risk_level,
                'rule_name': rule_name,
                'status': status
            },
            'llm_enabled': enable_llm
        })
    
    @app.route('/api/run-rules', methods=['POST'])
    def run_aml_rules():
        """Run AML rules on transactions with optional LLM analysis"""
        
        data = request.get_json() or {}
        transaction_id = data.get('transaction_id')
        run_llm_analysis = data.get('run_llm_analysis', False)
        batch_size = data.get('batch_size', 100)  # Limit batch size to prevent timeouts
        
        try:
            result = rule_engine.run_all_rules(transaction_id, run_llm_analysis)
            
            return jsonify({
                'success': True,
                'message': f'AML rules executed successfully',
                'results': result,
                'timestamp': datetime.utcnow().isoformat(),
                'llm_enabled': enable_llm
            })
        
        except Exception as e:
            return jsonify({
                'success': False,
                'error': str(e)
            }), 500
    
    @app.route('/api/llm/analyze', methods=['POST'])
    def run_llm_analysis():
        """Run LLM analysis on flagged transactions"""
        
        if not enable_llm or not llm_classifier:
            return jsonify({
                'success': False,
                'error': 'LLM analysis is not enabled or configured'
            }), 400
        
        data = request.get_json() or {}
        transaction_id = data.get('transaction_id')
        flagged_transaction_id = data.get('flagged_transaction_id')
        batch_limit = data.get('batch_limit', 5)
        
        try:
            if transaction_id and flagged_transaction_id:
                # Analyze specific flagged transaction
                result = llm_classifier.analyze_transaction_risk(transaction_id, flagged_transaction_id)
                return jsonify({
                    'success': True,
                    'analysis_result': result,
                    'timestamp': datetime.utcnow().isoformat()
                })
            
            elif transaction_id:
                # Analyze all flags for a specific transaction
                flagged_transactions = FlaggedTransaction.query.filter_by(
                    transaction_id=transaction_id
                ).filter(FlaggedTransaction.llm_analyzed_at.is_(None)).all()
                
                results = []
                for flag in flagged_transactions:
                    result = llm_classifier.analyze_transaction_risk(transaction_id, flag.id)
                    results.append(result)
                
                return jsonify({
                    'success': True,
                    'analyses_completed': len(results),
                    'results': results,
                    'timestamp': datetime.utcnow().isoformat()
                })
            
            else:
                # Batch analysis of recent flagged transactions
                recent_flags = FlaggedTransaction.query.filter(
                    FlaggedTransaction.llm_analyzed_at.is_(None)
                ).order_by(FlaggedTransaction.flagged_at.desc()).limit(batch_limit).all()
                
                results = []
                for flag in recent_flags:
                    try:
                        result = llm_classifier.analyze_transaction_risk(flag.transaction_id, flag.id)
                        results.append(result)
                    except Exception as e:
                        results.append({'error': str(e), 'flag_id': flag.id})
                
                return jsonify({
                    'success': True,
                    'analyses_completed': len([r for r in results if 'error' not in r]),
                    'analyses_failed': len([r for r in results if 'error' in r]),
                    'results': results,
                    'timestamp': datetime.utcnow().isoformat()
                })
        
        except Exception as e:
            return jsonify({
                'success': False,
                'error': str(e)
            }), 500

    @app.route('/api/transaction/<transaction_id>/explanation', methods=['GET'])
    def get_transaction_explanation(transaction_id):
        """Get comprehensive explanation for a specific transaction"""
        
        if not enable_llm or not llm_classifier:
            return jsonify({
                'success': False,
                'error': 'LLM analysis is not enabled or configured'
            }), 400
        
        try:
            # Get comprehensive analysis summary
            summary = llm_classifier.get_analysis_summary(transaction_id)
            
            if 'error' in summary:
                return jsonify(summary), 404
            
            return jsonify({
                'success': True,
                'explanation': summary,
                'timestamp': datetime.utcnow().isoformat()
            })
        
        except Exception as e:
            return jsonify({
                'success': False,
                'error': str(e)
            }), 500

    @app.route('/api/llm/audit', methods=['GET'])
    def get_llm_audit_logs():
        """Get LLM audit logs for transparency and compliance"""
        
        # Query parameters
        transaction_id = request.args.get('transaction_id')
        status = request.args.get('status')
        limit = request.args.get('limit', 50, type=int)
        offset = request.args.get('offset', 0, type=int)
        
        query = LLMAuditLog.query
        
        if transaction_id:
            query = query.filter(LLMAuditLog.transaction_id == transaction_id)
        if status:
            query = query.filter(LLMAuditLog.status == status)
        
        logs = query.order_by(LLMAuditLog.created_at.desc()).offset(offset).limit(limit).all()
        
        audit_logs = []
        for log in logs:
            audit_logs.append({
                'id': str(log.id),
                'transaction_id': str(log.transaction_id),
                'flagged_transaction_id': str(log.flagged_transaction_id) if log.flagged_transaction_id else None,
                'model_used': log.model_used,
                'status': log.status,
                'tokens_used': log.tokens_used,
                'response_time_ms': log.response_time_ms,
                'cost_estimate': log.cost_estimate,
                'error_message': log.error_message,
                'created_at': log.created_at.isoformat()
            })
        
        # Calculate summary statistics
        total_logs = LLMAuditLog.query.count()
        success_count = LLMAuditLog.query.filter_by(status='success').count()
        error_count = LLMAuditLog.query.filter_by(status='error').count()
        total_cost = db.session.query(db.func.sum(LLMAuditLog.cost_estimate)).scalar() or 0
        
        return jsonify({
            'audit_logs': audit_logs,
            'total_results': len(audit_logs),
            'summary': {
                'total_requests': total_logs,
                'successful_requests': success_count,
                'failed_requests': error_count,
                'success_rate': round((success_count / total_logs * 100) if total_logs > 0 else 0, 2),
                'total_estimated_cost': round(total_cost, 4)
            }
        })

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
        """Get AML system statistics with LLM analysis metrics"""
        
        # Basic counts
        total_customers = Customer.query.count()
        total_transactions = Transaction.query.count()
        total_flagged = FlaggedTransaction.query.count()
        
        # Enhanced flagged summary with LLM stats
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
        
        # LLM statistics
        llm_stats = {}
        if enable_llm:
            llm_logs_count = LLMAuditLog.query.count()
            llm_success_count = LLMAuditLog.query.filter_by(status='success').count()
            llm_total_cost = db.session.query(db.func.sum(LLMAuditLog.cost_estimate)).scalar() or 0
            
            llm_stats = {
                'total_llm_requests': llm_logs_count,
                'successful_requests': llm_success_count,
                'success_rate': round((llm_success_count / llm_logs_count * 100) if llm_logs_count > 0 else 0, 2),
                'total_cost_estimate': round(llm_total_cost, 4),
                'llm_analyzed_transactions': flagged_summary.get('llm_analyzed', 0),
                'llm_coverage': flagged_summary.get('llm_coverage', 0)
            }
        
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
            'top_triggered_rules': [{'rule': rule, 'count': count} for rule, count in top_rules],
            'llm_analysis': llm_stats,
            'llm_enabled': enable_llm
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
            'total_rules': len(rules_info),
            'llm_enhancement': 'Available for detailed risk analysis' if enable_llm else 'Not configured'
        })
    
    return app

# Create the app
app = create_app()

if __name__ == '__main__':
    with app.app_context():
        db.create_all()
    app.run(host='0.0.0.0', port=8080, debug=True) 
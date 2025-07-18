from models import db, Transaction, FlaggedTransaction, Customer, SanctionedEntity
from datetime import datetime, timedelta
from sqlalchemy import func, and_
import re

class AMLRuleEngine:
    def __init__(self, enable_llm=False):
        self.enable_llm = enable_llm
        self.llm_classifier = None
        
        # Initialize LLM classifier if enabled
        if enable_llm:
            try:
                from llm_classifier import LLMRiskClassifier
                self.llm_classifier = LLMRiskClassifier()
            except ImportError as e:
                print(f"Warning: Could not import LLM classifier: {e}")
                self.enable_llm = False
        
        self.rules = [
            self.large_cash_withdrawal_rule,
            self.multiple_high_value_transactions_rule,
            self.sanctioned_country_transfer_rule,
            self.ofac_counterparty_rule,
            self.structuring_pattern_rule,
            self.round_number_rule,
            self.velocity_rule,
            self.high_risk_customer_rule,
            self.unusual_time_pattern_rule,
            self.cross_border_threshold_rule
        ]
    
    def run_all_rules(self, transaction_id=None, run_llm_analysis=False):
        """Run all AML rules on transactions with optional LLM analysis"""
        flagged_count = 0
        llm_analyzed_count = 0
        
        if transaction_id:
            # Run rules on specific transaction
            transaction = Transaction.query.get(transaction_id)
            if transaction:
                for rule in self.rules:
                    if rule(transaction):
                        flagged_count += 1
                        
                # Run LLM analysis on newly flagged transactions
                if run_llm_analysis and self.enable_llm:
                    llm_analyzed_count += self._run_llm_analysis_for_transaction(transaction_id)
        else:
            # Run rules on all unflagged transactions (batch mode with limits)
            # Process in smaller batches to avoid timeouts
            batch_size = 100
            offset = 0
            
            while True:
                transactions = Transaction.query.filter(
                    ~Transaction.id.in_(
                        db.session.query(FlaggedTransaction.transaction_id)
                    )
                ).offset(offset).limit(batch_size).all()
                
                if not transactions:
                    break
                
                batch_flagged = 0
                for transaction in transactions:
                    for rule in self.rules:
                        if rule(transaction):
                            batch_flagged += 1
                
                flagged_count += batch_flagged
                offset += batch_size
                
                # Limit total processing to prevent timeouts
                if offset >= 1000:  # Process max 1000 transactions per call
                    break
            
            # Run LLM analysis on recently flagged transactions if enabled
            if run_llm_analysis and self.enable_llm:
                llm_analyzed_count = self._run_llm_analysis_batch()
        
        return {
            "flagged_count": flagged_count,
            "llm_analyzed_count": llm_analyzed_count,
            "llm_enabled": self.enable_llm
        }
    
    def _run_llm_analysis_for_transaction(self, transaction_id):
        """Run LLM analysis for a specific transaction's flags"""
        analyzed_count = 0
        
        # Get all flagged transactions for this transaction that haven't been LLM analyzed
        flagged_transactions = FlaggedTransaction.query.filter_by(
            transaction_id=transaction_id
        ).filter(
            FlaggedTransaction.llm_analyzed_at.is_(None)
        ).all()
        
        for flagged_tx in flagged_transactions:
            try:
                if self.llm_classifier:
                    self.llm_classifier.analyze_transaction_risk(transaction_id, flagged_tx.id)
                    analyzed_count += 1
            except Exception as e:
                print(f"Error in LLM analysis for flag {flagged_tx.id}: {e}")
        
        return analyzed_count
    
    def _run_llm_analysis_batch(self, limit=10):
        """Run LLM analysis on a batch of recently flagged transactions"""
        analyzed_count = 0
        
        # Get recently flagged transactions that haven't been LLM analyzed
        recent_flags = FlaggedTransaction.query.filter(
            FlaggedTransaction.llm_analyzed_at.is_(None)
        ).order_by(
            FlaggedTransaction.flagged_at.desc()
        ).limit(limit).all()
        
        for flagged_tx in recent_flags:
            try:
                if self.llm_classifier:
                    self.llm_classifier.analyze_transaction_risk(flagged_tx.transaction_id, flagged_tx.id)
                    analyzed_count += 1
            except Exception as e:
                print(f"Error in LLM analysis for flag {flagged_tx.id}: {e}")
        
        return analyzed_count
    
    def flag_transaction(self, transaction, rule_name, description, risk_level, risk_score):
        """Create a flag for a transaction"""
        # Check if already flagged by this rule
        existing_flag = FlaggedTransaction.query.filter_by(
            transaction_id=transaction.id,
            rule_name=rule_name
        ).first()
        
        if existing_flag:
            return False
        
        flag = FlaggedTransaction(
            transaction_id=transaction.id,
            rule_name=rule_name,
            rule_description=description,
            risk_level=risk_level,
            risk_score=risk_score
        )
        
        db.session.add(flag)
        db.session.commit()
        return True
    
    def large_cash_withdrawal_rule(self, transaction):
        """Flag large cash withdrawals (>$10,000)"""
        if (transaction.transaction_type == 'withdrawal' and 
            transaction.amount > 10000):
            
            return self.flag_transaction(
                transaction,
                'LARGE_CASH_WITHDRAWAL',
                f'Large cash withdrawal of ${transaction.amount:,.2f}',
                'high',
                85
            )
        return False
    
    def multiple_high_value_transactions_rule(self, transaction):
        """Flag multiple high-value transactions on same day"""
        if transaction.amount < 5000:
            return False
        
        same_day_start = transaction.transaction_date.replace(hour=0, minute=0, second=0, microsecond=0)
        same_day_end = same_day_start + timedelta(days=1)
        
        count = Transaction.query.filter(
            and_(
                Transaction.sender_id == transaction.sender_id,
                Transaction.amount >= 5000,
                Transaction.transaction_date >= same_day_start,
                Transaction.transaction_date < same_day_end,
                Transaction.id != transaction.id
            )
        ).count()
        
        if count >= 2:  # 3 or more including current
            return self.flag_transaction(
                transaction,
                'MULTIPLE_HIGH_VALUE_SAME_DAY',
                f'Multiple high-value transactions on same day (total: {count + 1})',
                'medium',
                70
            )
        return False
    
    def sanctioned_country_transfer_rule(self, transaction):
        """Flag transfers to sanctioned countries"""
        sanctioned_countries = ['AF', 'IR', 'KP', 'SY', 'MM', 'BY', 'RU']
        
        if (transaction.counterparty_country in sanctioned_countries and
            transaction.transaction_type in ['transfer', 'payment']):
            
            return self.flag_transaction(
                transaction,
                'SANCTIONED_COUNTRY_TRANSFER',
                f'Transfer to sanctioned country: {transaction.counterparty_country}',
                'critical',
                95
            )
        return False
    
    def ofac_counterparty_rule(self, transaction):
        """Flag transactions with OFAC sanctioned entities"""
        if not transaction.counterparty_name:
            return False
        
        # Check against sanctioned entities
        sanctioned = SanctionedEntity.query.filter(
            SanctionedEntity.name.ilike(f'%{transaction.counterparty_name}%')
        ).first()
        
        if sanctioned:
            return self.flag_transaction(
                transaction,
                'OFAC_SANCTIONED_ENTITY',
                f'Transaction with sanctioned entity: {transaction.counterparty_name}',
                'critical',
                100
            )
        return False
    
    def structuring_pattern_rule(self, transaction):
        """Flag potential structuring (amounts just under $10k)"""
        if (9000 <= transaction.amount < 10000 and
            transaction.transaction_type in ['transfer', 'withdrawal']):
            
            # Check for pattern of similar amounts
            last_week = transaction.transaction_date - timedelta(days=7)
            similar_transactions = Transaction.query.filter(
                and_(
                    Transaction.sender_id == transaction.sender_id,
                    Transaction.amount.between(9000, 9999),
                    Transaction.transaction_date >= last_week,
                    Transaction.id != transaction.id
                )
            ).count()
            
            if similar_transactions >= 1:
                return self.flag_transaction(
                    transaction,
                    'STRUCTURING_PATTERN',
                    f'Potential structuring: ${transaction.amount:,.2f} (similar amounts in past week)',
                    'high',
                    80
                )
        return False
    
    def round_number_rule(self, transaction):
        """Flag suspicious round number patterns"""
        amount = float(transaction.amount)
        
        # Check for exact round numbers above certain threshold
        if (amount >= 10000 and amount % 1000 == 0):
            return self.flag_transaction(
                transaction,
                'ROUND_NUMBER_PATTERN',
                f'Large round number transaction: ${amount:,.2f}',
                'low',
                40
            )
        return False
    
    def velocity_rule(self, transaction):
        """Flag high transaction velocity"""
        last_hour = transaction.transaction_date - timedelta(hours=1)
        
        recent_count = Transaction.query.filter(
            and_(
                Transaction.sender_id == transaction.sender_id,
                Transaction.transaction_date >= last_hour,
                Transaction.id != transaction.id
            )
        ).count()
        
        if recent_count >= 5:
            return self.flag_transaction(
                transaction,
                'HIGH_VELOCITY',
                f'High transaction velocity: {recent_count + 1} transactions in 1 hour',
                'medium',
                65
            )
        return False
    
    def high_risk_customer_rule(self, transaction):
        """Flag transactions from high-risk customers"""
        customer = Customer.query.get(transaction.sender_id)
        
        if customer and customer.risk_score >= 4 and transaction.amount >= 5000:
            return self.flag_transaction(
                transaction,
                'HIGH_RISK_CUSTOMER',
                f'High-risk customer (score: {customer.risk_score}) large transaction',
                'medium',
                60
            )
        return False
    
    def unusual_time_pattern_rule(self, transaction):
        """Flag transactions at unusual times"""
        hour = transaction.transaction_date.hour
        
        # Flag transactions between 2 AM and 5 AM
        if 2 <= hour <= 5 and transaction.amount >= 1000:
            return self.flag_transaction(
                transaction,
                'UNUSUAL_TIME_PATTERN',
                f'Transaction at unusual time: {transaction.transaction_date.strftime("%H:%M")}',
                'low',
                45
            )
        return False
    
    def cross_border_threshold_rule(self, transaction):
        """Flag cross-border transactions above $3,000"""
        sender = Customer.query.get(transaction.sender_id)
        
        if (sender and transaction.counterparty_country and 
            sender.country_code != transaction.counterparty_country and
            transaction.amount >= 3000):
            
            return self.flag_transaction(
                transaction,
                'CROSS_BORDER_THRESHOLD',
                f'Cross-border transaction: ${transaction.amount:,.2f} to {transaction.counterparty_country}',
                'medium',
                55
            )
        return False
    
    def get_flagged_summary(self):
        """Get summary of flagged transactions with LLM analysis stats"""
        summary = db.session.query(
            FlaggedTransaction.risk_level,
            func.count(FlaggedTransaction.id).label('count')
        ).group_by(FlaggedTransaction.risk_level).all()
        
        # Get LLM analysis summary
        llm_summary = db.session.query(
            FlaggedTransaction.llm_risk_level,
            func.count(FlaggedTransaction.id).label('count')
        ).filter(
            FlaggedTransaction.llm_risk_level.isnot(None)
        ).group_by(FlaggedTransaction.llm_risk_level).all()
        
        # Get analysis counts
        total_flagged = FlaggedTransaction.query.count()
        llm_analyzed = FlaggedTransaction.query.filter(
            FlaggedTransaction.llm_analyzed_at.isnot(None)
        ).count()
        
        return {
            "rule_based_flags": {level: count for level, count in summary},
            "llm_analysis": {level: count for level, count in llm_summary},
            "total_flagged": total_flagged,
            "llm_analyzed": llm_analyzed,
            "llm_coverage": round((llm_analyzed / total_flagged * 100) if total_flagged > 0 else 0, 2)
        } 
import openai
import json
import time
from datetime import datetime
from typing import Dict, Optional, Tuple
from models import db, Transaction, Customer, FlaggedTransaction, LLMAuditLog
from config import Config
import logging

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

class LLMRiskClassifier:
    def __init__(self, api_key: Optional[str] = None):
        self.client = openai.OpenAI(api_key=api_key or Config.OPENAI_API_KEY)
        self.model = "gpt-4-1106-preview"  # GPT-4 Turbo with function calling
        
    def analyze_transaction_risk(self, transaction_id: str, flagged_transaction_id: str) -> Dict:
        """
        Analyze a flagged transaction using LLM and return risk assessment
        
        Args:
            transaction_id: ID of the transaction to analyze
            flagged_transaction_id: ID of the flagged transaction record
            
        Returns:
            Dict containing LLM analysis results
        """
        
        start_time = time.time()
        
        try:
            # Get transaction and related data
            transaction = Transaction.query.get(transaction_id)
            flagged_tx = FlaggedTransaction.query.get(flagged_transaction_id)
            customer = Customer.query.get(transaction.sender_id)
            
            if not transaction or not flagged_tx or not customer:
                raise ValueError("Transaction, flagged transaction, or customer not found")
            
            # Prepare transaction metadata for LLM
            transaction_metadata = self._prepare_transaction_metadata(transaction, customer, flagged_tx)
            
            # Create the prompt
            prompt = self._create_analysis_prompt(transaction_metadata)
            
            # Call OpenAI with function calling
            response = self._call_openai_with_functions(prompt)
            
            # Calculate response time and cost
            response_time_ms = int((time.time() - start_time) * 1000)
            
            # Parse LLM response
            analysis_result = self._parse_llm_response(response)
            
            # Log the interaction for audit
            self._log_llm_interaction(
                transaction_id=transaction_id,
                flagged_transaction_id=flagged_transaction_id,
                prompt=prompt,
                response=response,
                response_time_ms=response_time_ms,
                status="success"
            )
            
            # Update flagged transaction with LLM results
            self._update_flagged_transaction(flagged_tx, analysis_result)
            
            return analysis_result
            
        except Exception as e:
            logger.error(f"Error in LLM analysis: {str(e)}")
            
            # Log the error
            self._log_llm_interaction(
                transaction_id=transaction_id,
                flagged_transaction_id=flagged_transaction_id,
                prompt=prompt if 'prompt' in locals() else "Error before prompt creation",
                response=None,
                response_time_ms=int((time.time() - start_time) * 1000),
                status="error",
                error_message=str(e)
            )
            
            return {
                "error": str(e),
                "risk_level": "Unknown",
                "explanation": "LLM analysis failed",
                "suggested_action": "manual_review"
            }
    
    def _prepare_transaction_metadata(self, transaction: Transaction, customer: Customer, flagged_tx: FlaggedTransaction) -> Dict:
        """Prepare structured transaction data for LLM analysis"""
        
        return {
            "transaction": {
                "id": transaction.id,
                "amount": float(transaction.amount),
                "currency": transaction.currency,
                "type": transaction.transaction_type,
                "channel": transaction.channel,
                "date": transaction.transaction_date.isoformat(),
                "reference": transaction.reference_number,
                "description": transaction.description
            },
            "counterparty": {
                "name": transaction.counterparty_name,
                "country": transaction.counterparty_country,
                "account": transaction.counterparty_account
            },
            "customer": {
                "risk_score": customer.risk_score,
                "account_type": customer.account_type,
                "country": customer.country_code,
                "is_sanctioned": customer.is_sanctioned,
                "balance": float(customer.balance)
            },
            "flag_details": {
                "rule_triggered": flagged_tx.rule_name,
                "rule_description": flagged_tx.rule_description,
                "initial_risk_level": flagged_tx.risk_level,
                "risk_score": flagged_tx.risk_score,
                "flagged_at": flagged_tx.flagged_at.isoformat()
            },
            "geolocation": {
                "ip_address": transaction.ip_address,
                "latitude": transaction.location_lat,
                "longitude": transaction.location_lng
            }
        }
    
    def _create_analysis_prompt(self, metadata: Dict) -> str:
        """Create a comprehensive prompt for LLM analysis"""
        
        return f"""
You are an expert Anti-Money Laundering (AML) analyst. Analyze the following flagged transaction and provide a comprehensive risk assessment.

Transaction Details:
- Amount: {metadata['transaction']['currency']} {metadata['transaction']['amount']:,.2f}
- Type: {metadata['transaction']['type']}
- Channel: {metadata['transaction']['channel']}
- Date: {metadata['transaction']['date']}
- Description: {metadata['transaction']['description']}

Customer Profile:
- Risk Score: {metadata['customer']['risk_score']}/5
- Account Type: {metadata['customer']['account_type']}
- Country: {metadata['customer']['country']}
- Current Balance: {metadata['transaction']['currency']} {metadata['customer']['balance']:,.2f}
- Is Sanctioned: {metadata['customer']['is_sanctioned']}

Counterparty Information:
- Name: {metadata['counterparty']['name']}
- Country: {metadata['counterparty']['country']}
- Account: {metadata['counterparty']['account']}

Initial Flag Details:
- Rule Triggered: {metadata['flag_details']['rule_triggered']}
- Rule Description: {metadata['flag_details']['rule_description']}
- Initial Risk Level: {metadata['flag_details']['initial_risk_level']}
- Initial Risk Score: {metadata['flag_details']['risk_score']}/100

Geolocation Data:
- IP Address: {metadata['geolocation']['ip_address']}
- Location: {metadata['geolocation']['latitude']}, {metadata['geolocation']['longitude']}

Please analyze this transaction for money laundering risk considering:
1. Transaction patterns and amounts
2. Customer risk profile
3. Counterparty and geographic risks
4. Regulatory compliance factors
5. Typology matching (structuring, layering, placement, etc.)

Provide your assessment using the analyze_transaction function.
"""
    
    def _call_openai_with_functions(self, prompt: str) -> Dict:
        """Call OpenAI with function calling for structured response"""
        
        functions = [
            {
                "name": "analyze_transaction",
                "description": "Analyze a transaction for AML risk and provide structured assessment",
                "parameters": {
                    "type": "object",
                    "properties": {
                        "risk_level": {
                            "type": "string",
                            "enum": ["High", "Medium", "Low"],
                            "description": "Overall risk level assessment"
                        },
                        "explanation": {
                            "type": "string",
                            "description": "Detailed explanation of the risk assessment reasoning"
                        },
                        "suggested_action": {
                            "type": "string",
                            "enum": ["escalate", "monitor", "ignore", "investigate"],
                            "description": "Recommended action based on the analysis"
                        },
                        "confidence_score": {
                            "type": "number",
                            "minimum": 0.0,
                            "maximum": 1.0,
                            "description": "Confidence level in the assessment (0.0-1.0)"
                        },
                        "risk_factors": {
                            "type": "array",
                            "items": {
                                "type": "string"
                            },
                            "description": "List of key risk factors identified"
                        },
                        "compliance_notes": {
                            "type": "string",
                            "description": "Additional compliance and regulatory considerations"
                        }
                    },
                    "required": ["risk_level", "explanation", "suggested_action", "confidence_score"]
                }
            }
        ]
        
        response = self.client.chat.completions.create(
            model=self.model,
            messages=[
                {
                    "role": "system",
                    "content": "You are an expert AML analyst with deep knowledge of financial crime patterns, regulatory requirements, and risk assessment methodologies. Provide thorough, professional analysis."
                },
                {
                    "role": "user",
                    "content": prompt
                }
            ],
            functions=functions,
            function_call={"name": "analyze_transaction"},
            temperature=0.1,  # Low temperature for consistent analysis
            max_tokens=1500
        )
        
        return response
    
    def _parse_llm_response(self, response) -> Dict:
        """Parse and validate LLM function call response"""
        
        try:
            # Extract function call result
            function_call = response.choices[0].message.function_call
            arguments = json.loads(function_call.arguments)
            
            # Validate required fields
            required_fields = ["risk_level", "explanation", "suggested_action", "confidence_score"]
            for field in required_fields:
                if field not in arguments:
                    raise ValueError(f"Missing required field: {field}")
            
            # Validate risk_level enum
            if arguments["risk_level"] not in ["High", "Medium", "Low"]:
                raise ValueError(f"Invalid risk_level: {arguments['risk_level']}")
            
            # Validate suggested_action enum
            if arguments["suggested_action"] not in ["escalate", "monitor", "ignore", "investigate"]:
                raise ValueError(f"Invalid suggested_action: {arguments['suggested_action']}")
            
            # Validate confidence_score range
            confidence = arguments["confidence_score"]
            if not (0.0 <= confidence <= 1.0):
                raise ValueError(f"confidence_score must be between 0.0 and 1.0, got: {confidence}")
            
            # Add usage metadata
            arguments["tokens_used"] = response.usage.total_tokens
            arguments["model_used"] = self.model
            
            return arguments
            
        except Exception as e:
            logger.error(f"Error parsing LLM response: {str(e)}")
            return {
                "risk_level": "Medium",
                "explanation": f"Error parsing LLM response: {str(e)}",
                "suggested_action": "manual_review",
                "confidence_score": 0.0,
                "error": str(e)
            }
    
    def _update_flagged_transaction(self, flagged_tx: FlaggedTransaction, analysis_result: Dict):
        """Update flagged transaction with LLM analysis results"""
        
        flagged_tx.llm_risk_level = analysis_result.get("risk_level")
        flagged_tx.llm_explanation = analysis_result.get("explanation")
        flagged_tx.llm_suggested_action = analysis_result.get("suggested_action")
        flagged_tx.llm_confidence_score = analysis_result.get("confidence_score")
        flagged_tx.llm_analyzed_at = datetime.utcnow()
        flagged_tx.llm_model_used = analysis_result.get("model_used", self.model)
        
        db.session.commit()
    
    def _log_llm_interaction(self, transaction_id: str, flagged_transaction_id: str, 
                           prompt: str, response, response_time_ms: int, 
                           status: str, error_message: str = None):
        """Log LLM interaction for audit purposes"""
        
        tokens_used = None
        cost_estimate = None
        response_text = None
        
        if response and status == "success":
            tokens_used = response.usage.total_tokens
            # Rough cost estimate for GPT-4 (input: $0.01/1K tokens, output: $0.03/1K tokens)
            cost_estimate = (tokens_used / 1000) * 0.02  # Average estimate
            response_text = json.dumps({
                "choices": [
                    {
                        "message": {
                            "function_call": {
                                "name": response.choices[0].message.function_call.name,
                                "arguments": response.choices[0].message.function_call.arguments
                            }
                        }
                    }
                ],
                "usage": {
                    "total_tokens": response.usage.total_tokens,
                    "prompt_tokens": response.usage.prompt_tokens,
                    "completion_tokens": response.usage.completion_tokens
                }
            })
        
        audit_log = LLMAuditLog(
            transaction_id=transaction_id,
            flagged_transaction_id=flagged_transaction_id,
            prompt_sent=prompt,
            model_used=self.model,
            temperature=0.1,
            max_tokens=1500,
            response_received=response_text,
            tokens_used=tokens_used,
            response_time_ms=response_time_ms,
            status=status,
            error_message=error_message,
            cost_estimate=cost_estimate
        )
        
        db.session.add(audit_log)
        db.session.commit()
    
    def get_analysis_summary(self, transaction_id: str) -> Dict:
        """Get comprehensive analysis summary for a transaction"""
        
        transaction = Transaction.query.get(transaction_id)
        if not transaction:
            return {"error": "Transaction not found"}
        
        flagged_transactions = FlaggedTransaction.query.filter_by(transaction_id=transaction_id).all()
        audit_logs = LLMAuditLog.query.filter_by(transaction_id=transaction_id).all()
        
        return {
            "transaction_id": transaction_id,
            "flagged_count": len(flagged_transactions),
            "llm_analyses": [
                {
                    "flag_id": ft.id,
                    "rule_name": ft.rule_name,
                    "llm_risk_level": ft.llm_risk_level,
                    "llm_explanation": ft.llm_explanation,
                    "llm_suggested_action": ft.llm_suggested_action,
                    "llm_confidence_score": ft.llm_confidence_score,
                    "analyzed_at": ft.llm_analyzed_at.isoformat() if ft.llm_analyzed_at else None
                }
                for ft in flagged_transactions if ft.llm_analyzed_at
            ],
            "audit_logs": [
                {
                    "id": log.id,
                    "status": log.status,
                    "tokens_used": log.tokens_used,
                    "cost_estimate": log.cost_estimate,
                    "response_time_ms": log.response_time_ms,
                    "created_at": log.created_at.isoformat()
                }
                for log in audit_logs
            ]
        } 
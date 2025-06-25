#!/usr/bin/env python3
"""
Raya Phase 2 Setup Script
Enhanced setup and testing for the Raya AML system with LLM analysis
"""

import requests
import time
import sys
import json
import os

BASE_URL = "http://localhost:5001"

def check_service():
    """Check if the service is running and get system info"""
    try:
        response = requests.get(f"{BASE_URL}/")
        if response.status_code == 200:
            data = response.json()
            print("✅ Raya service is running")
            print(f"   Version: {data.get('version', 'Unknown')}")
            print(f"   Phase: {data.get('phase', 'Unknown')}")
            print(f"   LLM Enabled: {'✅' if data.get('llm_enabled') else '❌'}")
            return data.get('llm_enabled', False)
    except requests.exceptions.ConnectionError:
        print("❌ Raya service is not running")
        print("Please start the service with: docker-compose up -d")
        return False

def check_llm_configuration():
    """Check if LLM is properly configured"""
    print("🧠 Checking LLM Configuration...")
    
    # Check if OpenAI API key is set
    openai_key = os.getenv('OPENAI_API_KEY')
    if not openai_key:
        print("⚠️  OPENAI_API_KEY environment variable not set")
        print("   LLM analysis will not be available")
        return False
    else:
        print("✅ OpenAI API key found")
        print(f"   Key preview: {openai_key[:8]}...{openai_key[-4:]}")
        return True

def seed_database(customers=1000, transactions=10000):
    """Seed the database with sample data"""
    print(f"🌱 Seeding database with {customers} customers and {transactions} transactions...")
    
    try:
        response = requests.post(
            f"{BASE_URL}/api/seed",
            json={"customers": customers, "transactions": transactions}
        )
        
        if response.status_code == 200:
            data = response.json()
            print(f"✅ Database seeded successfully!")
            print(f"   - Customers created: {data['customers_created']}")
            print(f"   - Transactions created: {data['transactions_created']}")
            return True
        else:
            print(f"❌ Failed to seed database: {response.json()}")
            return False
            
    except Exception as e:
        print(f"❌ Error seeding database: {e}")
        return False

def init_database():
    """Initialize the database tables"""
    print("🚀 Initializing database tables...")
    try:
        response = requests.post(f"{BASE_URL}/api/init-db")
        if response.status_code == 200:
            print("✅ Database tables created successfully.")
            return True
        else:
            print(f"❌ Failed to initialize database: {response.json()}")
            return False
    except Exception as e:
        print(f"❌ Error initializing database: {e}")
        return False

def run_aml_rules(with_llm=False):
    """Run AML rules on all transactions"""
    print(f"🔍 Running AML detection rules{'with LLM analysis' if with_llm else ''}...")
    
    try:
        payload = {"run_llm_analysis": with_llm}
        response = requests.post(f"{BASE_URL}/api/run-rules", json=payload)
        
        if response.status_code == 200:
            data = response.json()
            results = data.get('results', {})
            print(f"✅ AML rules executed successfully!")
            print(f"   - Transactions flagged: {results.get('flagged_count', 0)}")
            if with_llm:
                print(f"   - LLM analyses completed: {results.get('llm_analyzed_count', 0)}")
            return results
        else:
            print(f"❌ Failed to run AML rules: {response.json()}")
            return {}
            
    except Exception as e:
        print(f"❌ Error running AML rules: {e}")
        return {}

def run_llm_batch_analysis(batch_limit=5):
    """Run LLM analysis on flagged transactions"""
    print(f"🧠 Running LLM batch analysis (limit: {batch_limit})...")
    
    try:
        payload = {"batch_limit": batch_limit}
        response = requests.post(f"{BASE_URL}/api/llm/analyze", json=payload)
        
        if response.status_code == 200:
            data = response.json()
            print(f"✅ LLM batch analysis completed!")
            print(f"   - Analyses completed: {data.get('analyses_completed', 0)}")
            print(f"   - Analyses failed: {data.get('analyses_failed', 0)}")
            return data
        elif response.status_code == 400:
            error_data = response.json()
            print(f"⚠️  LLM analysis not available: {error_data.get('error')}")
            return {}
        else:
            print(f"❌ Failed to run LLM analysis: {response.json()}")
            return {}
            
    except Exception as e:
        print(f"❌ Error running LLM analysis: {e}")
        return {}

def get_statistics():
    """Get and display system statistics"""
    print("📊 Getting system statistics...")
    
    try:
        response = requests.get(f"{BASE_URL}/api/stats")
        
        if response.status_code == 200:
            data = response.json()
            
            print("\n" + "="*60)
            print("📈 RAYA PHASE 2 - AML SYSTEM STATISTICS")
            print("="*60)
            
            overview = data['overview']
            print(f"Total Customers: {overview['total_customers']:,}")
            print(f"Total Transactions: {overview['total_transactions']:,}")
            print(f"Total Flagged: {overview['total_flagged']:,}")
            print(f"Flag Rate: {overview['flag_rate']}%")
            
            print("\n🚨 Rule-Based Risk Level Breakdown:")
            rule_based = data['risk_levels'].get('rule_based_flags', {})
            for level, count in rule_based.items():
                print(f"   {level.upper()}: {count}")
            
            if data.get('llm_enabled'):
                print("\n🧠 LLM Analysis Breakdown:")
                llm_analysis = data['risk_levels'].get('llm_analysis', {})
                if llm_analysis:
                    for level, count in llm_analysis.items():
                        print(f"   LLM {level.upper()}: {count}")
                else:
                    print("   No LLM analyses completed yet")
                
                llm_stats = data.get('llm_analysis', {})
                if llm_stats:
                    print(f"\n💰 LLM Statistics:")
                    print(f"   Total LLM Requests: {llm_stats.get('total_llm_requests', 0)}")
                    print(f"   Success Rate: {llm_stats.get('success_rate', 0)}%")
                    print(f"   Coverage: {llm_stats.get('llm_coverage', 0)}% of flagged transactions")
                    print(f"   Estimated Cost: ${llm_stats.get('total_cost_estimate', 0):.4f}")
            
            print("\n🔥 Top Triggered Rules:")
            top_rules = data.get('top_triggered_rules', [])
            for i, rule_data in enumerate(top_rules[:5], 1):
                print(f"   {i}. {rule_data['rule']}: {rule_data['count']} flags")
            
            print("="*60)
            return True
        else:
            print(f"❌ Failed to get statistics: {response.json()}")
            return False
            
    except Exception as e:
        print(f"❌ Error getting statistics: {e}")
        return False

def show_sample_flagged_with_llm():
    """Show sample flagged transactions with LLM analysis"""
    print("\n🚩 Sample Flagged Transactions with LLM Analysis:")
    
    try:
        response = requests.get(f"{BASE_URL}/api/flagged?limit=3&include_llm=true")
        
        if response.status_code == 200:
            data = response.json()
            flagged = data['flagged_transactions']
            
            if not flagged:
                print("   No flagged transactions found.")
                return
            
            for i, flag in enumerate(flagged, 1):
                tx = flag['transaction']
                customer = flag['customer']
                
                print(f"\n   {i}. 🚨 Rule Flag:")
                print(f"      Rule: {flag['rule_name']}")
                print(f"      Risk: {flag['risk_level'].upper()} ({flag['risk_score']}/100)")
                print(f"      Amount: ${tx['amount']:,.2f} {tx['currency']}")
                print(f"      Customer: {customer['name']} ({customer['account_number']})")
                print(f"      Description: {flag['rule_description']}")
                
                # Show LLM analysis if available
                llm_analysis = flag.get('llm_analysis')
                if llm_analysis:
                    print(f"      \n      🧠 LLM Analysis:")
                    print(f"         Risk Level: {llm_analysis['risk_level']}")
                    print(f"         Confidence: {llm_analysis['confidence_score']:.2f}")
                    print(f"         Suggested Action: {llm_analysis['suggested_action']}")
                    print(f"         Explanation: {llm_analysis['explanation'][:100]}...")
                    print(f"         Model: {llm_analysis['model_used']}")
                else:
                    print(f"      🔍 LLM Analysis: Not completed")
                
        else:
            print(f"❌ Failed to get flagged transactions: {response.json()}")
            
    except Exception as e:
        print(f"❌ Error getting flagged transactions: {e}")

def demonstrate_transaction_explanation(transaction_id=None):
    """Demonstrate detailed transaction explanation"""
    if not transaction_id:
        # Get a flagged transaction ID
        try:
            response = requests.get(f"{BASE_URL}/api/flagged?limit=1")
            if response.status_code == 200:
                flagged = response.json()['flagged_transactions']
                if flagged:
                    transaction_id = flagged[0]['transaction_id']
                else:
                    print("   No flagged transactions available for demonstration")
                    return
        except Exception as e:
            print(f"   Error getting sample transaction: {e}")
            return
    
    print(f"\n🔍 Detailed Transaction Explanation for ID: {transaction_id[:8]}...")
    
    try:
        response = requests.get(f"{BASE_URL}/api/transaction/{transaction_id}/explanation")
        
        if response.status_code == 200:
            data = response.json()
            explanation = data['explanation']
            
            print(f"   Transaction analyzed: {explanation['flagged_count']} flags detected")
            
            for analysis in explanation.get('llm_analyses', []):
                print(f"\n   🧠 LLM Analysis for {analysis['rule_name']}:")
                print(f"      Risk Level: {analysis['llm_risk_level']}")
                print(f"      Suggested Action: {analysis['llm_suggested_action']}")
                print(f"      Confidence: {analysis['llm_confidence_score']:.2f}")
                print(f"      Explanation: {analysis['llm_explanation'][:150]}...")
                
        elif response.status_code == 400:
            error_data = response.json()
            print(f"   ⚠️  {error_data.get('error')}")
        else:
            print(f"   ❌ Failed to get explanation: {response.json()}")
            
    except Exception as e:
        print(f"   ❌ Error getting transaction explanation: {e}")

def show_llm_audit_summary():
    """Show LLM audit log summary"""
    print("\n📋 LLM Audit Log Summary:")
    
    try:
        response = requests.get(f"{BASE_URL}/api/llm/audit?limit=5")
        
        if response.status_code == 200:
            data = response.json()
            summary = data['summary']
            
            print(f"   Total LLM Requests: {summary['total_requests']}")
            print(f"   Success Rate: {summary['success_rate']}%")
            print(f"   Total Estimated Cost: ${summary['total_estimated_cost']:.4f}")
            
            audit_logs = data['audit_logs']
            if audit_logs:
                print(f"\n   Recent LLM Requests:")
                for i, log in enumerate(audit_logs[:3], 1):
                    status_icon = "✅" if log['status'] == 'success' else "❌"
                    print(f"   {i}. {status_icon} {log['model_used']} - "
                          f"{log['tokens_used']} tokens - "
                          f"{log['response_time_ms']}ms - "
                          f"${log['cost_estimate']:.4f}")
            
        else:
            print(f"   No audit logs available")
            
    except Exception as e:
        print(f"   ❌ Error getting audit logs: {e}")

def main():
    """Main Phase 2 setup and demonstration workflow"""
    print("="*50)
    print("🚀 Raya Phase 2 Setup & Testing Script")
    print("="*50)
    
    # Check if the service is running
    llm_enabled = check_service()
    
    # If LLM is enabled, check for API key
    if llm_enabled:
        llm_enabled = check_llm_configuration()
    
    print("\n" + "-"*50)
    print("1️⃣  Step 1: Initialize & Seed Database")
    print("-"*50)

    # Initialize database
    if not init_database():
        sys.exit(1)

    # Seed database
    if not seed_database(customers=100, transactions=1000):
        print("   Skipping further tests due to database seeding failure.")
        sys.exit(1)
    
    time.sleep(2) # Give a moment for data to settle
    
    print("\n2️⃣ Step 2: Run AML Rules")
    time.sleep(2)  # Brief pause
    rule_results = run_aml_rules(with_llm=False)  # Don't run LLM with rules initially
    if not rule_results:
        sys.exit(1)
    
    print("\n3️⃣ Step 3: Run LLM Analysis (if available)")
    if llm_enabled and rule_results.get('flagged_count', 0) > 0:
        time.sleep(1)
        llm_results = run_llm_batch_analysis(batch_limit=3)
    else:
        print("   Skipping LLM analysis (not configured or no flagged transactions)")
    
    print("\n4️⃣ Step 4: Display Results")
    time.sleep(1)
    get_statistics()
    show_sample_flagged_with_llm()
    
    if llm_enabled:
        demonstrate_transaction_explanation()
        show_llm_audit_summary()
    
    print("\n✅ Phase 2 setup completed successfully!")
    print("\n🔗 Useful endpoints:")
    print(f"   - API Root: {BASE_URL}/")
    print(f"   - Flagged Transactions: {BASE_URL}/api/flagged")
    print(f"   - Statistics: {BASE_URL}/api/stats")
    print(f"   - All Transactions: {BASE_URL}/api/transactions")
    print(f"   - Customers: {BASE_URL}/api/customers")
    
    if llm_enabled:
        print(f"   \n🧠 LLM-Enhanced endpoints:")
        print(f"   - LLM Analysis: {BASE_URL}/api/llm/analyze")
        print(f"   - Transaction Explanation: {BASE_URL}/api/transaction/<id>/explanation")
        print(f"   - LLM Audit Logs: {BASE_URL}/api/llm/audit")
    
    print(f"\n💡 Usage examples:")
    print(f"   - Get flagged with LLM: curl '{BASE_URL}/api/flagged?include_llm=true'")
    print(f"   - Run rules with LLM: curl -X POST '{BASE_URL}/api/run-rules' -d '{{\"run_llm_analysis\": true}}' -H 'Content-Type: application/json'")
    if llm_enabled:
        print(f"   - Batch LLM analysis: curl -X POST '{BASE_URL}/api/llm/analyze' -d '{{\"batch_limit\": 5}}' -H 'Content-Type: application/json'")

if __name__ == "__main__":
    main() 
#!/usr/bin/env python3
"""
Raya Setup Script
Quick setup and testing for the Raya AML system
"""

import requests
import time
import sys
import json

BASE_URL = "http://localhost:5001"

def check_service():
    """Check if the service is running"""
    try:
        response = requests.get(f"{BASE_URL}/")
        if response.status_code == 200:
            print("✅ Raya service is running")
            return True
    except requests.exceptions.ConnectionError:
        print("❌ Raya service is not running")
        print("Please start the service with: docker-compose up -d")
        return False

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

def run_aml_rules():
    """Run AML rules on all transactions"""
    print("🔍 Running AML detection rules...")
    
    try:
        response = requests.post(f"{BASE_URL}/api/run-rules")
        
        if response.status_code == 200:
            data = response.json()
            print(f"✅ AML rules executed successfully!")
            print(f"   - Transactions flagged: {data['flagged_transactions']}")
            return True
        else:
            print(f"❌ Failed to run AML rules: {response.json()}")
            return False
            
    except Exception as e:
        print(f"❌ Error running AML rules: {e}")
        return False

def get_statistics():
    """Get and display system statistics"""
    print("📊 Getting system statistics...")
    
    try:
        response = requests.get(f"{BASE_URL}/api/stats")
        
        if response.status_code == 200:
            data = response.json()
            
            print("\n" + "="*50)
            print("📈 AML GUARD SYSTEM STATISTICS")
            print("="*50)
            
            overview = data['overview']
            print(f"Total Customers: {overview['total_customers']:,}")
            print(f"Total Transactions: {overview['total_transactions']:,}")
            print(f"Total Flagged: {overview['total_flagged']:,}")
            print(f"Flag Rate: {overview['flag_rate']}%")
            
            print("\n🚨 Risk Level Breakdown:")
            risk_levels = data.get('risk_levels', {})
            for level, count in risk_levels.items():
                print(f"   {level.upper()}: {count}")
            
            print("\n🔥 Top Triggered Rules:")
            top_rules = data.get('top_triggered_rules', [])
            for i, rule_data in enumerate(top_rules[:5], 1):
                print(f"   {i}. {rule_data['rule']}: {rule_data['count']} flags")
            
            print("="*50)
            return True
        else:
            print(f"❌ Failed to get statistics: {response.json()}")
            return False
            
    except Exception as e:
        print(f"❌ Error getting statistics: {e}")
        return False

def show_sample_flagged():
    """Show sample flagged transactions"""
    print("\n🚩 Sample Flagged Transactions:")
    
    try:
        response = requests.get(f"{BASE_URL}/api/flagged?limit=5")
        
        if response.status_code == 200:
            data = response.json()
            flagged = data['flagged_transactions']
            
            if not flagged:
                print("   No flagged transactions found.")
                return
            
            for i, flag in enumerate(flagged, 1):
                tx = flag['transaction']
                customer = flag['customer']
                
                print(f"\n   {i}. Rule: {flag['rule_name']}")
                print(f"      Risk: {flag['risk_level'].upper()} ({flag['risk_score']}/100)")
                print(f"      Amount: ${tx['amount']:,.2f} {tx['currency']}")
                print(f"      Customer: {customer['name']} ({customer['account_number']})")
                print(f"      Description: {flag['rule_description']}")
                
        else:
            print(f"❌ Failed to get flagged transactions: {response.json()}")
            
    except Exception as e:
        print(f"❌ Error getting flagged transactions: {e}")

def main():
    """Main setup workflow"""
    print("🚀 Raya Setup & Testing Script")
    print("="*40)
    
    # Check if service is running
    if not check_service():
        sys.exit(1)
    
    # Get command line arguments
    if len(sys.argv) > 1:
        if sys.argv[1] == "--stats-only":
            get_statistics()
            show_sample_flagged()
            return
        elif sys.argv[1] == "--seed-only":
            customers = int(sys.argv[2]) if len(sys.argv) > 2 else 1000
            transactions = int(sys.argv[3]) if len(sys.argv) > 3 else 10000
            seed_database(customers, transactions)
            return
        elif sys.argv[1] == "--rules-only":
            run_aml_rules()
            return
    
    # Full setup workflow
    print("\n1️⃣ Step 1: Seed Database")
    if not seed_database():
        sys.exit(1)
    
    print("\n2️⃣ Step 2: Run AML Rules")
    time.sleep(2)  # Brief pause
    if not run_aml_rules():
        sys.exit(1)
    
    print("\n3️⃣ Step 3: Display Results")
    time.sleep(1)  # Brief pause
    get_statistics()
    show_sample_flagged()
    
    print("\n✅ Setup completed successfully!")
    print("\n🔗 Useful endpoints:")
    print(f"   - API Root: {BASE_URL}/")
    print(f"   - Flagged Transactions: {BASE_URL}/api/flagged")
    print(f"   - Statistics: {BASE_URL}/api/stats")
    print(f"   - All Transactions: {BASE_URL}/api/transactions")
    print(f"   - Customers: {BASE_URL}/api/customers")

if __name__ == "__main__":
    main() 
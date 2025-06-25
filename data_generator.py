from faker import Faker
import random
from datetime import datetime, timedelta
from models import db, Customer, Transaction, SanctionedEntity
import uuid

fake = Faker()

class DataGenerator:
    def __init__(self):
        self.fake = Faker(['en_US', 'en_GB', 'es_ES', 'fr_FR', 'de_DE'])
        self.high_risk_countries = ['AF', 'IR', 'KP', 'SY', 'MM', 'BY', 'RU']
        self.transaction_types = ['transfer', 'withdrawal', 'deposit', 'payment']
        self.channels = ['online', 'atm', 'branch', 'mobile', 'card']
        self.currencies = ['USD', 'EUR', 'GBP', 'JPY', 'CAD']
        
    def generate_customers(self, count=1000):
        """Generate fake customer data"""
        customers = []
        
        for _ in range(count):
            # 5% chance of creating a high-risk customer
            is_high_risk = random.random() < 0.05
            country_code = random.choice(self.high_risk_countries) if is_high_risk else fake.country_code()
            
            customer = Customer(
                name=self.fake.name(),
                email=self.fake.unique.email(),
                phone=self.fake.phone_number(),
                address=self.fake.address(),
                date_of_birth=self.fake.date_of_birth(minimum_age=18, maximum_age=80),
                account_number=self.fake.unique.numerify('##########'),
                account_type=random.choice(['checking', 'savings', 'business']),
                balance=round(random.uniform(100, 500000), 2),
                risk_score=random.randint(4, 5) if is_high_risk else random.randint(1, 3),
                is_sanctioned=is_high_risk and random.random() < 0.1,
                country_code=country_code
            )
            customers.append(customer)
            
        return customers
    
    def generate_transactions(self, customers, count=10000):
        """Generate fake transaction data"""
        transactions = []
        customer_ids = [c.id for c in customers]
        
        for _ in range(count):
            sender = random.choice(customers)
            
            # 80% chance of domestic transaction
            if random.random() < 0.8:
                receiver = random.choice(customers)
                counterparty_country = receiver.country_code
                counterparty_name = receiver.name
                counterparty_account = receiver.account_number
            else:
                # International transaction
                receiver = None
                counterparty_country = fake.country_code()
                counterparty_name = self.fake.company()
                counterparty_account = self.fake.numerify('##########')
            
            # Generate suspicious patterns for some transactions
            is_suspicious = random.random() < 0.15
            
            if is_suspicious:
                # Create suspicious amounts
                if random.random() < 0.3:
                    amount = round(random.uniform(9000, 15000), 2)  # Just under/over reporting threshold
                elif random.random() < 0.5:
                    amount = round(random.uniform(50000, 200000), 2)  # Large amounts
                else:
                    amount = round(random.uniform(100, 1000), 2)  # Small amounts for structuring
                    
                # Sometimes use high-risk countries
                if random.random() < 0.4:
                    counterparty_country = random.choice(self.high_risk_countries)
            else:
                amount = round(random.uniform(10, 5000), 2)
            
            transaction = Transaction(
                sender_id=sender.id,
                receiver_id=receiver.id if receiver else None,
                transaction_type=random.choice(self.transaction_types),
                amount=amount,
                currency=random.choice(self.currencies),
                description=self.fake.text(max_nb_chars=100),
                channel=random.choice(self.channels),
                counterparty_name=counterparty_name,
                counterparty_account=counterparty_account,
                counterparty_country=counterparty_country,
                transaction_date=self.fake.date_time_between(start_date='-30d', end_date='now'),
                reference_number=self.fake.unique.numerify('TXN############'),
                status='completed',
                ip_address=self.fake.ipv4(),
                location_lat=float(self.fake.latitude()),
                location_lng=float(self.fake.longitude())
            )
            transactions.append(transaction)
            
        return transactions
    
    def generate_sanctioned_entities(self):
        """Generate sample sanctioned entities list"""
        entities = []
        
        # Sample sanctioned countries/entities
        sanctioned_data = [
            {'name': 'North Korea', 'entity_type': 'country', 'country_code': 'KP', 'program': 'DPRK Sanctions'},
            {'name': 'Iran', 'entity_type': 'country', 'country_code': 'IR', 'program': 'Iran Sanctions'},
            {'name': 'Suspicious Company Ltd', 'entity_type': 'organization', 'country_code': 'RU', 'program': 'Russia Sanctions'},
            {'name': 'Bad Actor Corp', 'entity_type': 'organization', 'country_code': 'AF', 'program': 'Terrorism Sanctions'},
            {'name': 'John Doe Criminal', 'entity_type': 'individual', 'country_code': 'SY', 'program': 'SDN List'},
        ]
        
        for data in sanctioned_data:
            entity = SanctionedEntity(
                name=data['name'],
                entity_type=data['entity_type'],
                country_code=data['country_code'],
                sanctions_program=data['program'],
                effective_date=fake.date_between(start_date='-2y', end_date='today')
            )
            entities.append(entity)
            
        return entities
    
    def seed_database(self, customers_count=1000, transactions_count=10000):
        """Seed the database with fake data"""
        print("Generating customers...")
        customers = self.generate_customers(customers_count)
        
        print("Adding customers to database...")
        for customer in customers:
            db.session.add(customer)
        db.session.commit()
        
        print("Generating transactions...")
        transactions = self.generate_transactions(customers, transactions_count)
        
        print("Adding transactions to database...")
        for transaction in transactions:
            db.session.add(transaction)
        db.session.commit()
        
        print("Adding sanctioned entities...")
        entities = self.generate_sanctioned_entities()
        for entity in entities:
            db.session.add(entity)
        db.session.commit()
        
        print(f"Database seeded with {len(customers)} customers and {len(transactions)} transactions!")
        return customers, transactions 
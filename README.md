# 🧠 Raya - AI-Powered Suspicious Transaction Detection

An intelligent Anti-Money Laundering (AML) system that detects suspicious transactions using rule-based engines and prepares for AI-enhanced analysis.

## 🚀 Features

### Phase 1 (Current Implementation)
- **PostgreSQL Database** with transaction, customer, and flagged transaction models
- **Rule-Based Detection Engine** with 10+ AML rules
- **REST API** for data interaction and rule execution
- **Fake Data Generation** using Faker for realistic testing
- **Docker Support** for easy deployment
- **Comprehensive Statistics** and reporting

### Detection Rules Implemented
1. **Large Cash Withdrawals** (>$10,000)
2. **Multiple High-Value Transactions** (same day pattern)
3. **Sanctioned Country Transfers** (to high-risk countries)
4. **OFAC Sanctioned Entity** matching
5. **Structuring Patterns** (amounts just under $10k)
6. **Round Number Patterns** (suspicious exact amounts)
7. **High Velocity** (multiple transactions in short time)
8. **High-Risk Customer** transactions
9. **Unusual Time Patterns** (late night transactions)
10. **Cross-Border Threshold** violations

## 🛠️ Tech Stack

- **Backend**: Flask, Python 3.11
- **Database**: PostgreSQL 15
- **ORM**: SQLAlchemy
- **Data Generation**: Faker
- **Containerization**: Docker, Docker Compose
- **API**: RESTful APIs with JSON responses

## 📦 Quick Start

### Prerequisites
- Docker and Docker Compose
- Python 3.11+ (for local development)

### 1. Clone and Setup
```bash
git clone <repository>
cd aml-guard
```

### 2. Environment Configuration
```bash
# Copy and edit environment variables
cp .env.example .env
# Edit DATABASE_URL and other settings as needed
```

### 3. Start with Docker
```bash
# Start PostgreSQL and application
docker-compose up -d

# Wait for services to be healthy, then seed data
curl -X POST http://localhost:5000/api/seed \
  -H "Content-Type: application/json" \
  -d '{"customers": 1000, "transactions": 10000}'

# Run AML rules
curl -X POST http://localhost:5000/api/run-rules
```

### 4. Alternative: Local Development
```bash
# Install dependencies
pip install -r requirements.txt

# Start PostgreSQL only
docker-compose up -d db

# Initialize database
python -c "from app import app; from models import db; app.app_context().push(); db.create_all()"

# Start application
python app.py
```

## 🔗 API Endpoints

### Core Endpoints

#### 1. Get Flagged Transactions
```bash
GET /api/flagged?risk_level=high&limit=10&offset=0
```

**Response:**
```json
{
  "flagged_transactions": [
    {
      "flag_id": "uuid",
      "transaction_id": "uuid", 
      "rule_name": "LARGE_CASH_WITHDRAWAL",
      "rule_description": "Large cash withdrawal of $15,000.00",
      "risk_level": "high",
      "risk_score": 85,
      "status": "pending",
      "flagged_at": "2024-01-15T10:30:00",
      "transaction": {
        "amount": 15000.00,
        "currency": "USD",
        "type": "withdrawal",
        "counterparty_name": "John Smith",
        "counterparty_country": "US"
      },
      "customer": {
        "name": "Jane Doe",
        "account_number": "1234567890",
        "risk_score": 3
      }
    }
  ],
  "total_results": 1
}
```

#### 2. Run AML Rules
```bash
POST /api/run-rules
Content-Type: application/json

{
  "transaction_id": "optional-specific-transaction-id"
}
```

#### 3. Seed Database
```bash
POST /api/seed
Content-Type: application/json

{
  "customers": 1000,
  "transactions": 10000
}
```

#### 4. Get Statistics
```bash
GET /api/stats
```

**Response:**
```json
{
  "overview": {
    "total_customers": 1000,
    "total_transactions": 10000,
    "total_flagged": 150,
    "flag_rate": 1.5
  },
  "risk_levels": {
    "critical": 5,
    "high": 25,
    "medium": 70,
    "low": 50
  },
  "top_triggered_rules": [
    {"rule": "HIGH_RISK_CUSTOMER", "count": 45},
    {"rule": "CROSS_BORDER_THRESHOLD", "count": 32}
  ]
}
```

### Additional Endpoints

- `GET /api/transactions` - List transactions with filtering
- `GET /api/customers` - List customers with filtering  
- `GET /api/rules` - Get available AML rules

## 🎯 Usage Examples

### 1. Basic Workflow
```bash
# 1. Seed the database
curl -X POST http://localhost:5000/api/seed

# 2. Run AML detection rules
curl -X POST http://localhost:5000/api/run-rules

# 3. View flagged transactions
curl "http://localhost:5000/api/flagged?risk_level=critical"

# 4. Check system statistics
curl http://localhost:5000/api/stats
```

### 2. Filter Flagged Transactions
```bash
# By risk level
curl "http://localhost:5000/api/flagged?risk_level=high"

# By specific rule
curl "http://localhost:5000/api/flagged?rule_name=LARGE_CASH_WITHDRAWAL"

# By status
curl "http://localhost:5000/api/flagged?status=pending"

# Combined filters with pagination
curl "http://localhost:5000/api/flagged?risk_level=critical&limit=5&offset=0"
```

### 3. Transaction Analysis
```bash
# Large transactions
curl "http://localhost:5000/api/transactions?min_amount=10000"

# Specific transaction types
curl "http://localhost:5000/api/transactions?type=withdrawal"

# High-risk customers
curl "http://localhost:5000/api/customers?risk_score=4"
```

## 🏗️ Database Schema

### Core Tables
- **customers** - Customer information and risk profiles
- **transactions** - Transaction details with AML metadata
- **flagged_transactions** - Rule violations and flags
- **sanctioned_entities** - OFAC and sanctions lists

### Key Fields for AML Analysis
- Transaction amounts, types, and patterns
- Customer risk scores and sanctions status
- Counterparty information and countries
- Transaction timing and velocity
- Geographic and channel data

## 🔍 Rule Engine Details

The AML rule engine evaluates transactions against multiple criteria:

### High-Risk Patterns
- **Structuring**: Multiple transactions just under reporting thresholds
- **Smurfing**: High velocity micro-transactions
- **Geographic Risk**: Transactions to/from sanctioned countries
- **Entity Risk**: Dealings with sanctioned individuals/organizations

### Scoring System
- **Critical (95-100)**: Immediate investigation required
- **High (70-94)**: Priority review needed
- **Medium (50-69)**: Enhanced monitoring
- **Low (25-49)**: Standard review

## 🚀 Future Phases

### Phase 2: AI Integration
- OpenAI GPT-4 integration for transaction explanations
- LangChain for structured AI workflows
- Machine learning risk scoring

### Phase 3: Advanced Features
- Real-time transaction monitoring
- Network analysis with Neo4j
- Advanced statistical models
- Regulatory reporting automation

## 🧪 Testing

```bash
# Test the system
curl http://localhost:5000/
curl http://localhost:5000/api/stats
curl http://localhost:5000/api/rules
```

## 📋 Requirements

See `requirements.txt` for Python dependencies.

## 🐳 Docker Commands

```bash
# Start services
docker-compose up -d

# View logs
docker-compose logs -f app

# Stop services
docker-compose down

# Reset data
docker-compose down -v
docker-compose up -d
```

## 📊 Sample Data

The system generates realistic sample data including:
- 1000+ customers with varying risk profiles
- 10,000+ transactions with suspicious patterns
- Sanctioned entities and high-risk countries
- Multiple currencies and transaction types

## 🔐 Security Notes

- Use environment variables for sensitive configuration
- Implement proper authentication in production
- Regular security audits of AML rules
- Compliance with regulatory requirements

## 🤝 Contributing

1. Fork the repository
2. Create feature branch
3. Implement changes with tests
4. Submit pull request

## 📝 License

[Your License Here]

---

**Raya** - Protecting financial systems through intelligent transaction monitoring. 
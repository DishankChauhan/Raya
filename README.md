# 🧠 Raya - AI-Powered Suspicious Transaction Detection

An intelligent Anti-Money Laundering (AML) system that detects suspicious transactions using rule-based engines enhanced with **GPT-4 powered risk analysis**.

## 🚀 Features

### ✅ Phase 1 (Completed)
- **PostgreSQL Database** with transaction, customer, and flagged transaction models
- **Rule-Based Detection Engine** with 10+ AML rules
- **REST API** for data interaction and rule execution
- **Fake Data Generation** using Faker for realistic testing
- **Docker Support** for easy deployment
- **Comprehensive Statistics** and reporting

### 🔥 Phase 2 (Current - LLM Enhanced)
- **OpenAI GPT-4 Integration** for intelligent risk classification
- **Function Calling API** for structured LLM responses
- **Enhanced Risk Analysis** with AI-powered explanations
- **Audit Logging** for LLM interactions and compliance
- **Cost Tracking** for OpenAI API usage monitoring
- **Confidence Scoring** for LLM assessments

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
- **Database**: PostgreSQL 15 + SQLite (development)
- **ORM**: SQLAlchemy
- **AI/ML**: OpenAI GPT-4, LangChain
- **Data Generation**: Faker
- **Containerization**: Docker, Docker Compose
- **API**: RESTful APIs with JSON responses

## 📦 Quick Start

### Prerequisites
- Docker and Docker Compose
- Python 3.11+ (for local development)
- **OpenAI API Key** (for Phase 2 LLM features)

### 1. Clone and Setup
```bash
git clone <repository>
cd raya
```

### 2. Environment Configuration
```bash
# Copy and edit environment variables
cp env.example .env

# Edit .env file and add your OpenAI API key:
# OPENAI_API_KEY=your-openai-api-key-here
```

### 3. Start with Docker
```bash
# Start PostgreSQL and application
docker-compose up -d

# Initialize database tables
curl -X POST http://localhost:5001/api/init-db

# Seed with sample data
curl -X POST http://localhost:5001/api/seed \
  -H "Content-Type: application/json" \
  -d '{"customers": 1000, "transactions": 10000}'

# Run AML rules
curl -X POST http://localhost:5001/api/run-rules

# Run LLM analysis (Phase 2)
curl -X POST http://localhost:5001/api/llm/analyze \
  -H "Content-Type: application/json" \
  -d '{"batch_limit": 5}'
```

### 4. Quick Demo Script
```bash
# Run the enhanced setup script
python run_setup.py

# Or run specific operations:
python run_setup.py --llm-only    # LLM analysis only
python run_setup.py --demo-llm    # LLM demonstration
python run_setup.py --stats-only  # Statistics only
```

## 🔗 API Endpoints

### Phase 1 Endpoints

#### 1. Get Flagged Transactions (Enhanced)
```bash
GET /api/flagged?include_llm=true&llm_risk_level=High&limit=10
```

**Response:**
```json
{
  "flagged_transactions": [
    {
      "flag_id": "uuid",
      "rule_name": "LARGE_CASH_WITHDRAWAL",
      "risk_level": "high",
      "risk_score": 85,
      "transaction": {
        "amount": 15000.00,
        "currency": "USD",
        "type": "withdrawal"
      },
      "llm_analysis": {
        "risk_level": "High",
        "explanation": "Large cash withdrawal pattern consistent with structuring behavior...",
        "suggested_action": "escalate",
        "confidence_score": 0.89,
        "model_used": "gpt-4-1106-preview"
      }
    }
  ]
}
```

#### 2. Run AML Rules (Enhanced)
```bash
POST /api/run-rules
Content-Type: application/json

{
  "run_llm_analysis": true,
  "transaction_id": "optional-specific-id"
}
```

### 🧠 Phase 2 LLM Endpoints

#### 3. LLM Analysis
```bash
POST /api/llm/analyze
Content-Type: application/json

{
  "batch_limit": 5,
  "transaction_id": "optional-specific-transaction",
  "flagged_transaction_id": "optional-specific-flag"
}
```

**Response:**
```json
{
  "success": true,
  "analyses_completed": 5,
  "results": [
    {
      "risk_level": "High",
      "explanation": "Transaction shows multiple red flags including high amount, unusual timing, and high-risk counterparty location. The pattern suggests potential money laundering through structuring.",
      "suggested_action": "escalate",
      "confidence_score": 0.92,
      "risk_factors": [
        "Large amount near reporting threshold",
        "High-risk jurisdiction",
        "Unusual transaction time"
      ]
    }
  ]
}
```

#### 4. Transaction Explanation
```bash
GET /api/transaction/{transaction_id}/explanation
```

**Response:**
```json
{
  "success": true,
  "explanation": {
    "transaction_id": "uuid",
    "flagged_count": 2,
    "llm_analyses": [
      {
        "rule_name": "LARGE_CASH_WITHDRAWAL",
        "llm_risk_level": "High",
        "llm_explanation": "Detailed AI analysis...",
        "llm_suggested_action": "escalate",
        "llm_confidence_score": 0.89
      }
    ],
    "audit_logs": [
      {
        "status": "success",
        "tokens_used": 847,
        "cost_estimate": 0.0169,
        "response_time_ms": 1250
      }
    ]
  }
}
```

#### 5. LLM Audit Logs
```bash
GET /api/llm/audit?status=success&limit=20
```

**Response:**
```json
{
  "audit_logs": [
    {
      "id": "uuid",
      "transaction_id": "uuid",
      "model_used": "gpt-4-1106-preview",
      "status": "success",
      "tokens_used": 847,
      "response_time_ms": 1250,
      "cost_estimate": 0.0169,
      "created_at": "2024-01-15T10:30:00"
    }
  ],
  "summary": {
    "total_requests": 25,
    "successful_requests": 24,
    "success_rate": 96.0,
    "total_estimated_cost": 0.4238
  }
}
```

### Additional Endpoints

- `GET /api/transactions` - List transactions with filtering
- `GET /api/customers` - List customers with filtering  
- `GET /api/rules` - Get available AML rules
- `GET /api/stats` - Enhanced system statistics with LLM metrics

## 🎯 Usage Examples

### 1. Complete Workflow
```bash
# 1. Initialize and seed
curl -X POST http://localhost:5001/api/init-db
curl -X POST http://localhost:5001/api/seed

# 2. Run rules and LLM analysis together
curl -X POST http://localhost:5001/api/run-rules \
  -H "Content-Type: application/json" \
  -d '{"run_llm_analysis": true}'

# 3. View enhanced flagged transactions
curl "http://localhost:5001/api/flagged?include_llm=true&limit=5"

# 4. Get detailed explanation for specific transaction
curl "http://localhost:5001/api/transaction/{transaction_id}/explanation"
```

### 2. LLM-Specific Operations
```bash
# Batch analyze recent flags
curl -X POST http://localhost:5001/api/llm/analyze \
  -H "Content-Type: application/json" \
  -d '{"batch_limit": 10}'

# Analyze specific transaction
curl -X POST http://localhost:5001/api/llm/analyze \
  -H "Content-Type: application/json" \
  -d '{"transaction_id": "specific-uuid"}'

# Check LLM audit logs
curl "http://localhost:5001/api/llm/audit?status=success"
```

### 3. Enhanced Filtering
```bash
# Filter by LLM risk level
curl "http://localhost:5001/api/flagged?llm_risk_level=High"

# Compare rule-based vs LLM assessments
curl "http://localhost:5001/api/flagged?risk_level=medium&llm_risk_level=High"
```

## 🏗️ Database Schema

### Enhanced Tables (Phase 2)
- **flagged_transactions** - Enhanced with LLM analysis fields:
  - `llm_risk_level`, `llm_explanation`, `llm_suggested_action`
  - `llm_confidence_score`, `llm_analyzed_at`, `llm_model_used`
- **llm_audit_logs** - Complete audit trail:
  - Request/response data, token usage, costs, performance metrics

### LLM Analysis Fields
- **Risk Level**: High, Medium, Low (LLM assessment)
- **Explanation**: Detailed AI-generated reasoning
- **Suggested Action**: escalate, monitor, ignore, investigate
- **Confidence Score**: 0.0-1.0 confidence in assessment
- **Risk Factors**: Array of identified risk elements

## 🔍 LLM Analysis Details

### Prompt Engineering
The system uses carefully crafted prompts that include:
- **Transaction Details**: Amount, type, timing, channel
- **Customer Profile**: Risk score, country, account type, sanctions status  
- **Counterparty Information**: Name, country, account details
- **Geolocation Data**: IP address, transaction location
- **Historical Context**: Previous flags, transaction patterns

### Function Calling
Uses OpenAI's function calling for structured responses:
```json
{
  "name": "analyze_transaction",
  "parameters": {
    "risk_level": {"enum": ["High", "Medium", "Low"]},
    "explanation": {"type": "string"},
    "suggested_action": {"enum": ["escalate", "monitor", "ignore", "investigate"]},
    "confidence_score": {"type": "number", "minimum": 0.0, "maximum": 1.0}
  }
}
```

### Cost Management
- **Token Tracking**: Detailed monitoring of input/output tokens
- **Cost Estimation**: Real-time cost calculation per request
- **Batch Processing**: Configurable batch sizes to control costs
- **Error Handling**: Robust fallbacks for API failures

## 📊 Sample LLM Analysis

**Input Transaction:**
- Amount: $9,200 USD
- Type: Wire Transfer  
- Destination: Russia
- Time: 3:24 AM
- Customer Risk: High (4/5)

**LLM Analysis Output:**
```json
{
  "risk_level": "High",
  "explanation": "This transaction exhibits multiple red flags consistent with money laundering typologies: (1) Amount just below $10k reporting threshold suggests structuring, (2) Transfer to high-risk jurisdiction (Russia) during sanctions period, (3) Unusual timing (early morning) indicates attempt to avoid detection, (4) High-risk customer profile compounds concerns. Recommend immediate escalation to compliance team.",
  "suggested_action": "escalate",
  "confidence_score": 0.94,
  "risk_factors": [
    "Potential structuring - amount below reporting threshold",
    "High-risk jurisdiction - sanctioned country",
    "Unusual timing - 3:24 AM transaction",
    "High-risk customer profile",
    "Wire transfer to unknown entity"
  ]
}
```

## 🚀 Future Phases

### Phase 3: Advanced AI Features
- **Network Analysis** with Neo4j for entity relationships
- **Real-time Streaming** analysis
- **Custom Fine-tuned Models** for AML-specific tasks
- **Multi-model Ensemble** (GPT-4 + Claude + specialized models)

### Phase 4: Regulatory Compliance
- **FINCEN Reporting** automation
- **Regulatory Templates** (SAR, CTR)
- **Audit Trail Management** with blockchain verification
- **Real-time Sanctions Screening** with multiple data sources

## 🧪 Testing & Validation

### Phase 2 Testing
```bash
# Test basic functionality
python run_setup.py --stats-only

# Test LLM integration
export OPENAI_API_KEY="your-key-here"
python run_setup.py --demo-llm

# Full Phase 2 demo
python run_setup.py
```

### Performance Metrics
- **Rule Processing**: ~1000 transactions/second
- **LLM Analysis**: ~5-10 analyses/minute (rate limited)
- **Average LLM Response Time**: 1-3 seconds
- **Cost per Analysis**: $0.01-0.05 (depending on complexity)

## 💰 Cost Management

### OpenAI Usage Optimization
- **Batch Processing**: Process multiple flags efficiently
- **Intelligent Filtering**: Only analyze high-priority flags
- **Caching**: Avoid re-analyzing similar patterns
- **Cost Monitoring**: Real-time cost tracking and alerts

### Sample Costs (GPT-4)
- **Simple Analysis**: ~500 tokens (~$0.01)
- **Complex Analysis**: ~1500 tokens (~$0.03)
- **Daily Budget**: $10-50 for typical deployment
- **Monthly Estimate**: $300-1500 depending on volume

## 🔐 Security & Compliance

### Data Protection
- **API Key Security**: Environment variable management
- **Audit Logging**: Complete request/response tracking
- **Data Anonymization**: PII protection in LLM prompts
- **Error Handling**: Secure failure modes

### Regulatory Alignment
- **Model Transparency**: Explainable AI decisions
- **Audit Trails**: Complete decision history
- **Human Oversight**: LLM as augmentation, not replacement
- **Compliance Reports**: Automated reporting capabilities

## 📝 Configuration

### Required Environment Variables
```bash
# Essential for Phase 2
OPENAI_API_KEY=your-openai-api-key-here
DATABASE_URL=postgresql://raya_user:raya_password@localhost:5433/raya_db

# Optional
FLASK_ENV=development
SECRET_KEY=your-secret-key
```

### Docker Configuration
```yaml
# docker-compose.yml includes:
services:
  app:
    environment:
      - OPENAI_API_KEY=${OPENAI_API_KEY}
      - DATABASE_URL=postgresql://raya_user:raya_password@db:5432/raya_db
```

## 🤝 Contributing

1. Fork the repository
2. Create feature branch (`git checkout -b feature/llm-enhancement`)
3. Implement changes with tests
4. Add LLM-specific test cases
5. Submit pull request

## 📄 License

[Your License Here]

---

**Raya Phase 2** - Intelligent AML monitoring with human-level transaction analysis powered by GPT-4. 🧠🔍💼 
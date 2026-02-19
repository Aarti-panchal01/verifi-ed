# VerifiedProtocol — Decentralized Skill Reputation Layer

**Production-grade decentralized skill reputation protocol built on Algorand.**

## 🎯 Overview

VerifiedProtocol is a decentralized infrastructure for AI-verified talent reputation. It combines:
- **On-chain attestations** on Algorand blockchain
- **Deterministic AI scoring** without external API dependencies
- **Time-decay reputation** with trust index computation
- **Production-ready architecture** with retry logic, error handling, and monitoring

## 🏗️ Architecture

```
┌─────────────────────────────────────────────────────────────┐
│                     Frontend (React)                         │
│  • Wallet Dashboard  • Trust Meter  • Domain Radar Chart    │
└──────────────────────────┬──────────────────────────────────┘
                           │
┌──────────────────────────▼──────────────────────────────────┐
│                  Backend API (FastAPI)                       │
│  • Rate Limiting  • Structured Logging  • Error Middleware  │
├──────────────────────────────────────────────────────────────┤
│  Routers: /analyze  /verify-evidence  /submit  /reputation  │
└──────────────────────────┬──────────────────────────────────┘
                           │
        ┌──────────────────┼──────────────────┐
        │                  │                  │
┌───────▼────────┐ ┌──────▼──────┐ ┌────────▼────────┐
│  AI Scoring    │ │  Reputation │ │  Verification   │
│    Engine      │ │    Engine   │ │     Engine      │
├────────────────┤ ├─────────────┤ ├─────────────────┤
│ • GitHub       │ │ • Time-decay│ │ • GitHub        │
│ • Certificate  │ │ • Trust idx │ │ • Certificate   │
│ • Project      │ │ • Badges    │ │ • Project       │
└────────────────┘ └─────────────┘ └─────────────────┘
                           │
        ┌──────────────────┼──────────────────┐
        │                  │                  │
┌───────▼────────┐ ┌──────▼──────┐ ┌────────▼────────┐
│  Algorand      │ │  Contract   │ │  ARC-4          │
│  Client Mgr    │ │  Service    │ │  Decoder        │
├────────────────┤ ├─────────────┤ ├─────────────────┤
│ • Retry logic  │ │ • MBR fund  │ │ • Canonical     │
│ • Exponential  │ │ • Tx submit │ │ • Validation    │
│   backoff      │ │ • Record    │ │ • Error         │
│ • Timeouts     │ │   retrieval │ │   handling      │
└────────────────┘ └─────────────┘ └─────────────────┘
                           │
                ┌──────────▼──────────┐
                │  Algorand Testnet   │
                │  Smart Contract     │
                │  App ID: 755779875  │
                └─────────────────────┘
```

## 🚀 Quick Start

### Prerequisites
- Python 3.10+
- Node.js 18+
- Poetry (Python package manager)
- Algorand wallet with testnet funds

### Backend Setup

```bash
cd projects/verified_protocol

# Install dependencies
poetry install

# Configure environment
cp .env.example .env
# Edit .env with your Algorand credentials

# Run CLI tools
poetry run python interact.py submit python 85
poetry run python interact.py verify "*"
poetry run python read_records.py <WALLET_ADDRESS>

# Start API server
poetry run uvicorn backend.main:app --reload --port 8000
```

### Frontend Setup

```bash
cd frontend

# Install dependencies
npm install

# Configure environment
cp .env.example .env.local
# Edit .env.local if needed

# Start development server
npm run dev

# Build for production
npm run build
```

## 📁 Project Structure

```
projects/verified_protocol/
├── backend/
│   ├── core/                    # Core infrastructure
│   │   ├── algorand_client.py   # Algorand client manager
│   │   ├── contract_service.py  # Smart contract service
│   │   └── arc4_decoder.py      # ARC-4 decoder
│   ├── routers/                 # API endpoints
│   │   ├── scoring.py           # /analyze/*
│   │   ├── verification.py      # /verify-evidence/*
│   │   ├── submission.py        # /submit
│   │   ├── retrieval.py         # /wallet/*, /timeline/*
│   │   └── reputation.py        # /reputation/*, /verify/*
│   └── main.py                  # FastAPI application
├── ai_scoring/                  # AI scoring engine
│   ├── engine.py                # Main orchestrator
│   ├── github_analyzer.py       # GitHub repo analysis
│   ├── certificate_analyzer.py  # Certificate analysis
│   ├── project_analyzer.py      # Project analysis
│   ├── models.py                # Data models
│   └── rules.py                 # Scoring rules
├── reputation_engine/           # Reputation computation
│   └── engine.py                # Trust index & aggregation
├── verification_engine/         # Evidence verification
│   ├── github_verifier.py
│   ├── certificate_verifier.py
│   └── project_verifier.py
├── frontend/                    # React frontend
│   ├── src/
│   │   ├── components/          # Reusable components
│   │   ├── pages/               # Page components
│   │   └── utils/               # API client & utilities
│   └── vite.config.js
├── smart_contracts/             # Algorand smart contracts
├── interact.py                  # CLI interaction tool
├── read_records.py              # CLI record reader
└── hash_artifact.py             # Artifact hashing utility
```

## 🔧 Core Features

### Phase 1: Core Pipeline Hardening ✅
- Unified Algorand client with exponential backoff retry
- Centralized contract service with automatic MBR funding
- Canonical ARC-4 decoder with validation
- Timeout handling and structured exceptions
- Removed all code duplication

### Phase 2: AI Scoring Engine ✅
- **GitHub Analyzer**: Commit activity, code volume, language diversity, community signals, documentation, recency, maturity
- **Certificate Analyzer**: Issuer trust ranking, duration, proctoring, hands-on vs theoretical
- **Project Analyzer**: Architecture patterns, test coverage, modularity, CI configs
- **Deterministic scoring**: No external AI APIs, fully reproducible

### Phase 3: Reputation Engine ✅
- Time-decay weighted reputation (180-day half-life)
- Consistency score (standard deviation analysis)
- Domain authority index
- Diversity score
- Trust index formula: `(weighted_score × 0.4) + (consistency × 0.2) + (diversity × 0.1) + (volume × 0.1) + (longevity × 0.2)`

### Phase 4: Backend Hardening ✅
- Clean modular FastAPI architecture
- Rate limiting (60 req/min per IP)
- Structured logging with request timing
- Error middleware with proper HTTP status codes
- Health and version endpoints
- Service layer pattern (no direct contract calls in routers)

### Phase 5: Frontend (In Progress)
- Environment-based configuration
- Production-grade API client with retry logic
- Wallet reputation dashboard
- Animated trust meter
- Domain radar chart
- Timeline with time-decay visualization
- Verification badge animation
- Responsive layout

### Phase 6: Protocol Documentation ✅
- ARCHITECTURE.md
- WHITEPAPER.md
- Comprehensive README

## 📡 API Endpoints

### Scoring
- `POST /analyze/repo` — Analyze GitHub repository
- `POST /analyze/certificate` — Analyze certificate file
- `POST /analyze/project` — Analyze project directory

### Verification
- `POST /verify-evidence/repo` — Verify GitHub repository
- `POST /verify-evidence/certificate` — Verify certificate
- `POST /verify-evidence/project` — Verify project

### Submission
- `POST /submit` — Submit skill record on-chain

### Retrieval
- `GET /wallet/{wallet}` — Get wallet records
- `GET /timeline/{wallet}` — Get chronological timeline

### Reputation
- `GET /reputation/{wallet}` — Get reputation profile
- `GET /verify/{wallet}` — Verify wallet with reputation

### System
- `GET /` — API info
- `GET /health` — Health check
- `GET /docs` — Interactive API documentation

## 🧪 Testing

```bash
# Test CLI tools
poetry run python interact.py submit python 85
poetry run python interact.py verify "*"

# Test API endpoints
curl http://localhost:8000/health
curl http://localhost:8000/wallet/<WALLET_ADDRESS>
curl http://localhost:8000/reputation/<WALLET_ADDRESS>

# Test GitHub analysis
curl -X POST http://localhost:8000/analyze/repo \
  -H "Content-Type: application/json" \
  -d '{"repo_url": "https://github.com/algorand/go-algorand"}'
```

## 🔐 Security

- **No private keys in code**: All credentials via environment variables
- **Rate limiting**: 60 requests per minute per IP
- **Input validation**: Pydantic models for all API inputs
- **Timeout protection**: 30-second default timeout on all operations
- **Retry logic**: Exponential backoff with max 3 attempts
- **Structured exceptions**: Proper error classification and handling

## 📊 Reputation Formula

```
Trust Index = (weighted_score × 0.4) 
            + (consistency × 0.2) 
            + (diversity × 0.1) 
            + (volume × 0.1) 
            + (longevity × 0.2)

Where:
- weighted_score: Time-decay weighted average of all scores
- consistency: 1 - (std_dev / 30), measures score stability
- diversity: min(1.0, domain_count / 4), rewards multi-domain expertise
- volume: min(1.0, record_count / 10), rewards activity
- longevity: min(1.0, span_days / 180), rewards sustained participation
```

## 🎖️ Verification Badge Criteria

- Minimum 3 on-chain records
- Minimum 50/100 reputation score
- At least 1 distinct domain

## 🌐 Network Information

- **Network**: Algorand Testnet
- **Smart Contract**: App ID 755779875
- **Explorer**: https://testnet.explorer.perawallet.app/

## 📝 License

MIT License - See LICENSE file for details

## 🤝 Contributing

This is production infrastructure. All contributions must:
- Include comprehensive tests
- Follow existing architecture patterns
- Maintain deterministic behavior
- Include proper error handling
- Update documentation

## 📞 Support

For issues, questions, or contributions, please open an issue on the repository.

---

**Built with ❤️ for the decentralized future of talent verification**

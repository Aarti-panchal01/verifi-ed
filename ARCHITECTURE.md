# VerifiedProtocol — System Architecture

## Overview

VerifiedProtocol is a production-grade decentralized skill reputation layer built on Algorand. It combines on-chain attestations with deterministic AI scoring to create verifiable, tamper-proof skill credentials.

## Architecture Layers

```
┌─────────────────────────────────────────────────────────────┐
│                     Frontend (React)                         │
│  • Wallet Dashboard  • Trust Meter  • Domain Radar Chart    │
│  • Timeline Visualization  • Verification Badge Display     │
└──────────────────────┬──────────────────────────────────────┘
                       │ REST API
┌──────────────────────┴──────────────────────────────────────┐
│                  Backend API (FastAPI)                       │
│  ┌────────────────────────────────────────────────────────┐ │
│  │  Routers                                               │ │
│  │  • /analyze/*     — AI Scoring                         │ │
│  │  • /submit        — On-chain Submission                │ │
│  │  • /wallet/*      — Record Retrieval                   │ │
│  │  • /reputation/*  — Reputation Profiles                │ │
│  └────────────────────────────────────────────────────────┘ │
│  ┌────────────────────────────────────────────────────────┐ │
│  │  Core Services                                         │ │
│  │  • AlgorandClientManager  — Connection & Retry Logic   │ │
│  │  • ContractService        — Smart Contract Interface   │ │
│  │  • ARC4Decoder            — Record Decoding            │ │
│  └────────────────────────────────────────────────────────┘ │
│  ┌────────────────────────────────────────────────────────┐ │
│  │  AI Scoring Engine (Deterministic)                     │ │
│  │  • GitHubAnalyzer         — Repo Analysis              │ │
│  │  • ProjectAnalyzer        — Local Project Analysis     │ │
│  │  • CertificateAnalyzer    — Certificate Validation     │ │
│  └────────────────────────────────────────────────────────┘ │
│  ┌────────────────────────────────────────────────────────┐ │
│  │  Reputation Engine                                     │ │
│  │  • Time-decay Weighting   • Trust Index Computation    │ │
│  │  • Domain Aggregation     • Badge Eligibility          │ │
│  └────────────────────────────────────────────────────────┘ │
└──────────────────────┬──────────────────────────────────────┘
                       │ AlgoKit SDK
┌──────────────────────┴──────────────────────────────────────┐
│              Algorand Testnet (Layer 1)                      │
│  ┌────────────────────────────────────────────────────────┐ │
│  │  VerifiedProtocol Smart Contract (App ID: 755779875)   │ │
│  │  • submit_skill_record()  — Write attestation          │ │
│  │  • get_skill_records()    — Read records               │ │
│  │  • get_record_count()     — Count records              │ │
│  └────────────────────────────────────────────────────────┘ │
│  ┌────────────────────────────────────────────────────────┐ │
│  │  Box Storage (Per-Wallet)                              │ │
│  │  • Key: wallet_address                                 │ │
│  │  • Value: Length-prefixed ARC-4 SkillRecord array      │ │
│  └────────────────────────────────────────────────────────┘ │
└─────────────────────────────────────────────────────────────┘
```

## Core Components

### 1. Smart Contract Layer

**Technology**: Algorand PyTeal  
**Network**: Testnet (App ID: 755779875)  
**Storage**: Box storage (per-wallet key-value pairs)

**Data Schema** (ARC-4 Encoded):
```python
SkillRecord {
    mode: String           # "ai-graded", "self-attested", etc.
    domain: String         # "python", "solidity", "web3:defi"
    score: UInt64          # 0-100 credibility score
    artifact_hash: String  # SHA-256 hash of evidence
    timestamp: UInt64      # Unix timestamp
}
```

**Key Methods**:
- `submit_skill_record()` — Append new attestation to wallet's Box
- `get_skill_records()` — Retrieve all records for a wallet
- `get_record_count()` — Get total record count

**Security Features**:
- Immutable on-chain storage
- Cryptographic artifact hashing
- Timestamp-based ordering
- Minimum Balance Requirement (MBR) enforcement

### 2. Backend Core Services

#### AlgorandClientManager
**Purpose**: Centralized Algorand client lifecycle management

**Features**:
- Exponential backoff retry logic (3 attempts, 2-16s delay)
- Structured exception handling (TransactionError, RateLimitError, NetworkError)
- Connection pooling
- Transaction confirmation waiting
- Automatic validity window management (1000 rounds)

**Usage**:
```python
from backend.core.algorand_client import get_manager

manager = get_manager()
result = manager.send_and_confirm(
    lambda: client.send.submit_skill_record(...),
    operation_name="submit_skill_record"
)
```

#### ContractService
**Purpose**: High-level smart contract interface

**Features**:
- Automatic Box MBR calculation and funding (0.5 ALGO)
- Transaction submission with retry logic
- Record retrieval and decoding
- Structured result objects (SubmissionResult, RecordQueryResult)

**Usage**:
```python
from backend.core.contract_service import get_contract_service

service = get_contract_service()
result = service.submit_skill_record(
    mode="ai-graded",
    domain="python",
    score=85,
    artifact_hash="abc123...",
    timestamp=1234567890
)
```

#### ARC4Decoder
**Purpose**: Canonical ARC-4 decoding implementation

**Features**:
- Length-prefixed record parsing
- Offset-based dynamic field extraction
- UTF-8 string decoding with error handling
- Record validation
- Detailed error reporting

**Wire Format**:
```
[2B: record_len][record_len bytes: ARC-4 struct]

ARC-4 Struct:
[2B: mode_offset][2B: domain_offset][8B: score]
[2B: artifact_offset][8B: timestamp]
[dynamic strings at offsets...]
```

### 3. AI Scoring Engine

**Design Philosophy**: Fully deterministic, no external AI APIs

#### GitHubAnalyzer
**Signals Evaluated**:
1. **Commit Activity** (weight: 0.20)
   - Total contributions
   - Contributor count
   - Recent activity

2. **Code Volume** (weight: 0.10)
   - File count
   - Directory depth
   - Average file size

3. **Language Diversity** (weight: 0.10)
   - Primary language weight
   - Framework detection (Django, React, Flask, etc.)
   - Ecosystem maturity

4. **Community Signals** (weight: 0.20)
   - Stars (50% weight)
   - Forks (30% weight)
   - Watchers (20% weight)

5. **Documentation Quality** (weight: 0.15)
   - README length and structure
   - LICENSE presence
   - CI/CD configuration
   - Test coverage indicators

6. **Recency** (weight: 0.10)
   - Days since last push
   - Excellent: ≤7 days (1.0)
   - Good: ≤30 days (0.7)
   - Acceptable: ≤90 days (0.4)
   - Stale: >90 days (0.1)

7. **Repo Maturity** (weight: 0.10)
   - Repository age
   - Established: ≥365 days

8. **Code Quality Signals** (weight: 0.05)
   - LICENSE file
   - .gitignore
   - README
   - CI configuration
   - Test directories

**Output**:
```json
{
  "credibility_score": 85,
  "domain": "python",
  "subdomain": "web3",
  "confidence": 0.92,
  "explanation": "Strong credibility (85/100) in python...",
  "breakdown": [
    {
      "factor": "commit_activity",
      "weight": 0.20,
      "raw_score": 0.85,
      "weighted_score": 0.17,
      "explanation": "1250 contributions across 8 contributors"
    }
  ],
  "artifact_hash": "sha256:abc123..."
}
```

#### ProjectAnalyzer
**Evaluates**:
- Architecture patterns (MVC, microservices, monolith)
- Test coverage detection (pytest, jest, mocha)
- Code modularity (import graph analysis)
- Dependency graph density
- CI/CD configuration (GitHub Actions, CircleCI, Travis)
- Containerization (Dockerfile, docker-compose.yml)

#### CertificateAnalyzer
**Evaluates**:
- Issuer trust ranking (deterministic hardcoded table)
- Certificate duration
- Proctored vs non-proctored
- Hands-on vs theoretical
- Expiration status

**Trusted Issuers** (examples):
- AWS: 0.95
- Google Cloud: 0.95
- Microsoft: 0.90
- Coursera: 0.80
- Udemy: 0.60

### 4. Reputation Engine

**Purpose**: Aggregate on-chain records into trust profiles

#### Time-Decay Weighting
```python
decay_weight = exp(-0.693 * age_days / 180)
# Half-life: 180 days
```

#### Trust Index Formula
```python
trust_index = (
    (reputation / 85) * 0.40 +      # Reputation level
    (record_count / 10) * 0.20 +    # Volume
    (domain_count / 4) * 0.15 +     # Diversity
    consistency * 0.15 +             # Score std dev
    (span_days / 180) * 0.10        # Longevity
)
```

#### Credibility Levels
- **Exceptional**: ≥90/100
- **Strong**: 70-89/100
- **Moderate**: 50-69/100
- **Developing**: 30-49/100
- **Minimal**: <30/100

#### Verification Badge Eligibility
- Minimum 3 records
- Minimum 50/100 reputation
- Minimum 1 distinct domain

**Output**:
```json
{
  "wallet": "ALGORAND_ADDRESS",
  "total_reputation": 78.5,
  "credibility_level": "Strong",
  "trust_index": 0.7234,
  "verification_badge": true,
  "total_records": 12,
  "top_domain": "python",
  "active_since": 1640000000,
  "domain_scores": [
    {
      "domain": "python",
      "score": 82.3,
      "record_count": 7,
      "latest_timestamp": 1708560000,
      "trend": "rising"
    }
  ]
}
```

## API Endpoints

### Scoring
- `POST /analyze/repo` — Analyze GitHub repository
- `POST /analyze/certificate` — Analyze certificate
- `POST /analyze/project` — Analyze local project

### Submission
- `POST /submit` — Submit skill record on-chain

### Retrieval
- `GET /wallet/{wallet}` — Fetch all records
- `GET /timeline/{wallet}` — Chronological timeline

### Reputation
- `GET /reputation/{wallet}` — Compute reputation profile
- `GET /verify/{wallet}` — Verification status + reputation

## Data Flow

### Submission Flow
```
1. User submits evidence (GitHub repo, certificate, project)
2. AI Scoring Engine analyzes evidence
   → GitHubAnalyzer / ProjectAnalyzer / CertificateAnalyzer
3. Engine produces ScoringResult (0-100 score + breakdown)
4. Backend generates artifact_hash (SHA-256)
5. ContractService funds Box MBR (0.5 ALGO)
6. ContractService submits to smart contract
7. Smart contract appends ARC-4 encoded record to Box
8. Transaction confirmed on Algorand
9. Return transaction ID + explorer URL
```

### Retrieval Flow
```
1. User requests wallet records
2. ContractService queries smart contract
3. Smart contract returns raw Box bytes
4. ARC4Decoder decodes records
5. ReputationEngine computes trust profile
6. Return records + reputation + badge status
```

## Security Model

### On-Chain Security
- **Immutability**: Records cannot be modified or deleted
- **Cryptographic Integrity**: SHA-256 artifact hashing
- **Timestamp Ordering**: Chronological record sequence
- **Wallet Isolation**: Per-wallet Box storage

### Off-Chain Security
- **Rate Limiting**: 60 requests/minute per IP
- **Input Validation**: Pydantic schema validation
- **Error Handling**: Structured exceptions with retry logic
- **Timeout Management**: 30s default timeout

### Sybil Resistance
**Current Approach**:
- Time-decay weighting (recent records matter more)
- Consistency scoring (penalizes erratic scores)
- Domain diversity (rewards multi-domain expertise)
- Trust index (multi-factor reputation)

**Future Enhancements**:
- Zero-knowledge proofs for privacy-preserving verification
- Cross-chain identity linking
- Social graph analysis
- Stake-based attestations

## Technology Stack

### Smart Contract
- **Language**: Python (PyTeal)
- **Framework**: AlgoKit
- **Network**: Algorand Testnet
- **Storage**: Box storage (32KB max per box)

### Backend
- **Framework**: FastAPI 0.100+
- **Language**: Python 3.11+
- **SDK**: AlgoKit Utils
- **HTTP Client**: httpx (async)

### Frontend
- **Framework**: React 18+
- **Build Tool**: Vite
- **Styling**: Tailwind CSS
- **Charts**: Recharts / Chart.js

### Infrastructure
- **Deployment**: Docker containers
- **CI/CD**: GitHub Actions
- **Monitoring**: Structured logging
- **Rate Limiting**: In-memory store (production: Redis)

## Performance Characteristics

### Smart Contract
- **Transaction Time**: ~4 seconds (Algorand block time)
- **Box Read**: <1 second
- **Box Write**: ~4 seconds + MBR funding
- **Max Records per Wallet**: ~500 (32KB box limit)

### Backend
- **GitHub Analysis**: 2-5 seconds (API calls)
- **Project Analysis**: 1-3 seconds (local filesystem)
- **Certificate Analysis**: <1 second (deterministic)
- **Reputation Computation**: <100ms (in-memory)

### Scalability
- **Concurrent Users**: 1000+ (FastAPI async)
- **Records per Second**: 50+ (Algorand throughput)
- **Storage**: Unlimited wallets (Box storage)

## Deployment Architecture

### Development
```
Local Machine
├── Backend (uvicorn --reload)
├── Frontend (vite dev server)
└── Algorand Testnet (remote)
```

### Production
```
Cloud Infrastructure
├── Load Balancer
├── Backend Cluster (Docker + Kubernetes)
│   ├── API Pods (3+ replicas)
│   ├── Redis (rate limiting)
│   └── Prometheus (monitoring)
├── Frontend CDN (Vercel / Netlify)
└── Algorand Testnet (remote)
```

## Future Roadmap

### Phase 1: Mainnet Migration
- Deploy to Algorand Mainnet
- Implement governance token
- Add staking mechanism

### Phase 2: Advanced Features
- Zero-knowledge proof integration
- Cross-chain bridges (Ethereum, Polygon)
- NFT-based credentials
- Decentralized identity (DID) integration

### Phase 3: Ecosystem Growth
- Developer SDK (Python, JavaScript, Rust)
- Employer verification portal
- Talent marketplace integration
- API partnerships (LinkedIn, GitHub, etc.)

### Phase 4: Governance
- DAO formation
- Community-driven issuer trust rankings
- Protocol parameter voting
- Treasury management

## Contributing

See `CONTRIBUTING.md` for development guidelines.

## License

MIT License — See `LICENSE` file for details.

---

**Built with ❤️ for the decentralized future of work.**

"""
System Integration Test
========================

Comprehensive test to verify all components work together.
"""

import sys
from pathlib import Path

def test_imports():
    """Test all critical imports."""
    print("Testing imports...")
    
    try:
        from backend.core.algorand_client import get_manager, AlgorandClientManager
        from backend.core.contract_service import get_contract_service, ContractService
        from backend.core.arc4_decoder import ARC4Decoder
        print("  ✓ Core modules")
    except Exception as e:
        print(f"  ✗ Core modules failed: {e}")
        return False
    
    try:
        from ai_scoring.engine import ScoringEngine
        from ai_scoring.github_analyzer import GitHubAnalyzer
        from ai_scoring.certificate_analyzer import CertificateAnalyzer
        from ai_scoring.project_analyzer import ProjectAnalyzer
        print("  ✓ AI Scoring Engine")
    except Exception as e:
        print(f"  ✗ AI Scoring Engine failed: {e}")
        return False
    
    try:
        from reputation_engine.engine import ReputationEngine
        print("  ✓ Reputation Engine")
    except Exception as e:
        print(f"  ✗ Reputation Engine failed: {e}")
        return False
    
    try:
        from verification_engine.github_verifier import GitHubVerifier
        from verification_engine.certificate_verifier import CertificateVerifier
        from verification_engine.project_verifier import ProjectVerifier
        print("  ✓ Verification Engine")
    except Exception as e:
        print(f"  ✗ Verification Engine failed: {e}")
        return False
    
    try:
        from backend.routers import scoring, verification, submission, retrieval, reputation
        print("  ✓ API Routers")
    except Exception as e:
        print(f"  ✗ API Routers failed: {e}")
        return False
    
    return True


def test_arc4_decoder():
    """Test ARC-4 decoder with sample data."""
    print("\nTesting ARC-4 decoder...")
    
    try:
        from backend.core.arc4_decoder import ARC4Decoder
        
        decoder = ARC4Decoder()
        
        # Test empty input
        result = decoder.decode_skill_records(b"")
        assert result == [], "Empty input should return empty list"
        
        # Test validation
        valid_record = {
            "mode": "ai-graded",
            "domain": "python",
            "score": 85,
            "artifact_hash": "abc123",
            "timestamp": 1234567890,
        }
        assert decoder.validate_record(valid_record), "Valid record should pass validation"
        
        invalid_record = {"mode": "test"}
        assert not decoder.validate_record(invalid_record), "Invalid record should fail validation"
        
        print("  ✓ ARC-4 decoder working correctly")
        return True
    except Exception as e:
        print(f"  ✗ ARC-4 decoder failed: {e}")
        return False


def test_reputation_engine():
    """Test reputation engine with sample data."""
    print("\nTesting reputation engine...")
    
    try:
        from reputation_engine.engine import ReputationEngine
        
        engine = ReputationEngine()
        
        # Test with empty records
        profile = engine.compute("TEST_WALLET", [])
        assert profile.total_records == 0, "Empty records should have 0 count"
        assert profile.total_reputation == 0.0, "Empty records should have 0 reputation"
        
        # Test with sample records
        import time
        now = int(time.time())
        
        sample_records = [
            {
                "mode": "ai-graded",
                "domain": "python",
                "score": 85,
                "artifact_hash": "hash1",
                "timestamp": now - 86400,  # 1 day ago
            },
            {
                "mode": "ai-graded",
                "domain": "python",
                "score": 90,
                "artifact_hash": "hash2",
                "timestamp": now,
            },
            {
                "mode": "ai-graded",
                "domain": "javascript",
                "score": 75,
                "artifact_hash": "hash3",
                "timestamp": now - 172800,  # 2 days ago
            },
        ]
        
        profile = engine.compute("TEST_WALLET", sample_records)
        assert profile.total_records == 3, "Should have 3 records"
        assert profile.total_reputation > 0, "Should have positive reputation"
        assert len(profile.domain_scores) == 2, "Should have 2 domains"
        assert profile.trust_index > 0, "Should have positive trust index"
        
        print(f"  ✓ Reputation: {profile.total_reputation:.1f}/100")
        print(f"  ✓ Trust Index: {profile.trust_index:.3f}")
        print(f"  ✓ Level: {profile.credibility_level.value}")
        print(f"  ✓ Badge: {profile.verification_badge}")
        
        return True
    except Exception as e:
        print(f"  ✗ Reputation engine failed: {e}")
        import traceback
        traceback.print_exc()
        return False


def test_scoring_models():
    """Test scoring engine models."""
    print("\nTesting scoring models...")
    
    try:
        from ai_scoring.models import (
            ScoringInput,
            ScoringResult,
            EvidenceMode,
            SourceType,
            VerificationSignal,
            DomainDetection,
        )
        
        # Test ScoringInput
        inp = ScoringInput(
            mode=EvidenceMode.DEVELOPER,
            source_type=SourceType.GITHUB_REPO,
            source_url="https://github.com/test/repo",
        )
        assert inp.mode == EvidenceMode.DEVELOPER
        
        # Test VerificationSignal
        signal = VerificationSignal(
            signal_name="test_signal",
            value=50,
            max_value=100,
            normalized=0.5,
            detail="Test detail",
        )
        assert signal.normalized == 0.5
        
        # Test DomainDetection
        domain = DomainDetection(domain="python", confidence=0.9)
        assert domain.confidence == 0.9
        
        print("  ✓ All models working correctly")
        return True
    except Exception as e:
        print(f"  ✗ Models failed: {e}")
        return False


def test_api_structure():
    """Test API structure and endpoints."""
    print("\nTesting API structure...")
    
    try:
        from backend.main import app
        
        routes = [route.path for route in app.routes]
        
        required_endpoints = [
            "/",
            "/health",
            "/analyze/repo",
            "/analyze/certificate",
            "/analyze/project",
            "/verify-evidence/repo",
            "/verify-evidence/certificate",
            "/verify-evidence/project",
            "/submit",
            "/wallet/{wallet}",
            "/timeline/{wallet}",
            "/reputation/{wallet}",
            "/verify/{wallet}",
        ]
        
        for endpoint in required_endpoints:
            if endpoint not in routes:
                print(f"  ✗ Missing endpoint: {endpoint}")
                return False
        
        print(f"  ✓ All {len(required_endpoints)} required endpoints present")
        return True
    except Exception as e:
        print(f"  ✗ API structure test failed: {e}")
        return False


def main():
    """Run all tests."""
    print("=" * 60)
    print("VerifiedProtocol — System Integration Test")
    print("=" * 60)
    
    tests = [
        ("Imports", test_imports),
        ("ARC-4 Decoder", test_arc4_decoder),
        ("Reputation Engine", test_reputation_engine),
        ("Scoring Models", test_scoring_models),
        ("API Structure", test_api_structure),
    ]
    
    results = []
    for name, test_func in tests:
        try:
            result = test_func()
            results.append((name, result))
        except Exception as e:
            print(f"\n✗ {name} crashed: {e}")
            results.append((name, False))
    
    print("\n" + "=" * 60)
    print("Test Results")
    print("=" * 60)
    
    passed = sum(1 for _, result in results if result)
    total = len(results)
    
    for name, result in results:
        status = "✓ PASS" if result else "✗ FAIL"
        print(f"{status:8} {name}")
    
    print("=" * 60)
    print(f"Results: {passed}/{total} tests passed")
    print("=" * 60)
    
    if passed == total:
        print("\n🎉 ALL SYSTEMS OPERATIONAL — PRODUCTION READY")
        return 0
    else:
        print(f"\n⚠️  {total - passed} test(s) failed — review errors above")
        return 1


if __name__ == "__main__":
    sys.exit(main())

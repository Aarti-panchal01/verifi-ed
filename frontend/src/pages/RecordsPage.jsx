import { useState, useEffect } from 'react';
import { useWallet } from '../context/WalletContext';
import ScoreCircle from '../components/ScoreCircle';
import DomainChart from '../components/DomainChart';
import Timeline from '../components/SkillTimeline';

const API = 'http://localhost:8000';

export default function DashboardPage() {
    const { address, connected, connectWallet, setManualWallet } = useWallet();
    const [walletInput, setWalletInput] = useState('');
    const [reputation, setReputation] = useState(null);
    const [records, setRecords] = useState([]);
    const [loading, setLoading] = useState(false);
    const [error, setError] = useState('');

    /* Auto-load dashboard when wallet is connected */
    useEffect(() => {
        if (address && address.length >= 58) {
            handleLookup(address);
        }
    }, [address]);

    async function handleLookup(walletAddr) {
        const w = walletAddr || address || walletInput;
        if (!w || w.length < 58) return;

        setLoading(true);
        setError('');
        setReputation(null);
        setRecords([]);

        try {
            const [repRes, walletRes] = await Promise.all([
                fetch(`${API}/reputation/${w}`),
                fetch(`${API}/wallet/${w}`),
            ]);

            if (!repRes.ok) throw new Error((await repRes.json().catch(() => ({}))).detail || 'Reputation fetch failed');
            if (!walletRes.ok) throw new Error((await walletRes.json().catch(() => ({}))).detail || 'Records fetch failed');

            const repData = await repRes.json();
            const walletData = await walletRes.json();

            setReputation(repData);
            setRecords(walletData.records || []);
        } catch (e) {
            setError(e.message);
        } finally {
            setLoading(false);
        }
    }

    function handleManualLookup() {
        if (walletInput.length >= 58) {
            setManualWallet(walletInput);
            handleLookup(walletInput);
        }
    }

    const tierClass = reputation ? `tier-${reputation.credibility_level}` : '';

    return (
        <div className="page">
            <div className="page-header">
                <h1 className="page-title">Wallet Dashboard</h1>
                <p className="page-subtitle">
                    Your skill reputation: trust index, domain strengths, credibility history, and on-chain record timeline.
                </p>
            </div>

            {/* Wallet Input — Auto-fills when connected */}
            {!connected && (
                <div className="card" style={{ marginBottom: '24px' }}>
                    <div className="card-header">
                        <div className="card-icon">⬡</div>
                        <div>
                            <div className="card-title">Connect Wallet to View Dashboard</div>
                            <div className="card-description">Connect Pera Wallet or paste your address</div>
                        </div>
                    </div>
                    <div style={{ display: 'flex', gap: '10px', flexWrap: 'wrap' }}>
                        <button className="btn btn-accent" onClick={connectWallet}>
                            ⬡ Connect Pera Wallet
                        </button>
                        <span style={{ alignSelf: 'center', color: 'var(--text-muted)', fontSize: '0.82rem' }}>or</span>
                        <input
                            id="dashboard-wallet-input"
                            className="form-input form-input-mono"
                            placeholder="Paste Algorand wallet address…"
                            value={walletInput}
                            onChange={e => setWalletInput(e.target.value)}
                            onKeyDown={e => e.key === 'Enter' && handleManualLookup()}
                            style={{ flex: 1, minWidth: 200 }}
                        />
                        <button
                            id="dashboard-lookup-btn"
                            className={`btn btn-primary ${loading ? 'btn-loading' : ''}`}
                            onClick={handleManualLookup}
                            disabled={loading || walletInput.length < 58}
                        >
                            {loading ? '' : 'Lookup'}
                        </button>
                    </div>
                    {error && <div className="result-panel result-error" style={{ marginTop: '12px' }}>{error}</div>}
                </div>
            )}

            {/* Connected but loading */}
            {connected && loading && (
                <div className="card analyzing-skeleton">
                    <div className="skeleton-pulse" style={{ textAlign: 'center', padding: '40px' }}>
                        <div style={{ fontSize: '2rem', marginBottom: 12 }}>📊</div>
                        <div style={{ color: 'var(--accent-cyan)', fontWeight: 600 }}>Loading dashboard for {address.slice(0, 6)}…{address.slice(-4)}</div>
                    </div>
                </div>
            )}

            {/* Connected but error */}
            {connected && error && !loading && (
                <div className="card" style={{ marginBottom: 24 }}>
                    <div className="result-panel result-error">{error}</div>
                    <button className="btn btn-secondary" onClick={() => handleLookup(address)} style={{ marginTop: 12 }}>
                        Retry
                    </button>
                </div>
            )}

            {reputation && (
                <div className="animate-in">
                    {/* Connected wallet badge */}
                    {connected && (
                        <div style={{ marginBottom: 20, display: 'flex', alignItems: 'center', gap: 12 }}>
                            <div className="card-icon" style={{ width: 32, height: 32, fontSize: '0.9rem', background: 'var(--success-dim)' }}>✓</div>
                            <span style={{ fontFamily: 'var(--font-mono)', fontSize: '0.82rem', color: 'var(--text-secondary)' }}>{address}</span>
                        </div>
                    )}

                    {/* Top Stats */}
                    <div className="stats-grid">
                        <div className="stat-card">
                            <div className="stat-value">{Math.round(reputation.total_reputation)}</div>
                            <div className="stat-label">Reputation Score</div>
                            <div className="trust-meter">
                                <div className="trust-meter-fill" style={{ width: `${reputation.trust_index * 100}%` }} />
                            </div>
                        </div>
                        <div className="stat-card">
                            <div className="stat-value">{reputation.total_records}</div>
                            <div className="stat-label">On-Chain Records</div>
                        </div>
                        <div className="stat-card">
                            <div className={`stat-value ${tierClass}`} style={{ WebkitTextFillColor: 'unset' }}>
                                {reputation.credibility_level}
                            </div>
                            <div className="stat-label">Credibility Level</div>
                        </div>
                        <div className="stat-card">
                            <div className="stat-value">{(reputation.trust_index * 100).toFixed(1)}%</div>
                            <div className="stat-label">Trust Index</div>
                        </div>
                    </div>

                    {/* Badge + Metadata */}
                    <div style={{ display: 'flex', alignItems: 'center', gap: '12px', marginBottom: '24px', flexWrap: 'wrap' }}>
                        <span className={`verification-badge ${reputation.verification_badge ? 'verified' : 'unverified'}`}>
                            {reputation.verification_badge ? '✓ Verified Talent' : '◯ Not Yet Verified'}
                        </span>
                        {reputation.top_domain && (
                            <span className="tag tag-domain">Top: {reputation.top_domain}</span>
                        )}
                        {reputation.active_since && (
                            <span style={{ fontSize: '0.8rem', color: 'var(--text-muted)' }}>
                                Active since {new Date(reputation.active_since * 1000).toLocaleDateString()}
                            </span>
                        )}
                    </div>

                    <div className="grid-2">
                        {/* Domain Strengths */}
                        <div className="card">
                            <div className="card-header">
                                <div className="card-icon">📊</div>
                                <div>
                                    <div className="card-title">Domain Strengths</div>
                                    <div className="card-description">Skill distribution across domains</div>
                                </div>
                            </div>
                            <DomainChart domainScores={reputation.domain_scores} />
                        </div>

                        {/* Score Overview */}
                        <div className="card" style={{ textAlign: 'center' }}>
                            <div className="card-header" style={{ justifyContent: 'center' }}>
                                <div className="card-icon">⬡</div>
                                <div>
                                    <div className="card-title">Reputation Score</div>
                                    <div className="card-description">Weighted, time-decayed aggregate</div>
                                </div>
                            </div>
                            <ScoreCircle score={Math.round(reputation.total_reputation)} size={160} label={reputation.credibility_level} />
                        </div>
                    </div>

                    {/* Timeline */}
                    <div className="card" style={{ marginTop: '24px' }}>
                        <div className="card-header">
                            <div className="card-icon">📜</div>
                            <div>
                                <div className="card-title">Record Timeline</div>
                                <div className="card-description">{records.length} on-chain attestation(s)</div>
                            </div>
                        </div>
                        <Timeline records={records} />
                    </div>
                </div>
            )}

            {/* Empty State */}
            {!loading && !reputation && connected && !error && (
                <div className="empty-state" style={{ marginTop: '48px' }}>
                    <div className="empty-state-icon">📋</div>
                    <p>No reputation data found for this wallet</p>
                    <p style={{ fontSize: '0.82rem', color: 'var(--text-muted)', marginTop: 8 }}>Submit evidence first to build your on-chain reputation</p>
                </div>
            )}
        </div>
    );
}

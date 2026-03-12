import { useState } from 'react';
import { useWallet } from '../context/WalletContext';
import ScoreCircle from '../components/ScoreCircle';
import DomainChart from '../components/DomainChart';

const API = import.meta.env.VITE_API_URL;

export default function VerifierPage() {
    const { address, connected, connectWallet, setManualWallet } = useWallet();
    const [walletInput, setWalletInput] = useState('');
    const [data, setData] = useState(null);
    const [loading, setLoading] = useState(false);
    const [error, setError] = useState('');

    async function handleVerify(walletAddr) {
        const w = walletAddr || address || walletInput;
        if (!w || w.length < 58) return;

        setLoading(true);
        setError('');
        setData(null);

        try {
            const res = await fetch(`${API}/verify/${w}`);
            if (!res.ok) throw new Error((await res.json().catch(() => ({}))).detail || 'Verification failed');
            setData(await res.json());
        } catch (e) {
            console.error('Verify error:', e);
            let msg = e.message;
            if (msg === 'Failed to fetch') {
                msg = 'Failed to connect to backend. Ensure your local backend is running on port 8000.';
            }
            setError(msg);
        } finally {
            setLoading(false);
        }
    }

    function handleManualVerify() {
        const addrToVerify = walletInput || address;
        if (addrToVerify && addrToVerify.length >= 58) {
            handleVerify(addrToVerify);
        }
    }

    const tierLabel = data ? (
        data.total_reputation >= 90 ? 'exceptional' :
            data.total_reputation >= 70 ? 'strong' :
                data.total_reputation >= 50 ? 'moderate' :
                    data.total_reputation >= 30 ? 'developing' : 'minimal'
    ) : '';

    return (
        <div className="page">
            <div className="page-header">
                <h1 className="page-title">Verify Talent</h1>
                <p className="page-subtitle">
                    Enter any Algorand wallet to verify their on-chain skill reputation — trustless, transparent, and tamper-proof.
                </p>
            </div>

            {/* Wallet Input */}
            <div className="card" style={{ marginBottom: 24 }}>
                <div className="card-header">
                    <div className="card-icon">🔍</div>
                    <div>
                        <div className="card-title">Wallet Verification</div>
                        <div className="card-description">Verify any wallet's skill reputation</div>
                    </div>
                </div>

                <div style={{ display: 'flex', gap: 10, flexWrap: 'wrap' }}>
                    {!connected && (
                        <button className="btn btn-accent" onClick={async () => {
                            const addr = await connectWallet();
                            if (addr) handleVerify(addr);
                        }}>
                            ⬡ Connect Wallet
                        </button>
                    )}
                    <input
                        id="verifier-wallet-input"
                        className="form-input form-input-mono"
                        placeholder="Enter any Algorand wallet address…"
                        value={walletInput || (connected ? address : '')}
                        onChange={e => setWalletInput(e.target.value)}
                        onKeyDown={e => e.key === 'Enter' && handleManualVerify()}
                        style={{ flex: 1, minWidth: 200 }}
                    />
                    <button
                        id="verifier-verify-btn"
                        className={`btn btn-primary ${loading ? 'btn-loading' : ''}`}
                        onClick={handleManualVerify}
                        disabled={loading || (!connected && !walletInput && !address) || (walletInput && walletInput.length < 58)}
                    >
                        {loading ? '' : 'Verify'}
                    </button>
                </div>

                <div style={{ marginTop: 8, fontSize: '0.78rem', color: 'var(--text-muted)' }}>
                    {connected ? `Connected: ${address.slice(0, 8)}… — ` : ''}Paste any wallet address to verify their on-chain skill reputation.
                </div>

                {error && <div className="result-panel result-error" style={{ marginTop: 12 }}>{error}</div>}
            </div>

            {/* Loading skeleton */}
            {loading && (
                <div className="card analyzing-skeleton">
                    <div className="skeleton-pulse" style={{ textAlign: 'center', padding: 40 }}>
                        <div style={{ fontSize: '2rem', marginBottom: 12 }}>🔍</div>
                        <div style={{ color: 'var(--accent-cyan)', fontWeight: 600 }}>Verifying on-chain records…</div>
                    </div>
                </div>
            )}

            {/* Results */}
            {data && !loading && (
                <div className="animate-in">
                    {/* Verification Header */}
                    <div className="score-hero" style={{ marginBottom: 24 }}>
                        <ScoreCircle score={Math.round(data.total_reputation || 0)} size={140} label="Verified" />
                        <div className="score-hero-info" style={{ flex: 1 }}>
                            <h3 style={{ margin: 0 }}>
                                <span className={`verification-badge ${data.verified ? 'verified' : 'unverified'}`} style={{ marginRight: 12 }}>
                                    {data.verified ? '✓ Verified' : '◯ Unverified'}
                                </span>
                                Skill Profile
                            </h3>
                            <p style={{ margin: '6px 0 0', color: 'var(--text-secondary)', fontSize: '0.88rem' }}>
                                {data.total_records || 0} on-chain attestation(s) • Trust index: {((data.trust_index || 0) * 100).toFixed(1)}%
                            </p>
                            <span className={`tier-badge ${tierLabel}`}>
                                {tierLabel} — {Math.round(data.total_reputation || 0)}/100
                            </span>
                        </div>
                    </div>

                    {/* Stats */}
                    <div className="stats-grid" style={{ marginBottom: 24 }}>
                        <div className="stat-card">
                            <div className="stat-value">{data.total_records || 0}</div>
                            <div className="stat-label">Records</div>
                        </div>
                        <div className="stat-card">
                            <div className="stat-value">{data.top_domain || 'N/A'}</div>
                            <div className="stat-label">Top Domain</div>
                        </div>
                        <div className="stat-card">
                            <div className="stat-value">{((data.trust_index || 0) * 100).toFixed(0)}%</div>
                            <div className="stat-label">Trust Index</div>
                            <div className="trust-meter">
                                <div className="trust-meter-fill" style={{ width: `${(data.trust_index || 0) * 100}%` }} />
                            </div>
                        </div>
                        <div className="stat-card">
                            <div className="stat-value" style={{ color: data.verified ? 'var(--success)' : 'var(--text-muted)' }}>
                                {data.verified ? '✓' : '—'}
                            </div>
                            <div className="stat-label">Verified Badge</div>
                        </div>
                    </div>

                    {/* Domain Chart */}
                    {data.domain_scores?.length > 0 && (
                        <div className="card" style={{ marginBottom: 24 }}>
                            <div className="card-header">
                                <div className="card-icon">📊</div>
                                <div>
                                    <div className="card-title">Domain Breakdown</div>
                                    <div className="card-description">Verified skill domains from on-chain records</div>
                                </div>
                            </div>
                            <DomainChart domainScores={data.domain_scores} />
                        </div>
                    )}

                    {/* Records List */}
                    {data.records?.length > 0 && (
                        <div className="card">
                            <div className="card-header">
                                <div className="card-icon">📜</div>
                                <div>
                                    <div className="card-title">On-Chain Records</div>
                                    <div className="card-description">{data.records.length} verified attestation(s)</div>
                                </div>
                            </div>
                            <div className="record-list">
                                {data.records.map((r, i) => {
                                    const rScore = r.score ?? 0;
                                    const rTier = rScore >= 90 ? 'exceptional' : rScore >= 70 ? 'strong' : rScore >= 50 ? 'moderate' : rScore >= 30 ? 'developing' : 'minimal';
                                    return (
                                        <div key={i} className="record-item" style={{ animationDelay: `${i * 0.05}s` }}>
                                            <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center' }}>
                                                <div>
                                                    <span className="tag tag-domain" style={{ marginRight: 8 }}>{r.domain || 'Unknown'}</span>
                                                    <span className="tag tag-mode">{r.mode || 'ai-graded'}</span>
                                                </div>
                                                <span className={`tier-badge ${rTier}`} style={{ fontSize: '0.78rem' }}>
                                                    {rScore}/100
                                                </span>
                                            </div>
                                            {r.timestamp && (
                                                <div style={{ marginTop: 6, fontSize: '0.78rem', color: 'var(--text-muted)' }}>
                                                    {new Date(r.timestamp * 1000).toLocaleDateString('en-US', { month: 'short', day: 'numeric', year: 'numeric' })}
                                                </div>
                                            )}
                                        </div>
                                    );
                                })}
                            </div>
                        </div>
                    )}
                </div>
            )}
        </div>
    );
}

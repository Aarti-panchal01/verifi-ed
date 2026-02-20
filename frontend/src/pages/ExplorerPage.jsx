import { useState, useEffect } from 'react';
import ScoreCircle from '../components/ScoreCircle';

const API = 'http://localhost:8000';

/* Color palette for domains */
const DOMAIN_COLORS = {
    'backend': '#3178c6', 'frontend': '#f1e05a', 'python': '#3572A5',
    'blockchain': '#AA6746', 'ai/ml': '#ff6b6b', 'devops': '#00ADD8',
    'mobile': '#F05138', 'data-science': '#198CE7', 'security': '#c22d40',
    'web': '#e34c26', 'systems': '#555555',
};

export default function ExplorerPage() {
    const [profiles, setProfiles] = useState([]);
    const [search, setSearch] = useState('');
    const [domain, setDomain] = useState('');
    const [loading, setLoading] = useState(false);
    const [error, setError] = useState('');

    /* Load featured profiles on mount */
    useEffect(() => {
        loadProfiles();
    }, []);

    async function loadProfiles(searchTerm, domainFilter) {
        setLoading(true);
        setError('');

        try {
            const params = new URLSearchParams();
            if (searchTerm || search) params.set('q', searchTerm || search);
            if (domainFilter || domain) params.set('domain', domainFilter || domain);
            params.set('limit', '20');

            const res = await fetch(`${API}/reputation/explore?${params}`);
            if (!res.ok) {
                // Fallback — endpoint might not exist yet
                setProfiles([]);
                return;
            }
            const data = await res.json();
            setProfiles(data.profiles || data || []);
        } catch (e) {
            setError(e.message);
            setProfiles([]);
        } finally {
            setLoading(false);
        }
    }

    function handleSearch() {
        loadProfiles(search, domain);
    }

    const filteredProfiles = profiles;

    return (
        <div className="page">
            <div className="page-header">
                <h1 className="page-title">Talent Explorer</h1>
                <p className="page-subtitle">
                    Discover verified talent on Algorand. Browse profiles, filter by domain, and verify skill reputation — all on-chain.
                </p>
            </div>

            {/* Search + Filters */}
            <div className="card" style={{ marginBottom: 24 }}>
                <div className="card-header">
                    <div className="card-icon">🔍</div>
                    <div>
                        <div className="card-title">Search Talent</div>
                        <div className="card-description">Search by wallet address or filter by skill domain</div>
                    </div>
                </div>

                <div style={{ display: 'flex', gap: 10, flexWrap: 'wrap' }}>
                    <input
                        id="explorer-search-input"
                        className="form-input form-input-mono"
                        placeholder="Search wallet address…"
                        value={search}
                        onChange={e => setSearch(e.target.value)}
                        onKeyDown={e => e.key === 'Enter' && handleSearch()}
                        style={{ flex: 1, minWidth: 200 }}
                    />
                    <select
                        className="form-input"
                        value={domain}
                        onChange={e => { setDomain(e.target.value); loadProfiles(search, e.target.value); }}
                        style={{ width: 160 }}
                    >
                        <option value="">All Domains</option>
                        <option value="backend">Backend</option>
                        <option value="frontend">Frontend</option>
                        <option value="python">Python</option>
                        <option value="blockchain">Blockchain</option>
                        <option value="ai/ml">AI/ML</option>
                        <option value="web">Web</option>
                        <option value="devops">DevOps</option>
                        <option value="mobile">Mobile</option>
                        <option value="data-science">Data Science</option>
                    </select>
                    <button
                        className={`btn btn-primary ${loading ? 'btn-loading' : ''}`}
                        onClick={handleSearch}
                        disabled={loading}
                    >
                        {loading ? '' : 'Search'}
                    </button>
                </div>
            </div>

            {error && (
                <div className="result-panel result-error" style={{ marginBottom: 20 }}>
                    <p>{error}</p>
                    <button
                        className="btn btn-sm btn-ghost"
                        onClick={() => loadProfiles(search, domain)}
                        style={{ marginTop: 8, fontSize: '0.8rem' }}
                    >
                        ↻ Retry
                    </button>
                </div>
            )}

            {/* Results Grid */}
            {filteredProfiles.length > 0 ? (
                <div className="explorer-grid">
                    {filteredProfiles.map((p, i) => {
                        const score = Math.round(p.total_reputation || p.credibility_score || 0);
                        const tier = score >= 90 ? 'exceptional' : score >= 70 ? 'strong' : score >= 50 ? 'moderate' : score >= 30 ? 'developing' : 'minimal';

                        return (
                            <div className="explorer-card" key={i} style={{ animationDelay: `${i * 0.05}s` }}>
                                <div className="explorer-card-header">
                                    <ScoreCircle score={score} size={64} label="" />
                                    <div style={{ flex: 1, minWidth: 0 }}>
                                        <div style={{ fontFamily: 'var(--font-mono)', fontSize: '0.82rem', color: 'var(--text-primary)', overflow: 'hidden', textOverflow: 'ellipsis', whiteSpace: 'nowrap' }}>
                                            {(p.wallet || '').slice(0, 8)}…{(p.wallet || '').slice(-6)}
                                        </div>
                                        <div style={{ display: 'flex', gap: 6, marginTop: 6, flexWrap: 'wrap' }}>
                                            <span className={`tier-badge ${tier}`} style={{ fontSize: '0.72rem' }}>{tier}</span>
                                            {p.verification_badge && (
                                                <span className="verification-badge verified" style={{ fontSize: '0.7rem', padding: '2px 8px' }}>✓</span>
                                            )}
                                        </div>
                                    </div>
                                </div>

                                <div className="explorer-card-stats">
                                    <div>
                                        <span style={{ fontSize: '1rem', fontWeight: 700, color: 'var(--accent-cyan)' }}>{p.total_records || 0}</span>
                                        <span style={{ fontSize: '0.72rem', color: 'var(--text-muted)', display: 'block' }}>Records</span>
                                    </div>
                                    {p.top_domain && (
                                        <div className="tag tag-domain" style={{ fontSize: '0.72rem', padding: '3px 10px' }}>
                                            {p.top_domain}
                                        </div>
                                    )}
                                    <div>
                                        <span style={{ fontSize: '0.9rem', fontWeight: 600 }}>{((p.trust_index || 0) * 100).toFixed(0)}%</span>
                                        <span style={{ fontSize: '0.72rem', color: 'var(--text-muted)', display: 'block' }}>Trust</span>
                                    </div>
                                </div>

                                {/* Domain pills */}
                                {p.domain_scores?.length > 0 && (
                                    <div style={{ display: 'flex', gap: 4, flexWrap: 'wrap', marginTop: 8 }}>
                                        {p.domain_scores.slice(0, 3).map((ds, j) => (
                                            <span
                                                key={j}
                                                className="lang-pill"
                                                style={{ fontSize: '0.7rem', padding: '2px 8px' }}
                                            >
                                                <span className="lang-pill-dot" style={{ background: DOMAIN_COLORS[ds.domain?.toLowerCase()] || '#888' }} />
                                                {ds.domain}
                                            </span>
                                        ))}
                                    </div>
                                )}
                            </div>
                        );
                    })}
                </div>
            ) : (
                !loading && (
                    <div className="empty-state">
                        <div className="empty-state-icon">🔭</div>
                        <p>No profiles found</p>
                        <p style={{ fontSize: '0.82rem', color: 'var(--text-muted)', marginTop: 8 }}>
                            Talent profiles appear here as wallets submit on-chain skill attestations
                        </p>
                    </div>
                )
            )}
        </div>
    );
}

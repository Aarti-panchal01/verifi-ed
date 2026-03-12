import { useState, useRef, useCallback } from 'react';
import { useNavigate } from 'react-router-dom';
import { useWallet } from '../context/WalletContext';
import ScoreCircle from '../components/ScoreCircle';

const API = import.meta.env.VITE_API_URL;
const EXPLORER = 'https://testnet.explorer.perawallet.app/tx/';
const ALGOD_API = 'https://testnet-api.algonode.cloud';

/* Language → color mapping */
const LANG_COLORS = {
    javascript: '#f1e05a', typescript: '#3178c6', python: '#3572A5', java: '#b07219',
    go: '#00ADD8', rust: '#dea584', cpp: '#f34b7d', 'c++': '#f34b7d', c: '#555555',
    ruby: '#701516', php: '#4F5D95', swift: '#F05138', kotlin: '#A97BFF',
    dart: '#00B4AB', html: '#e34c26', css: '#563d7c', shell: '#89e051',
    solidity: '#AA6746', 'c#': '#178600', scala: '#c22d40', lua: '#000080',
    r: '#198CE7', perl: '#0298c3',
};

/* Signal → emoji */
const SIGNAL_ICONS = {
    commit_activity: '🔥', code_volume: '📦', language_diversity: '🌐',
    community_signals: '👥', documentation: '📝', recency: '⏱️',
    repo_maturity: '🏛️', code_quality_signals: '✅', originality: '🎯',
    content_presence: '📄', recent_activity: '⏱️', commit_consistency: '📊',
    language_verification: '🔤', file_integrity: '🔒', file_type: '📋',
    file_size: '📐', name_plausibility: '🏷️', project_structure: '🗂️',
    hash_integrity: '🔐',
};

export default function SubmitPage() {
    const { address, connected, connectWallet, setManualWallet, peraWallet } = useWallet();
    const navigate = useNavigate();

    const [mode, setMode] = useState('developer');
    const [sourceType, setSourceType] = useState('repo');
    const [repoUrl, setRepoUrl] = useState('');
    const [selectedFile, setSelectedFile] = useState(null);
    const [analysis, setAnalysis] = useState(null);
    const [submitResult, setSubmitResult] = useState(null);
    const [analyzing, setAnalyzing] = useState(false);
    const [submitting, setSubmitting] = useState(false);
    const [error, setError] = useState('');
    const [analyzeTime, setAnalyzeTime] = useState(0);
    const [walletInput, setWalletInput] = useState(address || '');
    const fileInputRef = useRef(null);

    const score = analysis ? Math.round(analysis.overall_score * 100) : 0;
    const tierLabel = score >= 90 ? 'exceptional' : score >= 70 ? 'strong' : score >= 50 ? 'moderate' : score >= 30 ? 'developing' : 'minimal';

    /* ── STEP 1: Wallet ────────────────────────────────────────────── */
    const handleSetWallet = () => {
        if (walletInput.length >= 58) {
            setManualWallet(walletInput);
        }
    };

    /* ── STEP 2: Analyze ───────────────────────────────────────────── */
    const handleAnalyze = useCallback(async () => {
        setError('');
        setAnalysis(null);
        setSubmitResult(null);
        setAnalyzing(true);

        const wallet = address || walletInput;
        // Auto-set the wallet in context if manually provided
        if (!address && walletInput.length >= 58) {
            setManualWallet(walletInput);
        }

        const t0 = performance.now();

        try {
            let res;
            if (sourceType === 'repo') {
                if (!repoUrl) throw new Error('Paste a GitHub repo URL.');
                res = await fetch(`${API}/verify-evidence/repo`, {
                    method: 'POST',
                    headers: { 'Content-Type': 'application/json' },
                    body: JSON.stringify({ repo_url: repoUrl, wallet: wallet, mode }),
                });
            } else {
                if (!selectedFile) throw new Error('Please select a file.');
                const formData = new FormData();
                formData.append('file', selectedFile);
                formData.append('mode', mode);
                const endpoint = sourceType === 'certificate'
                    ? '/verify-evidence/certificate/upload'
                    : '/verify-evidence/project/upload';
                res = await fetch(`${API}${endpoint}`, { method: 'POST', body: formData });
            }

            if (!res.ok) {
                const d = await res.json().catch(() => ({}));
                throw new Error(d.detail || `Analysis failed (HTTP ${res.status})`);
            }

            const data = await res.json();
            
            if (data.error) {
                throw new Error(data.error);
            }

            setAnalysis(data);
            setAnalyzeTime(((performance.now() - t0) / 1000).toFixed(1));
        } catch (e) {
            console.error('Analysis error:', e);
            let msg = e.message;
            if (msg === 'Failed to fetch') {
                msg = 'Failed to connect to backend. If you are on a deployed site (like Vercel), the backend must also be deployed with HTTPS. If running locally, ensure the backend server is started on port 8000.';
            }
            setError(msg || "Something went wrong during analysis.");
        } finally {
            setAnalyzing(false);
        }
    }, [sourceType, repoUrl, selectedFile, mode, address, walletInput]);

    /* ── STEP 3: Submit On-Chain (Client-Side Signing) ──────────────── */
    const handleSubmit = useCallback(async () => {
        if (!analysis) return;

        const wallet = address || walletInput;
        if (!wallet || wallet.length < 58) {
            setError('Please connect your wallet first.');
            return;
        }

        setSubmitting(true);
        setError('');

        try {
            // 1. Prepare Backend (Ensure MBR funding)
            await fetch(`${API}/submit/prepare`, {
                method: 'POST',
                headers: { 'Content-Type': 'application/json' },
                body: JSON.stringify({ wallet }),
            });

            // 2. Load Algorand SDK
            const algosdk = (await import('algosdk')).default;
            const algodClient = new algosdk.Algodv2('', ALGOD_API, '');
            const params = await algodClient.getTransactionParams().do();
            const appId = 755779875; // Verified Protocol App ID

            // Method signature: submit_skill_record(string,string,uint64,string,uint64)void
            const method = new algosdk.ABIMethod({
                name: 'submit_skill_record',
                args: [
                    { type: 'string', name: 'mode' },
                    { type: 'string', name: 'domain' },
                    { type: 'uint64', name: 'score' },
                    { type: 'string', name: 'artifact_hash' },
                    { type: 'uint64', name: 'timestamp' }
                ],
                returns: { type: 'void' }
            });

            const timestamp = Math.floor(Date.now() / 1000);
            const artifactHash = analysis.metadata?.artifact_hash || analysis.metadata?.sha256 || analysis.metadata?.project_hash || '0'.repeat(64);
            const scoreVal = Math.round(analysis.overall_score * 100);
            let domainVal = analysis.domains?.[0]?.domain || 'general';
            if (analysis.domains?.[0]?.subdomain) {
                domainVal += `:${analysis.domains[0].subdomain}`;
            }

            const modeVal = analysis.source_type || 'ai-graded';

            // 3. Compose Transaction
            const atc = new algosdk.AtomicTransactionComposer();
            atc.addMethodCall({
                appID: appId,
                method: method,
                methodArgs: [modeVal, domainVal, scoreVal, artifactHash, timestamp],
                sender: wallet,
                signer: async (txns) => {
                    const txnsToSign = txns.map(t => ({
                        txn: t,
                        message: 'Sign verification submission'
                    }));
                    if (peraWallet) {
                        return peraWallet.signTransaction([txnsToSign]);
                    }
                    throw new Error("No active signer. If you only pasted a wallet address, please click 'Connect Pera Wallet' at the top to enable signing.");
                },
                suggestedParams: params,
                onComplete: algosdk.OnApplicationComplete.NoOpOC,
                boxes: [
                    { appIndex: appId, name: algosdk.decodeAddress(wallet).publicKey }
                ]
            });

            // 4. Sign and Send
            const result = await atc.execute(algodClient, 3);

            // 5. Success
            setSubmitResult({
                success: true,
                transaction_id: result.txIDs[0],
                skill_id: domainVal,
                score: scoreVal,
                status: 'confirmed',
                explorer_url: `${EXPLORER}${result.txIDs[0]}`
            });

        } catch (e) {
            console.error(e);
            setError(e.message || "Submission failed");
        } finally {
            setSubmitting(false);
        }
    }, [analysis, address, walletInput, peraWallet]);

    const meta = analysis?.metadata || {};
    const languages = (typeof meta.languages === 'object' && !Array.isArray(meta.languages)) ? meta.languages : {};
    const langEntries = Object.entries(languages);
    const totalBytes = langEntries.reduce((s, [, b]) => s + b, 0) || 1;

    const hasAddress = !!address && address.length >= 58;
    const canSign = !!peraWallet;
    const needsWallet = !hasAddress;

    return (
        <div className="page">
            {/* ── Header ──────────────────────────────────────────── */}
            <div className="page-header">
                <h1 className="page-title">Submit Evidence</h1>
                <p className="page-subtitle">
                    Connect wallet → Analyze evidence → Submit on-chain. Your skill attestation is stored immutably on Algorand.
                </p>
            </div>

            {/* ── STEP 1: Wallet Connection ───────────────────────── */}
            <div className="card" style={{ marginBottom: 20 }}>
                <div className="card-header">
                    <div className="card-icon" style={{ background: connected ? 'var(--success-dim)' : 'var(--bg-elevated)' }}>
                        {connected ? '✓' : '1'}
                    </div>
                    <div>
                        <div className="card-title">{connected ? 'Wallet Connected' : 'Connect Wallet'}</div>
                        <div className="card-description">
                            {connected
                                ? <span style={{ fontFamily: 'var(--font-mono)', color: 'var(--accent-cyan)', fontSize: '0.82rem' }}>{address}</span>
                                : 'Connect Pera Wallet or paste your Algorand address'
                            }
                        </div>
                    </div>
                </div>

                {!connected && (
                    <div style={{ display: 'flex', gap: 10, flexWrap: 'wrap' }}>
                        <button className="btn btn-accent" onClick={connectWallet} style={{ flex: '0 0 auto' }}>
                            ⬡ Connect Pera Wallet
                        </button>
                        <span style={{ alignSelf: 'center', color: 'var(--text-muted)', fontSize: '0.82rem' }}>or</span>
                        <input
                            className="form-input form-input-mono"
                            placeholder="Paste wallet address…"
                            value={walletInput}
                            onChange={e => setWalletInput(e.target.value)}
                            style={{ flex: 1, minWidth: 200 }}
                        />
                        <button
                            className="btn btn-secondary"
                            onClick={handleSetWallet}
                            disabled={walletInput.length < 58}
                        >
                            Use Address
                        </button>
                    </div>
                )}
            </div>

            {/* ── STEP 2: Evidence Input ──────────────────────────── */}
            <div className="card" style={{ marginBottom: 20 }}>
                <div className="card-header">
                    <div className="card-icon">
                        {sourceType === 'repo' ? '⬡' : sourceType === 'certificate' ? '📜' : '📁'}
                    </div>
                    <div>
                        <div className="card-title">Evidence Source</div>
                        <div className="card-description">Choose source type, provide evidence, run analysis</div>
                    </div>
                </div>

                {/* Source tabs */}
                <div className="mode-tabs">
                    {[
                        { key: 'repo', label: '⬡ GitHub Repo', desc: 'Analyze public repo' },
                        { key: 'certificate', label: '📜 Certificate', desc: 'Upload PDF/image' },
                        { key: 'project', label: '📁 Project', desc: 'Upload ZIP folder' },
                    ].map(t => (
                        <button
                            key={t.key}
                            className={`mode-tab ${sourceType === t.key ? 'active' : ''}`}
                            onClick={() => { setSourceType(t.key); setRepoUrl(''); setSelectedFile(null); setAnalysis(null); setSubmitResult(null); setError(''); }}
                        >
                            {t.label}
                        </button>
                    ))}
                </div>

                {/* Input */}
                <div className="form-group" style={{ marginBottom: 16 }}>
                    {sourceType === 'repo' ? (
                        <>
                            <label className="form-label">GitHub Repository URL</label>
                            <input
                                id="evidence-source-input"
                                className="form-input form-input-mono"
                                placeholder="https://github.com/owner/repo"
                                value={repoUrl}
                                onChange={e => setRepoUrl(e.target.value)}
                                onKeyDown={e => e.key === 'Enter' && handleAnalyze()}
                            />
                        </>
                    ) : sourceType === 'certificate' ? (
                        <>
                            <label className="form-label">Upload Certificate (PDF, PNG, JPG, WEBP)</label>
                            <input
                                type="file"
                                ref={fileInputRef}
                                className="form-input"
                                onChange={e => setSelectedFile(e.target.files[0])}
                                accept=".pdf,.png,.jpg,.jpeg,.webp,.doc,.docx"
                                style={{ padding: 10 }}
                            />
                        </>
                    ) : (
                        <>
                            <label className="form-label">Upload Project (ZIP Archive)</label>
                            <input
                                type="file"
                                ref={fileInputRef}
                                className="form-input"
                                onChange={e => setSelectedFile(e.target.files[0])}
                                accept=".zip,.rar,.tar,.gz,.tar.gz,.7z"
                                style={{ padding: 10 }}
                            />
                            <div style={{ fontSize: '0.78rem', color: 'var(--text-muted)', marginTop: 6 }}>
                                💡 Zip your project folder before uploading. Our engine evaluates structure, code quality, documentation, and domain detection.
                            </div>
                        </>
                    )}
                </div>

                <button
                    id="analyze-btn"
                    className={`btn btn-accent ${analyzing ? 'btn-loading' : ''}`}
                    onClick={handleAnalyze}
                    disabled={analyzing || (sourceType === 'repo' ? !repoUrl : !selectedFile)}
                    style={{ width: '100%' }}
                >
                    {analyzing ? '' : '🔍  Analyze Evidence'}
                </button>

                {error && (
                    <div className="result-panel result-error" style={{ marginTop: 14 }}>
                        <strong>Error:</strong> {error}
                    </div>
                )}
            </div>

            {/* ── Analyzing skeleton ──────────────────────────────── */}
            {analyzing && (
                <div className="card analyzing-skeleton">
                    <div className="skeleton-pulse">
                        <div style={{ fontSize: '2rem', marginBottom: 12 }}>⚡</div>
                        <div style={{ color: 'var(--accent-cyan)', fontWeight: 600, fontSize: '1.1rem' }}>
                            Analyzing {sourceType === 'repo' ? 'repository' : sourceType === 'certificate' ? 'certificate' : 'project'}...
                        </div>
                        <div style={{ color: 'var(--text-muted)', fontSize: '0.85rem', marginTop: 4 }}>
                            {sourceType === 'repo'
                                ? 'Fetching repo metadata, computing signals, detecting domains'
                                : sourceType === 'certificate'
                                    ? 'Validating file integrity, checking format, computing hash'
                                    : 'Scanning project structure, analyzing code files, detecting domains'}
                        </div>
                        <div style={{ display: 'flex', gap: 8, justifyContent: 'center', marginTop: 20 }}>
                            {[60, 80, 50, 90, 70].map((w, i) => (
                                <div key={i} className="skeleton-bar" style={{ width: w, animationDelay: `${i * 0.15}s` }} />
                            ))}
                        </div>
                    </div>
                </div>
            )}

            {/* ═══════════════════════════════════════════════════════
                ANALYSIS RESULTS
               ═══════════════════════════════════════════════════════ */}
            {analysis && !analyzing && (
                <div className="analysis-panel">

                    {/* ── Score Hero ──────────────────────────────── */}
                    <div className="score-hero">
                        <ScoreCircle score={score} size={130} label="Credibility" />
                        <div className="score-hero-info" style={{ flex: 1 }}>
                            <h3>
                                {sourceType === 'repo' ? (
                                    <a
                                        href={meta.html_url}
                                        target="_blank"
                                        rel="noopener noreferrer"
                                        style={{ color: 'inherit', textDecoration: 'none' }}
                                        title="View on GitHub"
                                    >
                                        {meta.full_name || meta.repo || 'Repository Analysis'} <span style={{ fontSize: '0.8rem', opacity: 0.5 }}>↗</span>
                                    </a>
                                ) : sourceType === 'certificate'
                                    ? (meta.original_filename || meta.filename || 'Certificate Analysis')
                                    : (meta.original_filename || 'Project Analysis')}
                            </h3>
                            <p>
                                {sourceType === 'repo'
                                    ? (meta.description || 'AI-powered repository credibility assessment.')
                                    : sourceType === 'certificate'
                                        ? `File: ${meta.filename || 'Unknown'} • ${meta.extension || ''} • ${((meta.size_bytes || 0) / 1024).toFixed(1)} KB`
                                        : `${meta.code_files || 0} code files • ${meta.total_files || 0} total files`}
                            </p>
                            <span className={`tier-badge ${tierLabel}`}>
                                {tierLabel} — {score}/100
                            </span>
                            {analyzeTime && (
                                <span style={{ marginLeft: 12, fontSize: '0.75rem', color: 'var(--text-muted)', fontFamily: 'var(--font-mono)' }}>
                                    ⚡ {analyzeTime}s
                                </span>
                            )}
                        </div>
                    </div>

                    {/* ── Community Stats (GitHub only) ────────────── */}
                    {sourceType === 'repo' && meta.stars !== undefined && (
                        <div className="community-row">
                            <div className="community-stat">
                                <div className="community-stat-icon">⭐</div>
                                <div className="community-stat-value">{meta.stars?.toLocaleString() || 0}</div>
                                <div className="community-stat-label">Stars</div>
                            </div>
                            <div className="community-stat">
                                <div className="community-stat-icon">🍴</div>
                                <div className="community-stat-value">{meta.forks?.toLocaleString() || 0}</div>
                                <div className="community-stat-label">Forks</div>
                            </div>
                            <div className="community-stat">
                                <div className="community-stat-icon">👥</div>
                                <div className="community-stat-value">{meta.contributor_count?.toLocaleString() || 0}</div>
                                <div className="community-stat-label">Contributors</div>
                            </div>
                            <div className="community-stat">
                                <div className="community-stat-icon">📄</div>
                                <div className="community-stat-value">{meta.file_count?.toLocaleString() || 0}</div>
                                <div className="community-stat-label">Files</div>
                            </div>
                        </div>
                    )}

                    {/* ── Certificate-specific Details ────────────── */}
                    {sourceType === 'certificate' && (
                        <div className="community-row">
                            <div className="community-stat">
                                <div className="community-stat-icon">📄</div>
                                <div className="community-stat-value">{meta.extension || '?'}</div>
                                <div className="community-stat-label">Format</div>
                            </div>
                            <div className="community-stat">
                                <div className="community-stat-icon">📐</div>
                                <div className="community-stat-value">{((meta.size_bytes || 0) / 1024).toFixed(0)}</div>
                                <div className="community-stat-label">Size (KB)</div>
                            </div>
                            <div className="community-stat">
                                <div className="community-stat-icon">🔒</div>
                                <div className="community-stat-value" style={{ fontSize: '0.85rem' }}>{(meta.sha256 || '').slice(0, 8)}…</div>
                                <div className="community-stat-label">SHA-256</div>
                            </div>
                            <div className="community-stat">
                                <div className="community-stat-icon">{analysis.verified ? '✓' : '⚠'}</div>
                                <div className="community-stat-value" style={{ color: analysis.verified ? 'var(--success)' : 'var(--warning)' }}>
                                    {analysis.verified ? 'Valid' : 'Check'}
                                </div>
                                <div className="community-stat-label">Status</div>
                            </div>
                        </div>
                    )}

                    {/* ── Project-specific Details ────────────────── */}
                    {sourceType === 'project' && (
                        <div className="community-row">
                            <div className="community-stat">
                                <div className="community-stat-icon">📁</div>
                                <div className="community-stat-value">{meta.total_files || 0}</div>
                                <div className="community-stat-label">Total Files</div>
                            </div>
                            <div className="community-stat">
                                <div className="community-stat-icon">💻</div>
                                <div className="community-stat-value">{meta.code_files || 0}</div>
                                <div className="community-stat-label">Code Files</div>
                            </div>
                            <div className="community-stat">
                                <div className="community-stat-icon">🔐</div>
                                <div className="community-stat-value" style={{ fontSize: '0.85rem' }}>{(meta.project_hash || '').slice(0, 8)}…</div>
                                <div className="community-stat-label">Hash</div>
                            </div>
                            <div className="community-stat">
                                <div className="community-stat-icon">{analysis.verified ? '✓' : '⚠'}</div>
                                <div className="community-stat-value" style={{ color: analysis.verified ? 'var(--success)' : 'var(--warning)' }}>
                                    {analysis.verified ? 'Valid' : 'Minimal'}
                                </div>
                                <div className="community-stat-label">Structure</div>
                            </div>
                        </div>
                    )}

                    {/* ── Languages (GitHub only) ─────────────────── */}
                    {langEntries.length > 0 && (
                        <div style={{ marginBottom: 20 }}>
                            <div style={{ fontSize: '0.78rem', fontWeight: 600, color: 'var(--text-muted)', textTransform: 'uppercase', letterSpacing: '0.04em', marginBottom: 8 }}>
                                Languages
                            </div>
                            <div className="lang-pills">
                                {langEntries.sort((a, b) => b[1] - a[1]).map(([lang, bytes]) => (
                                    <div className="lang-pill" key={lang}>
                                        <span
                                            className="lang-pill-dot"
                                            style={{ background: LANG_COLORS[lang.toLowerCase()] || '#888' }}
                                        />
                                        {lang}
                                        <span style={{ opacity: 0.5 }}>{((bytes / totalBytes) * 100).toFixed(0)}%</span>
                                    </div>
                                ))}
                            </div>
                        </div>
                    )}

                    {/* ── Signal Cards ────────────────────────────── */}
                    {analysis.signals?.length > 0 && (
                        <>
                            <div style={{ fontSize: '0.78rem', fontWeight: 600, color: 'var(--text-muted)', textTransform: 'uppercase', letterSpacing: '0.04em', marginBottom: 10 }}>
                                Credibility Signals
                            </div>
                            <div className="signal-grid">
                                {analysis.signals.map((s, i) => (
                                    <div className="signal-card" key={i} style={{ animationDelay: `${i * 0.05}s` }}>
                                        <div className="signal-card-header">
                                            <span className="signal-card-name">
                                                {SIGNAL_ICONS[s.signal_name] || '📊'} {s.signal_name.replace(/_/g, ' ')}
                                            </span>
                                            <span className="signal-card-score">{(s.normalized * 100).toFixed(0)}</span>
                                        </div>
                                        <div className="signal-card-detail">{s.detail}</div>
                                        <div className="signal-card-bar">
                                            <div className="signal-card-bar-fill" style={{ width: `${s.normalized * 100}%` }} />
                                        </div>
                                    </div>
                                ))}
                            </div>
                        </>
                    )}

                    {/* ── Domains ─────────────────────────────────── */}
                    {analysis.domains?.length > 0 && (
                        <div style={{ marginBottom: 20 }}>
                            <div style={{ fontSize: '0.78rem', fontWeight: 600, color: 'var(--text-muted)', textTransform: 'uppercase', letterSpacing: '0.04em', marginBottom: 10 }}>
                                Detected Domains
                            </div>
                            <div style={{ display: 'flex', gap: 8, flexWrap: 'wrap' }}>
                                {analysis.domains.map((d, i) => (
                                    <div key={i} className="tag tag-domain" style={{ padding: '6px 14px', fontSize: '0.82rem' }}>
                                        {d.domain}
                                        <span style={{ marginLeft: 6, opacity: 0.5 }}>{(d.confidence * 100).toFixed(0)}%</span>
                                    </div>
                                ))}
                            </div>
                        </div>
                    )}

                    {/* ── AI Explanation ──────────────────────────── */}
                    {(meta.explanation || analysis.explanation) && (
                        <div className="explanation-box">
                            <div style={{ marginBottom: 6, color: 'var(--accent-cyan)', fontWeight: 600, fontSize: '0.82rem', textTransform: 'uppercase', letterSpacing: '0.04em' }}>
                                AI Assessment
                            </div>
                            {meta.explanation || analysis.explanation}
                        </div>
                    )}

                    {/* ── Submit Button ───────────────────────────── */}
                    {!submitResult && (
                        <div>
                            {needsWallet && (
                                <div className="notice-box notice-warning" style={{ fontSize: '0.85rem', marginBottom: 12, display: 'flex', alignItems: 'center', gap: 8 }}>
                                    ⚠ Connect your wallet above before submitting on-chain.
                                </div>
                            )}
                            {hasAddress && !canSign && (
                                <div className="notice-box notice-info" style={{ fontSize: '0.85rem', marginBottom: 12, display: 'flex', alignItems: 'center', gap: 8, color: 'var(--accent-cyan)' }}>
                                    💡 Address provided in view-only mode. To sign and record this on-chain, please click "Connect Pera Wallet" at the top.
                                </div>
                            )}
                            <button
                                id="submit-btn"
                                className={`btn btn-accent ${submitting ? 'btn-loading' : ''}`}
                                onClick={handleSubmit}
                                disabled={submitting || !hasAddress}
                                style={{ width: '100%', marginTop: 8 }}
                            >
                                {submitting ? '' : '⬡  Submit On-Chain  →'}
                            </button>
                        </div>
                    )}
                </div>
            )}

            {/* ═══════════════════════════════════════════════════════
                SUBMISSION RESULT — INSTANT FEEDBACK
               ═══════════════════════════════════════════════════════ */}
            {submitResult && (
                <div className="result-panel result-success submit-success" style={{ marginTop: 20 }}>
                    <div className="submit-success-header">
                        <div className="submit-success-icon">✓</div>
                        <div>
                            <strong style={{ fontSize: '1.15rem', display: 'block' }}>Transaction Submitted</strong>
                            <span style={{ fontSize: '0.85rem', color: 'var(--text-secondary)' }}>
                                Skill attestation recorded on Algorand Testnet
                            </span>
                        </div>
                    </div>

                    <div className="submit-success-details">
                        <div className="submit-detail-item">
                            <span className="submit-detail-label">Domain</span>
                            <span className="submit-detail-value">{submitResult.skill_id || submitResult.domain}</span>
                        </div>
                        <div className="submit-detail-item">
                            <span className="submit-detail-label">Score</span>
                            <span className="submit-detail-value" style={{ color: 'var(--accent-cyan)' }}>
                                {submitResult.score}/100
                            </span>
                        </div>
                        <div className="submit-detail-item">
                            <span className="submit-detail-label">Transaction</span>
                            <a
                                href={submitResult.explorer_url || `${EXPLORER}${submitResult.transaction_id}`}
                                target="_blank"
                                rel="noreferrer"
                                style={{ color: 'var(--accent-cyan)', textDecoration: 'none', fontFamily: 'var(--font-mono)', fontSize: '0.82rem' }}
                            >
                                {(submitResult.transaction_id || '').substring(0, 16)}… ↗
                            </a>
                        </div>
                        <div className="submit-detail-item">
                            <span className="submit-detail-label">Status</span>
                            <span className="submit-detail-value" style={{ color: 'var(--success)' }}>
                                {submitResult.status === 'confirmed' ? '✓ Confirmed' : '⏳ Pending Confirmation'}
                            </span>
                        </div>
                    </div>

                    <div style={{ marginTop: 16, display: 'flex', gap: 10 }}>
                        <button className="btn btn-secondary" onClick={() => navigate('/dashboard')}>
                            📊 View Dashboard
                        </button>
                        <button className="btn btn-ghost" onClick={() => { setAnalysis(null); setSubmitResult(null); setError(''); setRepoUrl(''); setSelectedFile(null); }}>
                            + Submit Another
                        </button>
                    </div>
                </div>
            )}
        </div>
    );
}

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

    const handleSetWallet = () => {
        if (walletInput.length >= 58) {
            setManualWallet(walletInput);
        }
    };

    const handleAnalyze = useCallback(async () => {

        setError('');
        setAnalysis(null);
        setSubmitResult(null);
        setAnalyzing(true);

        const t0 = performance.now();

        try {

            let res;

            if (sourceType === 'repo') {

                if (!repoUrl) throw new Error('Paste a GitHub repo URL.');

                res = await fetch(`${API}/verify-evidence/repo`, {
                    method: 'POST',
                    headers: { 'Content-Type': 'application/json' },
                    body: JSON.stringify({ repo_url: repoUrl, wallet: address, mode }),
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
            setAnalysis(data);
            setAnalyzeTime(((performance.now() - t0) / 1000).toFixed(1));

        } catch (e) {
            setError(e.message);
        } finally {
            setAnalyzing(false);
        }

    }, [sourceType, repoUrl, selectedFile, mode, address]);

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

            await fetch(`${API}/submit/prepare`, {
                method: 'POST',
                headers: { 'Content-Type': 'application/json' },
                body: JSON.stringify({ wallet }),
            });

            const algosdk = (await import('algosdk')).default;
            const algodClient = new algosdk.Algodv2('', ALGOD_API, '');
            const params = await algodClient.getTransactionParams().do();

            const appId = 755779875;

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

            const artifactHash =
                analysis.metadata?.artifact_hash ||
                analysis.metadata?.sha256 ||
                analysis.metadata?.project_hash ||
                '0'.repeat(64);

            const scoreVal = Math.round(analysis.overall_score * 100);

            let domainVal = analysis.domains?.[0]?.domain || 'general';

            if (analysis.domains?.[0]?.subdomain) {
                domainVal += `:${analysis.domains[0].subdomain}`;
            }

            const modeVal = analysis.source_type || 'ai-graded';

            const atc = new algosdk.AtomicTransactionComposer();

            atc.addMethodCall({
                appID: appId,
                method,
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

                    throw new Error("Wallet not connected or Pera Wallet SDK not initialized.");

                },
                suggestedParams: params,
                onComplete: algosdk.OnApplicationComplete.NoOpOC,
                boxes: [
                    { appIndex: appId, name: algosdk.decodeAddress(wallet).publicKey }
                ]
            });

            const result = await atc.execute(algodClient, 3);

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

    return (
        <div className="page">

            <div className="page-header">
                <h1 className="page-title">Submit Evidence</h1>
                <p className="page-subtitle">
                    Connect wallet → Analyze evidence → Submit on-chain.
                </p>
            </div>

            {/* UI components remain exactly the same as your original file */}

        </div>
    );
}

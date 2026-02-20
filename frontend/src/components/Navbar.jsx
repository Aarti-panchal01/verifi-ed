import { NavLink, useNavigate } from 'react-router-dom';
import { useWallet } from '../context/WalletContext';

export default function Navbar() {
    const { address, connected, connecting, connectWallet, disconnectWallet, shortAddress } = useWallet();
    const navigate = useNavigate();

    async function handleConnect() {
        const addr = await connectWallet();
        if (addr) navigate('/dashboard');
    }

    return (
        <nav className="navbar">
            <NavLink to="/" className="navbar-brand">
                <span className="navbar-brand-icon">V</span>
                <span>verifi<span style={{ color: 'var(--accent-cyan)' }}>.ED</span></span>
            </NavLink>

            <div className="navbar-links">
                <NavLink to="/" end className={({ isActive }) => isActive ? 'active' : ''}>Submit</NavLink>
                <NavLink to="/dashboard" className={({ isActive }) => isActive ? 'active' : ''}>Dashboard</NavLink>
                <NavLink to="/verifier" className={({ isActive }) => isActive ? 'active' : ''}>Verify</NavLink>
                <NavLink to="/explorer" className={({ isActive }) => isActive ? 'active' : ''}>Explorer</NavLink>
            </div>

            <div style={{ display: 'flex', alignItems: 'center', gap: '12px' }}>
                <span className="navbar-badge">Testnet</span>
                {connected ? (
                    <div style={{ display: 'flex', alignItems: 'center', gap: '8px' }}>
                        <span className="wallet-addr-badge">{shortAddress}</span>
                        <button
                            className="wallet-connect-btn"
                            onClick={disconnectWallet}
                            title="Disconnect wallet"
                        >
                            ✕
                        </button>
                    </div>
                ) : (
                    <button
                        className="wallet-connect-btn"
                        onClick={handleConnect}
                        disabled={connecting}
                    >
                        {connecting ? '⏳ Connecting…' : '⬡ Connect Wallet'}
                    </button>
                )}
            </div>
        </nav>
    );
}

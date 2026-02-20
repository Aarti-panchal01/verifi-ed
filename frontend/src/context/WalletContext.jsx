import { createContext, useContext, useState, useCallback, useRef } from 'react';

const WalletContext = createContext(null);

// Lazy-load Pera SDK to avoid Vite polyfill issues (Buffer/global)
let peraWallet = null;
async function getPeraWallet() {
    if (!peraWallet) {
        try {
            const { PeraWalletConnect } = await import('@perawallet/connect');
            peraWallet = new PeraWalletConnect();
        } catch (err) {
            console.warn('Pera Wallet SDK not available:', err.message);
            return null;
        }
    }
    return peraWallet;
}

export function WalletProvider({ children }) {
    const [address, setAddress] = useState(() => localStorage.getItem('verified_wallet') || '');
    const [connected, setConnected] = useState(() => !!localStorage.getItem('verified_wallet'));
    const [connecting, setConnecting] = useState(false);
    const [peraWalletInstance, setPeraWalletInstance] = useState(null);
    const reconnectAttempted = useRef(false);

    function handleDisconnect() {
        setAddress('');
        setConnected(false);
        setPeraWalletInstance(null);
        localStorage.removeItem('verified_wallet');
    }

    const connectWallet = useCallback(async () => {
        setConnecting(true);
        try {
            const pera = await getPeraWallet();
            if (!pera) {
                setConnecting(false);
                return null;
            }
            setPeraWalletInstance(pera);
            const accounts = await pera.connect();
            const addr = accounts[0];
            setAddress(addr);
            setConnected(true);
            localStorage.setItem('verified_wallet', addr);

            pera.connector?.on('disconnect', handleDisconnect);
            return addr;
        } catch (err) {
            if (err?.data?.type !== 'CONNECT_MODAL_CLOSED') {
                console.error('Pera connect error:', err);
            }
            return null;
        } finally {
            setConnecting(false);
        }
    }, []);

    const disconnectWallet = useCallback(async () => {
        try {
            const pera = await getPeraWallet();
            if (pera) await pera.disconnect();
        } catch (e) { /* ignore */ }
        handleDisconnect();
    }, []);

    // Manual entry fallback
    const setManualWallet = useCallback((addr) => {
        setAddress(addr);
        setConnected(!!addr);
        if (addr) localStorage.setItem('verified_wallet', addr);
        else localStorage.removeItem('verified_wallet');
    }, []);

    return (
        <WalletContext.Provider value={{
            address,
            connected,
            connecting,
            connectWallet,
            disconnectWallet,
            setManualWallet,
            shortAddress: address ? `${address.slice(0, 6)}…${address.slice(-4)}` : '',
            peraWallet: peraWalletInstance,
        }}>
            {children}
        </WalletContext.Provider>
    );
}

export function useWallet() {
    const ctx = useContext(WalletContext);
    if (!ctx) throw new Error('useWallet must be used within WalletProvider');
    return ctx;
}

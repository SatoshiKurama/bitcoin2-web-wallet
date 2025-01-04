import React, { useState, useEffect } from 'react';
import { QRCodeSVG as QRCode } from 'qrcode.react';
import QRScanner from './QRScanner';

function WalletApp() {
  const [isLoggedIn, setIsLoggedIn] = useState(false);
  const [loginKey, setLoginKey] = useState('');
  const [showNewWallet, setShowNewWallet] = useState(false);
  const [newWalletData, setNewWalletData] = useState(null);
  const [address, setAddress] = useState('');
  const [balance, setBalance] = useState(0);
  const [transactionHistory, setTransactionHistory] = useState([]);
  const [lastRefresh, setLastRefresh] = useState(new Date().toLocaleTimeString());
  const [sendAddress, setSendAddress] = useState('');
  const [amount, setAmount] = useState('');
  const [showScanner, setShowScanner] = useState(false);
  const [error, setError] = useState('');
  const [isLoggingIn, setIsLoggingIn] = useState(false);
  const [isLoading, setIsLoading] = useState(false);
  const [balanceLoading, setBalanceLoading] = useState(false);
  const [historyLoading, setHistoryLoading] = useState(false);
  const [estimatedFee, setEstimatedFee] = useState(0.0001);

  useEffect(() => {
    if (isLoggedIn) {
      fetchWalletData();
      fetchEstimatedFee();
    }
  }, [isLoggedIn]);

  const fetchEstimatedFee = async () => {
    try {
      const res = await fetch('/api/estimatefee');
      const data = await res.json();
      if (data.success) {
        setEstimatedFee(data.fee);
      }
    } catch (err) {
      console.error('Error fetching fee estimate:', err);
    }
  };

  const fetchWalletData = async () => {
    if (isLoading) return;
    
    setIsLoading(true);
    setBalanceLoading(true);
    setHistoryLoading(true);

    try {
      const [balanceRes, historyRes] = await Promise.all([
        fetch('/api/balance'),
        fetch('/api/history')
      ]);

      const balData = await balanceRes.json();
      if (balData.success) {
        setBalance(balData.balance);
      } else {
        console.error('Balance fetch error:', balData.error);
      }
      setBalanceLoading(false);

      const histData = await historyRes.json();
      if (histData.success) {
        setTransactionHistory(histData.history);
      } else {
        console.error('History fetch error:', histData.error);
      }
      setHistoryLoading(false);

      setLastRefresh(new Date().toLocaleTimeString());
    } catch (err) {
      console.error('fetchWalletData error:', err);
      setError('Error fetching wallet data');
    } finally {
      setIsLoading(false);
      setBalanceLoading(false);
      setHistoryLoading(false);
    }
  };

  const handleCreateWallet = async () => {
    setError('');
    setNewWalletData(null);
    try {
      const res = await fetch('/api/create_wallet', { method: 'POST' });
      const data = await res.json();
      if (data.success) {
        setNewWalletData({
          encrypted_key: data.encrypted_key,
          private_key: data.private_key,
          address: data.address
        });
      } else {
        setError(data.error || 'Failed to create wallet');
      }
    } catch (err) {
      console.error('Create wallet error:', err);
      setError('Failed to create wallet');
    }
  };

  const handleLogin = async () => {
    setError('');
    setIsLoggingIn(true);
    setBalanceLoading(true);
    
    try {
      const res = await fetch('/api/login', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ encrypted_key: loginKey })
      });
      const data = await res.json();
      if (data.success) {
        setIsLoggedIn(true);
        setAddress(data.address);
        setBalance(data.balance);
        fetchWalletData();
      } else {
        setError(data.error || 'Login failed');
      }
    } catch (err) {
      console.error('Login error:', err);
      setError('Login request failed');
    } finally {
      setIsLoggingIn(false);
    }
  };

  const handleSend = async (e) => {
    e.preventDefault();
    setError('');
    if (!sendAddress || !amount) {
      setError('Please enter both address and amount');
      return;
    }

    const sendAmount = parseFloat(amount);
    if (isNaN(sendAmount) || sendAmount <= 0) {
      setError('Please enter a valid amount');
      return;
    }

    const totalNeeded = sendAmount + estimatedFee;

    if (totalNeeded > balance) {
      setError(`Insufficient funds. You need ${totalNeeded.toFixed(8)} BTC2 (${sendAmount} + ${estimatedFee.toFixed(8)} fee) but have ${balance} BTC2`);
      return;
    }

    try {
      const res = await fetch('/api/transaction', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({
          address: sendAddress,
          amount: sendAmount
        })
      });
      const data = await res.json();
      
      if (data.success && data.txid) {
        alert(`Transaction sent successfully!\nTXID: ${data.txid}\nAmount: ${sendAmount} BTC2\nEstimated Fee: ${estimatedFee.toFixed(8)} BTC2`);
        setSendAddress('');
        setAmount('');
        fetchWalletData();
      } else {
        setError(data.error || `Transaction failed. Please ensure you have enough funds to cover the amount plus transaction fees (${estimatedFee.toFixed(8)} BTC2).`);
      }
    } catch (err) {
      console.error('Transaction error:', err);
      setError('Failed to send transaction. Please try again.');
    }
  };

  const handleScan = (data) => {
    if (data) {
      setSendAddress(data);
      setShowScanner(false);
    }
  };

  const handleLogout = () => {
    setIsLoggedIn(false);
    setLoginKey('');
    setAddress('');
    setBalance(0);
    setTransactionHistory([]);
    setSendAddress('');
    setAmount('');
    setError('');
  };

  // 1. Login Screen
  if (!isLoggedIn && !showNewWallet && !newWalletData) {
    return (
      <div className="wallet-container">
        <div className="login-screen">
          <h1>Bitcoin 2 Web Wallet</h1>
          {error && <p style={{color: 'red'}}>{error}</p>}

          <input
            type="password"
            placeholder="Encrypted private key"
            value={loginKey}
            onChange={(e) => setLoginKey(e.target.value)}
          />
          <div className="button-group">
            <button className="primary-button" onClick={handleLogin} disabled={isLoggingIn}>
              {isLoggingIn ? 'Logging in...' : 'Login'}
            </button>
            <button className="secondary-button" onClick={() => setShowNewWallet(true)}>
              Create New Wallet
            </button>
          </div>
        </div>
        <div className="disclaimer-link">
          <a href="/disclaimer" target="_blank" rel="noopener noreferrer">Disclaimer & Terms of Use</a>
        </div>
      </div>
    );
  }

  // 2. New Wallet Creation
  if (!isLoggedIn && showNewWallet) {
    return (
      <div className="wallet-container">
        <div className="new-wallet-screen">
          <h2>Create a New BTC2 Wallet</h2>
          {error && <p style={{ color: 'red' }}>{error}</p>}

          {!newWalletData && (
            <div className="button-group">
              <button className="primary-button" onClick={handleCreateWallet}>
                Generate New Wallet
              </button>
              <button className="secondary-button" onClick={() => setShowNewWallet(false)}>
                Cancel
              </button>
            </div>
          )}

          {newWalletData && (
            <>
              <p>Wallet created.</p>
              <p>
                Please copy/paste and write down both private keys below. 
                They will only be displayed once, and no one can help you recover them.
              </p>
              <div className="key-display">
                <label>Encrypted private key (your login password):</label>
                <code>{newWalletData.encrypted_key}</code>
              </div>

              <div className="key-display">
                <label>Private key (WIF):</label>
                <code>{newWalletData.private_key}</code>
              </div>

              <p className="warning">
                This acts as your backup method to access your coins with the Bitcoin 2 Core wallet or third-party wallets supporting WIF.
              </p>

              <p>Best to log out and log back in before sending any BTC2 to this address.</p>
              <div className="address-display">
                <label>Public address for receiving BTC2:</label>
                <code>{newWalletData.address}</code>
              </div>

              <button
                className="secondary-button"
                onClick={() => {
                  setShowNewWallet(false);
                  setNewWalletData(null);
                }}
              >
                Back to Login
              </button>
            </>
          )}
        </div>
        <div className="disclaimer-link">
          <a href="/disclaimer" target="_blank" rel="noopener noreferrer">Disclaimer & Terms of Use</a>
        </div>
      </div>
    );
  }

  // 3. Main Wallet Interface
  if (isLoggedIn) {
    return (
      <div className="wallet-container">
        <h1>Bitcoin 2 Wallet</h1>
        {error && <p style={{ color: 'red' }}>{error}</p>}

        <div className="balance-display">
          {balanceLoading ? (
            <p>Loading balance...</p>
          ) : (
            <p>Current Balance: {balance} BTC2</p>
          )}
          <p>Your Address: {address}</p>
          {address && (
            <div className="qr-container">
              <QRCode value={address} size={256} level="H" />
            </div>
          )}
        </div>

        <div className="control-buttons">
          <button onClick={fetchWalletData}>Refresh</button>
          <button onClick={handleLogout}>Log Out</button>
          <p className="refresh-time">Last refresh time: {lastRefresh}</p>
        </div>

        <hr />

        <h2>Send BTC2</h2>
        <form onSubmit={handleSend}>
          <input
            type="text"
            placeholder="Recipient Address"
            value={sendAddress}
            onChange={(e) => setSendAddress(e.target.value)}
            required
          />
          <input
            type="number"
            step="0.00000001"
            placeholder="Amount"
            value={amount}
            onChange={(e) => setAmount(e.target.value)}
            required
          />
          <div className="fee-notice" style={{ fontSize: '0.85em', color: 'var(--medium-gray)', marginTop: '5px' }}>
            Note: Current network fee: {estimatedFee.toFixed(8)} BTC2 (estimated for next 6 blocks)
          </div>
          <div className="zbtc2-notice">
            Note: zBTC2 private transactions are temporarily disabled
          </div>
          <div className="transaction-buttons">
            <button type="button" onClick={() => setShowScanner(!showScanner)}>
              {showScanner ? 'Hide Scanner' : 'Scan QR'}
            </button>
            <button type="submit">Send</button>
          </div>
        </form>

        {showScanner && <QRScanner onScan={handleScan} />}

        <hr />

        <h2>Transaction History</h2>
        {historyLoading ? (
          <div className="loading-text">Loading transaction history...</div>
        ) : transactionHistory.length === 0 ? (
          <div className="no-transactions">No transactions yet</div>
        ) : (
          <ul className="transaction-list">
            {transactionHistory.map((tx, i) => (
              <li key={i}>
                {tx.category === 'receive' ? 'Received' : 'Sent'} {Math.abs(tx.amount)} BTC2
                | Confirmations: {tx.confirmations}
                | TXID: {tx.txid}
              </li>
            ))}
          </ul>
        )}

        <div className="disclaimer-link">
          <a href="/disclaimer" target="_blank" rel="noopener noreferrer">Disclaimer & Terms of Use</a>
        </div>
      </div>
    );
  }

  // Fallback
  return <div className="wallet-container">Loading...</div>;
}

export default WalletApp;
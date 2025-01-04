import os
import time
from flask import Flask, jsonify, request, render_template, session
from config.settings import RPC_USER, RPC_PASSWORD, RPC_HOST, RPC_PORT
from utils.btc2_rpc import btc2_rpc
from utils.btc2_wallet import generate_btc2_key_pair, derive_address_from_wif
from utils.encryption import wallet_encryption

app = Flask(__name__)
app.secret_key = os.urandom(24)

# Demo in-memory session store: { session_id: {private_key, address} }
user_sessions = {}

# Basic rate-limiting for create_wallet
last_wallet_creation = {}
CREATION_COOLDOWN = 30  # seconds

@app.route('/')
def index():
    return render_template('index.html')

@app.route('/disclaimer')
def disclaimer():
    return render_template('disclaimer.html')

@app.route('/api/create_wallet', methods=['POST'])
def create_wallet():
    try:
        ip_addr = request.remote_addr
        now = time.time()

        if ip_addr in last_wallet_creation:
            elapsed = now - last_wallet_creation[ip_addr]
            if elapsed < CREATION_COOLDOWN:
                return jsonify({
                    'success': False,
                    'error': 'Rate limit exceeded'
                }), 429

        last_wallet_creation[ip_addr] = now

        private_wif, derived_address = generate_btc2_key_pair()
        encrypted_key = wallet_encryption.encrypt_data(private_wif)

        return jsonify({
            'success': True,
            'encrypted_key': encrypted_key.decode('utf-8'),
            'private_key': private_wif,
            'address': derived_address
        })
    except Exception as e:
        return jsonify({'success': False, 'error': str(e)}), 500

@app.route('/api/login', methods=['POST'])
def login():
    try:
        data = request.get_json()
        enc_key = data.get('encrypted_key')
        if not enc_key:
            return jsonify({'success': False, 'error': 'No encrypted key provided'}), 400

        # Decrypt and validate
        decrypted_pk = wallet_encryption.decrypt_data(enc_key.encode('utf-8'))
        derived_address = derive_address_from_wif(decrypted_pk)

        # Import if needed
        if not btc2_rpc.fast_import_check(derived_address):
            from threading import Thread
            Thread(
                target=btc2_rpc.import_privkey,
                args=(decrypted_pk, derived_address, False),
                daemon=True
            ).start()

        # Get address-specific balance
        balance = btc2_rpc.get_balance(derived_address)

        # Create session
        session_id = os.urandom(16).hex()
        user_sessions[session_id] = {
            'private_key': decrypted_pk,
            'address': derived_address
        }
        session['user_session'] = session_id

        return jsonify({
            'success': True,
            'address': derived_address,
            'balance': balance
        })

    except Exception as e:
        return jsonify({'success': False, 'error': str(e)}), 500

@app.route('/api/balance', methods=['GET'])
def get_balance():
    try:
        session_id = session.get('user_session')
        if not session_id or session_id not in user_sessions:
            return jsonify({'success': False, 'error': 'Not logged in'}), 401

        user_data = user_sessions[session_id]
        balance = btc2_rpc.get_balance(user_data['address'])
        return jsonify({'success': True, 'balance': balance})
    except Exception as e:
        return jsonify({'success': False, 'error': str(e)}), 500

@app.route('/api/history', methods=['GET'])
def get_history():
    try:
        session_id = session.get('user_session')
        if not session_id or session_id not in user_sessions:
            return jsonify({'success': False, 'error': 'Not logged in'}), 401

        user_data = user_sessions[session_id]
        txs = btc2_rpc.list_transactions(address=user_data['address'])
        return jsonify({'success': True, 'history': txs})
    except Exception as e:
        return jsonify({'success': False, 'error': str(e)}), 500

@app.route('/api/transaction', methods=['POST'])
def send_transaction():
    try:
        session_id = session.get('user_session')
        if not session_id or session_id not in user_sessions:
            return jsonify({'success': False, 'error': 'Not logged in'}), 401

        data = request.get_json()
        to_address = data.get('address')
        amount = data.get('amount')
        
        if not to_address or not amount:
            return jsonify({'success': False, 'error': 'Invalid transaction data'}), 400

        user_data = user_sessions[session_id]
        txid = btc2_rpc.send_to_address(user_data['address'], to_address, float(amount))
        return jsonify({'success': True, 'txid': txid})
    except Exception as e:
        return jsonify({'success': False, 'error': str(e)}), 500

@app.route('/api/estimatefee', methods=['GET'])
def estimate_fee():
    try:
        blocks = request.args.get('blocks', 6, type=int)
        fee = btc2_rpc.estimate_fee(blocks)
        return jsonify({
            'success': True,
            'fee': fee
        })
    except Exception as e:
        return jsonify({'success': False, 'error': str(e)}), 500

@app.route('/api/logout', methods=['POST'])
def logout():
    try:
        session_id = session.get('user_session')
        if session_id and session_id in user_sessions:
            del user_sessions[session_id]
        session.clear()
        return jsonify({'success': True})
    except Exception as e:
        return jsonify({'success': False, 'error': str(e)}), 500

if __name__ == '__main__':
    app.run(host='0.0.0.0', port=5000)
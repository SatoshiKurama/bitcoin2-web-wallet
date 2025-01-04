import requests
import json
import time
from requests.adapters import HTTPAdapter
from requests.packages.urllib3.util.retry import Retry
from functools import wraps
from config.settings import RPC_USER, RPC_PASSWORD, RPC_HOST, RPC_PORT

class BTC2RPC:
    def __init__(self, user, password, host, port):
        self.url = f"http://{host}:{port}"
        self.auth = (user, password)
        self.session = self._init_session()
        self.imported_addresses = set()
        self._init_imported_addresses()

    def _init_session(self):
        session = requests.Session()
        retry = Retry(total=3, backoff_factor=0.1)
        adapter = HTTPAdapter(max_retries=retry, pool_connections=20, pool_maxsize=20)
        session.mount('http://', adapter)
        return session

    def _init_imported_addresses(self):
        try:
            addresses = self._call('getaddressesbyaccount', ['']) or []
            self.imported_addresses.update(addresses)
        except:
            pass

    def _call(self, method, params=None, timeout=5):
        if params is None:
            params = []

        payload = {
            "jsonrpc": "2.0",
            "id": int(time.time() * 1000),
            "method": method,
            "params": params
        }

        try:
            resp = self.session.post(
                self.url,
                auth=self.auth,
                json=payload,
                timeout=timeout
            )

            if resp.status_code == 200:
                result = resp.json()
                if result.get('error'):
                    if result['error'].get('code') == -32601:
                        return None
                    raise Exception(f"RPC error: {result['error']}")
                return result['result']
            raise Exception(f"HTTP {resp.status_code}")

        except requests.exceptions.Timeout:
            if method == 'getbalance':
                return 0.0
            elif method == 'listtransactions':
                return []
            return None
        except Exception as e:
            print(f"RPC error in {method}: {str(e)}")
            return None

    def fast_import_check(self, address):
        return address in self.imported_addresses

    def import_privkey(self, wif_key, label="", rescan=False):
        try:
            address = label
            if self.fast_import_check(address):
                return None

            # First validate the address
            validate = self._call('validateaddress', [address])
            if not validate or not validate.get('isvalid'):
                raise Exception("Invalid address")

            result = self._call('importprivkey', [wif_key, label, rescan], timeout=10)
            if result is not None:
                self.imported_addresses.add(address)
            return result
        except Exception as e:
            if "already have this key" in str(e) or "Key already exists" in str(e):
                self.imported_addresses.add(address)
                return None
            print(f"Import error: {e}")
            return None

    def get_balance(self, address=None):
        try:
            if address:
                # Get unspent outputs for address
                unspent = self._call('listunspent', [1, 9999999, [address]]) or []
                balance = sum(float(tx['amount']) for tx in unspent)
                return float(balance)
            return float(self._call('getbalance') or 0)
        except:
            return 0.0

    def list_transactions(self, address=None, count=50):
        try:
            if address:
                # Get specific address transactions
                received = self._call('listreceivedbyaddress', [0, True]) or []
                address_txs = []
                
                for entry in received:
                    if entry.get('address') == address:
                        txids = entry.get('txids', [])
                        for txid in txids:
                            tx = self._call('gettransaction', [txid]) or {}
                            if tx:
                                tx_details = tx.get('details', [])
                                for detail in tx_details:
                                    if detail.get('address') == address:
                                        address_txs.append({
                                            'address': address,
                                            'category': detail.get('category'),
                                            'amount': detail.get('amount'),
                                            'confirmations': tx.get('confirmations', 0),
                                            'txid': txid,
                                            'time': tx.get('time', 0)
                                        })
                return address_txs

            # Get all wallet transactions if no address specified
            return self._call('listtransactions', ["*", count]) or []
        except Exception as e:
            print(f"Error listing transactions: {e}")
            return []

    def send_to_address(self, from_address, to_address, amount):
        try:
            if not isinstance(amount, (int, float)) or amount <= 0:
                raise ValueError("Invalid amount")

            # Get unspent outputs for the from_address
            unspent = self._call('listunspent', [1, 9999999, [from_address]]) or []
            balance = sum(float(tx['amount']) for tx in unspent)

            if balance < amount:
                raise Exception(f"Insufficient funds: {balance} < {amount}")

            # Create raw transaction
            inputs = [{"txid": tx['txid'], "vout": tx['vout']} for tx in unspent]
            outputs = {to_address: amount}
            
            # Add change output if needed
            fee = 0.0001  # Fixed fee for example
            if balance > amount + fee:
                outputs[from_address] = balance - amount - fee

            # Create and sign raw transaction
            raw_tx = self._call('createrawtransaction', [inputs, outputs])
            signed_tx = self._call('signrawtransaction', [raw_tx])
            
            if not signed_tx or signed_tx.get('complete') != True:
                raise Exception("Failed to sign transaction")

            # Broadcast
            return self._call('sendrawtransaction', [signed_tx['hex']])
        except Exception as e:
            raise Exception(f"Send failed: {str(e)}")
    def estimate_fee(self, blocks=6):
        """
        Estimate fee rate in BTC2/kb for getting included within specified blocks.
        Default to 6 blocks which is roughly 1 hour target.
        """
        try:
            fee = self._call('estimatefee', [blocks])
            if fee is not None and fee >= 0:
                return fee
            return 0.0001  # Fallback fee if estimate fails
        except:
            return 0.0001  # Fallback fee if RPC fails

btc2_rpc = BTC2RPC(RPC_USER, RPC_PASSWORD, RPC_HOST, RPC_PORT)
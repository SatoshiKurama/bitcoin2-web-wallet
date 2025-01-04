import os
import json

# In real usage, store these in environment variables or a secure secrets manager
RPC_USER = os.environ.get("BTC2_RPC_USER", "youruser")  # same as rpcuser in bitcoin2.conf
RPC_PASSWORD = os.environ.get("BTC2_RPC_PASSWORD", "yourpassword")  # same as rpcpassword
RPC_HOST = os.environ.get("BTC2_RPC_HOST", "127.0.0.1")
RPC_PORT = int(os.environ.get("BTC2_RPC_PORT", 8332))  # default for BTC2 (Bitcoin-like)
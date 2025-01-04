import hashlib
import base58
import os
from cryptography.hazmat.primitives import hashes
from cryptography.hazmat.primitives.asymmetric import ec
from cryptography.hazmat.primitives.serialization import (
    Encoding,
    PrivateFormat,
    NoEncryption
)

"""
btc2_wallet.py

Generates a real P2PKH address from an EC private key on secp256k1 (like Bitcoin).
Addresses derived here are recognized by the Bitcoin 2 daemon if wallet=1 is enabled.
"""

P2PKH_VERSION = b'\x00'  # BTC2 mainnet typically uses 0x00 (Bitcoin-style)

def generate_btc2_key_pair():
    """
    1) Generate EC private key
    2) Extract raw secret -> WIF
    3) Derive the compressed public key
    4) Convert to P2PKH address
    """
    private_key = ec.generate_private_key(ec.SECP256K1())
    private_key_bytes = private_key.private_bytes(
        encoding=Encoding.DER,
        format=PrivateFormat.PKCS8,
        encryption_algorithm=NoEncryption()
    )
    wif = convert_der_to_wif(private_key_bytes)
    address = derive_address_from_wif(wif)
    return wif, address

def extract_raw_secret(der_bytes):
    """
    Locate the 32-byte private key octet string in the DER-encoded key.
    We'll do a quick scan for 0x04, 0x20 and read 32 bytes.
    """
    idx = der_bytes.find(b'\x04\x20')
    if idx == -1:
        raise ValueError("Could not find private key in DER.")
    return der_bytes[idx+2 : idx+2+32]

def convert_der_to_wif(der_bytes):
    """Convert DER-encoded private key to a WIF with compression."""
    raw_secret = extract_raw_secret(der_bytes)
    version_byte = b'\x80'
    extended_key = version_byte + raw_secret + b'\x01'  # compression flag

    # Double sha256
    checksum_full = hashlib.sha256(hashlib.sha256(extended_key).digest()).digest()
    checksum = checksum_full[:4]
    final = extended_key + checksum
    return base58.b58encode(final).decode('utf-8')

def derive_compressed_pubkey(ec_private_key):
    """
    Create 33-byte compressed pubkey from an ec.EllipticCurvePrivateKey.
    0x02 if y is even, 0x03 if y is odd, plus 32-byte x.
    """
    public_key = ec_private_key.public_key()
    numbers = public_key.public_numbers()
    x = numbers.x
    y = numbers.y
    prefix = b'\x02' if (y % 2) == 0 else b'\x03'
    x_bytes = x.to_bytes(32, 'big')
    return prefix + x_bytes

def pubkey_to_p2pkh_address(compressed_pubkey):
    """
    1) sha256 -> ripemd160 => keyhash
    2) Add version byte 0x00
    3) Double sha256 => 4-byte checksum
    4) base58check
    """
    sha = hashlib.sha256(compressed_pubkey).digest()
    ripe = hashlib.new('ripemd160')
    ripe.update(sha)
    keyhash = ripe.digest()

    extended = P2PKH_VERSION + keyhash
    chksum_full = hashlib.sha256(hashlib.sha256(extended).digest()).digest()
    chk = chksum_full[:4]

    return base58.b58encode(extended + chk).decode('utf-8')

def derive_address_from_wif(wif):
    """Recreate the same compressed pubkey + P2PKH address from WIF."""
    raw = base58.b58decode(wif)
    secret = raw[1:33]
    from cryptography.hazmat.primitives.asymmetric import ec
    ec_private_key = ec.derive_private_key(int.from_bytes(secret, 'big'), ec.SECP256K1())
    compressed = derive_compressed_pubkey(ec_private_key)
    return pubkey_to_p2pkh_address(compressed)
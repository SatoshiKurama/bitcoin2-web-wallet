import os
import base64
from cryptography.hazmat.backends import default_backend
from cryptography.hazmat.primitives.ciphers import Cipher, algorithms, modes
from cryptography.hazmat.primitives import padding, hashes
from cryptography.hazmat.primitives.kdf.pbkdf2 import PBKDF2HMAC

class WalletEncryption:
    def __init__(self):
        # Normally, you'd store a strong key in ENV or a vault
        base_key = os.environ.get('ENCRYPTION_KEY', 'defaultdevkey').encode('utf-8')
        salt = b'btc2_salt_demo'
        kdf = PBKDF2HMAC(
            algorithm=hashes.SHA256(),
            length=32,
            salt=salt,
            iterations=100000,
            backend=default_backend()
        )
        self.key = kdf.derive(base_key)

    def encrypt_data(self, plain_text: str) -> bytes:
        """
        AES-256-CBC encryption for the private key. Returns base64 bytes.
        """
        if not isinstance(plain_text, str):
            raise ValueError("Input must be a string")

        iv = os.urandom(16)
        cipher = Cipher(algorithms.AES(self.key), modes.CBC(iv), backend=default_backend())
        encryptor = cipher.encryptor()

        padder = padding.PKCS7(128).padder()
        padded_data = padder.update(plain_text.encode('utf-8')) + padder.finalize()

        encrypted = encryptor.update(padded_data) + encryptor.finalize()
        return base64.b64encode(iv + encrypted)

    def decrypt_data(self, encrypted_data: bytes) -> str:
        """
        Decrypt from base64 bytes -> raw AES -> unpad -> UTF-8
        """
        raw_data = base64.b64decode(encrypted_data)
        iv = raw_data[:16]
        actual_enc = raw_data[16:]

        cipher = Cipher(algorithms.AES(self.key), modes.CBC(iv), backend=default_backend())
        decryptor = cipher.decryptor()
        decrypted_padded = decryptor.update(actual_enc) + decryptor.finalize()

        unpadder = padding.PKCS7(128).unpadder()
        decrypted = unpadder.update(decrypted_padded) + unpadder.finalize()
        return decrypted.decode('utf-8')

wallet_encryption = WalletEncryption()
import hashlib
import json
import base64

from cryptography.hazmat.primitives.asymmetric import rsa, padding
from cryptography.hazmat.primitives import serialization, hashes

class Account:
    # Default balance is 100 if not sent during account creation
    # nonce is incremented once every transaction to ensure tx can't be replayed and can be ordered (similar to Ethereum)
    # private and public pem strings should be set inside __generate_key_pair
    def __init__(self, sender_id, balance=100):
        self._id = sender_id
        self._balance = balance
        self._initial_balance = balance
        self._nonce = 0
        self._private_pem = None
        self._public_pem = None
        self.__generate_key_pair()

    @property
    def id(self):
        return self._id

    @property
    def public_key(self):
        return self._public_pem

    @property
    def balance(self):
        return self._balance

    @property
    def initial_balance(self):
        return self._initial_balance

    def increase_balance(self, value):
        self._balance += value

    def decrease_balance(self, value):
        self._balance -= value

    def __generate_key_pair(self):
        # Implement key pair generation logic
        # Convert them to pem format strings and store in the class attributes already defined

        # Create the private key using the rsa
        # hazardous cryptographic module
        private_key = rsa.generate_private_key(
            public_exponent=65537,
            key_size=2048
        )

        # Convert it to PEM format
        self._private_pem = private_key.private_bytes(
            encoding=serialization.Encoding.PEM,
            format=serialization.PrivateFormat.PKCS8,
            encryption_algorithm=serialization.NoEncryption()
        )

        # Derive the public key from private key
        public_key = private_key.public_key()
        # Convert to PEM format
        self._public_pem = public_key.public_bytes(
            encoding=serialization.Encoding.PEM,
            format=serialization.PublicFormat.SubjectPublicKeyInfo
        )

    def create_transaction(self, receiver_id, value, tx_metadata=''):
        nonce = self._nonce + 1
        transaction_message = {'sender': self._id, 'receiver': receiver_id, 'value': value, 'tx_metadata': tx_metadata, 'nonce': nonce}

        # Create the transaction hash using SHA256
        transaction_message_hash = hashlib.sha256(json.dumps(transaction_message, sort_keys=True).encode()).hexdigest()

        signature = ''

        # Implement digital signature of the hash of the message

        # Revert the private key from PEM format
        private_key = serialization.load_pem_private_key(
            self._private_pem, password=None
        )

        # Obtain the digital signature in bytes format
        signature_bytes = private_key.sign(
            transaction_message_hash.encode(),
            padding.PSS(
                mgf=padding.MGF1(hashes.SHA256()),
                salt_length=padding.PSS.MAX_LENGTH
            ),
            hashes.SHA256()
        )
        # Encode it is base64 format
        signature = base64.b64encode(signature_bytes).decode()

        self._nonce = nonce
        return {'message': transaction_message, 'signature': signature}
        


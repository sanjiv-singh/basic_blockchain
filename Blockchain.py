import json
import hashlib
import base64

from cryptography.hazmat.primitives.asymmetric import rsa, padding
from cryptography.hazmat.primitives import serialization, hashes
from cryptography.exceptions import InvalidSignature

from Block import Block


class Blockchain:
    # Basic blockchain init
    # Includes the chain as a list of blocks in order, pending transactions, and known accounts
    # Includes the current value of the hash target. It can be changed at any point to vary the difficulty
    # Also initiates a genesis block
    def __init__(self, hash_target):
        self._chain = []
        self._pending_transactions = []
        self._chain.append(self.__create_genesis_block())
        self._hash_target = hash_target
        self._accounts = {}

    def __str__(self):
        return f"Chain:\n{self._chain}\n\nPending Transactions: {self._pending_transactions}\n"

    @property
    def hash_target(self):
        return self._hash_target

    @hash_target.setter
    def hash_target(self, hash_target):
        self._hash_target = hash_target

    # Creating the genesis block, taking arbitrary previous block hash since there is no previous block
    # Using the famous bitcoin genesis block string here :)  
    def __create_genesis_block(self):
        genesis_block = Block(0, [], 'The Times 03/Jan/2009 Chancellor on brink of second bailout for banks', 
            None, 'Genesis block using same string as bitcoin!')
        return genesis_block

    def __validate_transaction(self, transaction):
        # Serialize transaction data with keys ordered, and then convert to bytes format
        hash_string = json.dumps(transaction['message'], sort_keys=True)
        encoded_hash_string = hash_string.encode('utf-8')
        
        # Take sha256 hash of the serialized message, and then convert to bytes format
        message_hash = hashlib.sha256(encoded_hash_string).hexdigest()
        encoded_message_hash = message_hash.encode('utf-8')

        # Signature - Encode to bytes and then Base64 Decode to get the original signature format back 
        signature = base64.b64decode(transaction['signature'].encode('utf-8'))

        try:
            # Load the public_key object and verify the signature against the calculated hash
            sender_public_pem = self._accounts.get(transaction['message']['sender']).public_key
            sender_public_key = serialization.load_pem_public_key(sender_public_pem)
            sender_public_key.verify(
                                        signature,
                                        encoded_message_hash,
                                        padding.PSS(
                                            mgf=padding.MGF1(hashes.SHA256()),
                                            salt_length=padding.PSS.MAX_LENGTH
                                        ),
                                        hashes.SHA256()
                                    )
        except InvalidSignature:
            return False

        return True

    def __process_transactions(self, transactions):
        # Appropriately transfer value from the sender to the receiver
        # For all transactions, first check that the sender has enough balance. 
        # Return False otherwise

        # Get all pending tansaction messages into a list
        transactions = [t["message"] for t in transactions]
        # Create a new dict to hold all transactions. Here the key will be the account_id
        # and the value will be the net transfer value based on all transactions processed so far.
        # Transactions are being recorded in separate dict so that they may be committed all at
        # once after checking that the balance never falls below zero.
        transaction_dict = {}

        # Now evaluate the transactions one by one in a loop
        for transaction in transactions:
            sender = transaction.get("sender")
            receiver = transaction.get("receiver")
            value = transaction.get("value")

            # If a sender account is not registered with blockchain return False
            if sender not in self._accounts:
                return False
            # If a receiver account is not registered with blockchain return False
            if receiver not in self._accounts:
                return False
            # Get account balance of sender and check if it has balance
            sender_account = self._accounts.get(sender)
            if sender_account.balance < value:
                return False
            
            # Also, check whether the balance is diminishing below
            # the transferred value at any subsequent transaction 
            transaction_dict[sender] = transaction_dict.get(sender, 0) - value
            if sender_account.balance < transaction_dict[sender]:
                return False
            transaction_dict[receiver] = transaction_dict.get(receiver, 0) + value
        # Validation check (acct balance should never go negative)
        #for account_balance in self.get_account_balances():
        #    if account_balance["id"] not in transaction_dict:
        #        continue
        #    if account_balance["balance"] < -1.0*transaction_dict[account_balance["id"]]:
        #        return False

        # Finally commit the transactions all at once and return True
        for account_id, value in transaction_dict.items():
            account = self._accounts.get(account_id)
            account.increase_balance(value)
        return True

    def __process_valid_transactions(self, transactions):
        # Appropriately transfer value from the sender to the receiver
        # For all transactions, first check that the sender has enough balance. 
        # If balance falls below transferred value for any transaction, 
        # do not add it to valid_transactions list

        # Get all pending tansaction messages into a list
        #transactions = [t["message"] for t in transactions]

        # Create a new empty list to hold all valid transactions
        valid_transactions = []

        # Create a new dict to hold all transactions. Here the key will be the account_id
        # and the value will be the net transfer value based on all transactions processed so far.
        # Transactions are being recorded in separate dict so that they may be committed all at
        # once after checking that the balance never falls below zero.
        transaction_dict = {}

        # Now evaluate the transactions one by one in a loop
        for transaction in transactions:
            sender = transaction["message"].get("sender")
            receiver = transaction["message"].get("receiver")
            value = transaction["message"].get("value")

            # If a sender account is not registered with blockchain reject transaction and continue
            if sender not in self._accounts:
                continue
            # If a receiver account is not registered with blockchain reject transaction and continue
            if receiver not in self._accounts:
                continue
            # Get account balance of sender and check if it has balance
            # else reject the transaction and continue
            sender_account = self._accounts.get(sender)
            if sender_account.balance < value:
                print(f"Insufficient balance, rejecting tx: {transaction}")
                continue
            
            # Also, check whether the balance is diminishing below
            # the transferred value at any subsequent transaction 
            # If so, reject the transaction and continue
            transaction_dict[sender] = transaction_dict.get(sender, 0) - value
            if sender_account.balance < transaction_dict[sender]:
                print(f"Insufficient balance, rejecting tx: {transaction}")
                continue
            transaction_dict[receiver] = transaction_dict.get(receiver, 0) + value

            # If all the above tests pass add the transaction to list of valid transactions
            valid_transactions.append(transaction)
        # Validation check (acct balance should never go negative)
        #for account_balance in self.get_account_balances():
        #    if account_balance["id"] not in transaction_dict:
        #        continue
        #    if account_balance["balance"] < -1.0*transaction_dict[account_balance["id"]]:
        #        return False

        # Finally commit the transactions all at once and
        # return the list of valid transactions
        for account_id, value in transaction_dict.items():
            account = self._accounts.get(account_id)
            account.increase_balance(value)
        return valid_transactions

    # Creates a new block and appends to the chain
    # Also clears the pending transactions as they are part of the new block now
    def create_new_block(self):
        if self.__process_transactions(self._pending_transactions):
            new_block = Block(len(self._chain), self._pending_transactions, self._chain[-1].block_hash, self._hash_target)
        else:
            valid_transactions = self.__process_valid_transactions(self._pending_transactions)
            new_block = Block(len(self._chain), valid_transactions, self._chain[-1].block_hash, self._hash_target)
        self._chain.append(new_block)
        self._pending_transactions = []

    # Simple transaction with just one sender, one receiver, and one value
    # Created by the account and sent to the blockchain instance
    def add_transaction(self, transaction):
        if self.__validate_transaction(transaction):
            self._pending_transactions.append(transaction)
            return True
        else:
            print(f'ERROR: Transaction: {transaction} failed signature validation')
            return False


    def __validate_chain_hash_integrity(self):
        # Run through the whole blockchain and ensure that previous hash is actually the hash of the previous block
        # Return False otherwise

        # Number of blocks in the chain
        nblocks = len(self._chain)

        # return True in case there is either no block
        # or only the genesis block
        if nblocks < 2:
            return True
        
        # Loop through the chain and check if hash of previous block
        # is equal to the value stored in previous_block_hash attriibute
        # of current block
        for index in range(nblocks-1):
            previous_block = self._chain[index]
            current_block = self._chain[index+1]
            if previous_block.hash_block() != current_block.previous_block_hash:
                return False
        return True

    def __validate_block_hash_target(self):
        # Run through the whole blockchain and ensure that block hash meets hash target criteria, and is the actual hash of the block
        # Return False otherwise
        for block in self._chain:

            # Ignore genesis block
            if block._index == 0:
                continue

            # Check that the value stored in block_hash attribute
            # is actually the hash of block including the nonce
            if block.hash_block() != block.block_hash:
                print('Block hash is invalid.')
                return False
            
            # Check that the block has is less than the target hash
            if int(block.block_hash, 16) >= int(block.hash_target, 16):
                print('Block hash is not less than hash target.')
                return False
        print('Block hashes are less than hash target.')
        return True

    def __validate_complete_account_balances(self):
        # Run through the whole blockchain and ensure that balances never become negative from any transaction
        # Return False otherwise

        # The below method was implemented by taking the final account balance as the starting point.
        # The loop goes backwards with reverse order of transactions (reverse of block index and reverse of nonce)
        """
        account_balance = {}
        for balance in self.get_account_balances():
            account_balance[balance.get("id")] = balance.get("balance")
        for block in sorted(self._chain, key=lambda x: x._index, reverse=True):
            transaction_messages = [t["message"] for t in block._transactions]
            sorted_transactions = sorted(transaction_messages, key=lambda x: x['nonce'], reverse=True)
            for transaction in sorted_transactions:
                receiver = transaction.get("receiver")
                sender = transaction.get("sender")
                if account_balance[sender] < 0 or account_balance[receiver] < 0:
                    return False
                account_balance[receiver] -= transaction.get("value")
                account_balance[sender] += transaction.get("value")
        return True
        """

        # The below method is as per solution suggested in project explanation.
        # The initial balance is stored in a new attribute (_initial_balance).
        # The blocks and transactions are looped and checked whether account balance
        # fell below zero at any stage.
        account_balance = {}
        for id, account in self._accounts.items():
            account_balance[id] = account.initial_balance
        for block in sorted(self._chain, key=lambda x: x._index):
            transaction_messages = [t["message"] for t in block._transactions]
            sorted_transactions = sorted(transaction_messages, key=lambda x: x['nonce'])
            for transaction in sorted_transactions:
                receiver = transaction.get("receiver")
                sender = transaction.get("sender")
                value = transaction.get("value")
                account_balance[receiver] = account_balance.get(receiver, 0) + value
                account_balance[sender] = account_balance.get(sender, 0) - value
                if account_balance[sender] < 0:
                    return False
        return True

    # Blockchain validation function
    # Runs through the whole blockchain and applies appropriate validations
    def validate_blockchain(self):
        # Call __validate_chain_hash_integrity and implement that method. Return False if check fails
        if not self.__validate_chain_hash_integrity():
            print('Chain hash integrity is invalid.')
            return False
        print('Chain hash integrity is valid.')
        # Call __validate_block_hash_target and implement that method. Return False if check fails
        if not self.__validate_block_hash_target():
            print('Block hash target is invalid.')
            return False
        print('Block hash target is valid.')
        # Call __validate_complete_account_balances and implement that method. Return False if check fails
        if not self.__validate_complete_account_balances():
            print('Account balances are invalid.')
            return False
        print('Account balances are valid.')
        return True

    def add_account(self, account):
        self._accounts[account.id] = account
    
    def get_account_balances(self):
        return [{'id': account.id, 'balance': account.balance} for account in self._accounts.values()]




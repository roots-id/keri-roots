# -*- encoding: utf-8 -*-
"""
KERI
keri.ledger.cardaning module

Backer operations on Cardano Ledger
"""

from blockfrost import BlockFrostApi, ApiError, ApiUrls
from pycardano import * 
import os
import time

class Cardano:

    def __init__(self, *, name='test', base="", temp=False,
                 ks=None, db=None, cf=None, clear=False, headDirPath=None, **kwa):
        print("ROOTSLOG Cardaning started")
        self.name = name
        
        self.network = Network.TESTNET
        blockfrostProjectId="previewapifaDDKsMZE7asmrcG8W3zbRE1pojXY"
        self.api = BlockFrostApi(
            project_id=blockfrostProjectId,
            base_url=ApiUrls.preview.value
            )
        
        self.context = BlockFrostChainContext(blockfrostProjectId,self.network, ApiUrls.preview.value)

        if os.path.exists("payment.skey"):
            # Loads keys
            self.payment_signing_key = PaymentSigningKey.load("payment.skey")
            payment_verification_key = PaymentVerificationKey.load("payment.vkey")
            stake_signing_key = StakeSigningKey.load("stake.skey")
            stake_verification_key = StakeVerificationKey.load("stake.vkey")

            self.spending_addr = Address(payment_verification_key.hash(), stake_verification_key.hash(), network=self.network)
            stake_addr = Address(payment_part=None, staking_part=stake_verification_key.hash(), network=self.network)
            print("Cardano Backer Address:", self.spending_addr.encode())
        else:
            payment_key_pair = PaymentKeyPair.generate()
            self.payment_signing_key = payment_key_pair.signing_key
            payment_verification_key = payment_key_pair.verification_key
            stake_key_pair = StakeKeyPair.generate()
            stake_signing_key = stake_key_pair.signing_key
            stake_verification_key = stake_key_pair.verification_key

            # Save keys
            self.payment_signing_key.save("payment.skey")
            payment_verification_key.save("payment.vkey")
            stake_signing_key.save("stake.skey")
            stake_verification_key.save("stake.vkey")

            self.spending_addr = Address(payment_verification_key.hash(), stake_verification_key.hash(), network=self.network)
            stake_addr = Address(payment_part=None, staking_part=stake_verification_key.hash(), network=self.network)
            
            self.fundAddress(self.spending_addr)
            print("Cardano Backer Address:", self.spending_addr.encode())
            time.sleep(50)

        
        balance = self.getaddressBalance()
        
        if balance and balance > 1000000:
            print("Address balance:",balance/1000000, "ADA")
        else:
            print("Insuficient balance")


    def publishEvent(self, event):

        try:
            print("ROOTSLOG TX SUBMIT")
            print(event)
            seq_no = int(event['ked']['s'])
            for sig in event['signatures']:
                event['signatures'][sig['index']]['signature'] = [sig['signature'][:44],sig['signature'][44:]]
            for wsig in event['witness_signatures']:
                event['witness_signatures'][wsig['index']]['signature']  = [wsig['signature'][:44],wsig['signature'][44:]]
            for seal in event['ked']['a']:
                if 'ca' in seal:
                    seal['ca']= [seal['ca'][:64],seal['ca'][64:]]
            tx_meta = {
                'ked': event['ked'],
                'witnesses': event['witnesses'],
                'signatures': event['signatures'],
                'witness_signatures': event['witness_signatures']
            }
            builder = TransactionBuilder(self.context)
            builder.add_input_address(self.spending_addr)
            # utxos = self.api.address_utxos(self.spending_addr.encode())
            # utxo_sum = 0
            # for u in utxos:
            #     utxo_sum = utxo_sum + int(u.amount[0].quantity)
            #     print(u.amount[0].quantity)
            #     print(u.tx_hash, u.tx_index)
            #     builder.add_input(TransactionInput.from_primitive([u.tx_hash, u.tx_index]))
            #     if utxo_sum > 1000000: break

            builder.add_output(TransactionOutput(self.spending_addr,Value.from_primitive([1000000])))
            
            builder.auxiliary_data = AuxiliaryData(Metadata(
                        { 
                            seq_no: tx_meta
                        }
                    )
                )
            signed_tx = builder.build_and_sign([self.payment_signing_key], change_address=self.spending_addr)
            self.context.submit_tx(signed_tx.to_cbor())
        except Exception as e:
            print("error", e)

    def getaddressBalance(self):
        try:
            address = self.api.address(
                address=self.spending_addr.encode())
            return int(address.amount[0].quantity)
        except ApiError as e:
            return 0

    def fundAddress(self, addr):
        # Load funding address or create
        if os.path.exists("funding_p.skey"):
            # Loads keys
            funding_payment_signing_key = PaymentSigningKey.load("funding_p.skey")
            funding_payment_verification_key = PaymentVerificationKey.load("funding_p.vkey")
            funding_stake_signing_key = StakeSigningKey.load("funding_s.skey")
            funding_stake_verification_key = StakeVerificationKey.load("funding_s.vkey")

            funding_addr = Address(funding_payment_verification_key.hash(), funding_stake_verification_key.hash(), network=self.network)

        else:
            funding_payment_key_pair = PaymentKeyPair.generate()
            funding_payment_signing_key = funding_payment_key_pair.signing_key
            funding_payment_verification_key = funding_payment_key_pair.verification_key
            funding_stake_key_pair = StakeKeyPair.generate()
            funding_stake_signing_key = funding_stake_key_pair.signing_key
            funding_stake_verification_key = funding_stake_key_pair.verification_key

            # Save keys
            funding_payment_signing_key.save("funding_p.skey")
            funding_payment_verification_key.save("funding_p.vkey")
            funding_stake_signing_key.save("funding_s.skey")
            funding_stake_verification_key.save("funding_s.vkey")

            funding_addr = Address(funding_payment_verification_key.hash(), funding_stake_verification_key.hash(), network=self.network)
            print("Funding address generated:",funding_addr)

        funding_balance = self.api.address(address=funding_addr.encode()).amount[0]
        print("Funding address:", funding_addr)
        print("Funding balance:", int(funding_balance.quantity)/1000000,"ADA")
        if int(funding_balance.quantity) > 100000000:
            builder = TransactionBuilder(self.context)
            builder.add_input_address(funding_addr)
            builder.add_output(TransactionOutput(addr,Value.from_primitive([100000000])))
            
            signed_tx = builder.build_and_sign([funding_payment_signing_key], change_address=funding_addr)
            self.context.submit_tx(signed_tx.to_cbor())
            print("Address funded")

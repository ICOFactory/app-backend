from ethereum_node import EthereumNode
from database import Database
import json

MAX_PENDING_COMMANDS = 25
GROWTH_RATE = 15


class TransactionData:
    def __init__(self, from_address=None, gas=None, gas_price=None, tx_hash=None,
                 to_address=None, wei_value=None, json_data=None):
        if json_data:
            tx_data = json.loads(json_data)
            self.from_address = tx_data["from"]
            self.gas = tx_data["gas"]
            self.gas_price = tx_data["gas_price"]
            self.tx_hash = tx_data["hash"]
            self.to_address = tx_data["to"]
            self.wei_value = tx_data["value"]
        else:
            self.from_address = from_address
            self.gas = gas
            self.gas_price = gas_price
            self.tx_hash = tx_hash
            self.to_address = to_address
            self.wei_value = wei_value

    def __str__(self):
        output = dict()
        output["from"] = self.from_address
        output["gas"] = self.gas
        output["gas_price"] = self.gas_price
        output["hash"] = self.tx_hash
        output["to"] = self.to_address
        output["value"] = self.wei_value
        return json.dumps(output)


class BlockData:
    def __init__(self, block_number=None, block_hash=None, block_timestamp=None, gas_used=None, gas_limit=None,
                 block_size=None, tx_count=None, json_data=None):
        if json_data:
            block_data = json.loads(json_data)
            self.block_number = block_data["block_number"]
            self.block_hash = block_data["block_hash"]
            self.block_timestamp = block_data["block_timestamp"]
            self.gas_used = block_data["gas_used"]
            self.gas_limit = block_data["gas_limit"]
            self.block_size = block_data["block_size"]
            self.tx_count = block_data["tx_count"]
            self.transactions = []
            for each_tx in block_data["transactions"]:
                self.transactions.append(TransactionData(json_data=each_tx))
        else:
            self.block_number = block_number
            self.block_hash = block_hash
            self.block_timestamp = block_timestamp
            self.gas_used = gas_used
            self.gas_limit = gas_limit
            self.block_size = block_size
            self.tx_count = tx_count
            self.transactions = []

    def __str__(self):
        tr_strings = []
        for each_tx in self.transactions:
            tr_strings.append(str(each_tx))
        output = dict()
        output["transactions"] = tr_strings
        output["block_number"] = self.block_number
        output["block_hash"] = self.block_hash
        output["block_timestamp"] = self.block_timestamp
        output["gas_used"] = self.gas_used
        output["gas_limit"] = self.gas_limit
        output["block_size"] = self.block_size
        output["tx_count"] = self.tx_count
        return json.dumps(output)


class BlockDataManager:
    def __init__(self, db, logger=None):
        self.db = db
        self.logger = logger

    def put_block(self, block_data):
        eth_node = EthereumNode(None, self.logger, self.db)
        for each_tx in block_data.transactions:
            if each_tx.from_address:
                each_tx.from_address = eth_node.add_new_ethereum_address(each_tx.from_address)
            if each_tx.to_address:
                each_tx.to_address = eth_node.add_new_ethereum_address(each_tx.to_address)
        return self.db.put_block(block_data)

    def get_block(self, block_number):
        found = False
        self.logger.info("Attempting to fetch block data for block {0} from db...".format(block_number))
        block_data = self.db.get_block(block_number)
        if block_data:
            found = True

        pending_commands = self.db.get_pending_commands()
        undirected_commands = pending_commands[0]
        remaining = 0
        if undirected_commands < MAX_PENDING_COMMANDS:
            remaining = MAX_PENDING_COMMANDS - undirected_commands
            if remaining > GROWTH_RATE:
                remaining = GROWTH_RATE

        target_list = []

        while remaining > 0:
            if not found:
                target_list.append(block_number)
                remaining -= 1
            block_number -= 1
            found = self.db.get_block(block_number)
        for each in target_list:
            command_data = {"get_block_data": each}
            if self.logger:
                self.logger.info("Posting command to get_block_data for {0}".format(each))
            self.db.post_command(json.dumps(command_data))
        return block_data

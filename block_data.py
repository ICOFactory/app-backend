from ethereum_address_pool import EthereumAddressPool
import MySQLdb
import json
import logging

MAX_PENDING_COMMANDS = 25
WINDOW_SIZE = 100
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
    def __init__(self, db=None, logger=None):
        config_stream = open("config.json", "r")
        self.config = json.load(config_stream)
        config_stream.close()
        self.MAX_PENDING_COMMANDS = self.config["block_data"]["max_pending_commands"]
        self.WINDOW_SIZE = self.config["block_data"]["window_size"]

        if db:
            self.db = db
            self.db_conn = db.db
        else:
            self.db_conn = MySQLdb.connect(self.config["block_data"]["mysql_host"],
                                           self.config["block_data"]["mysql_user"],
                                           self.config["block_data"]["mysql_password"],
                                           self.config["block_data"]["mysql_database"])
        self.logger = logger

    def put_block(self, block_data):
        eth_pool = EthereumAddressPool(db, logger)
        for each_tx in block_data.transactions:
            if each_tx.from_address:
                each_tx.from_address = eth_pool.add_new_ethereum_address(each_tx.from_address)
            if each_tx.to_address:
                each_tx.to_address = eth_pool.add_new_ethereum_address(each_tx.to_address)
        return self.db.put_block(block_data)

    def target_new_blocks(self, latest_block, window_size=WINDOW_SIZE, max_targets=MAX_PENDING_COMMANDS):
        """
        Target new blocks for addition and removal (duplicates)

        :param latest_block: latest_block_number
        :param window: search window size
        :param max_targets: max target to add, no limit on removal of duplicates
        :return: [block_numbers_to_add],[block_numbers_to_remove]
        """

        # maybe use numpy here...
        self.logger.info("Searching for missing/duplicate blocks...")

        targets_for_addition = []
        targets_for_removal = []

        frame = [0] * window_size
        reference = latest_block
        offset = 0

        sql = "SELECT block_number, block_data_id FROM block_data ORDER BY block_number DESC LIMIT %s OFFSET %s;"
        c = self.db_conn.cursor()

        while len(targets_for_addition) < max_targets:
            try:
                c.execute(sql, (window_size, offset,))
                for row in c:
                    x = reference - row[0]
                    if x < window_size:
                        frame[x] += 1
            except MySQLdb.Error as e:
                try:
                    error_message = "MySQL Error [%d]: %s" % (e.args[0], e.args[1])
                except IndexError:
                    error_message = "MySQL Error: %s" % (str(e),)
                if self.logger:
                    logger.error(error_message)
                else:
                    print(error_message)

            for x in range(window_size):
                value = frame[x]
                if value == 0 and len(targets_for_addition) < max_targets:
                    targets_for_addition.append(x+reference)
                elif value > 1:
                    targets_for_removal.append(x+reference)

            reference -= window_size
            offset += window_size

        return targets_for_addition, targets_for_removal

    def get_block(self, block_number, no_txns=False):
        try:
            sql = "SELECT block_data_id, block_hash, block_timestamp, gas_used, gas_limit, block_size, tx_count "
            sql += "FROM block_data WHERE block_number=%s"
            c = self.db_conn.cursor()
            c.execute(sql, (block_number,))
            row = c.fetchone()
            if row:
                block_data_id = row[0]
                block_data = {"block_number": block_number,
                              "block_hash": row[1],
                              "block_timestamp": row[2],
                              "gas_used": row[3],
                              "gas_limit": row[4],
                              "block_size": row[5],
                              "tx_count": row[6],
                              "transactions": []}
                if no_txns:
                    return block_data
                txns = []
                sql = "SELECT sender_address_id, received_address_id, external_erc20_contract_id,amount,"
                sql += "transaction_hash,gas_used,priority,usd_price"
                sql += " FROM external_transaction_ledger WHERE block_data_id=%s"
                c.execute(sql, (block_data_id,))
                for row in c:
                    new_tx = {"from": row[0],
                              "to": row[1],
                              "external_contract_id": row[2],
                              "amount": ether_to_wei(row[3]),
                              "hash": row[4],
                              "gas_used": row[5],
                              "priority": row[6],
                              "usd_price": row[7]}
                    txns.append(new_tx)

                for each_tx in txns:
                    sql = "SELECT ethereum_address FROM ethereum_address_pool WHERE id=%s"
                    c.execute(sql, (each_tx["from"],))
                    row = c.fetchone()
                    if row:
                        each_tx["from"] = row[0]
                    else:
                        each_tx["from"] = None
                    c.execute(sql, (each_tx["to"],))
                    row = c.fetchone()
                    if row:
                        each_tx["to"] = row[0]
                    else:
                        each_tx["to"] = None

                block_data["transactions"] = txns
                return block_data
        except MySQLdb.Error as e:
            try:
                error_message = "MySQL Error [%d]: %s" % (e.args[0], e.args[1])
            except IndexError:
                error_message = "MySQL Error: %s" % (str(e),)

            if self.logger:
                self.logger.error(error_message)
            else:
                print(error_message)
        return None

    def get_block(self, block_number):
        block_data = self.get_block(block_number)

        pending_commands = self.db.get_pending_commands()
        undirected_commands = pending_commands[0]
        remaining = 0
        if undirected_commands < MAX_PENDING_COMMANDS:
            remaining = MAX_PENDING_COMMANDS - undirected_commands
            if remaining > GROWTH_RATE:
                remaining = GROWTH_RATE

        result = self.target_new_blocks(block_number, max_targets=remaining)
        target_list = result[0]

        for each in target_list:
            command_data = {"get_block_data": each}
            if self.logger:
                self.logger.info("Posting command to get_block_data for {0}".format(each))
            self.db.post_command(json.dumps(command_data))

        return block_data


if __name__ == "__main__":
    logger = logging.getLogger("Block Data Module")
    logger.setLevel(logging.INFO)
    ch = logging.StreamHandler()
    ch.setLevel(logging.INFO)
    # create formatter and add it to the handlers
    formatter = logging.Formatter('%(asctime)s - %(name)s - %(levelname)s - %(message)s')
    ch.setFormatter(formatter)
    # add the handlers to the logger
    logger.addHandler(ch)
    logger.info("Testing target_new_blocks on block number 7110893")
    manager = BlockDataManager(logger=logger)
    targets = manager.target_new_blocks(7110893)
    print(targets[0])
    print(targets[1])

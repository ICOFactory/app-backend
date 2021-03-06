from ethereum_address_pool import EthereumAddressPool
import MySQLdb
import json
import logging
import datetime
import random

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

    @property
    def age(self):
        age = datetime.datetime.utcnow() - self.block_timestamp
        remainder = age.seconds % 3600
        hours = int((age.seconds - remainder) / 3600)
        remainder = age.seconds % 60
        minutes = int((age.seconds - (remainder + (hours * 3600))) / 60)
        seconds = remainder
        if age.days > 0:
            return "{0} days, {1} hours, {2} minutes, {3} seconds".format(age.days,
                                                                          hours,
                                                                          minutes,
                                                                          seconds)
        elif hours > 0:
            return "{0} hours, {1} minutes, {2} seconds".format(
                hours,
                minutes,
                seconds)
        elif minutes > 0:
            return "{0} minutes, {1} seconds".format(minutes,
                seconds)
        else:
            return "{0} seconds".format(seconds)

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

    def get_block_numbers_since(self, block_number):
        sql = "SELECT block_number, block_data_id FROM block_data WHERE block_number > %s ORDER BY block_number DESC;"
        c = self.db_conn.cursor()
        latest_blocks = []

        try:
            c.execute(sql, (block_number,))
            for row in c:
                latest_blocks.append(row[0])

        except MySQLdb.Error as e:
            try:
                error_message = "MySQL Error [%d]: %s" % (e.args[0], e.args[1])
            except IndexError:
                error_message = "MySQL Error: %s" % (str(e),)
            if self.logger:
                self.logger.error(error_message)
            else:
                print(error_message)
        return latest_blocks

    def get_latest_block_numbers(self, count):
        sql = "SELECT block_number, block_data_id FROM block_data ORDER BY block_number DESC LIMIT %s;"
        c = self.db_conn.cursor()
        latest_blocks = []

        try:
            c.execute(sql, (count,))
            for row in c:
                latest_blocks.append(row[0])

        except MySQLdb.Error as e:
            try:
                error_message = "MySQL Error [%d]: %s" % (e.args[0], e.args[1])
            except IndexError:
                error_message = "MySQL Error: %s" % (str(e),)
            if self.logger:
                self.logger.error(error_message)
            else:
                print(error_message)
        return latest_blocks

    def put_block(self, block_data):
        eth_pool = EthereumAddressPool(self.db, self.logger)
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
        :param window_size: search window size
        :param max_targets: max target to add, no limit on removal of duplicates
        :return: [block_numbers_to_add]
        """

        self.logger.info("Searching for missing/duplicate blocks...")

        targets_for_addition = []

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
                    self.logger.error(error_message)
                else:
                    print(error_message)

            for x in range(window_size):
                value = frame[x]
                if value == 0 and len(targets_for_addition) < max_targets:
                    targets_for_addition.append(x+reference)

            reference -= window_size
            offset += window_size
            random.shuffle(targets_for_addition)

        return targets_for_addition

    def get_moving_average_for_block_number(self, block_number):
        c = self.db_conn.cursor()
        sql = "SELECT moving_average_gas_price FROM charting WHERE block_number=%s"
        c.execute(sql, (block_number,))
        row = c.fetchone()
        if row:
            return row[0]
        return 0

    def get_block_from_db(self, block_number, no_txns=False):
        # converts to something that will not overflow the database column
        def ether_to_wei(ether):
            return ether * 10 ** 18

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
                sql = "SELECT sender_address_id, received_address_id, contract_id,amount,"
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

                sql = "SELECT moving_average_gas_price FROM charting WHERE block_number=%s"
                c.execute(sql, (block_number,))
                row = c.fetchone()
                if row:
                    block_data["moving_average_gas_price"] = row[0]
                else:
                    block_data["moving_average_gas_price"] = None
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

    def get_block(self, block_number: int, no_txns=True) -> BlockData:
        block_dict = self.get_block_from_db(block_number, no_txns=no_txns)
        if block_dict:
            block_data = BlockData(block_dict["block_number"],
                                   block_dict["block_hash"],
                                   block_dict["block_timestamp"],
                                   block_dict["gas_used"],
                                   block_dict["gas_limit"],
                                   block_dict["block_size"],
                                   block_dict["tx_count"])
        else:
            block_data = None

        pending_commands = self.db.get_pending_commands()
        undirected_commands = pending_commands[0]
        remaining = 0
        if undirected_commands < MAX_PENDING_COMMANDS:
            remaining = MAX_PENDING_COMMANDS - undirected_commands
            if remaining > GROWTH_RATE:
                remaining = GROWTH_RATE

        target_list = self.target_new_blocks(block_number, max_targets=remaining)

        for each in target_list:
            command_data = {"get_block_data": each}
            if self.logger:
                self.logger.info("Posting command to get_block_data for {0}".format(each))
            self.db.post_command(json.dumps(command_data))

        return block_data


if __name__ == "__main__":
    stream_logger = logging.getLogger("Block Data Module")
    stream_logger.setLevel(logging.INFO)
    ch = logging.StreamHandler()
    ch.setLevel(logging.INFO)
    # create formatter and add it to the handlers
    formatter = logging.Formatter('%(asctime)s - %(name)s - %(levelname)s - %(message)s')
    ch.setFormatter(formatter)
    # add the handlers to the logger
    stream_logger.addHandler(ch)
    stream_logger.info("Testing get_block on block number 7110893")
    import database
    db = database.Database()
    import time
    start = time.time()
    manager = BlockDataManager(db, logger=stream_logger)
    block = manager.get_block(7110893)
    elapsed = time.time() - start
    if block:
        import pprint
        pprint.pprint(block)
        print("Fetched block in {0} seconds".format(elapsed))
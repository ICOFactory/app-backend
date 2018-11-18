# for managing distributed ethereum nodes
#
# The main module can be used to add/remove node api
# keys using the command line! to add an API key:
#   python ethereum_node.py add <new_identifier>
# to remove an API key
#   python ethereum_node.py remove <node_id>
# to list all registered nodes
#   python ethereum_node.py list-nodes

import MySQLdb
import json
import binascii
import database
import os
import sys
import pprint
import re

ETH_ADDRESS_REGEX = re.compile("^0x[0-9a-fA-F]{40}$")


def get_new_addresses(count):
    output = []
    for x in range(0, count):
        new_address = "0x"
        rng_out = os.urandom(20)
        new_address += binascii.hexlify(rng_out).decode()
        output.append(new_address)
    return output


def create_erc20_smart_contract(token_name, token_symbol, token_count,owner_id):
    smart_token = {"action": "create_erc2_token",
                   "token_info": {"token_name": token_name,
                                  "token_symbol": token_symbol,
                                  "token_count": token_count,
                                  "owner_id": owner_id}}
    token_data = json.dumps(smart_token)
    db = database.Database()
    return db.post_command(None, token_data)


class EthereumNode:
    def __init__(self, ip_addr=None, logger=None):
        self.ip_addr = ip_addr
        self.logger = logger
        config_data = json.load(open("config.json", "r"))
        self.db = MySQLdb.connect(config_data["mysql_host"],
                                  config_data["mysql_user"],
                                  config_data["mysql_password"],
                                  config_data["mysql_database"])
        self.wallet_address = config_data["wallet_address"]
        self.address_pool_min = config_data["eth_address_pool_min"]
        self.address_pool_max = config_data["eth_address_pool_max"]
        self.logger = logger

        try:
            c = self.db.cursor()
            c.execute("SELECT COUNT(*) FROM ethereum_address_pool WHERE assigned IS NULL")
            row = c.fetchone()
            if row[0] < self.address_pool_min:
                new_address_count = self.address_pool_max - row[0]
                new_eth_addresses = get_new_addresses(new_address_count)
                for each in new_eth_addresses:
                    c.execute("INSERT INTO ethereum_address_pool (ethereum_address) VALUES (%s);", (each,))
                self.db.commit()
        except MySQLdb.Error as e:
            try:
                if self.logger:
                    self.logger.error("MySQL Error [%d]: %s" % (e.args[0], e.args[1]))
                else:
                    print("MySQL Error [%d]: %s" % (e.args[0], e.args[1]))
            except IndexError:
                if self.logger:
                    self.logger.error("MySQL Error: %s" % (str(e),))
                else:
                    print("MySQL Error [%d]: %s" % (e.args[0], e.args[1]))

    def get_address_pool(self):
        output = []
        try:
            c = self.db.cursor()
            c.execute("SELECT id, ethereum_address FROM ethereum_address_pool WHERE assigned IS NULL")
            for row in c:
                output.append((row[0],row[1]))
            c.close()
        except MySQLdb.Error as e:
            try:
                if self.logger:
                    self.logger.error("MySQL Error [%d]: %s" % (e.args[0], e.args[1]))
                else:
                    print("MySQL Error [%d]: %s" % (e.args[0], e.args[1]))
            except IndexError:
                if self.logger:
                    self.logger.error("MySQL Error: %s" % (str(e),))
                else:
                    print("MySQL Error [%d]: %s" % (e.args[0], e.args[1]))
            return None
        return output

    def add_new_ethereum_address(self,new_address):
        if not ETH_ADDRESS_REGEX.match(new_address):
            raise TypeError
        try:
            c = self.db.cursor()
            c.execute("INSERT INTO ethereum_address_pool (ethereum_address) VALUES (%s);",(new_address,))
            self.db.commit()
            return c.lastrowid
        except MySQLdb.Error as e:
            try:
                if self.logger:
                    self.logger.error("MySQL Error [%d]: %s" % (e.args[0], e.args[1]))
                else:
                    print("MySQL Error [%d]: %s" % (e.args[0], e.args[1]))
            except IndexError:
                if self.logger:
                    self.logger.error("MySQL Error: %s" % (str(e),))
                else:
                    print("MySQL Error [%d]: %s" % (e.args[0], e.args[1]))
        return None

    def assign_new_ethereum_address(self):
        try:
            c = self.db.cursor()
            c.execute("SELECT id, ethereum_address FROM ethereum_address_pool WHERE assigned IS NULL ORDER BY id DESC LIMIT 1 ")
            row = c.fetchone()
            if row:
                c.execute("UPDATE ethereum_address_pool SET assigned=NOW() WHERE id=%s", (row[0],))
                self.db.commit()
                eth_address_id = row[0]
                eth_address = row[1]
                c.execute("SELECT COUNT(*) FROM ethereum_address_pool WHERE assigned IS NULL")
                row = c.fetchone()
                if row[0] < self.address_pool_min:
                    new_address_count = self.address_pool_max - row[0]
                    new_eth_addresses = self.get_new_addresses(new_address_count)
                    for each in new_eth_addresses:
                        c.execute("INSERT INTO ethereum_address_pool (ethereum_address) VALUES (%s);", (each,))
                    self.db.commit()
                return eth_address_id, eth_address
        except MySQLdb.Error as e:
            try:
                if self.logger:
                    self.logger.error("MySQL Error [%d]: %s" % (e.args[0], e.args[1]))
                else:
                    print("MySQL Error [%d]: %s" % (e.args[0], e.args[1]))
            except IndexError:
                if self.logger:
                    self.logger.error("MySQL Error: %s" % (str(e),))
                else:
                    print("MySQL Error [%d]: %s" % (e.args[0], e.args[1]))
        return None


if __name__ == "__main__":
    HELP = """python ethereum_node.py command argument
        
        add <node identifier(location name)>
        remove <node_id>
        list-nodes
        
        python ethereum_node.py add London
        python ethereum_node.py remove 2
        python ethereum_node.py list-nodes
"""
    if len(sys.argv) < 2:
        print(HELP)
    else:
        db = database.Database()
        command = sys.argv[1]
        if command == "add":
            api_key = db.add_ethereum_node(sys.argv[2])
            if api_key:
                print("API key of new node: " + api_key.decode())
        elif command == "remove":
            success = db.remove_ethereum_node(int(sys.argv[2]))
            if success:
                print("Successfully removed API key.")
            else:
                print("db.remove_ethereum_node reported failure, check config.json")
        elif command == "list-nodes":
            nodes = db.list_ethereum_nodes()
            pprint.pprint(nodes)
        else:
            print("Unknown command.\n\n")
            print(HELP)

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
import datetime
import os
import sys
import pprint
import re
import events

ETH_ADDRESS_REGEX = re.compile("^0x[0-9a-fA-F]{40}$")


def get_new_addresses(count):
    output = []
    for x in range(0, count):
        new_address = "0x"
        rng_out = os.urandom(20)
        new_address += rng_out.hex()
        output.append(new_address)
    return output


def generate_api_key():
    new_api_key = os.urandom(16).hex()
    return new_api_key


class EthereumNode:
    def __init__(self, ip_addr=None, logger=None, db=None):
        self.ip_addr = ip_addr
        self.logger = logger
        config_stream = open("config.json", "r")
        config_data = json.load(config_stream)
        config_stream.close()
        if db:
            if db.db:
                self.db = db.db
            else:
                self.db = db
        else:
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

    def get_id_for_ethereum_address(self, ethereum_address):
        try:
            c = self.db.cursor()
            c.execute("SELECT ethereum_address FROM ethereum_address_pool WHERE ethereum_address=%s;",
                      (ethereum_address,))
            row = c.fetchone()
            if row:
                return row[0]
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

    def add_ethereum_node(self, node_identifier):
        c = self.db.cursor()
        sql = "INSERT INTO ethereum_network (node_identifier,api_key) VALUES (%s,%s)"
        try:
            new_api_key = generate_api_key()
            result = c.execute(sql, (node_identifier, new_api_key))
            self.db.commit()
            if result == 1:
                return new_api_key
        except MySQLdb.Error as e:
            try:
                self.logger.error("MySQL Error [%d]: %s" % (e.args[0], e.args[1]))
            except IndexError:
                self.logger.error("MySQL Error: %s" % (str(e),))
        return None

    def get_address_pool(self):
        output = []
        try:
            c = self.db.cursor()
            c.execute("SELECT id, ethereum_address FROM ethereum_address_pool WHERE assigned IS NULL")
            for row in c:
                output.append((row[0], row[1]))
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

    def add_new_ethereum_address(self, new_address):
        self.logger.info("Adding new address {0} to Ethereum pool.".format(new_address))
        if not ETH_ADDRESS_REGEX.match(new_address):
            raise TypeError
        try:
            c = self.db.cursor()
            c.execute("INSERT INTO ethereum_address_pool (ethereum_address,assigned) VALUES (%s,NOW());",
                      (new_address,))
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
            sql = "SELECT id, ethereum_address FROM ethereum_address_pool"
            sql += " WHERE assigned IS NULL ORDER BY id DESC LIMIT 1;"
            c.execute(sql)
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
                    new_eth_addresses = get_new_addresses(new_address_count)
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

    def remove_ethereum_node(self, node_id):
        try:
            c = self.db.cursor()
            c.execute("DELETE FROM ethereum_network WHERE id=%s", (node_id,))
            self.db.commit()
            if c.rowcount == 1:
                return True
        except MySQLdb.Error as e:
            try:
                self.logger.error("MySQL Error [%d]: %s" % (e.args[0], e.args[1]))
            except IndexError:
                self.logger.error("MySQL Error: %s" % (str(e),))
        return False

    def list_ethereum_nodes(self):
        try:
            c = self.db.cursor()
            sql = "SELECT id,node_identifier,last_event_id,last_update,last_update_ip,api_key,status"
            sql += " FROM ethereum_network;"
            c.execute(sql)
            nodes = []
            for row in c:
                last_update = row[3]
                event_data = None
                if last_update:
                    update_event = events.Event("Ethereum Node Update", self.db, logger=self.logger)
                    event_data = update_event.get_latest_event(row[0])
                    new_node_data = dict(id=row[0],
                                         node_identifier=row[1],
                                         last_event_id=row[2],
                                         last_update=row[3],
                                         last_update_ip=row[4],
                                         api_key=row[5],
                                         status=row[6])
                if event_data:
                    try:
                        epoch = datetime.datetime.now() - datetime.timedelta(hours=24)
                        decoded_data = json.loads(event_data[0])
                        new_node_data["peers"] = decoded_data["peers"]
                        new_node_data["commands"] = events.Event("Ethereum Node Command Dispatch",
                                                                 self.db,
                                                                 logger=self.logger).get_event_count_since(epoch,
                                                                                                           new_node_data[
                                                                                                               "id"])
                    except json.JSONDecodeError as err:
                        self.logger.error("JSON Decoder Exception: {0}".format(err))
                nodes.append(new_node_data)
            return nodes
        except MySQLdb.Error as e:
            try:
                msg = "MySQL Error [{0}]: {1}".format(e.args[0], e.args[1])
                if self.logger:
                    self.logger.error(msg)
                else:
                    print(msg)
            except IndexError:
                msg = "MySQL Error: " + str(e)
                if self.logger:
                    self.logger.error(msg)
                else:
                    print(msg)
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
        eth_node_manager = EthereumNode()
        command = sys.argv[1]
        if command == "add":
            api_key = eth_node_manager.add_ethereum_node(sys.argv[2])
            if api_key:
                print("API key of new node: " + api_key.decode())
        elif command == "remove":
            success = eth_node_manager.remove_ethereum_node(int(sys.argv[2]))
            if success:
                print("Successfully removed API key.")
            else:
                print("db.remove_ethereum_node reported failure, check config.json")
        elif command == "list-nodes":
            nodes = eth_node_manager.list_ethereum_nodes()
            pprint.pprint(nodes)
        else:
            print("Unknown command.\n\n")
            print(HELP)

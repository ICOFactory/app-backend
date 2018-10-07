import MySQLdb
import random
import json


def random_eth_address():
    output = "0x"
    for x in range(0, 5):
        output += "%08x" % random.randint(0, 0xffffffff)
    return output


class EthereumNode():
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
                new_eth_addresses = self.get_new_addresses(new_address_count)
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

    def get_new_addresses(self, count):
        # TODO: actually get addresses from ETH node
        output = []
        for x in range(0, count):
            output.append(random_eth_address())
        return output


if __name__ == "__main__":
    eth_node = EthereumNode()
    unused_address_pool = eth_node.get_address_pool()
    print("Unallocated ETH address pool")
    for each in unused_address_pool:
        print("{0}\t{1}".format(each[0], each[1]))

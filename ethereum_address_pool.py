# ethereum_address_pool.py
#
# module to marshall ethereum address in and out of the address pool
# may change to a more suitable database in the long run,
# in the short run trying to reduce the size of the database module

import MySQLdb
import json
import re
import os

ETH_ADDRESS_REGEX = re.compile("^0x[0-9a-fA-F]{40}$")


def get_new_addresses(count):
    output = []
    for x in range(0, count):
        new_address = "0x"
        rng_out = os.urandom(20)
        new_address += rng_out.hex()
        output.append(new_address)
    return output


class EthAddressPoolStats:
    assigned: int
    duplicates: int
    total: int

    def __init__(self, total, assigned, duplicates):
        self.total = total
        self.assigned = assigned
        self.duplicates = duplicates

    def __str__(self):
        usage = float(self.assigned) / float(self.total) * 100.0
        duplicate_percent = (float(self.duplicates) / float(self.assigned)) * 100.0
        return "{0} assigned out of {1} total in pool. ({2}%%) {3} duplicates. ({4}%%)".format(self.assigned,
                                                                                               self.total,
                                                                                               usage,
                                                                                               self.duplicates,
                                                                                               self.assigned,
                                                                                               duplicate_percent)


class EthereumAddressPool:
    def __init__(self, db=None, logger=None):
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
            self.db = MySQLdb.connect(config_data["eth_address_pool"]["mysql_host"],
                                      config_data["eth_address_pool"]["mysql_user"],
                                      config_data["eth_address_pool"]["mysql_password"],
                                      config_data["eth_address_pool"]["mysql_database"])

        self.address_pool_min = config_data["eth_address_pool"]["eth_address_pool_min"]
        self.address_pool_max = config_data["eth_address_pool"]["eth_address_pool_max"]
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

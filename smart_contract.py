import MySQLdb
import json
from ethereum_node import EthereumNode
from ethereum_address_pool import EthereumAddressPool
from flask import render_template
import re

ETH_ADDRESS_REGEX = re.compile("^0x[0-9a-fA-F]{40}$")


def token_symbol_decorator(symbol):
    return " = \"" + symbol.upper() + "\""


class SmartContract:
    def __init__(self,
                 eth_address=None,
                 logger=None,
                 token_name=None,
                 token_count=-1,
                 token_symbol=None,
                 max_priority=10,
                 owner_id=None,
                 smart_token_id=None):
        self.tokens = token_count
        self.eth_node = EthereumNode()
        self.contract_address = eth_address
        self.smart_contract_id = -1
        self.max_priority = max_priority
        self.token_name = token_name
        self.token_symbol = token_symbol
        self.created = None
        self.logger = logger
        self.config_data = json.load(open("config.json", "r"))
        self.db = MySQLdb.connect(self.config_data["mysql_host"],
                                  self.config_data["mysql_user"],
                                  self.config_data["mysql_password"],
                                  self.config_data["mysql_database"])

        if token_name and token_count > 0 and token_symbol:
            try:
                c = self.db.cursor()
                token_count_string = "{0}".format(token_count)
                new_smart_contract = render_template("erc20_token.sol",
                                                     ico_name=token_name,
                                                     ico_symbol=token_symbol_decorator(token_symbol),
                                                     total_supply=token_count_string,
                                                     owner_id=None)
                sql = "INSERT INTO smart_contracts (token_name,tokens,max_priority,"
                sql += "solidity_source,token_symbol,owner_id) VALUES (%s,%s,%s,%s,%s,%s)"
                c.execute(sql,(self.token_name,
                               self.tokens,
                               self.max_priority,
                               new_smart_contract,
                               token_symbol,
                               owner_id))
                self.db.commit()
                new_row_id = c.lastrowid
                self.smart_contract_id = new_row_id
                self.solidity_code = new_smart_contract
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
        elif smart_token_id:
            try:
                c = self.db.cursor()
                sql = "SELECT id, token_name, tokens, max_priority, created, token_symbol, solidity_source FROM smart_contracts"
                sql += " WHERE id=%s"
                c.execute(sql, (smart_token_id,))
                inner_row = c.fetchone()
                if inner_row:
                    self.smart_contract_id = inner_row[0]
                    self.token_name = inner_row[1]
                    self.tokens = inner_row[2]
                    self.max_priority = inner_row[3]
                    self.created = inner_row[4]
                    self.token_symbol = inner_row[5]
                    self.solidity_code = inner_row[6]
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
        else:
            try:
                c = self.db.cursor()
                c.execute("SELECT id FROM ethereum_address_pool WHERE ethereum_address=%s", (eth_address,))
                row = c.fetchone()
                if row:
                    sql = "SELECT id, token_name, tokens, max_priority, created, token_symbol, solidity_source FROM smart_contracts"
                    sql += " WHERE eth_address=%s"
                    c.execute(sql, (row[0],))
                    inner_row = c.fetchone()
                    if inner_row:
                        self.smart_contract_id = inner_row[0]
                        self.token_name = inner_row[1]
                        self.tokens = inner_row[2]
                        self.max_priority = inner_row[3]
                        self.created = inner_row[4]
                        self.token_symbol = inner_row[5]
                        self.solidity_code = inner_row[6]
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

    def list_owned_tokens_for_user_id(self, user_id):
        output = []
        sql = "SELECT serial, ethereum_address_pool.ethereum_address, issued "
        sql += "FROM tokens LEFT JOIN ethereum_address_pool ON tokens.eth_address = ethereum_address_pool.id "
        sql += "WHERE smart_contract_id=%s AND owner_id=%s"
        try:
            c = self.db.cursor()
            c.execute(sql, (self.smart_contract_id,user_id))
            for row in c:
                output.append({"serial": row[0], "eth_address": row[1], "issued": row[2]})
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
        return output

    def set_contract_address(self, contract_address):
        eth_address_pool = EthereumAddressPool(self.db, self.logger)
        new_eth_address = eth_address_pool.add_new_ethereum_address(contract_address)
        if new_eth_address is None:
            return False
        try:
            c = self.db.cursor()
            c.execute("UPDATE smart_contracts SET eth_address=% WHERE id=%s",(new_eth_address,
                                                              self.smart_contract_id,))
            self.db.commit()
            return True
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
        return False

    def get_issued_token_count(self):
        try:
            c = self.db.cursor()
            c.execute("SELECT COUNT(*) FROM tokens WHERE smart_contract_id=%s AND issued IS NOT NULL;",
                      (self.smart_contract_id,))
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
        return 0

    def issue_token(self, token_address):
        if self.smart_contract_id > 0:
            if not ETH_ADDRESS_REGEX.match(token_address):
                raise ValueError
            try:
                c = self.db.cursor()
                c.execute("INSERT INTO tokens (eth_address,smart_contract_id) VALUES (%s,%s)",
                          (token_address, self.smart_contract_id))
                self.db.commit()
                c.close()
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

    def issue_tokens(self, tokens):
        if self.smart_contract_id > 0:
            try:
                c = self.db.cursor()
                for x in range(0, tokens):
                    eth_address = self.eth_node.assign_new_ethereum_address()
                    c.execute("INSERT INTO tokens (eth_address,smart_contract_id) VALUES (%s,%s);",
                              (eth_address, self.smart_contract_id))
                    command_data = {"issue-token": {"eth_address": eth_address,
                                                    "smart_contract_id": self.smart_contract_id}}
                    c.execute("INSERT INTO commands (command) VALUES (%s);", (json.dumps(command_data),))
                self.db.commit()
                c.close()
                return tokens
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
                return 0
        return -1

    def unassign_tokens_from_user_id(self, user_id, tokens):
        try:
            c = self.db.cursor()
            counter = 0
            c.execute("SELECT serial FROM tokens WHERE owner_id=%s AND smart_contract_id=%s LIMIT %s",
                      (user_id, self.smart_contract_id, tokens))
            for row in c:
                c.execute("UPDATE tokens SET owner_id=NULL WHERE serial=%s", (row[0],))
                c.execute("INSERT INTO transaction_ledger (token_id,sender_id,initiated_by) VALUES (%s,%s,%s)",
                          (row[0], user_id, user_id))
                counter += 1
            self.db.commit()
            c.close()
            return counter
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
        return 0

    def get_token_count_for_user_id(self, user_id):
        try:
            c = self.db.cursor()
            c.execute("SELECT COUNT(*) FROM tokens WHERE smart_contract_id=%s AND owner_id=%s",
                      (self.smart_contract_id, user_id))
            row = c.fetchone()
            c.close()
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
        return 0

    def assign_tokens_to_user_id(self,user_id,tokens):
        try:
            c = self.db.cursor()
            c.execute("SELECT user_id FROM users WHERE email_address='admin';")
            row = c.fetchone()
            admin_user_id = -1
            if row:
                admin_user_id = row[0]
            if admin_user_id > 0:
                assigned_tokens = 0
                c.execute("SELECT serial FROM tokens WHERE smart_contract_id=%s AND owner_id IS NULL LIMIT %s",
                          (self.smart_contract_id, tokens))
                for row in c:
                    token_id = row[0]
                    c.execute("UPDATE tokens SET owner_id=%s WHERE serial=%s;", (user_id, token_id,))
                    c.execute("INSERT INTO transaction_ledger (token_id,receiver_id,initiated_by) VALUES (%s,%s,%s)",
                              (token_id, user_id, admin_user_id))
                    assigned_tokens += 1
                c.close()
                self.db.commit()
                return assigned_tokens
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
        return 0

    def publish_smart_contract(self):
        if self.smart_contract_id > 0:
            sql = "UPDATE smart_contracts SET published=NOW() WHERE id=%s"
            try:
                c = self.db.cursor()
                c.execute(sql,(self.smart_contract_id,))
                self.db.commit()
                c.close()
                return True
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
        return False

    def get_unassigned_token_count(self):
        try:
            c = self.db.cursor()
            c.execute("SELECT COUNT(*) FROM tokens WHERE smart_contract_id=%s AND owner_id IS NULL",
                      (self.smart_contract_id,))
            row = c.fetchone()
            c.close()
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
        return 0

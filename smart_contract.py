import MySQLdb
import json
from ethereum_node import EthereumNode


class SmartContract:
    def __init__(self, eth_address=None, logger=None, token_name=None, token_count=-1, max_priority=10):
        self.tokens = token_count
        self.eth_node = EthereumNode()
        self.contract_address = eth_address
        self.smart_contract_id = -1
        self.max_priority = max_priority
        self.token_name = token_name
        self.created = None
        self.logger = logger
        self.config_data = json.load(open("config.json", "r"))
        self.db = MySQLdb.connect(self.config_data["mysql_host"],
                                  self.config_data["mysql_user"],
                                  self.config_data["mysql_password"],
                                  self.config_data["mysql_database"])

        if token_name and token_count > 0:
            try:
                c = self.db.cursor()
                new_eth_address = self.eth_node.assign_new_ethereum_address()
                c.execute(
                    "INSERT INTO smart_contracts (token_name,tokens,max_priority,eth_address) VALUES (%s,%s,%s,%s)",
                          (self.token_name, self.tokens, self.max_priority, new_eth_address[0]))
                self.db.commit()
                new_row_id = c.lastrowid
                self.smart_contract_id = new_row_id
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
        else:
            try:
                c = self.db.cursor()
                c.execute("SELECT id FROM ethereum_address_pool WHERE ethereum_address=%s", (eth_address,))
                row = c.fetchone()
                if row:
                    sql = "SELECT id, token_name, tokens, max_priority, created FROM smart_contracts WHERE eth_address=%s"
                    c.execute(sql, (row[0],))
                    inner_row = c.fetchone()
                    if inner_row:
                        self.smart_contract_id = inner_row[0]
                        self.token_name = inner_row[1]
                        self.tokens = inner_row[2]
                        self.max_priority = inner_row[3]
                        self.created = inner_row[4]
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

    def issue_tokens(self, tokens):
        if self.smart_contract_id > 0:
            try:
                # TODO: add commands to issue tokens
                c = self.db.cursor()
                for x in range(0, tokens):
                    eth_address = self.eth_node.assign_new_ethereum_address()
                    c.execute("INSERT INTO tokens (eth_address,smart_contract_id) VALUES (%s,%s)",
                              (eth_address[0], self.smart_contract_id))
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
                c.execute("INSERT INTO transaction_ledger (token_id,sender_id,initiated_by)",
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

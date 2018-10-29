# MySQLdb layer interface
#
# To install database, run the optimized_database_schema on a new
# database, change config.json values to match your MySQL configuration,
# and finally run this script from the command line to create the admin superuser
import MySQLdb
from hashlib import sha256
import re
import json
import binascii
import os

UUID_REGEX = re.compile("[A-Fa-f0-9]{8}-[A-Fa-f0-9]{4}-[A-Fa-f0-9]{4}-[A-Fa-f0-9]{4}-[A-Fa-f0-9]{12}")


def random_token():
    new_session_token = binascii.hexlify(os.urandom(8))
    return new_session_token


def generate_api_key():
    new_api_key = binascii.hexlify(os.urandom(16))
    return new_api_key


class Database:
    # I really hate using ENUMs
    ETH_NODE_STATUS_UNKNOWN = 'Unknown'
    ETH_NODE_STATUS_SYNCING = 'Syncing'
    ETH_NODE_STATUS_SYNCED = "Synchronized"
    ETH_NODE_STATUS_RESTART = "Restarting"
    ETH_NODE_STATUS_ERROR = "Error"
    ETH_NODE_VALID_STATES = [ETH_NODE_STATUS_UNKNOWN,
                             ETH_NODE_STATUS_SYNCING,
                             ETH_NODE_STATUS_SYNCED,
                             ETH_NODE_STATUS_RESTART,
                             ETH_NODE_STATUS_ERROR]

    def __init__(self):
        config_stream = open("config.json", "r")
        config_data = json.load(config_stream)
        config_stream.close()
        db_host = config_data['mysql_host']
        db_username = config_data['mysql_user']
        db_password = config_data['mysql_password']
        db_name = config_data['mysql_database']
        self.db = MySQLdb.connect(db_host, db_username, db_password, db_name)
        self.logger = None

    def validate_permission(self, user_id, permission, smart_contract_id=None):
        # TODO: query access control lists
        try:
            c = self.db.cursor()
            if smart_contract_id:
                sql = "SELECT * FROM access_control_list WHERE user_id=%s AND permission=%s AND smart_contract_id=%s"
                c.execute(sql, (user_id, permission, smart_contract_id))
                row = c.fetchone()
                if row:
                    return True
            else:
                sql = "SELECT * FROM access_control_list WHERE user_id=%s AND permission=%s"
                c.execute(sql, (user_id, permission))
                row = c.fetchone()
                if row:
                    return True
        except MySQLdb.Error as e:
            try:
                error_message = "MySQL Error [%d]: %s" % (e.args[0], e.args[1])
            except IndexError:
                error_message = "MySQL Error: %s" % (str(e),)

            if self.logger:
                self.logger.error(error_message)
            else:
                print(error_message)
        # TODO: return false if permission not found
        return True

    def update_user_permissions(self, user_id, acl_data_json):
        acl_data = json.loads(acl_data_json)
        new_admin_permissions = []
        if type(acl_data) == dict:
            if "administrator" in acl_data:
                for every_admin_permission in acl_data["administrator"]:
                    new_admin_permissions.append(every_admin_permission)
            else:
                return False
        else:
            return False
        try:
            c = self.db.cursor()
            c.execute("UPDATE users SET json_metadata=%s WHERE user_id=%s",(acl_data_json, user_id))
            if c.rowcount == 1:
                # flush old permissions
                c.execute("DELETE FROM access_control_list WHERE user_id=%s")
                # insert new admin permissions
                for each in new_admin_permissions:
                    c.execute("INSERT INTO access_control_list (user_id,permission) VALUES (%s,%s);",each[0],each[1])
                self.db.commit()
                return True
        except MySQLdb.Error as e:
            try:
                error_message = "MySQL Error [%d]: %s" % (e.args[0], e.args[1])
            except IndexError:
                error_message = "MySQL Error: %s" % (str(e),)

            if self.logger:
                self.logger.error(error_message)
            else:
                print(error_message)
        return False

    def list_permissions(self, user_id, smart_contract_id=None):
        try:
            c = self.db.cursor()
            output = ["view-event-log"]
            if smart_contract_id:
                sql = "SELECT permission FROM access_control_list WHERE user_id=%s AND smart_contract_id=%s"
                c.execute(sql, (user_id, smart_contract_id))
            else:
                sql = "SELECT permission FROM access_control_list WHERE user_id=%s"
                c.execute(sql, (user_id,))
            for row in c:
                output.append(row[0])
            return output
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

    def get_latest_events(self, event_type_id, limit):
        try:
            c = self.db.cursor()
            output = []
            sql = """SELECT event_id,full_name,email_address,event_log.user_id,event_log.json_metadata,event_log.created
 FROM event_log LEFT JOIN users ON users.user_id=event_log.user_id WHERE event_type_id=%s 
 ORDER BY event_id DESC LIMIT %s"""
            c.execute(sql, (event_type_id, limit))
            for row in c:
                output.append({"event_id": row[0],
                               "full_name": row[1],
                               "email_address": row[2],
                               "user_id": row[3],
                               "event_data": row[4],
                               "event_created": row[5]})
            return output
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

    def list_event_types(self):
        try:
            c = self.db.cursor()
            output = []
            c.execute("SELECT event_type_id,event_type FROM event_type;")
            for row in c:
                output.append({"event_type_id": row[0],
                               "event_type_name": row[1]})
            return output
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

    def validate_api_key(self, api_key):
        try:
            c = self.db.cursor()
            c.execute("SELECT id FROM ethereum_network WHERE api_key=%s", (api_key,))
            row = c.fetchone()
            if row:
                return row[0]
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

    def get_pending_commands(self,node_id):
        try:
            c = self.db.cursor()
            c.execute("SELECT COUNT(*) FROM commands WHERE dispatch_event_id IS NULL AND node_id is NULL")
            row = c.fetchone()
            undirected_commands = -1
            if row:
                undirected_commands = row[0]
            c.execute("SELECT COUNT(*) FROM commands WHERE dispatch_event_id IS NULL AND node_id=%s",node_id)
            directed_commands = -1
            if row:
                directed_commands = row[0]
            return undirected_commands, directed_commands
        except MySQLdb.Error as e:
            try:
                self.logger.error("MySQL Error [%d]: %s" % (e.args[0], e.args[1]))
            except IndexError:
                self.logger.error("MySQL Error: %s" % (str(e),))
        return None

    def remove_ethereum_node(self,node_id):
        try:
            c = self.db.cursor()
            c.execute("DELETE FROM ethereum_network WHERE id=%s",(node_id,))
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
        c = self.db.cursor()
        sql = "SELECT id,node_identifier,last_event_id,last_update,last_update_ip,api_key,status"
        sql += " FROM ethereum_network;"
        c.execute(sql)
        nodes = []
        for row in c:
            last_update = row[3]
            if last_update:
                last_update = last_update.isoformat()
            nodes.append(dict(id=row[0],
                              node_identifier=row[1],
                              last_event_id=row[2],
                              last_update=last_update,
                              last_update_ip=row[4],
                              api_key=row[5],
                              status=row[6]))
        return nodes

    def update_ethereum_node_status(self, node_id, ip_addr, event_id, status):
        if status not in self.ETH_NODE_VALID_STATES:
            return False
        try:
            c = self.db.cursor()
            sql = "UPDATE ethereum_network SET status=%s,last_event_id=%s,last_update_ip=%s,last_update=NOW() WHERE id=%s"
            c.execute(sql, (status, event_id, ip_addr, node_id))
            if c.rowcount == 1:
                self.db.commit()
                return True
        except MySQLdb.Error as e:
            try:
                self.logger.error("MySQL Error [%d]: %s" % (e.args[0], e.args[1]))
            except IndexError:
                self.logger.error("MySQL Error: %s" % (str(e),))
        return False

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

    def fetch_commands(self, device_id):
        c = self.db.cursor()
        device_id_param = int(device_id)
        sql = "SELECT command_id, node_id, command, created FROM commands WHERE node_id=%s"
        commands = []
        c.execute(sql, (device_id_param,))
        for row in c:
            commands.append((row[0], row[2], row[3].isoformat()))
        for each in commands:
            sql = "DELETE FROM commands WHERE command_id={0}".format(each[0])
            c.execute(sql)
        c.close()
        self.db.commit()
        return commands

    def get_smart_contracts(self, user_id):
        # TODO: where user_id = owner
        sql = "SELECT smart_contracts.id,token_name,tokens,smart_contracts.created,max_priority,ethereum_address_pool."
        sql += "ethereum_address,token_symbol,owner_id FROM smart_contracts LEFT JOIN ethereum_address_pool "
        sql += "ON eth_address=ethereum_address_pool.id;"
        try:
            c = self.db.cursor()
            c.execute(sql)
            output = []
            for row in c:
                output.append({
                    "token_id": row[0],
                    "token_name": row[1],
                    "tokens": row[2],
                    "created": row[3].isoformat(),
                    "max_priority": row[4],
                    "eth_address": row[5],
                    "token_symbol": row[6],
                    "owner_id": row[7]
                })
            c.close()
            return output
        except MySQLdb.Error as e:
            try:
                self.logger.error("MySQL Error [%d]: %s" % (e.args[0], e.args[1]))
            except IndexError:
                self.logger.error("MySQL Error: %s" % (str(e),))
        return None

    def get_user_info(self, user_id):
        c = self.db.cursor()
        sql = "SELECT email_address,last_logged_in,last_logged_in_ip,created,created_ip,json_metadata,full_name,user_id"
        sql += " FROM users WHERE user_id=%s"
        c.execute(sql, (user_id,))
        row = c.fetchone()
        if row:
            user_info = {"email_address": row[0],
                         "last_logged_in": row[1],
                         "last_logged_in_ip": row[2],
                         "created": row[3],
                         "created_ip": row[4],
                         "json_metadata": row[5],
                         "full_name": row[6],
                         "user_id": row[7]}
            return user_info
        return None

    def get_next_directed_command(self, node_id):
        sql = "SELECT command_id, command FROM commands WHERE dispatch_event_id IS NULL AND node_id=%s "
        sql += "ORDER BY created DESC LIMIT 1;"
        # no table lock since we're only looking for one node's command
        try:
            c = self.db.cursor()
            c.execute(sql, (node_id,))
            row = c.fetchone()
            return row
        except MySQLdb.Error as e:
            try:
                self.logger.error("MySQL Error [%d]: %s" % (e.args[0], e.args[1]))
            except IndexError:
                self.logger.error("MySQL Error: %s" % (str(e),))
        return None

    def dispatch_directed_command(self, command_id, new_event_id):
        sql = "UPDATE commands SET dispatch_event_id=%s WHERE command_id=%s"
        try:
            c = self.db.cursor()
            c.execute(sql, (new_event_id, command_id))
            self.db.commit()
            if c.rowcount == 1:
                return True
        except MySQLdb.Error as e:
            try:
                self.logger.error("MySQL Error [%d]: %s" % (e.args[0], e.args[1]))
            except IndexError:
                self.logger.error("MySQL Error: %s" % (str(e),))
        return False

    def post_command(self, node_id, command_data):
        c = self.db.cursor()
        command_param = self.db.escape_string(command_data).decode('utf-8')

        try:
            if node_id:
                sql = "INSERT INTO commands (node_id,command) VALUES (%s,%s);"
                c.execute(sql, (node_id, command_param,))
            else:
                sql = "INSERT INTO commands (command) VALUES (%s);"
                c.execute(sql, (command_param,))
            last_row_id = c.lastrowid
            self.db.commit()
            return last_row_id
        except MySQLdb.Error as e:
            try:
                self.logger.error("MySQL Error [%d]: %s" % (e.args[0], e.args[1]))
            except IndexError:
                self.logger.error("MySQL Error: %s" % (str(e),))
            return -1
    
    def get_frame(self, device_id, offset):
        device_id_param = int(device_id)
        offset_param = int(offset)
        sql = "SELECT frame_id,created,metadata FROM frames WHERE device_id=%s ORDER BY frame_id ASC LIMIT 1 OFFSET %s;"
        c = self.db.cursor()
        c.execute(sql, (device_id_param,offset_param))
        return c.fetchone()
    
    def last_frame(self, device_id):
        device_id_param = int(device_id)
        sql = "SELECT frame_id,created,metadata FROM frames WHERE device_id={0} ORDER BY frame_id DESC LIMIT 1".format(device_id_param)
        c = self.db.cursor()
        c.execute(sql)
        return c.fetchone()
    
    def frame_count(self, device_id):
        device_id_param = int(device_id)
        sql = "SELECT COUNT(*) FROM frames WHERE device_id=%s"
        c = self.db.cursor()
        c.execute(sql, (device_id_param,))
        row = c.fetchone()
        if row:
            return row[0]
        return 0
    
    def add_frame(self, device_id, json_string):
        device_id_param = int(device_id)
        escaped_string = self.db.escape_string(json_string)
        sql = "INSERT INTO frames (device_id,metadata) VALUES ({0},'{1}')".format(device_id_param,escaped_string.decode('utf-8'))
        c = self.db.cursor()
        try:
            c.execute(sql)
            last_row_id = c.lastrowid
            c.close()
            self.db.commit()
            return last_row_id
        except MySQLdb.Error as e:
            return -1

    def device_info(self, uuid):
        if UUID_REGEX.match(uuid):
            uuid_param = uuid.upper()
            sql = "SELECT device_id, owner_id FROM devices WHERE uuid='{0}'".format(uuid_param)
            c = self.db.cursor()
            c.execute(sql)
            row = c.fetchone()
            if row:
                return row[0], row[1]
            return None

    def list_devices(self, user_id):
        c = self.db.cursor()
        user_id_param = int(user_id)
        sql = "SELECT device_id,uuid FROM devices WHERE owner_id={0};".format(user_id_param)
        try:
            output = []
            c.execute(sql)
            for each in c:
                output.append((each[0],each[1]))
            return output
        except MySQLdb.Error as e:
            pass
        return None

    def list_users(self):
        c = self.db.cursor()
        try:
            output = []
            c.execute("SELECT user_id,email_address,last_logged_in,last_logged_in_ip,created,created_ip FROM users")
            for row in c:
                output.append({"user_id": row[0],
                               "email": row[1],
                               "last_logged_in": row[2],
                               "last_logged_in_ip": row[3],
                               "created": row[4],
                               "created_ip": row[5]})
            c.close()
            return output
        except MySQLdb.Error as e:
            try:
                self.logger.error("MySQL Error [%d]: %s" % (e.args[0], e.args[1]))
            except IndexError:
                self.logger.error("MySQL Error: %s" % (str(e),))
            c.close()
            return None

    def add_device(self, user_id, uuid):
        c = self.db.cursor()
        if UUID_REGEX.match(uuid):
            uuid_param = uuid.upper()
            try:
                if user_id:
                    user_id_param = int(user_id)
                    c.execute("INSERT INTO devices (owner_id,uuid) VALUES (%s,%s);", (user_id_param,uuid_param))
                else:
                    c.execute("INSERT INTO devices (uuid) VALUES (%s);", (uuid_param,))
                last_row_id = c.lastrowid
                c.close()
                self.db.commit()
                return last_row_id
            except MySQLdb.Error as e:
                try:
                    self.logger.error("MySQL Error [%d]: %s" % (e.args[0], e.args[1]))
                except IndexError:
                    self.logger.error("MySQL Error: %s" % (str(e),))
                c.close()
                return -3
        else:
            self.logger.error("UUID regex check did not match.")
            return -2

    def verify_session(self, user_id, session_id):
        c = self.db.cursor()
        user_id_param = int(user_id)
        sql = "SELECT session_token FROM users WHERE user_id={0}".format(user_id_param)
        c.execute(sql)
        row = c.fetchone()
        if row:
            if row[0] == session_id:
                return True
        return False

    def validate_session(self, session_id):
        c = self.db.cursor()
        c.execute("SELECT user_id FROM users WHERE session_token=%s", (session_id,))
        row = c.fetchone()
        if row:
            return row[0]
        return None

    def reset_password(self, user_id, password):
        c = self.db.cursor()
        c.execute("SELECT email_address FROM users WHERE user_id=%s", (user_id,))
        row = c.fetchone()
        if row:
            combined_pw = row[0] + password
            passwd_hash = sha256(combined_pw)
            result = c.execute("UPDATE users SET password=%s WHERE user_id=%s", (passwd_hash.hexdigest(), user_id))
            if result > 0:
                return True
        return False

    def login(self, email_address, password, ip_addr):
        c = self.db.cursor()
        email_param = self.db.escape_string(email_address)
        try:
            c.execute("SELECT user_id, email_address, password FROM users WHERE email_address=%s;", (email_param.decode('utf-8'),))
            row = c.fetchone()
            if row:
                data = email_address + password
                pw_hash = sha256(data.encode("utf-8"))
                if pw_hash.hexdigest() == row[2]:
                    new_session_token = random_token()
                    sql = "UPDATE users SET session_token=%s,last_logged_in=NOW(),last_logged_in_ip=%s WHERE user_id=%s"
                    if c.execute(sql, (new_session_token, ip_addr, row[0])) == 1:
                        c.close()
                        self.db.commit()
                        return row[0], new_session_token
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
                    print("MySQL Error: %s" % (str(e),))
            return None
        return None

    def create_user(self, full_name, email_address, password, ip_addr):
        c = self.db.cursor()
        data = email_address + password
        pw_hash = sha256(data.encode("utf-8"))
        digest = pw_hash.hexdigest()
        new_session_token = random_token()
        email_param = self.db.escape_string(email_address).decode('utf-8')
        sql = "INSERT INTO users (email_address,password,session_token,created_ip,created,full_name) VALUES (%s,%s,%s,%s,NOW(),%s);"
        try:
            c.execute(sql, (email_param, digest, new_session_token,ip_addr,full_name))
            last_row_id = c.lastrowid
            c.close()
            self.db.commit()
        except MySQLdb.Error as e:
            try:
                if e.args[0] == 1062:
                    return -1, "E-mail address already exists in database!"
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
        return last_row_id, new_session_token

    def view_wallet(self,user_id):
        try:
            c = self.db.cursor()
            sql = "SELECT serial,ethereum_address_pool.ethereum_address,issued,smart_contract_id FROM tokens "
            sql += " LEFT JOIN ethereum_address_pool ON ethereum_address_pool.id=tokens.eth_address WHERE owner_id=%s"
            c.execute(sql,(user_id,))
            all_tokens = []
            for row in c:
                all_tokens.append({"token_serial": row[0],
                                   "token_eth_address": row[1],
                                   "token_issued": row[2].isoformat(),
                                   "smart_contract_id": row[3]})
            sql = "SELECT txid,sender_id,receiver_id,initiated_by,timestamp FROM transaction_ledger WHERE token_id=%s"
            for every_token in all_tokens:
                c.execute(sql, (every_token["token_serial"],))
                every_token["transactions"] = []
                for row in c:
                    every_token["transactions"].append({"txid": row[0],
                                                        "sender_id": row[1],
                                                        "receiver_id": row[2],
                                                        "initiated_by": row[3],
                                                        "timestamp": row[4].isoformat()})
            return all_tokens
        except MySQLdb.Error as e:
            try:
                if e.args[0] == 1062:
                    return -1, "E-mail address already exists in database!"
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
    db = Database()
    print("Creating admin user...")
    raw_password = input("Admin password: ")
    result = db.create_user("Administrator", "admin", raw_password, None)
    if result:
        print("Admin user created successfully.")
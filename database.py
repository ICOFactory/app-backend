# MySQLdb layer interface
import MySQLdb
from hashlib import sha256
import random
import re
import json

UUID_REGEX = re.compile("[A-Fa-f0-9]{8}-[A-Fa-f0-9]{4}-[A-Fa-f0-9]{4}-[A-Fa-f0-9]{4}-[A-Fa-f0-9]{12}")


def random_token():
    new_session_token = "%08x%08x" % (random.randint(0, 0xffffffff), random.randint(0, 0xffffffff))
    return new_session_token


MYSQL_HOST = "localhost"
MYSQL_USERNAME = "root"
MYSQL_PASSWORD = ""
MYSQL_DATABASE_NAME = "service"


class Database:
    def __init__(self, host=MYSQL_HOST, username=MYSQL_USERNAME, password=MYSQL_PASSWORD, database=MYSQL_DATABASE_NAME):
        config_data = json.load(open("config.json","r"))
        if host:
            db_host = host
        else:
            db_host = config_data['mysql_host']
        if username:
            db_username = username
        else:
            db_username = config_data['mysql_username']
        if password:
            db_password = password
        else:
            db_password = config_data['mysql_password']
        if database:
            db_name = database
        else:
            db_name = config_data['mysql_database']
        self.db = MySQLdb.connect(db_host, db_username, db_password, db_name)
        self.logger = None
        
    def fetch_commands(self, device_id):
        c = self.db.cursor()
        device_id_param = int(device_id)
        sql = "SELECT command_id, device_id, command, created FROM commands WHERE device_id=%s"
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

    def get_user_info(self, user_id):
        c = self.db.cursor()
        sql = "SELECT email_address,last_logged_in,last_logged_in_ip,created,created_ip,json_metadata,full_name FROM users WHERE user_id=%s"
        c.execute(sql, (user_id,))
        row = c.fetchone()
        if row:
            user_info = {"email_address": row[0],
                       "last_logged_in": row[1],
                        "last_logged_in_ip": row[2],
                        "created": row[3],
                        "created_ip": row[4],
                        "json_metadata": row[5],
                        "full_name":row[6]}
            return user_info
        return None

    def post_command(self, device_id, command_data):
        c = self.db.cursor()
        device_id_param = int(device_id)
        command_param = self.db.escape_string(command_data).decode('utf-8')
        sql = "INSERT INTO commands (device_id,command) VALUES ({0},'{1}');".format(device_id_param,command_param)
        try:
            c.execute(sql)
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

    def count_glosspoints(self, user_id):
        sql = "SELECT COUNT(*) FROM tokens WHERE owner_id=%s"
        c = self.db.cursor()
        try:
            c.execute(sql,(user_id,))
            row = c.fetchone()
            c.close()
            return row[0]
        except MySQLdb.Error as e:
            try:
                self.logger.error("MySQL Error [%d]: %s" % (e.args[0], e.args[1]))
            except IndexError:
                self.logger.error("MySQL Error: %s" % (str(e),))
            return 0
    
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
                output.append({"user_id":row[0],
                               "email":row[1],
                               "last_logged_in":row[2],
                               "last_logged_in_ip":row[3],
                               "created":row[4],
                               "created_ip":row[5]})
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
                    if c.execute(sql, (new_session_token,ip_addr,row[0])) == 1:
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
        sql = "INSERT INTO users (email_address,password,session_token,created_ip,created) VALUES (%s,%s,%s,%s,NOW(),full_name);"
        try:
            c.execute(sql, (email_param, digest, new_session_token,ip_addr))
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


if __name__ == "__main__":
    db = Database(MYSQL_HOST, MYSQL_USERNAME, MYSQL_PASSWORD, MYSQL_DATABASE_NAME)
    print("Creating admin user...")
    raw_password = input("Admin password: ")
    result = db.create_user("Administrator", "admin", raw_password, None)
    if result:
        print("Admin user created successfully.")
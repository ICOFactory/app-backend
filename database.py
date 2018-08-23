# MySQLdb layer interface
import MySQLdb
from hashlib import sha256
import random
import re

UUID_REGEX = re.compile("[A-Fa-f0-9]{8}-[A-Fa-f0-9]{4}-[A-Fa-f0-9]{4}-[A-Fa-f0-9]{4}-[A-Fa-f0-9]{12}")


def random_token():
    new_session_token = "%08x%08x" % (random.randint(0,0xffffffff),random.randint(0,0xffffffff))
    return new_session_token

MYSQL_HOST = "localhost"
MYSQL_USERNAME = "root"
MYSQL_PASSWORD = ""
MYSQL_DATABASE_NAME = "service"

class Database():
    def __init__(self,host=MYSQL_HOST,username=MYSQL_USERNAME,password=MYSQL_PASSWORD,database=MYSQL_DATABASE_NAME):
        self.db = MySQLdb.connect(host,username,password,database)
        
    def fetch_commands(self,device_id):
        c = self.db.cursor()
        device_id_param = int(device_id)
        sql = "SELECT command_id, device_id, command, created FROM commands WHERE device_id={0}".format(device_id)
        commands = []
        c.execute(sql)
        for row in c:
            commands.append((row[0],row[2],row[3].isoformat()))
        for each in commands:
            sql = "DELETE FROM commands WHERE command_id={0}".format(each[0])
            c.execute(sql)
        c.close()
        self.db.commit()
        return commands
            
        
    def post_command(self,device_id,command_data):
        c = self.db.cursor()
        device_id_param = int(device_id)
        command_param = self.db.escape_string(command_data).decode('utf-8')
        sql = "INSERT INTO commands (device_id,command) VALUES ({0},'{1}');".format(device_id_param,command_param)
        try:
            c.execute(sql)
            last_row_id = c.lastrowid
            self.db.commit()
            return last_row_id
        except:
            return -1
    
    def get_frame(self,device_id,offset):
        device_id_param = int(device_id)
        offset_param = int(offset)
        sql = "SELECT frame_id,created,metadata FROM frames ORDER BY frame_id ASC LIMIT 1 OFFSET {0};".format(offset_param)
        c = self.db.cursor()
        c.execute(sql)
        return c.fetchone()
    
    def last_frame(self,device_id):
        device_id_param = int(device_id)
        sql = "SELECT frame_id,created,metadata FROM frames WHERE device_id={0} ORDER BY frame_id DESC LIMIT 1".format(device_id_param)
        c = self.db.cursor()
        c.execute(sql)
        return c.fetchone()
    
    def frame_count(self,device_id):
        device_id_param = int(device_id)
        sql = "SELECT COUNT(*) FROM frames WHERE device_id={0}".format(device_id_param)
        c = self.db.cursor()
        c.execute(sql)
        row = c.fetchone()
        if row:
            return row[0]
        return 0
    
    def add_frame(self,device_id,json_string):
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
        except:
            return -1
    
    def device_info(self,uuid):
        if UUID_REGEX.match(uuid):
            uuid_param = uuid.upper()
            sql = "SELECT device_id, owner_id FROM devices WHERE uuid='{0}'".format(uuid_param)
            c = self.db.cursor()
            c.execute(sql)
            row = c.fetchone()
            if row:
                return (row[0],row[1])
            return None

    def list_devices(self,user_id):
        c = self.db.cursor()
        user_id_param = int(user_id)
        sql = "SELECT device_id,uuid FROM devices WHERE owner_id={0};".format(user_id_param)
        try:
            output = []
            c.execute(sql)
            for each in c:
                output.append((each[0],each[1]))
            return output
        except:
            pass
        return None

    def add_device(self,user_id,uuid):
        c = self.db.cursor()
        user_id_param = int(user_id)
        if UUID_REGEX.match(uuid):
            uuid_param = uuid.upper()
            sql = "INSERT INTO devices (owner,uuid) VALUES ({0},'{1}');".format(user_id_param,uuid_param)
            try:
                c.execute(sql)
                last_row_id = c.lastrowid
                c.close()
                self.db.commit()
                return last_row_id
            except:
                return -3
        else:
            return -2

    def verify_session(self,user_id,session_id):
        c = self.db.cursor()
        user_id_param = int(user_id)
        sql = "SELECT session_token FROM users WHERE user_id={0}".format(user_id_param)
        c.execute(sql)
        row = c.fetchone()
        if row:
            if row[0] == session_id:
                return True
        return False

    def login(self,email_address,password):
        c = self.db.cursor()
        email_param = self.db.escape_string(email_address)
        sql = "SELECT user_id, email_address, password FROM users WHERE email_address='%s';" % email_param.decode('utf-8')
        row = c.execute(sql)
        row = c.fetchone()
        if row:
            data = email_address + password
            pw_hash = sha256(data.encode("utf-8"))
            if pw_hash.hexdigest() == row[2]:
                new_session_token = random_token()
                sql = "UPDATE users SET session_token='{0}' WHERE user_id={1}".format(new_session_token,row[0])
                if c.execute(sql) == 1:
                    c.close()
                    self.db.commit()
                    return (row[0],new_session_token)
        return None

    def create_user(self,email_address,password):
        c = self.db.cursor()
        data = email_address + password
        pw_hash = sha256(data.encode("utf-8"))
        digest = pw_hash.hexdigest()
        new_session_token = random_token()
        email_param = self.db.escape_string(email_address).decode('utf-8')
        sql = "INSERT INTO users (email_address,password,session_token) VALUES ('%s','%s','%s');" % (email_param,digest,new_session_token)
        try:
            c.execute(sql)
            last_row_id = c.lastrowid
            c.close()
            self.db.commit()
        except MySQLdb.Error as e:
            try:
                if e.args[0] == 1062:
                    return (-1,"E-mail address already exists in database!")
                print("MySQL Error [%d]: %s" % (e.args[0],e.args[1]))
            except IndexError:
                print("MySQL Error: %s" % (str(e),))
            return None
        return (last_row_id,new_session_token)

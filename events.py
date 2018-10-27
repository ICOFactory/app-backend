import MySQLdb
import json


class InvalidEventException(Exception):
    def __init__(self, event_type):
        self.message = "{0} not found in list of available events".format(event_type)


class Event:
    AVAILABLE_EVENTS = ["Ethereum Node Update",
                        "Ethereum Node Command Dispatch",
                        "Ethereum Node Command Output",
                        "Users Create User",
                        "Users Reset Password",
                        "Users Changed Permissions",
                        "Users Assigned Tokens",
                        "Users Removed Tokens",
                        "Users Issued Credits",
                        "Users Purchased Credits",
                        "ERC20 Token Created",
                        "ERC20 Token Mined",
                        "ERC20 Token Premined",
                        "ERC20 Token Burned",
                        "ERC20 Token Issue",
                        "ERC20 Token External Transfer"]

    def __init__(self, event_type, db, logger=None):
        if event_type in AVAILABLE_EVENTS:
            raise InvalidEventException(event_type)
        self.db = db
        self.logger = logger
        # if no logger specified, use the db's logger if available
        # this is always the same flask app logger passed around from
        # the request
        if self.logger is None and self.db.logger:
            self.logger = self.db.logger
        try:
            c = self.db.cursor()
            c.execute("SELECT event_type_id FROM event_type WHERE event_type=%s;",(self.EVENT_TYPE_STRING,))
            row = c.fetchone()
            if not row:
                c.execute("INSERT INTO event_type (event_type) VALUES (%s)",(self.EVENT_TYPE_STRING,))
                self.db.commit()
                self.event_type_id = c.lastrowid
            else:
                self.event_type_id = row[0]
        except MySQLdb.Error as e:
            try:
                error_message = "MySQL Error [%d]: %s" % (e.args[0], e.args[1])
            except IndexError:
                error_message = "MySQL Error: %s" % (str(e),)

            if self.logger:
                self.logger.error(error_message)
            else:
                print(error_message)

    def get_latest_event(self,user_id=None):
        if self.event_type_id < 1:
            return None
        try:
            if user_id:
                sql = "SELECT json_metadata,created FROM event_log WHERE event_type_id=%s AND user_id=%s;"
                c.execute(sql,(self.event_type_id,user_id))
            else:
                sql = "SELECT json_metadata,created FROM event_log WHERE event_type_id=%s"
                c.execute(sql,(self.event_type_id,))
            row = c.fetchone()
            return row
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

    def log_event(self, user_id, metadata):
        if self.event_type_id > 0:
            if type(metadata) is not str:
                metadata = json.dumps(metadata)
            c = self.db.cursor()
            sql = "INSERT INTO event_log (event_type_id, user_id, json_metadata) VALUES (%s,%s,%s)"
            try:
                c.execute(sql, (self.event_type_id, user_id, metadata))
                last_row_id = c.lastrowid
                self.db.commit()
                c.close()
                return last_row_id
            except MySQLdb.Error as e:
                try:
                    error_message = "MySQL Error [%d]: %s" % (e.args[0], e.args[1])
                except IndexError:
                    error_message = "MySQL Error: %s" % (str(e),)

                if self.logger:
                    self.logger.error(error_message)
                else:
                    print(error_message)
        return -1

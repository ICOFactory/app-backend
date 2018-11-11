import MySQLdb
import json
import datetime


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
                        "Users Debit Credits",
                        "Users Purchased Credits",
                        "ERC20 Token Created",
                        "ERC20 Token Mined",
                        "ERC20 Token Premined",
                        "ERC20 Token Burned",
                        "ERC20 Token Issue",
                        "ERC20 Token External Transfer"]

    def __init__(self, event_type, db, logger=None):
        if event_type not in self.AVAILABLE_EVENTS:
            raise InvalidEventException(event_type)
        self.db = db.db
        self.logger = logger
        self.event_type = event_type

        try:
            c = self.db.cursor()
            c.execute("SELECT event_type_id FROM event_type WHERE event_type=%s;",(event_type,))
            row = c.fetchone()
            if not row:
                c.execute("INSERT INTO event_type (event_type) VALUES (%s)",(event_type,))
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

    def get_event_count(self,user_id=None):
        if self.event_type_id < 1:
            raise InvalidEventException
        if user_id and type(user_id) is not int:
            raise TypeError
        try:
            c = self.db.cursor()
            if user_id:
                sql = "SELECT COUNT(*) FROM event_log WHERE event_type_id=%s AND user_id=%s;"
                c.execute(sql, (self.event_type_id, user_id))
            else:
                sql = "SELECT COUNT(*) FROM event_log WHERE event_type_id=%s;"
                c.execute(sql, (self.event_type_id, ))
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

    def get_events_since(self, epoch, user_id=None):
        if self.event_type_id < 1:
            raise InvalidEventException
        if user_id and type(user_id) is not int:
            raise TypeError
        try:
            last_events = []
            c = self.db.cursor()
            if user_id:
                sql = "SELECT event_data,created,user_id FROM event_log "
                sql += "WHERE event_type_id=%s AND user_id=%s AND created > %s;"
                c.execute(sql, (self.event_type_id, user_id, epoch))
            else:
                sql = "SELECT event_data,created,user_id FROM event_log "
                sql += "WHERE event_type_id=%s AND created > %s;"
                c.execute(sql, (self.event_type_id, epoch))
            for row in c:
                last_events.append(row)
            return last_events
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

    def get_latest_events(self, limit, user_id=None):
        if self.event_type_id < 1:
            raise InvalidEventException
        if type(limit) is not int:
            raise TypeError
        if user_id and type(user_id) is not int:
            raise TypeError
        try:
            last_events = []
            c = self.db.cursor()
            if user_id:
                sql = "SELECT event_data,created,user_id FROM event_log WHERE event_type_id=%s AND user_id=%s LIMIT %s;"
                c.execute(sql, (self.event_type_id, user_id, limit))
            else:
                sql = "SELECT event_data,created,user_id FROM event_log WHERE event_type_id=%s LIMIT %s;"
                c.execute(sql, (self.event_type_id, limit))
            for row in c:
                last_events.append(row)
            return last_events
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

    def get_latest_event(self, user_id=None):
        if self.event_type_id < 1:
            raise InvalidEventException
        try:
            c = self.db.cursor()
            if user_id:
                sql = "SELECT event_data,created FROM event_log WHERE event_type_id=%s AND user_id=%s"
                sql += " ORDER BY event_id DESC LIMIT 1;"
                c.execute(sql, (self.event_type_id, user_id))
            else:
                sql = "SELECT event_data,created FROM event_log WHERE event_type_id=%s"
                sql += " ORDER BY event_id DESC LIMIT 1;"
                c.execute(sql, (self.event_type_id,))
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
            sql = "INSERT INTO event_log (event_type_id, user_id, event_data) VALUES (%s,%s,%s)"
            try:
                c.execute(sql, (self.event_type_id, user_id, metadata))
                last_row_id = c.lastrowid
                self.db.commit()
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
                return None
        else:
            raise InvalidEventException


if __name__ == "__main__":
    import database
    epoch = datetime.datetime.today() - datetime.timedelta(hours=24)
    db = database.Database()
    node_update_event = Event("Ethereum Node Update", db)
    latest_events = node_update_event.get_latest_events(1000)
    todays_events = node_update_event.get_events_since(epoch)
    event_count = node_update_event.get_event_count()
    blocks = {}
    for each_event in todays_events:
        event_data = json.loads(each_event[0])
        event_timestamp = each_event[1]
        latest_block_hash = event_data["latest_block_hash"]
        if latest_block_hash not in blocks:
            blocks[latest_block_hash] = {"block_size": event_data["latest_block_size"],
                                         "block_number": event_data["latest_block_number"],
                                         "gas_used": event_data["latest_block_gas_used"],
                                         "gas_limit": event_data["latest_block_gas_limit"],
                                         "timestamp": event_data["latest_block_timestamp"],
                                         "tx_count": event_data["latest_block_transaction_count"],
                                         "gas_price": event_data["gas_price"]}

    print("Total node update events: {0}".format(event_count))
    print("Events in last 24 hours: {0}".format(len(todays_events)))
    sorted
    print(len(blocks))

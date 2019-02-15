import MySQLdb
import json
import datetime
import database


class InvalidEventException(Exception):
    def __init__(self, event_type):
        self.message = "{0} not found in list of available events".format(event_type)


class Event:
    AVAILABLE_EVENTS = ["Ethereum Node Update",
                        "Ethereum Node Command Dispatch",
                        "Ethereum Node Command Output",
                        "Ethereum Node Command Failed",
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
                        "ERC20 Token Published",
                        "ERC20 Token Burned",
                        "ERC20 Token Issued",
                        "ERC20 Token External Transfer",
                        "Mailer Password Reset",
                        "Mailer Account Confirmation",
                        "Mailer Notify Deposit",
                        "Whitepaper Viewed",
                        "Block Data Transactions"]

    def __init__(self, event_type, db, logger=None):
        if event_type not in self.AVAILABLE_EVENTS:
            raise InvalidEventException(event_type)
        if isinstance(db, database.Database):
            self.db = db.db
        else:
            self.db = db
        self.logger = logger
        self.event_type = event_type

        try:
            c = self.db.cursor()
            c.execute("SELECT event_type_id FROM event_type WHERE event_type=%s;", (event_type,))
            row = c.fetchone()
            if not row:
                c.execute("INSERT INTO event_type (event_type) VALUES (%s)", (event_type,))
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

        def serialized(self):
            return json.dumps({"block_size": self.latest_block_size,
                           "block_number": self.latest_block_number,
                           "gas_used": self.latest_gas_used,
                           "gas_limit": self.latest_gas_limit,
                           "timestamp": self.latest_block_timestamp,
                           "tx_count": self.transaction_count,
                           "gas_price": self.gas_price})

    def get_latest_event(self, user_id=None):
        if self.event_type_id < 1:
            raise InvalidEventException
        if user_id and type(user_id) is not int:
            raise TypeError
        try:
            c = self.db.cursor()
            if user_id:
                sql = "SELECT event_data,created,user_id,event_id FROM event_log WHERE event_type_id=%s AND user_id=%s ORDER BY created DESC LIMIT 1;"
                c.execute(sql, (self.event_type_id, user_id))
            else:
                sql = "SELECT event_data,created,user_id,event_id FROM event_log WHERE event_type_id=%s ORDER BY created DESC LIMIT 1;"
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

    def get_event_count(self, user_id=None):
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
                c.execute(sql, (self.event_type_id,))
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

    def get_event_count_since(self, epoch, user_id=None):
        if self.event_type_id < 1:
            raise InvalidEventException
        if user_id and type(user_id) is not int:
            raise TypeError
        try:
            c = self.db.cursor()
            if user_id:
                sql = "SELECT COUNT(*) FROM event_log "
                sql += "WHERE event_type_id=%s AND user_id=%s AND created > %s;"
                c.execute(sql, (self.event_type_id, user_id, epoch))
            else:
                sql = "SELECT COUNT(*) FROM event_log "
                sql += "WHERE event_type_id=%s AND created > %s;"
                c.execute(sql, (self.event_type_id, epoch))
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
        return 0

    def get_events_since(self, epoch, user_id=None):
        if self.event_type_id < 1:
            raise InvalidEventException
        if user_id and type(user_id) is not int:
            raise TypeError
        try:
            last_events = []
            c = self.db.cursor()
            if user_id:
                sql = "SELECT event_data,created,user_id,event_id FROM event_log "
                sql += "WHERE event_type_id=%s AND user_id=%s AND created > %s;"
                c.execute(sql, (self.event_type_id, user_id, epoch))
            else:
                sql = "SELECT event_data,created,user_id,event_id FROM event_log "
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

    def get_event_by_id(self, event_id):
        try:
            c = self.db.cursor()
            sql = "SELECT event_data,created,user_id,event_id FROM event_log WHERE event_id = %s;"
            c.execute(sql, (event_id,))
            row = c.fetchone()
            if row:
                return [row]
            return None
        except MySQLdb.Error as e:
            try:
                error_message = "MySQL Error [%d]: %s" % (e.args[0], e.args[1])
            except IndexError:
                error_message = "MySQL Error: %s" % (str(e),)

            if self.logger:
                self.logger.error(error_message)
            else:
                print(error_message)

    def get_events_before_event_id(self, event_id, limit, user_id=None):
        if self.event_type_id < 1:
            raise InvalidEventException
        if type(event_id) is not int:
            raise TypeError
        if type(limit) is not int:
            raise TypeError
        if user_id and type(user_id) is not int:
            raise TypeError
        try:
            last_events = []
            c = self.db.cursor()
            if user_id:
                sql = "SELECT event_data,created,user_id,event_id FROM event_log WHERE event_id < %s AND event_type_id=%s AND user_id=%s ORDER BY created DESC LIMIT %s;"
                c.execute(sql, (event_id, self.event_type_id, user_id, limit))
            else:
                sql = "SELECT event_data,created,user_id,event_id FROM event_log WHERE event_id < %s AND event_type_id=%s ORDER BY created DESC LIMIT %s;"
                c.execute(sql, (event_id, self.event_type_id, limit))
            if self.logger:
                self.logger.error("SQL: " + sql)
                self.logger.error("event_id: {0}\tevent_type_id: {1}\tlimit: {2}".format(event_id,
                                                                                         self.event_type_id,
                                                                                         limit))
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
                sql = "SELECT event_data,created,user_id,event_id FROM event_log WHERE event_type_id=%s AND user_id=%s ORDER BY created DESC LIMIT %s;"
                c.execute(sql, (self.event_type_id, user_id, limit))
            else:
                sql = "SELECT event_data,created,user_id,event_id FROM event_log WHERE event_type_id=%s ORDER BY created DESC LIMIT %s;"
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


class NodeUpdateEvent(Event):
    def __init__(self,
                 db,
                 from_event_id=None,
                 synchronized=False,
                 blocks_behind=0,
                 latest_block_timestamp=None,
                 latest_block_number=0,
                 latest_block_hash=None,
                 latest_block_size=0,
                 latest_gas_used=0,
                 latest_gas_limit=0,
                 transaction_count=0,
                 gas_price=0,
                 node_id=0,
                 node_peers=0,
                 event_id=0,
                 logger=None):
        super().__init__("Ethereum Node Update", db, logger=logger)
        if isinstance(db, database.Database):
            self.db = db.db
        else:
            self.db = db
        self.logger = logger
        if from_event_id:
            event_tuples = super().get_event_by_id(from_event_id)
            if event_tuples:
                event_data = self.deserialize_event_data(event_tuples)
                node_update_event = event_data[0]
                self.synchronized = node_update_event.synchronized
                self.blocks_behind = node_update_event.blocks_behind
                self.latest_block_timestamp = node_update_event.latest_block_timestamp
                self.latest_block_number = node_update_event.latest_block_number
                self.latest_block_hash = node_update_event.latest_block_hash
                self.latest_block_size = node_update_event.latest_block_size
                self.latest_gas_used = node_update_event.latest_gas_used
                self.latest_gas_limit = node_update_event.latest_gas_limit
                self.peers = node_update_event.peers
                self.gas_price = node_update_event.gas_price
                self.transaction_count = node_update_event.transaction_count
                self.node_id = node_update_event.node_id
                self.event_id = node_update_event.event_id

        else:
            self.synchronized = synchronized
            self.blocks_behind = blocks_behind
            self.latest_block_timestamp = latest_block_timestamp
            self.latest_block_number = latest_block_number
            self.latest_block_hash = latest_block_hash
            self.latest_block_size = latest_block_size
            self.latest_gas_used = latest_gas_used
            self.latest_gas_limit = latest_gas_limit
            self.peers = node_peers
            self.gas_price = gas_price
            self.transaction_count = transaction_count
            self.node_id = node_id
            self.event_id = event_id

    def __str__(self):
        return "Ethereum Node Update"

    def deserialize_event_data(self, event_tuples):
        output = []
        for event in event_tuples:
            event_data = json.loads(event[0])
            if event_data["synchronized"]:
                timestamp = datetime.datetime.fromtimestamp(event_data["latest_block_timestamp"])
                new_event = NodeUpdateEvent(db=self.db,
                                            synchronized=event_data["synchronized"],
                                            blocks_behind=event_data["blocks_behind"],
                                            latest_block_timestamp=timestamp,
                                            latest_block_number=event_data["latest_block_number"],
                                            latest_block_hash=event_data["latest_block_hash"],
                                            latest_block_size=event_data["latest_block_size"],
                                            latest_gas_limit=event_data["latest_block_gas_limit"],
                                            latest_gas_used=event_data["latest_block_gas_used"],
                                            transaction_count=event_data["latest_block_transaction_count"],
                                            gas_price=event_data["gas_price"],
                                            node_peers=event_data["peers"],
                                            node_id=event[2],
                                            event_id=event[3],
                                            logger=self.logger)
            else:
                new_event = NodeUpdateEvent(db=self.db,
                                            synchronized=event_data["synchronized"],
                                            blocks_behind=event_data["blocks_behind"],
                                            node_id=event[2],
                                            event_id=event[3],
                                            logger=self.logger)
            output.append(new_event)
        return output

    def log_event(self, user_id, metadata):
        new_log_event_id = super().log_event(user_id=user_id, metadata=metadata)
        if new_log_event_id:
            import charting
            charting_module = charting.Charting(db=self.db, logger=self.logger)
            update_event = NodeUpdateEvent(self.db, logger=self.logger).get_latest_events(user_id=user_id, limit=1)[0]
            if update_event and charting_module:
                charting_module.add_chart_data(update_event)
                return new_log_event_id
        return None

    def get_latest_event(self, user_id=None):
        event_tuple = super().get_latest_event()
        events = self.deserialize_event_data([event_tuple])
        if type(events) == list and len(events) == 1:
            return events[0]
        else:
            return None

    def get_latest_events(self, limit, user_id=None):
        event_tuples = super().get_latest_events(limit, user_id)
        return self.deserialize_event_data(event_tuples)

    def get_events_since(self, epoch, user_id=None):
        event_tuples = super().get_events_since(epoch, user_id)
        return self.deserialize_event_data(event_tuples)

    def get_events_before_event_id(self, event_id, limit, user_id=None):
        event_tuples = super().get_events_before_event_id(event_id, limit, user_id)
        node_updates = self.deserialize_event_data(event_tuples)
        output = []
        # filter out update events from unsynchronized nodes
        for update in node_updates:
            if update.synchronized:
                output.append(update)
        while len(output) < limit:
            last_event = node_updates[-1]
            event_tuples = super().get_events_before_event_id(last_event.event_id, limit, user_id)
            node_updates = self.deserialize_event_data(event_tuples)
            for update in node_updates:
                if update.synchronized:
                    output.append(update)
                    if len(output) == limit:
                        return output
            # end of the line
            if len(node_updates) < limit:
                return output


if __name__ == "__main__":
    epoch = datetime.datetime.today() - datetime.timedelta(hours=24)
    db = database.Database()
    node_update_event = NodeUpdateEvent(db)
    latest_events = node_update_event.get_latest_events(1000)
    todays_events = node_update_event.get_events_since(epoch)
    event_count = node_update_event.get_event_count()
    latest_event = NodeUpdateEvent(db, from_event_id=latest_events[-1].event_id)
    blocks = {}
    block_numbers = []
    for each_event in todays_events:
        latest_block_hash = each_event.latest_block_hash
        if latest_block_hash not in blocks:
            blocks[latest_block_hash] = each_event.deserialize()

    import pprint
    pprint.pprint(blocks)
    print("Total node update events: {0}".format(event_count))
    print("Events in last 24 hours: {0}".format(len(todays_events)))

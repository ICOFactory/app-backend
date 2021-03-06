import MySQLdb
import json
from events import NodeUpdateEvent
import unittest
import datetime
import time

MOVING_AVERAGE_WINDOW = 30


class Charting:
    def __init__(self, db=None, logger=None):
        self.logger = logger
        config_stream = open("config.json", "r")
        config_data = json.load(config_stream)
        config_stream.close()
        self.log_string("Charting module: configuration loaded.")

        db_host = config_data["charting"]['mysql_host']
        db_username = config_data["charting"]['mysql_user']
        db_password = config_data["charting"]['mysql_password']
        db_name = config_data["charting"]['mysql_database']
        self._db = MySQLdb.connect(db_host, db_username, db_password, db_name)

    def log_string(self, event):
        if self.logger:
            self.logger.info(event)
        else:
            print(event)

    def get_distinct_blocks(self, start=None, end=None):
        try:
            c = self._db.cursor()
            if start and not end:
                sql = "SELECT DISTINCT(block_number) FROM charting WHERE timestamp > %s ORDER BY block_number ASC"
                c.execute(sql, (start,))
            elif start and end:
                sql = "SELECT DISTINCT(block_number) FROM charting WHERE timestamp > %s AND timestamp < %s ORDER BY block_number ASC"
                c.execute(sql, (start, end,))
            elif end:
                sql = "SELECT DISTINCT(block_number) FROM charting WHERE timestamp < %s ORDER BY block_number ASC"
                c.execute(sql, (end,))
            else:
                sql = "SELECT DISTINCT(block_number) FROM charting ORDER BY block_number ASC"
                c.execute(sql)
            output = []
            for row in c:
                output.append(row[0])
            return output
        except MySQLdb.MySQLError as e:
            self.log_string("MySQL error: {0}".format(e))
            return None

    def get_gas_price_for_node_id(self, node_id, start=None, end=None):
        output = []
        try:
            sql = "SELECT block_number, node_gas_price FROM charting WHERE node_id=%s AND timestamp>%s"
            c = self._db.cursor()
            epoch = datetime.datetime.now() - datetime.timedelta(hours=24)
            c.execute(sql, (node_id, epoch))
            for row in c:
                output.append((row[0], row[1]))
            return output
        except MySQLdb.MySQLError as e:
            self.log_string("MySQL error: {0}".format(e))
        return None

    def get_block_size_per_block(self, start=None, end=None):
        sql = "SELECT block_number,block_size FROM charting WHERE timestamp>%s"
        output = []
        try:
            c = self._db.cursor()
            c.execute(sql, (start,))
            for row in c:
                output.append((row[0], row[1]))
            return output
        except MySQLdb.MySQLError as e:
            self.log_string("MySQL error: {0}".format(e))
        return None

    def get_utilization_per_block(self, start=None, end=None):
        sql = "SELECT block_number,gas_used,gas_limit FROM charting WHERE timestamp>%s"
        output = []
        try:
            c = self._db.cursor()
            c.execute(sql, (start,))
            for row in c:
                output.append((row[0], row[2] - row[1]))
            return output
        except MySQLdb.MySQLError as e:
            self.log_string("MySQL error: {0}".format(e))
        return None

    def get_transactions_per_block(self, start=None, end=None):
        sql = "SELECT block_number,transaction_count FROM charting WHERE timestamp>%s"
        output = []
        try:
            c = self._db.cursor()
            c.execute(sql, (start,))
            for row in c:
                output.append((row[0], row[1]))
            return output
        except MySQLdb.MySQLError as e:
            self.log_string("MySQL error: {0}".format(e))
        return None

    def get_gas_price_moving_average(self, start=None, end=None):
        sql = "SELECT block_number,moving_average_gas_price FROM charting WHERE timestamp>%s"
        output = []
        try:
            c = self._db.cursor()
            c.execute(sql, (start,))
            for row in c:
                output.append((row[0], row[1]))
            return output
        except MySQLdb.MySQLError as e:
            self.log_string("MySQL error: {0}".format(e))
        return None

    def add_chart_data(self, node_update_event):
        if not isinstance(node_update_event, NodeUpdateEvent):
            raise TypeError
        if node_update_event.synchronized:
            moving_average_window = node_update_event.get_events_before_event_id(node_update_event.event_id,
                                                                                 MOVING_AVERAGE_WINDOW)
            if moving_average_window is None:
                self.log_string("Could not get a window for moving average.")
                return False
            gas_price_window = map(lambda event_data: event_data.gas_price, moving_average_window)
            moving_average = float(sum(gas_price_window)) / float(MOVING_AVERAGE_WINDOW)
            self.log_string("Charting module: new moving average: {0}".format(moving_average))
            try:
                c = self._db.cursor()
                sql = "INSERT INTO charting (moving_average_gas_price, node_id, node_gas_price, block_number,"
                sql += " transaction_count, block_size, gas_limit, gas_used,node_peers,timestamp)"
                sql += " VALUES (%s,%s,%s,%s,%s,%s,%s,%s,%s,%s);"
                result = c.execute(sql, (moving_average, node_update_event.node_id, node_update_event.gas_price,
                                         node_update_event.latest_block_number, node_update_event.transaction_count,
                                         node_update_event.latest_block_size,
                                         node_update_event.latest_gas_limit, node_update_event.latest_gas_used,
                                         node_update_event.peers, node_update_event.latest_block_timestamp))
                if result:
                    self._db.commit()
                    self._db.close()
                    self.log_string("Chart module: added row to chart table.")
                    return True
            except MySQLdb.Error as err:
                self.log_string(err)
        else:
            self.log_string("Not logging from unsynchronized node.")
        return False


class TestCase(unittest.TestCase):
    def test_unified_db(self):
        import database
        db = database.Database()
        charting = Charting(db)
        test_event = NodeUpdateEvent(db).get_latest_events(1)[0]
        result = charting.add_chart_data(test_event)
        self.assertTrue(result)

    def test_separate_db(self):
        charting = Charting()
        import database
        db = database.Database()
        test_event = NodeUpdateEvent(db).get_latest_events(1)[0]
        result = charting.add_chart_data(test_event)
        self.assertTrue(result)

    def test_moving_average(self):
        import database
        db = database.Database()
        charting = Charting(db)
        query_start = time.time()
        charting_data = charting.get_gas_price_moving_average()
        query_end = time.time()
        elapsed = query_end - query_start
        print("Elapsed: {0} seconds".format(elapsed))
        self.assertIsNotNone(charting_data)


if __name__ == "__main__":
    # unittest.main()
    print("Prepopulating chart table for last 24 hours...")
    epoch = datetime.datetime.now() - datetime.timedelta(hours=24)
    import database

    db = database.Database()
    charting = Charting(db)
    events = NodeUpdateEvent(db).get_events_since(epoch)
    for each in events:
        if each.synchronized:
            result = charting.add_chart_data(each)
            if not result:
                break

from events import NodeUpdateEvent
import MySQLdb
import json
import unittest

MOVING_AVERAGE_WINDOW = 100


class Charting:
    def __init__(self, db=None, logger=None):
        self.logger = logger
        config_stream = open("config/charting.json", "r")
        config_data = json.load(config_stream)
        config_stream.close()
        self.log_string("Charting module: configuration loaded.")
        self.db = None
        if db:
            self._db = db.db
            self.db = db
        else:
            db_host = config_data['mysql_host']
            db_username = config_data['mysql_user']
            db_password = config_data['mysql_password']
            db_name = config_data['mysql_database']
            self._db = MySQLdb.connect(db_host, db_username, db_password, db_name)

    def log_string(self, event):
        if self.logger:
            logger.info(event)
        else:
            print(event)

    def get_chart_data(self, moving_average_gas_price=False,
                       node_id=None,
                       node_gas_price=False, block_number=False,
                       transaction_count=False, block_size=False,
                       gas_limit=False, gas_used=False, node_peers=False,
                       limit=None, offset=None, before=None, since=None, latest=None):
        args = []
        columns = []
        output = {}
        sql = "SELECT "
        if moving_average_gas_price:
            sql += "moving_average_gas_price,"
            columns.append("moving_average_gas_price")
        if node_gas_price:
            sql += "node_gas_price,"
            columns.append("node_gas_price")
        if block_number:
            sql += "block_number,"
            columns.append("block_number")
        if transaction_count:
            sql += "transaction_count,"
            columns.append("transaction_count")
        if block_size:
            sql += "block_size,"
            columns.append("block_size")
        if gas_limit:
            sql += "gas_limit,"
            columns.append("gas_limit")
        if gas_used:
            sql += "gas_used,"
            columns.append("gas_used")
        if node_peers:
            sql += "node_peers,"
            columns.append("node_peers")
        if sql == "SELECT ":
            raise AssertionError
        sql += "timestamp FROM charting"
        columns.append("timestamp")
        if node_id:
            sql += " WHERE node_id=%s"
            args.append(node_id)
        if since:
            sql += " AND timestamp > %s ORDER BY chart_data_id DESC"
            args.append(since)
        elif latest:
            sql += " ORDER BY chart_data_id DESC LIMIT %s"
            args.append(latest)
        if limit:
            sql += " LIMIT %s"
            args.append(limit)
            if offset:
                sql += " OFFSET %s"
                args.append(offset)
        for each in columns:
            output[each] = []
        try:
            c = self._db.cursor()
            c.execute(sql, tuple(args))
            for row in c:
                for x in range(0, len(row) - 1):
                    output[columns[x]].append(row[x], row[len(row) - 1])
            return output
        except MySQLdb.MySQLError as e:
            self.log_string("MySQL error: " + e)
            return None

    def add_chart_data(self, node_update_event):
        if not isinstance(node_update_event, NodeUpdateEvent):
            raise TypeError
        if node_update_event.synchronized:
            moving_average_window = node_update_event.get_latest_events(MOVING_AVERAGE_WINDOW)
            gas_price_window = map(lambda event_data: event_data.gas_price, moving_average_window)
            moving_average = float(sum(gas_price_window)) / float(MOVING_AVERAGE_WINDOW)
            self.log_string("Charting module: new moving average: {0}".format(moving_average))
            try:
                c = self._db.cursor()
                sql = """INSERT INTO charting (moving_average_gas_price, 
node_id, node_gas_price, block_number, transaction_count, block_size, gas_limit, gas_used,node_peers) VALUES (%s,%s,%s,%s,%s,%s,%s,%s,%s);"""
                result = c.execute(sql, (moving_average, node_update_event.node_id, node_update_event.gas_price,
                                         node_update_event.latest_block_number, node_update_event.latest_block_size,
                                         node_update_event.latest_gas_limit, node_update_event.latest_gas_used,
                                         node_update_event.node_peers))
                if result:
                    self._db.commit()
                    if self.db is None:
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
        test_event = NodeUpdateEvent(db).get_latest_event()
        result = charting.add_chart_data(test_event)
        self.assertTrue(result)

    def test_separted_db(self):
        charting = Charting()
        import database
        db = database.Database()
        test_event = NodeUpdateEvent(db).get_latest_event()
        result = charting.add_chart_data(test_event)
        self.assertTrue(result)


if __name__ == "__main__":
    unittest.main()

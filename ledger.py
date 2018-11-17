# Transaction ledger
import database
import MySQLdb


class TransactionLedger:
    def __init__(self, user_id, db=None, logger=None):
        if db:
            self.db = db
            self._db = db.db
        else:
            self.db = database.Database()
            self._db = self.db.db
        self.logger = logger
        self.user_id = user_id

    def get_owned_token_count(self):
        if self.user_id < 1:
            raise ValueError
        sql = "SELECT COUNT(*) FROM tokens WHERE owner_id=%s"
        try:
            c = self._db.cursor()
            c.execute(sql, (self.user_id,))
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
                    print("MySQL Error: %s" % (str(e),))
        return None

    def get_transaction_count(self):
        if self.user_id < 1:
            raise ValueError
        sql = "SELECT COUNT(*) FROM transaction_ledger WHERE sender_id=%s OR receiver_id=%s"
        try:
            c = self._db.cursor()
            c.execute(sql, (self.user_id, self.user_id))
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
                    print("MySQL Error: %s" % (str(e),))
        return None

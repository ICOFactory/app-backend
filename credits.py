import events
import database
import unittest
import json


class Credits:
    def __init__(self, user_id, db, logger=None):
        self.user_id = user_id
        self.db = db
        self.logger = logger
        config_stream = open("config.json", "r")
        config_data = json.load(config_stream)
        config_stream.close()
        self.erc20_publish_price = config_data["erc20_publish_price"]

    def get_credit_balance(self):
        balance = self.db.get_credit_balance(self.user_id)
        return balance

    def issue_credits(self, amount, event_data):
        new_event = events.Event("Users Issued Credits", self.db, self.logger)
        event_id = new_event.log_event(self.user_id, event_data)
        if event_id:
            return self.db.credit_user(self.user_id, amount, event_id)
        return False

    def debit(self, amount, event_data):
        new_event = events.Event("Users Debit Credits", self.db, self.logger)
        event_id = new_event.log_event(self.user_id, event_data)
        if event_id:
            return self.db.debit_user(self.user_id, amount, event_id)
        return False


class CreditsUnitTests(unittest.TestCase):
    def setUp(self):
        self.db = database.Database()

    def test_issue_credits(self):
        user_credits = Credits(1, self.db)
        starting_credits = user_credits.get_credit_balance()
        self.assertTrue(user_credits.issue_credits(1000, {"issuer": 1, "msg": "Unit test"}))
        self.assertGreaterEqual(user_credits.get_credit_balance(), 1000)
        self.assertTrue(user_credits.debit(1000, {"issuer": 1, "msg": "Unit test"}))
        ending_credits = user_credits.get_credit_balance()
        self.assertEqual(starting_credits, ending_credits, "Ending credits not equal to starting credits.")


if __name__ == "__main__":
    unittest.main()

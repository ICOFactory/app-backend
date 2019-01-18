from events import Event
from database import Database
import os


class Mailer:
    def __init__(self, email_address, ip_addr=None, logger=None):
        self.email_address = email_address
        self.ip_address = ip_addr
        self.logger = logger

    def recover_password(self):
        db = Database(self.logger)
        new_event = Event("Mailer Password Reset", db, self.logger)
        confirmation_code = os.urandom(16).hex()
        user_id = db.validate_email(self.email_address)
        if user_id:
            new_event_id = new_event.log_event(user_id, {"ip_address": self.ip_address,
                                                         "confirmation": confirmation_code})
            # TODO: Sendgrid

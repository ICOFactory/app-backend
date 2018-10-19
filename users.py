import database


class UserContext:
    def __init__(self, user_id, db, logger=None):
        self.db = db
        if logger:
            self.logger = logger
        elif db.logger:
            self.logger = logger
        self.user_info = db.get_user_info(user_id)
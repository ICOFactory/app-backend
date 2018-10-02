import random
import datetime


def random_token():
    new_session_token = "%08x%08x" % (random.randint(0,0xffffffff),random.randint(0,0xffffffff))
    return new_session_token


class Database():
    def verify_session(self,user_id,session_id):
        if user_id < 0:
            return False # user id cannot be less than 0
        return True
    
    def last_frame(self,device_id):
        return (1,datetime.datetime.now(),"{\"data\":2}")
    
    def list_devices(self,user_id):
        return []
    
    def add_device(self,user_id,uuid):
        return 1
    
    def login(self,email_address,password):
        if email_address == "test_fail":
            return None
        return (1,random_token())
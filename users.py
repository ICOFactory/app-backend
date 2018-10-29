import database


def add_if_not_found(tokens,new_permission,token_id,db):
    found = False
    for key in tokens.keys():
        if tokens[key]["token_id"] == token_id:
            found = True
            if new_permission not in tokens[key]["permissions"]:
                tokens[key]["permissions"].append(new_permission)
            break
    if not found:
        new_token = db.get_smart_contract_info(token_id)
        if new_token:
            tokens[new_token["token_name"]] = {"token_id": new_token["token_id"],
                                               "permissions": new_permission}


class UserContext:
    MEMBER_PERMISSIONS = ["view-tokens",
                          "external-transfer-tokens"]
    MANAGER_PERMISSIONS = ["change-priority",
                           "issue-tokens",
                           "assign-tokens",
                           "remove-tokens",
                           "premine-tokens",
                           "burn-tokens"]
    ADMIN_PERMISSIONS = ["onboard-users",
                         "change-permissions",
                         "reset-passwords",
                         "launch-ico",
                         "ethereum-network",
                         "view-event-log",
                         "issue-credits"]

    def __init__(self, user_id, db=None, logger=None):
        if db:
            self.db = db
        else:
            self.db = database.Database()
        if logger:
            self.logger = logger
        self.user_info = db.get_user_info(user_id)
        user_id = self.user_info["user_id"]
        new_acl = {"administrator": [],
                   "membership": {},
                   "management": {}}
        self.member_tokens = dict()
        self.manager_tokens = dict()
        all_user_permissions = self.db.list_permissions(user_id)
        for each in all_user_permissions:
            if each[0]:
                token_id = each[0]
                new_permission = each[1]
                if new_permission in self.MANAGER_PERMISSIONS:
                    add_if_not_found(manager_tokens,new_permission,token_id,self.db)
                elif new_permission in self.MEMBER_PERMISSIONS:
                    add_if_not_found(member_tokens,new_permission,token_id,self.db)
            else:
                new_permission = each[1]
                if new_permission not in new_acl["administrator"]:
                    new_acl["administrator"].append(new_permission)
        new_acl["membership"] = member_tokens
        new_acl["management"] = manager_tokens
        self._acl = new_acl

    def _remove_permission(self,permission,token_id=None):
        if token_id:
            if permission in self.MEMBER_PERMISSIONS:
                for key in self.member_tokens.keys():
                    if self.member_tokens[key]["token_id"] == token_id:
                        token_permissions = self.member_tokens[key]["permissions"]
                        if permission in token_permissions:
                            token_permissions.remove(permission)
                        if len(token_permissions):
                            del self.member_tokens[key]
                        return True
            elif permission in self.MANAGER_PERMISSIONS:
                for key in self.manager_tokens.keys():
                    if self.manager_tokens[key]["token_id"] == token_id:
                        token_permissions = self.manager_tokens[key]["permissions"]
                        if permission in token_permissions:
                            token_permissions.remove(permission)
                        if len(token_permissions):
                            del self.manager_tokens[key]
                        return True
        else:
            if permission in self.ADMIN_PERMISSIONS:
                if permission in self._acl["administrator"]:
                    self._acl["administrator"].remove(permission)
                    return True
        return False

    def _add_permission(self,permission,token_id=None):
        if token_id:
            if permission in self.MEMBER_PERMISSIONS:
                add_if_not_found(self.member_tokens,permission,token_id,self.db)
                return True
            elif permission in self.MANAGER_PERMISSIONS:
                add_if_not_found(self.manager_tokens,permission,token_id,self.db)
                return True
        else:
            if permission in self.ADMIN_PERMISSIONS:
                if permission not in self._acl["administrator"]:
                    self._acl["administrator"].append(permission)
                    return True
        return False

    def remove_permission(self,permission,token_id=None):
        result = self._add_permission(permission,token_id)
        if token_id and self.logger:
            contract_info = self.db.get_smart_contract_info(token_id)
            self.logger.info("Remove permission {0} for {1} on {2}: {3}".format(permission,self.user_info["email_address"],contract_info["token_name"],result))
        elif self.logger:
            self.logger.info("Remove permission {0} for {1}: {2}".format(permission,self.user_info["email_address"],result))
        return result


    def add_permission(self,permission,token_id=None):
        result = self._add_permission(permission,token_id)
        if token_id and self.logger:
            contract_info = self.db.get_smart_contract_info(token_id)
            self.logger.info("Add permission {0} for {1} on {2}: {3}".format(permission,self.user_info["email_address"],contract_info["token_name"],result))
        elif self.logger:
            self.logger.info("Add permission {0} for {1}: {2}".format(permission,self.user_info["email_address"],result))
        return result

    def check_acl(self,permission,token_id=None):
        result = self._check_acl(permission,token_id)
        if token_id and self.logger:
            contract_info = self.db.get_smart_contract_info(token_id)
            self.logger.info("ACL check for user {0}, permission {1} on {2}: {3}".format(self.user_info["email_address"],permission,contract_info["token_name"],result))
        elif self.logger:
            self.logger.info("ACL check for user {0}, permission {1}: {2}".format(self.user_info["email_address"],permission,result))
        return result

    def _check_acl(self,permission,token_id=None):
        if token_id:
            if permission in self.MEMBER_PERMISSIONS:
                for key in self.member_tokens.keys():
                    if token_id == self.member_tokens[key]["token_id"]:
                        return permission in self.member_tokens[key]["permissions"]
            elif permission in self.MANAGER_PERMISSIONS:
                for key in self.manager_tokens.keys():
                    if token_id == self.manager_tokens[key]["token_id"]:
                        return permission in self.manager_tokens[key]["permissions"]

    def acl(self):
        return self._acl

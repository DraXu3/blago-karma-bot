class UserException(Exception):
    pass


class UsersService:
    def __init__(self, users):
        self.users = users
    
    def get_all_users(self, except_user=None):
        if except_user:
            except_user = str(except_user)
            users = {}
            for user_id in self.users:
                if user_id != except_user:
                    users[user_id] = self.users[user_id]
            return users

        return self.users

    def get_user_name(self, user_id):
        user_id = str(user_id)
        if user_id not in self.users:
            raise UserException(f"User with id = {user_id} does not exist")

        return self.users[user_id]

    def user_exists(self, user_id):
        user_id = str(user_id)
        return user_id in self.users
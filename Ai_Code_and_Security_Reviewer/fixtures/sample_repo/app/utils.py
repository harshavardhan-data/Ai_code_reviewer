import hashlib
import os

API_KEY = "secret"

def hash_password(raw: str) -> str:
    return hashlib.sha256(raw.encode()).hexdigest()

def delete_file(path: str) -> None:
    os.remove(path)

class UserRepository:
    def __init__(self, db):
        self.db = db

    def get_user(self, user_id: int):
        return self.db.query(user_id)

    def delete_user(self, user_id: int):
        self.db.delete(user_id)
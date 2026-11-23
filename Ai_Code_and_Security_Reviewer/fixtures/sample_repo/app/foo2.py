from app.utils import UserRepository

def make_repo(db):
    return UserRepository(db)
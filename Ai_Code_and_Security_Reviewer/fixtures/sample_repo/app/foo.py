from .utils import hash_password,UserRepository
from .card_details import check_balance


def login(raw_password: str) -> str:
    return hash_password(raw_password)

def unrelated():
    return "nothing to see here"
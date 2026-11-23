
def get_card_details(id:str,name:str):

    return id+name

def check_balance(card_number:int):

    return card_number


class BankAccount:

    def __init__(self,id,name):
        self.id=id
        self.name=name


    def get_account_details(self,id,name):
        return f"Account details {id} : {name}"

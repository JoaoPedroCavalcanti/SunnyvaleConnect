# Functions to be use in the rules of a password (in Serializer)
def hasUpperCase(password: str):
    for lettler in password:
        if lettler.isupper():
            return True
    return False


def hasAtLeast8Characters(password: str):
    if len(password) < 8:
        return False
    return True

def hasSpecialCharacter(password: str):
    return not password.isalnum()

print(hasSpecialCharacter('asd'))

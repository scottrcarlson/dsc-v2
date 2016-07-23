#!/usr/bin/python
# ----------------------------
# --- Crypto Helper Class
#----------------------------

 # TODO: quantify entropy of these passphrases
 # TODO: Notes on improving entropy on rpi linux using broadcom feature?
def generate_random_passphrase(self, length):
    passphrase = ""
    for i in range(length + 1):
        char = os.urandom(1)
        while char not in CHARACTERS_SUPPORTED_BY_YUBIKEY:
            char = os.urandom(1)
        passphrase += char
    return passphrase

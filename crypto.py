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

#!/usr/bin/env python

import os, binascii, sys, keyczar

if __name__ == '__main__':
    if len(sys.argv) != 2 or not os.path.isdir(sys.argv[1]):
        print >> sys.stderr, "Provide an empty temp directory as argument."
        sys.exit(1)

    # create dirs for sign/verif keypair
    rsa_path2 = os.path.join(sys.argv[1], 'rsa2')
    rsa_pub_path2 = os.path.join(sys.argv[1], 'rsa_pub2')
    if os.path.isdir(rsa_path2) or os.path.isdir(rsa_pub_path2):
        print >> sys.stderr, 'Error:', sys.argv[1], 'is not empty.'
        sys.exit(1)
    os.mkdir(rsa_path2)
    os.mkdir(rsa_pub_path2)


    keyset_type = keyczar.KeyczarTool.JSON_FILE
    keyset_password = 'cartman'

    kt = keyczar.KeyczarTool(keyset_type)

    # Create a RSA key set for signing and verifying
    kt.CmdCreate(rsa_path2, keyczar.KeyPurpose.SIGN_AND_VERIFY,
                 "MyRSATest2", keyczar.KeyczarTool.RSA)
    version = kt.CmdAddKey(rsa_path2, keyczar.KeyStatus.ACTIVE, 0,
                           keyczar.KeyczarTool.PBE, keyset_password)
    kt.CmdPromote(rsa_path2, version)
    # Exports public keys
    kt.CmdPubKey(rsa_path2, rsa_pub_path2, keyczar.KeyczarTool.PBE,
                 keyset_password)

    reader = keyczar.KeysetPBEJSONFileReader(rsa_path2, keyset_password)


    signer = keyczar.Signer.Read(reader) # sender's private signing key
    signer.set_encoding(signer.NO_ENCODING)
    signature = signer.Sign("mymsg")
    print "signature:", binascii.hexlify(signature)
    print "signature length:", len(signature)
    verified = signer.Verify("mymsg", signature)
    print "was signed by sender?", verified


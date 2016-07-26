#!/usr/bin/env python
# ----------------------------
# --- Crypto Helper Class
#----------------------------
import os, binascii, sys, keyczar

KEYPAIR_ROOT_PATH = '/home/pi/.dsc2/'
ENCR_DECR_KEYPAIR_PATH = KEYPAIR_ROOT_PATH + 'encr_decr_keypair'
ENCR_DECR_KEYPAIR_PUB_PATH = KEYPAIR_ROOT_PATH + 'encr_decr_keypair_pub'
SIGN_VERI_KEYPAIR_PATH = KEYPAIR_ROOT_PATH + 'sign_veri_keypair'
SIGN_VERI_KEYPAIR_PUB_PATH = KEYPAIR_ROOT_PATH + 'sign_veri_keypair_pub'

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


def gen_keysets(keyset_password):
	# ensure we're not stomping old keysets
	if os.path.isdir(ENCR_DECR_KEYPAIR_PATH) or \
           os.path.isdir(ENCR_DECR_KEYPAIR_PUB_PATH) or\
           os.path.isdir(SIGN_VERI_KEYPAIR_PATH) or \
           os.path.isdir(SIGN_VERI_KEYPAIR_PUB_PATH):
		print "keypair directory(s) already exist. aborting to avoid stomping old keypairs."
		sys.exit(1)
	os.makedirs(ENCR_DECR_KEYPAIR_PATH)
	os.makedirs(ENCR_DECR_KEYPAIR_PUB_PATH)
	os.makedirs(SIGN_VERI_KEYPAIR_PATH)
	os.makedirs(SIGN_VERI_KEYPAIR_PUB_PATH)

	keyset_type = keyczar.KeyczarTool.JSON_FILE
	kt = keyczar.KeyczarTool(keyset_type)

	# create a rsa keypair for encrypting and decrypting
	kt.CmdCreate(ENCR_DECR_KEYPAIR_PATH, keyczar.KeyPurpose.DECRYPT_AND_ENCRYPT,
                 "ENCR_DECR_KEYPAIR", keyczar.KeyczarTool.RSA)
	version = kt.CmdAddKey(ENCR_DECR_KEYPAIR_PATH, keyczar.KeyStatus.ACTIVE, 0,
                           keyczar.KeyczarTool.PBE, keyset_password)
	kt.CmdPromote(ENCR_DECR_KEYPAIR_PATH, version)

	# export public key
	kt.CmdPubKey(ENCR_DECR_KEYPAIR_PATH, ENCR_DECR_KEYPAIR_PUB_PATH, keyczar.KeyczarTool.PBE,
                 keyset_password)


	# create a rsa keypair for signing and verifying
	kt.CmdCreate(SIGN_VERI_KEYPAIR_PATH, keyczar.KeyPurpose.SIGN_AND_VERIFY,
                 "SIGN_VERIF_KEYPAIR", keyczar.KeyczarTool.RSA)
	version = kt.CmdAddKey(SIGN_VERI_KEYPAIR_PATH, keyczar.KeyStatus.ACTIVE, 0,
                           keyczar.KeyczarTool.PBE, keyset_password)
	kt.CmdPromote(SIGN_VERI_KEYPAIR_PATH, version)

	# export public key
	kt.CmdPubKey(SIGN_VERI_KEYPAIR_PATH, SIGN_VERI_KEYPAIR_PUB_PATH, keyczar.KeyczarTool.PBE,
                 keyset_password)

def sign_msg(msg, keyset_password):
	reader = keyczar.KeysetPBEJSONFileReader(SIGN_VERI_KEYPAIR_PATH, keyset_password)
	signer = keyczar.Signer.Read(reader) # sender's private signing key
	signer.set_encoding(signer.NO_ENCODING)
	signature = signer.Sign(msg)
	return signature

def verify_msg(msg, signature, verifying_key_path):
	verifier = keyczar.Verifier.Read(verifying_key_path) # sender's public verifying key
	verifier.set_encoding(verifier.NO_ENCODING)
	verified = verifier.Verify(msg, signature)
	return verified

def encrypt_msg(msg, encr_decr_keypair_pub):
	encrypter = keyczar.Encrypter.Read(encr_decr_keypair_pub) # recipient's public encrypting key
	encrypter.set_encoding(encrypter.NO_ENCODING)
	encrypted_msg = encrypter.Encrypt(msg)
	return encrypted_msg

def decrypt_msg(encrypted_msg, keyset_password):
	reader = keyczar.KeysetPBEJSONFileReader(ENCR_DECR_KEYPAIR_PATH, keyset_password)
	crypter = keyczar.Crypter.Read(reader)
	crypter.set_encoding(crypter.NO_ENCODING)
	decrypted_msg = crypter.Decrypt(encrypted_msg)
	return decrypted_msg

if __name__ == '__main__':
	test_password = "mypassword"
	test_msg = "mymsg"
	print "test_password:", test_password
	print "test_msg:", test_msg

	gen_keysets(test_password)

	signature = sign_msg(test_msg, test_password)
	print "signature:", binascii.hexlify(signature)
	print "signature length:", len(signature)

	print "verified:", verify_msg(test_msg, signature, SIGN_VERI_KEYPAIR_PUB_PATH)

	encrypted_msg = encrypt_msg(test_msg, ENCR_DECR_KEYPAIR_PUB_PATH)
	print "encrypted_msg:", binascii.hexlify(encrypted_msg)
	print "encrypted_msg len:", len(encrypted_msg)

	decrypted_msg = decrypt_msg(encrypted_msg, test_password)
	print "decrypted_msg:", decrypted_msg

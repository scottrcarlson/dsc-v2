#!/usr/bin/env python
# ----------------------------
# --- Crypto Helper Class
#----------------------------
import os, binascii, sys, keyczar, datetime
import shutil
from config import Config
from sh import mount
from sh import umount
from sh import Command
from sh import mkdir
from sh import cp

ROOT_PATH = '/dscdata/'
KEYPAIR_ROOT_PATH = ROOT_PATH + 'keys/'
ENCR_DECR_KEYPAIR_PATH = KEYPAIR_ROOT_PATH + 'encr_decr_keypair'
ENCR_DECR_KEYPAIR_PUB_PATH = KEYPAIR_ROOT_PATH + 'encr_decr_keypair_pub'
SIGN_VERI_KEYPAIR_PATH = KEYPAIR_ROOT_PATH + 'sign_veri_keypair'
SIGN_VERI_KEYPAIR_PUB_PATH = KEYPAIR_ROOT_PATH + 'sign_veri_keypair_pub'
USB_DRV_PATH = ROOT_PATH + 'usb/'
USB_DRV_PUBKEY_PATH = USB_DRV_PATH + 'public_keys/'
USB_DRV_DEVICE_PATH = '/dev/sda1'

mkfs_vfat = Command("mkfs.vfat")

# from https://github.com/stapelberg/pw-to-yubi/blob/master/pw-to-yubi.pl
CHARACTERS_SUPPORTED_BY_YUBIKEY = '0123456789-=[]\;`./+_{}|:"~<>?abcdefghijklmnopqrstuvwxyzABCDEFGHIJKLMNOPQRSTUVWXYZ'

class Crypto(object):
    # TODO: quantify entropy of these passwords
    # TODO: Notes on improving entropy on rpi linux using broadcom feature?
    def generate_random_password(self, length):
        password = ""
        for i in range(length):
            char = os.urandom(1)
            while char not in CHARACTERS_SUPPORTED_BY_YUBIKEY:
                char = os.urandom(1)
            password += char
        return password

    def inport_keys(self):
        pass

    def export_keys(self, alias):
        print "device exist?: ", os.path.isdir(USB_DRV_DEVICE_PATH)
        try:
            self.mount_usb_drv()
        except:
            print "Export Key: Failed to mount. Already mounted, or drive is not plugged in."
        if not os.path.isdir(USB_DRV_PUBKEY_PATH):
            mkdir(USB_DRV_PUBKEY_PATH)
        if not os.path.isdir(USB_DRV_PUBKEY_PATH + alias):
            mkdir(USB_DRV_PUBKEY_PATH + alias)
        print ENCR_DECR_KEYPAIR_PUB_PATH + "/*"
        print USB_DRV_PUBKEY_PATH + alias

        try:
            cp('-R', ENCR_DECR_KEYPAIR_PUB_PATH,USB_DRV_PUBKEY_PATH + alias)
            cp('-R', SIGN_VERI_KEYPAIR_PUB_PATH,USB_DRV_PUBKEY_PATH + alias)
        except:
            print "Failed to copy public keys."
        try:
            self.unmount_usb_drv()
        except:
            print "Drive not mounted or does not exist"

    def mount_usb_drv(self):
        try:
            mount(USB_DRV_DEVICE_PATH, USB_DRV_PATH)
        except:
            print "Failed to mount, Drive mounted or does not exist"            

    def unmount_usb_drv(self):
        try:
            umount(USB_DRV_PATH)
        except:
            print "Failed to unmount. Drive not mounted?"
        
    def prepare_usb_drv(self):      # Unmount / Format / Create Directory Structure
        self.unmount_usb_drv()
        try:
            mkfs_vfat(USB_DRV_DEVICE_PATH)
        except:
            print "Failed to Format, Drive mounted or does not exist."
        self.mount_usb_drv()
        if not os.path.isdir(USB_DRV_PUBKEY_PATH):
            mkdir(USB_DRV_PUBKEY_PATH)
        self.unmount_usb_drv()        

    def wipe_all_data(self):
        print "Wiping Keys from System."
        if os.path.isdir(KEYPAIR_ROOT_PATH):
            shutil.rmtree(KEYPAIR_ROOT_PATH)
        if os.path.isfile(ROOT_PATH + 'dsc.config'):
            os.remove(ROOT_PATH + 'dsc.config')

    def gen_keysets(self, keyset_password):
        print "Generating new keyset"
        # ensure we're not stomping old keysets
        if os.path.isdir(ENCR_DECR_KEYPAIR_PATH) or \
                os.path.isdir(ENCR_DECR_KEYPAIR_PUB_PATH) or\
                os.path.isdir(SIGN_VERI_KEYPAIR_PATH) or \
                os.path.isdir(SIGN_VERI_KEYPAIR_PUB_PATH):
            print "keypair directory(s) already exist. aborting to avoid stomping old keypairs."
            return False
        else:
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

            print "Keyset generation complete."
            return True

    def sign_msg(self, msg, keyset_password):
        reader = keyczar.KeysetPBEJSONFileReader(SIGN_VERI_KEYPAIR_PATH, keyset_password)
        signer = keyczar.Signer.Read(reader) # sender's private signing key
        signer.set_encoding(signer.NO_ENCODING)
        signature = signer.Sign(msg)
        return signature

    def verify_msg(self, msg, signature, verifying_key_path):
        verifier = keyczar.Verifier.Read(verifying_key_path) # sender's public verifying key
        verifier.set_encoding(verifier.NO_ENCODING)
        verified = verifier.Verify(msg, signature)
        return verified

    def encrypt_msg(self, msg, encr_decr_keypair_pub):
        encrypter = keyczar.Encrypter.Read(encr_decr_keypair_pub) # recipient's public encrypting key
        encrypter.set_encoding(encrypter.NO_ENCODING)
        encrypted_msg = encrypter.Encrypt(msg)
        return encrypted_msg

    def decrypt_msg(self, encrypted_msg, keyset_password):
        reader = keyczar.KeysetPBEJSONFileReader(ENCR_DECR_KEYPAIR_PATH, keyset_password)
        crypter = keyczar.Crypter.Read(reader)
        crypter.set_encoding(crypter.NO_ENCODING)
        decrypted_msg = crypter.Decrypt(encrypted_msg)
        return decrypted_msg

    def authenticate_user(self,keyset_password):
        if not os.path.isdir(KEYPAIR_ROOT_PATH):
            #Node has not been configured (Factory State). Probably Temp. We will add a first time sequence
            return True
        reader = keyczar.KeysetPBEJSONFileReader(ENCR_DECR_KEYPAIR_PATH, keyset_password)
        crypter = keyczar.Crypter.Read(reader)
        if crypter != None:
            return True
        else:
            return False

if __name__ == '__main__':
    test_password = "mypassword"
    test_msg = "mymsg"
    print "test_password:", test_password
    print "test_msg:", test_msg
    print ""

    c = Crypto()

    #c.prepare_usb_drv()
    #c.export_keys('scott')
    #sys.exit()

    #print c.authenticate_user('\`7eSHO~h"kK7KYC2A;To7mcI[Ge<+QHSll')
    print "generating keysets..."
    print datetime.datetime.now()
    c.gen_keysets(test_password)
    print datetime.datetime.now()
    print ""

    print "signing msg..."
    print datetime.datetime.now()
    signature = c.sign_msg(test_msg, test_password)
    print datetime.datetime.now()
    print "signature:", binascii.hexlify(signature)
    print "signature length:", len(signature)
    print ""

    print "verifying msg..."
    print datetime.datetime.now()
    print "verified:", c.verify_msg(test_msg, signature, SIGN_VERI_KEYPAIR_PUB_PATH)
    print datetime.datetime.now()
    print ""
	
    print "encrypting msg..."
    print datetime.datetime.now()
    encrypted_msg = c.encrypt_msg(test_msg, ENCR_DECR_KEYPAIR_PUB_PATH)
    print datetime.datetime.now()
    print "encrypted_msg:", binascii.hexlify(encrypted_msg)
    print "encrypted_msg len:", len(encrypted_msg)
    print ""

    print "decrypting msg..."
    print datetime.datetime.now()
    decrypted_msg = c.decrypt_msg(encrypted_msg, test_password)
    print datetime.datetime.now()
    print "decrypted_msg:", decrypted_msg
    print ""

    print "random password:", c.generate_random_password(80)

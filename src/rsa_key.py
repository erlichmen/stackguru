import os, logging
from tlslite.utils import keyfactory
import base64
from array import array
from tlslite.utils.cryptomath import stringToBytes, bytesToString, numberToBytes, createByteArraySequence
from google.appengine.api import memcache

class RSAKey:
    @staticmethod
    def get_token_b64(email):
        key = RSAKey.get_private_key()
        token = key.hashAndSign(email)
        token = bytesToString(token)
        return base64.urlsafe_b64encode(token)

    @staticmethod
    #Hack: assume that that the public key is 1024
    def get_public_as_der():
        public_der_key = memcache.get("public_der", namespace="rsa_keys")
        
        if not public_der_key:
            result = array("B")
            public_key = RSAKey.get_public_key()
            der_1024 = createByteArraySequence([0x30,0x81,0x9F,0x30,0x0D,0x06,0x09,0x2A,0x86,0x48,0x86,0xF7,0x0D,0x01,0x01,0x01,0x05,0x00,0x03,0x81,0x8D,0x00,0x30,0x81,0x89,0x02,0x81,0x81,0x00])
            result += der_1024            
            result += numberToBytes(public_key.n)
            result += createByteArraySequence([0x02, 0x03])
            result += numberToBytes(public_key.e)
            
            public_der_key = bytesToString(result)
            memcache.set("public_der", public_der_key, namespace="rsa_keys")
                 
        return public_der_key

    @staticmethod
    def is_valid(email, token_b64):
        token = memcache.get(email, namespace="hashes2")
        
        if token == None:
            email = email.encode("utf8")
            token_b64 = token_b64.encode("utf8")
            token = stringToBytes(base64.urlsafe_b64decode(token_b64))
            key = RSAKey.get_public_key()
            valid = key.hashAndVerify(token, email)
            
            if valid:
                memcache.set(email, token_b64, namespace="hashes2")
                
            return valid
        else:
            return token == token_b64
    
    @staticmethod
    def get_key(key_name, on_key):
        pem = memcache.get("pem", namespace="rsa_keys")
        if not pem:        
            private_key_file = os.path.join(os.path.dirname(__file__), "./static/chrome/private_key.pem")
            logging.debug("key file name %s" % private_key_file)
            f = file(private_key_file)
            try:
                pem = f.read()
                memcache.set("pem", pem, namespace="rsa_keys")
                logging.debug("key size %d" % len(pem))
            finally:
                f.close();
        
        key = on_key(pem)
        
        return key

    @staticmethod
    def get_public_key():
        def on_key(pem):
            return keyfactory.parsePEMKey(pem, public=True, implementations=["python"])
                    
        return RSAKey.get_key("public", on_key)
            
    @staticmethod
    def get_private_key():
        def on_key(pem):
            return keyfactory.parsePEMKey(pem, private=True, implementations=["python"])
            
        return RSAKey.get_key("private", on_key)
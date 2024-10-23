from Crypto.Cipher import AES
from Crypto.Random import get_random_bytes
from Crypto.Util.Padding import pad, unpad
from Crypto.Protocol.KDF import PBKDF2
import base64

default_secret_key = "uaZCB7mBN/ZcDgNSPv7gtUIIJ9Mrf9pzEZzcG9jOEEE="

def generate_aes_key():
    return get_random_bytes(32)  # 256-bit AES key

def generate_salt():
    return get_random_bytes(16)

def aes_to_base64(aes_key):
    return base64.b64encode(aes_key).decode('utf-8')

def base64_to_aes(aes_key):
    secret_key = base64.b64decode(aes_key)

    # Ensure the key is 32 bytes long (valid for AES-256)
    if len(secret_key) != 32:
        raise ValueError("Invalid secret key length")
    return secret_key

# Derive a strong encryption key using PBKDF2
def derive_key(secret_key, salt):
    # Derive a 256-bit AES key using PBKDF2 with 100,000 iterations
    return PBKDF2(secret_key, salt, dkLen=32, count=100000)

def encrypt_message(secret_key, message):
    salt = generate_salt()  # Generate a random salt
    derived_key = derive_key(secret_key, salt)  # Derive a key from the secret key and salt

    cipher = AES.new(derived_key, AES.MODE_GCM)
    ciphertext, tag = cipher.encrypt_and_digest(pad(message.encode('utf-8'), AES.block_size))

    # Combine salt, nonce, tag, and ciphertext
    return salt + cipher.nonce + tag + ciphertext

def decrypt_message(secret_key, encrypted_message):
    salt = encrypted_message[:16]  # Extract the salt
    nonce = encrypted_message[16:32]  # Extract the nonce
    tag = encrypted_message[32:48]  # Extract the tag
    ciphertext = encrypted_message[48:]  # The rest is the ciphertext

    derived_key = derive_key(secret_key, salt)  # Derive the key using the same salt
    cipher = AES.new(derived_key, AES.MODE_GCM, nonce=nonce)

    decrypted_message = unpad(cipher.decrypt_and_verify(ciphertext, tag), AES.block_size)
    return decrypted_message.decode('utf-8')
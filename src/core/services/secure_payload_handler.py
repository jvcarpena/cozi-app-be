import base64
import json
import os

from Crypto.Cipher import AES
from Crypto.Random import get_random_bytes

from domains.guest.dtos.sign_up_login_dto import EncryptedDataDTO, DecryptedSignUpDataDTO, DecryptedLoginDataDTO

NONCE_SIZE = 12
TAG_SIZE = 16


class SecurePayloadHandler:
    """
    Utility class to encrypt and decrypt API payloads using AES-256-GCM.
    """

    def __init__(self, data_to_encrypt: dict = None, data_to_decrypt: str = None):
        self.data_to_encrypt = data_to_encrypt
        self.data_to_decrypt = data_to_decrypt
        self.encryption_key = base64.b64decode(os.environ.get("COZI_ENCRYPTION_KEY"))

    def encrypt_payload(self) -> EncryptedDataDTO:

        nonce = get_random_bytes(NONCE_SIZE)

        cipher = AES.new(self.encryption_key, AES.MODE_GCM, nonce=nonce)
        cipher_text, tag = cipher.encrypt_and_digest(json.dumps(self.data_to_encrypt).encode())

        combined = nonce + tag + cipher_text

        return EncryptedDataDTO(data=base64.urlsafe_b64encode(combined).decode())

    def decrypt_payload(self, is_sign_up: bool = False) -> DecryptedSignUpDataDTO | DecryptedLoginDataDTO:

        combined = base64.urlsafe_b64decode(self.data_to_decrypt)

        # UNPACK

        nonce = combined[:NONCE_SIZE]
        tag = combined[NONCE_SIZE : NONCE_SIZE + TAG_SIZE]
        cipher_text = combined[NONCE_SIZE + TAG_SIZE :]

        cipher = AES.new(self.encryption_key, AES.MODE_GCM, nonce=nonce)

        plain_text = cipher.decrypt_and_verify(cipher_text, tag)

        decrypted_data = json.loads(plain_text.decode())

        if is_sign_up:
            return DecryptedSignUpDataDTO(**decrypted_data)

        return DecryptedLoginDataDTO(**decrypted_data)


if __name__ == "__main__":

    payload_signup = {
        "email": "jvcarpena2@gmail.com",
        "first_name": "jv",
        "last_name": "carpena",
        "password": "jv1234",
        "phone": "",
    }

    payload_login = {
        "email": "jvcarpena2@gmail.com",
        "password": "jv1234",
    }

    signup_encrypted = SecurePayloadHandler(data_to_encrypt=payload_signup).encrypt_payload()
    print(f"signup_encrypted: {signup_encrypted}")

    signup_decrypted = SecurePayloadHandler(data_to_decrypt=signup_encrypted.data).decrypt_payload(is_sign_up=True)
    print(f"signup_decrypted: {signup_decrypted}")

    login_encrypted = SecurePayloadHandler(data_to_encrypt=payload_login).encrypt_payload()
    print(f"login_encrypted: {login_encrypted}")

    login_decrypted = SecurePayloadHandler(data_to_decrypt=login_encrypted.data).decrypt_payload()
    print(f"login_decrypted: {login_decrypted}")

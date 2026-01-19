import base64
import json
import os

from Crypto.Cipher import AES
from Crypto.Random import get_random_bytes

from domains.guest.dtos.sign_up_login_dto import EncryptedDataDTO, DecryptedSignUpDataDTO, DecryptedLoginDataDTO


class SecurePayloadHandler:
    """
    Utility class to encrypt and decrypt API payloads using AES-256-GCM.
    """

    def __init__(self, data_to_encrypt: dict = None, data_to_decrypt: dict = None):
        self.data_to_encrypt = data_to_encrypt
        self.data_to_decrypt = data_to_decrypt
        self.encryption_key = base64.b64decode(os.environ.get("COZI_ENCRYPTION_KEY"))

    def encrypt_payload(self) -> EncryptedDataDTO:

        nonce = get_random_bytes(12)

        cipher = AES.new(self.encryption_key, AES.MODE_GCM, nonce=nonce)
        cipher_text, tag = cipher.encrypt_and_digest(json.dumps(self.data_to_encrypt).encode())

        return EncryptedDataDTO(
            ciphertext=base64.b64encode(cipher_text).decode(),
            nonce=base64.b64encode(nonce).decode(),
            tag=base64.b64encode(tag).decode(),
        )

    def decrypt_payload(self, is_sign_up: bool = False) -> DecryptedSignUpDataDTO | DecryptedLoginDataDTO:

        cipher = AES.new(
            self.encryption_key,
            AES.MODE_GCM,
            nonce=base64.b64decode(self.data_to_decrypt["nonce"]),
        )

        plain_text = cipher.decrypt_and_verify(
            base64.b64decode(self.data_to_decrypt["ciphertext"]),
            base64.b64decode(self.data_to_decrypt["tag"]),
        )

        decrypted_data = json.loads(plain_text.decode())

        if is_sign_up:
            return DecryptedSignUpDataDTO(**decrypted_data)

        return DecryptedLoginDataDTO(**decrypted_data)


if __name__ == "__main__":

    payload_signup = {
        "email": "jose_carpena@gmail.com",
        "first_name": "jv",
        "last_name": "carpena",
        "password": "jv1234",
    }

    payload_login = {
        "email": "jm_roales@gmail.com",
        "password": "jm1234",
    }

    signup_encrypted = SecurePayloadHandler(data_to_encrypt=payload_signup).encrypt_payload()
    print(f"signup_encrypted: {signup_encrypted}")

    signup_decrypted = SecurePayloadHandler(data_to_decrypt=signup_encrypted.model_dump()).decrypt_payload(
        is_sign_up=True
    )
    print(f"signup_decrypted: {signup_decrypted}")

    login_encrypted = SecurePayloadHandler(data_to_encrypt=payload_login).encrypt_payload()
    print(f"login_encrypted: {login_encrypted}")

    login_decrypted = SecurePayloadHandler(data_to_decrypt=login_encrypted.model_dump()).decrypt_payload()
    print(f"login_decrypted: {login_decrypted}")

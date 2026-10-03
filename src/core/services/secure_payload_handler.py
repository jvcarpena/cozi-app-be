import base64
import json
import os
from enum import StrEnum

from Crypto.Cipher import AES
from Crypto.Random import get_random_bytes
from fastapi import HTTPException
from pydantic import ValidationError

from domains.guest.dtos.sign_up_login_dto import (
    EncryptedDataDTO,
    DecryptedSignUpDataDTO,
    DecryptedLoginDataDTO,
    DecryptedPasswordResetDTO,
)

from domains.manager.dtos.sign_up_dto import DecryptedManagerSignUpDataDTO

NONCE_SIZE = 12
TAG_SIZE = 16


class PayloadError(StrEnum):

    INVALID_PAYLOAD = "The request payload is invalid."


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

    def decrypt_payload(
        self, is_sign_up: bool = False, is_password_reset: bool = False, is_manager_sign_up: bool = False
    ) -> DecryptedSignUpDataDTO | DecryptedLoginDataDTO | DecryptedPasswordResetDTO | DecryptedManagerSignUpDataDTO:

        # A PAYLOAD THAT CANNOT BE DECRYPTED (BAD BASE64, WRONG KEY, TAMPERED DATA, NOT JSON) IS A BAD REQUEST.

        try:

            decrypted_data = self._decrypt()

        except ValueError:

            raise HTTPException(status_code=400, detail=PayloadError.INVALID_PAYLOAD.name)

        # A PAYLOAD THAT DECRYPTS BUT HAS MISSING OR INVALID FIELDS IS AN UNPROCESSABLE REQUEST.
        # ERRORS RAISED BY THE FIELD VALIDATORS THEMSELVES (E.G. INVALID_NAME) ARE HTTP ERRORS AND PASS THROUGH.

        try:

            if is_manager_sign_up:
                return DecryptedManagerSignUpDataDTO(**decrypted_data)

            if is_sign_up:
                return DecryptedSignUpDataDTO(**decrypted_data)

            if is_password_reset:
                return DecryptedPasswordResetDTO(**decrypted_data)

            return DecryptedLoginDataDTO(**decrypted_data)

        except (ValidationError, TypeError):

            raise HTTPException(status_code=422, detail=PayloadError.INVALID_PAYLOAD.name)

    def _decrypt(self) -> dict:

        combined = base64.urlsafe_b64decode(self.data_to_decrypt)

        # UNPACK

        nonce = combined[:NONCE_SIZE]
        tag = combined[NONCE_SIZE : NONCE_SIZE + TAG_SIZE]
        cipher_text = combined[NONCE_SIZE + TAG_SIZE :]

        cipher = AES.new(self.encryption_key, AES.MODE_GCM, nonce=nonce)

        plain_text = cipher.decrypt_and_verify(cipher_text, tag)

        return json.loads(plain_text.decode())


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

    payload_password_reset = {"email": "dawnaianne.laguisma@gmail.com"}

    signup_encrypted = SecurePayloadHandler(data_to_encrypt=payload_signup).encrypt_payload()
    print(f"signup_encrypted: {signup_encrypted}")

    signup_decrypted = SecurePayloadHandler(data_to_decrypt=signup_encrypted.data).decrypt_payload(is_sign_up=True)
    print(f"signup_decrypted: {signup_decrypted}")

    login_encrypted = SecurePayloadHandler(data_to_encrypt=payload_login).encrypt_payload()
    print(f"login_encrypted: {login_encrypted}")

    login_decrypted = SecurePayloadHandler(data_to_decrypt=login_encrypted.data).decrypt_payload()
    print(f"login_decrypted: {login_decrypted}")

    password_reset_encrypted = SecurePayloadHandler(data_to_encrypt=payload_password_reset).encrypt_payload()
    print(f"password_reset_encrypted: {password_reset_encrypted}")

    password_reset_decrypted = SecurePayloadHandler(data_to_decrypt=password_reset_encrypted.data).decrypt_payload(
        is_password_reset=True
    )
    print(f"password_reset_decrypted: {password_reset_decrypted}")

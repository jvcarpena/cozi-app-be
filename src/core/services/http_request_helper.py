from pydantic import BaseModel, Field

from core.models.user import User
from core.services.auth_token_handler import AuthTokenHandler


class HTTPRequestDTO(BaseModel):
    headers: dict
    body: dict | None
    query_string_parameters: dict | None


class HTTPRequestHelper(BaseModel):

    headers: dict | None = Field(default_factory=dict)
    body: dict | None = Field(default_factory=dict)
    query_string_parameters: dict | None = Field(default_factory=dict)

    def create_request(self, user: User) -> HTTPRequestDTO:

        self.headers.setdefault("Authorization", AuthTokenHandler(user_id=user.id).generate_auth_token())

        self.headers.setdefault("origin", "http://localhost")

        return HTTPRequestDTO(
            headers=self.headers,
            body=self.body,
            query_string_parameters=self.query_string_parameters,
        )

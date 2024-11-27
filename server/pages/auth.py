import logging
from dataclasses import dataclass
from datetime import datetime, timedelta
from typing import Dict

import jwt
from fastapi import Request
from typing_extensions import Self

from core.config import settings
from server.err import RequiresLoginException

logger = logging.getLogger()


@dataclass
class User:
    user_id: int

    def auth_user(self) -> Dict[str, str]:
        payload = {"user_id": self.user_id, "exp": datetime.now() + timedelta(days=30)}
        token = jwt.encode(
            payload,
            settings.JWT_SECRET.get_secret_value(),
            algorithm=settings.ALGORITHM,
        )

        return token

    @classmethod
    def from_request(cls, request: Request) -> Self:
        user = cls.from_request_opt(request)
        if user is None:
            raise RequiresLoginException
        else:
            return user

    @classmethod
    def from_request_opt(cls, request: Request) -> Self | None:
        try:
            token = request.cookies.get("users_access_token")
            payload = decodeJWT(token)

        except (jwt.DecodeError, jwt.ExpiredSignatureError):
            return None

        else:
            # existing token might not have 'exp' field
            payload.pop("exp", None)
            return cls(**payload)


def decodeJWT(token: str) -> dict:
    decoded_token = jwt.decode(
        token,
        settings.JWT_SECRET.get_secret_value(),
        algorithms=[settings.ALGORITHM],
    )

    return (
        decoded_token
        if datetime.fromtimestamp(decoded_token["exp"]) > datetime.now()
        else None
    )


# class JWTBearer(HTTPBearer):
#     def __init__(self, auto_error: bool = True):
#         super(JWTBearer, self).__init__(auto_error=auto_error)

#     def __call__(self, request: Request):
#         credentials = HTTPAuthorizationCredentials(
#             scheme="Bearer", credentials=request.cookies.get("users_access_token")
#         )
#         if credentials:
#             if not credentials.scheme == "Bearer":
#                 raise HTTPException(
#                     status_code=status.HTTP_403_FORBIDDEN,
#                     detail="Invalid authentication scheme.",
#                     headers={"WWW-Authenticate": "Bearer"},
#                 )

#             payload = self.get_payload(credentials.credentials)
#             if not payload:
#                 raise HTTPException(
#                     status_code=status.HTTP_401_UNAUTHORIZED,
#                     detail="Token expired",
#                     headers={"WWW-Authenticate": "Bearer"},
#                 )
#             return payload
#         else:
#             raise HTTPException(
#                 status_code=status.HTTP_403_FORBIDDEN,
#                 detail="Invalid authorization code.",
#                 headers={"WWW-Authenticate": "Bearer"},
#             )

#     def get_payload(self, jwtoken: str) -> bool:
#         payload = None
#         try:
#             payload = decodeJWT(jwtoken)
#         except Exception:
#             pass
#         else:
#             return payload

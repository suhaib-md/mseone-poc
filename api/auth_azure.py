import base64
import os
from functools import lru_cache

import jwt
import requests
from cryptography.hazmat.primitives import serialization
from cryptography.hazmat.primitives.asymmetric import rsa
from fastapi import Header, HTTPException, status

TENANT_ID = os.getenv("AZURE_TENANT_ID", "d2fd2d1b-9f4e-459b-84ab-d6f0db24a087")
AUDIENCE = os.getenv("AZURE_AUDIENCE", "api://5551da76-8fe1-4a20-ac0f-6f817cc75f2f")
ISSUER = f"https://sts.windows.net/{TENANT_ID}/"  # ✅ Correct for v1.0 tokens


@lru_cache
def get_jwks():
    # ✅ Use v1.0 keys endpoint to match your v1.0 token
    jwks_uri = f"https://login.microsoftonline.com/{TENANT_ID}/discovery/keys"
    try:
        response = requests.get(jwks_uri, timeout=10)
        response.raise_for_status()
        return response.json()["keys"]
    except Exception as e:
        print(f"Failed to fetch JWKS: {e}")
        raise


def jwk_to_pem(jwk):
    """Convert JWK to PEM format for PyJWT"""
    try:
        # Extract the modulus and exponent from JWK
        n = base64.urlsafe_b64decode(jwk["n"] + "==")  # Add padding
        e = base64.urlsafe_b64decode(jwk["e"] + "==")  # Add padding

        # Convert bytes to integers
        n_int = int.from_bytes(n, "big")
        e_int = int.from_bytes(e, "big")

        # Create RSA public key
        public_key = rsa.RSAPublicNumbers(e_int, n_int).public_key()

        # Convert to PEM
        pem = public_key.public_bytes(
            encoding=serialization.Encoding.PEM,
            format=serialization.PublicFormat.SubjectPublicKeyInfo,
        )

        return pem
    except Exception as e:
        print(f"Error converting JWK to PEM: {e}")
        raise


def validate_jwt(token: str):
    try:
        # First, let's decode without verification to see the claims
        unverified_payload = jwt.decode(token, options={"verify_signature": False})
        print(f"Unverified payload: {unverified_payload}")

        # Extract header to find which key was used
        unverified_header = jwt.get_unverified_header(token)
        kid = unverified_header["kid"]

        print(f"Token kid: {kid}")
        print(f"Expected audience: {AUDIENCE}")
        print(f"Expected issuer: {ISSUER}")
        print(f"Token audience: {unverified_payload.get('aud')}")
        print(f"Token issuer: {unverified_payload.get('iss')}")

        # Find matching key
        keys = get_jwks()
        key = next((k for k in keys if k["kid"] == kid), None)
        if not key:
            available_kids = [k["kid"] for k in keys]
            print(f"Available kids: {available_kids}")
            raise Exception(f"Signing key not found. Token kid: {kid}, Available: {available_kids}")

        print(f"Found matching key with kid: {kid}")

        # Convert JWK to PEM format
        try:
            public_key = jwk_to_pem(key)
            print("Successfully converted JWK to PEM")
        except Exception as key_error:
            print(f"Failed to convert JWK to PEM: {key_error}")
            raise

        # Try decoding with minimal validation first
        try:
            payload = jwt.decode(
                token,
                public_key,
                algorithms=["RS256"],
                options={
                    "verify_signature": True,
                    "verify_exp": True,
                    "verify_aud": False,
                    "verify_iss": False,
                },
            )
            print("Signature validation passed")
        except Exception as sig_error:
            print(f"Signature validation failed: {sig_error}")
            raise

        # Now try with audience validation
        try:
            payload = jwt.decode(
                token,
                public_key,
                algorithms=["RS256"],
                audience=AUDIENCE,
                options={
                    "verify_signature": True,
                    "verify_exp": True,
                    "verify_aud": True,
                    "verify_iss": False,
                },
            )
            print("Audience validation passed")
        except Exception as aud_error:
            print(f"Audience validation failed: {aud_error}")
            raise

        # Finally try with full validation
        payload = jwt.decode(
            token,
            public_key,
            algorithms=["RS256"],
            audience=AUDIENCE,
            issuer=ISSUER,
            options={"verify_exp": True},
        )

        print(f"Token validated successfully for app: {payload.get('appid')}")
        return payload

    except jwt.ExpiredSignatureError as e:
        print(f"Token expired: {e}")
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Token has expired",
        )
    except jwt.InvalidTokenError as e:
        print(f"JWT Invalid token error: {e}")
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail=f"Token validation failed: {e}",
        )
    except Exception as e:
        print(f"Token validation error: {e}")
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail=f"Invalid token: {e}",
        )


async def require_aad_bearer(authorization: str = Header(None)):
    print(
        f"require_aad_bearer called with authorization: {authorization[:50] if authorization else None}..."
    )

    if not authorization or not authorization.lower().startswith("bearer "):
        print("Missing or invalid authorization header")
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Missing bearer token")

    token = authorization.split(" ", 1)[1]
    print(f"Extracted token (first 50 chars): {token[:50]}...")
    print("Calling validate_jwt...")

    try:
        result = validate_jwt(token)
        print("validate_jwt succeeded")
        return result
    except Exception as e:
        print(f"validate_jwt failed: {e}")
        raise

"""Encrypted local BYOK storage backed by the operating system keyring."""

from __future__ import annotations

import os
from datetime import datetime, timezone
from typing import Protocol

from cryptography.fernet import Fernet
from sqlalchemy import select
from sqlalchemy.orm import Session

from backend.models import ProviderCredential


KEYRING_SERVICE = "assisted-trading-backend"
KEYRING_ACCOUNT = "credential-encryption-key"
OPENROUTER_ENV = "OPENROUTER_API_KEY"


class CredentialStorageUnavailable(RuntimeError):
    """The OS vault cannot safely persist an encryption key."""


class KeyringBackend(Protocol):
    priority: float

    def get_password(self, service: str, username: str) -> str | None: ...
    def set_password(self, service: str, username: str, password: str) -> None: ...


def system_keyring() -> KeyringBackend:
    try:
        import keyring

        backend = keyring.get_keyring()
        if float(getattr(backend, "priority", 0)) <= 0:
            raise CredentialStorageUnavailable("OS credential vault is unavailable")
        return backend
    except CredentialStorageUnavailable:
        raise
    except Exception as exc:
        raise CredentialStorageUnavailable("OS credential vault is unavailable") from exc


class OpenRouterCredentialStore:
    def __init__(self, session: Session, keyring_backend: KeyringBackend | None = None):
        self.session = session
        self.keyring_backend = keyring_backend

    def _vault(self) -> KeyringBackend:
        if self.keyring_backend is not None:
            if float(getattr(self.keyring_backend, "priority", 0)) <= 0:
                raise CredentialStorageUnavailable("OS credential vault is unavailable")
            return self.keyring_backend
        return system_keyring()

    def _fernet(self, create: bool) -> Fernet:
        vault = self._vault()
        key = vault.get_password(KEYRING_SERVICE, KEYRING_ACCOUNT)
        if key is None and create:
            key = Fernet.generate_key().decode("ascii")
            vault.set_password(KEYRING_SERVICE, KEYRING_ACCOUNT, key)
            if vault.get_password(KEYRING_SERVICE, KEYRING_ACCOUNT) != key:
                raise CredentialStorageUnavailable("OS credential vault could not verify the encryption key")
        if key is None:
            raise CredentialStorageUnavailable("Encryption key is not available in the OS credential vault")
        try:
            return Fernet(key.encode("ascii"))
        except Exception as exc:
            raise CredentialStorageUnavailable("OS credential vault returned an invalid encryption key") from exc

    def store(self, api_key: str) -> None:
        if not isinstance(api_key, str) or not api_key.strip():
            raise ValueError("OpenRouter API key must be non-empty")
        cipher = self._fernet(create=True)
        encrypted = cipher.encrypt(api_key.encode("utf-8"))
        record = self.session.scalar(select(ProviderCredential).where(ProviderCredential.provider == "openrouter"))
        if record is None:
            record = ProviderCredential(provider="openrouter", encrypted_secret=encrypted, updated_at=datetime.now(timezone.utc))
            self.session.add(record)
        else:
            record.encrypted_secret = encrypted
            record.updated_at = datetime.now(timezone.utc)
        self.session.commit()

    def get(self) -> str | None:
        # Runtime configuration (including the project .env) takes precedence,
        # while preserving compatibility with previously saved credentials.
        configured_key = os.getenv(OPENROUTER_ENV)
        if configured_key:
            return configured_key
        record = self.session.scalar(select(ProviderCredential).where(ProviderCredential.provider == "openrouter"))
        if record is not None:
            try:
                return self._fernet(create=False).decrypt(record.encrypted_secret).decode("utf-8")
            except Exception:
                return None
        return None

    def source(self) -> str:
        if os.getenv(OPENROUTER_ENV):
            return "environment"
        record = self.session.scalar(select(ProviderCredential).where(ProviderCredential.provider == "openrouter"))
        if record is not None:
            try:
                self._fernet(create=False).decrypt(record.encrypted_secret)
                return "os_keyring"
            except Exception:
                return "unavailable"
        return "missing"

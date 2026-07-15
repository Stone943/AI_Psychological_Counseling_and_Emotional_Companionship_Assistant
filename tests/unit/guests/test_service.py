"""Persistent guest token lifecycle tests."""

from __future__ import annotations

import pytest
from sqlalchemy.ext.asyncio import async_sessionmaker, create_async_engine
from sqlalchemy.pool import StaticPool

from mental_health_api.config import Settings
from mental_health_api.database.base import Base
from mental_health_api.guests.service import GuestService


@pytest.mark.asyncio
async def test_guest_token_is_persisted_only_as_digest_and_can_be_revoked() -> None:
    engine = create_async_engine("sqlite+aiosqlite://", poolclass=StaticPool)
    async with engine.begin() as connection:
        await connection.run_sync(Base.metadata.create_all)

    factory = async_sessionmaker(engine, expire_on_commit=False)
    settings = Settings(environment="test", force_tls=False, jwt_secret_key="unit-test-secret")
    async with factory() as session:
        service = GuestService(settings, session)
        device_proof = "0123456789abcdef" * 4
        subject, stored_session, token = await service.create_guest(device_proof)

        assert len(token) == 64
        assert token != stored_session.token_digest
        assert stored_session.device_key_hash != device_proof
        assert await service.verify_token(token, "abcdef0123456789" * 4) is None
        verified = await service.verify_token(token, device_proof)
        assert verified is not None
        assert verified.guest_subject_id == subject.guest_subject_id

        assert await service.revoke(token, device_proof) == subject.guest_subject_id
        assert await service.verify_token(token, device_proof) is None

    await engine.dispose()

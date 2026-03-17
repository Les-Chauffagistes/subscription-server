import os
import subprocess
import sys
from datetime import timedelta
from pathlib import Path
from shutil import which
from dotenv import load_dotenv
from prisma import Prisma
import pytest
import pytest_asyncio
import asyncpg
from src.modules.logger.logger import Logger

load_dotenv(".env.test", override=True)


def _resolve_prisma_cli() -> str:
    prisma = which("prisma")
    if prisma:
        return prisma

    candidates = [
        Path(sys.executable).resolve().parent / "prisma",
        Path(__file__).resolve().parents[1] / "venv" / "bin" / "prisma",
    ]
    for candidate in candidates:
        if candidate.exists():
            return str(candidate)

    raise FileNotFoundError(
        "Unable to locate the Prisma CLI. Expected it in PATH or venv/bin/prisma."
    )


def _ensure_test_db():
    """Crée la BDD de test et applique le schéma Prisma si nécessaire."""
    db_url = os.environ["DATABASE_URL"]
    db_name = db_url.rsplit("/", 1)[-1].split("?")[0]
    server_url = db_url.rsplit("/", 1)[0] + "/postgres"

    import asyncio

    async def _create_db():
        conn = await asyncpg.connect(server_url)
        try:
            exists = await conn.fetchval(
                "SELECT 1 FROM pg_database WHERE datname = $1", db_name
            )
            if not exists:
                await conn.execute(f'CREATE DATABASE "{db_name}"')
        finally:
            await conn.close()

    asyncio.run(_create_db())

    subprocess.run(
        [_resolve_prisma_cli(), "db", "push", "--skip-generate"],
        env={**os.environ, "DATABASE_URL": db_url},
        check=True,
        capture_output=True,
    )


_ensure_test_db()


@pytest_asyncio.fixture(scope="session", loop_scope="session")
async def prisma_client():
    prisma = Prisma()
    await prisma.connect()
    yield prisma
    await prisma.disconnect()


@pytest_asyncio.fixture(scope="session", loop_scope="session", autouse=True)
async def seed_db(prisma_client: Prisma):
    """Purge et peuple la BDD une seule fois au début de la session de tests."""
    # Purge (ordre respectant les FK)
    await prisma_client.subscriptionpayment.delete_many()
    await prisma_client.lightninginvoice.delete_many()
    await prisma_client.subscription.delete_many()
    await prisma_client.subscriptionrate.delete_many()
    await prisma_client.opennodewebhooklog.delete_many()

    # Seed
    await prisma_client.subscriptionrate.create(
        data={
            "satsPerDay": 100,
        }
    )

    yield

    # Nettoyage après tous les tests
    await prisma_client.subscriptionpayment.delete_many()
    await prisma_client.lightninginvoice.delete_many()
    await prisma_client.subscription.delete_many()
    await prisma_client.subscriptionrate.delete_many()
    await prisma_client.opennodewebhooklog.delete_many()


@pytest_asyncio.fixture(loop_scope="session")
async def db(prisma_client: Prisma):
    """Contexte transactionnel : rollback automatique après chaque test."""
    tx = prisma_client.tx(timeout=timedelta(seconds=30))
    transaction = await tx.start()
    try:
        yield transaction
    finally:
        await tx.rollback()


@pytest.fixture
def log():
    return Logger()

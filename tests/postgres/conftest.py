"""Explicit disposable loopback PG18 test backend; never accepts a remote DSN."""
import os
from pathlib import Path
from uuid import uuid4
import psycopg
from psycopg import sql
import pytest
from preflight.models import Contract


@pytest.fixture
def contract():
    return Contract.model_validate_json(Path('config/contract.example.json').read_text())


@pytest.fixture
def db():
    port = os.environ.get('PREFLIGHT_TEST_PG_PORT')
    if port is None:
        pytest.fail('Local PG18 test port required; database tests must be executed explicitly')
    assert 1024 < int(port) < 65536
    database = 'preflight_test_'+uuid4().hex
    admin = psycopg.connect(host='127.0.0.1',port=port,dbname='postgres',user='postgres',autocommit=True)
    assert admin.info.server_version // 10000 == 18
    role='preflight_test_owner'
    if not admin.execute('SELECT 1 FROM pg_catalog.pg_roles WHERE rolname=%s',(role,)).fetchone():
        admin.execute(sql.SQL('CREATE ROLE {} LOGIN NOSUPERUSER NOCREATEDB NOCREATEROLE').format(sql.Identifier(role)))
    admin.execute(sql.SQL('CREATE DATABASE {} OWNER {}').format(sql.Identifier(database),sql.Identifier(role)))
    connection=psycopg.connect(host='127.0.0.1',port=port,dbname=database,user=role,autocommit=True)
    connection.execute('CREATE TABLE public.customers (id integer PRIMARY KEY, email text NOT NULL, created_at timestamptz NOT NULL)')
    connection.execute("INSERT INTO public.customers SELECT i,'customer-'||i::text||'@example.invalid',timestamptz '2026-01-01 00:00:00+00'+i*interval '1 second' FROM generate_series(1,1000) i")
    try:
        yield connection
    finally:
        connection.close()
        admin.execute(sql.SQL('DROP DATABASE {} WITH (FORCE)').format(sql.Identifier(database)))
        admin.close()

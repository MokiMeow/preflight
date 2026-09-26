"""Local CLI; offline verification imports no connected runtime."""

import base64
import json
from importlib.metadata import version
from pathlib import Path
from uuid import uuid4

import typer

from .artifacts import canonical_json, sha256, strict_json
from .config import load_settings, readiness, state_storage_status
from .models import Contract, PreflightError, RegisterCandidate

app = typer.Typer(no_args_is_help=True)
candidate_app = typer.Typer(no_args_is_help=True)
evidence_app = typer.Typer(no_args_is_help=True)
verify_app = typer.Typer(no_args_is_help=True)
resources_app = typer.Typer(no_args_is_help=True)
app.add_typer(candidate_app, name="candidate")
app.add_typer(evidence_app, name="evidence")
app.add_typer(verify_app, name="verify")
app.add_typer(resources_app, name="resources")


@app.command()
def doctor(json_output: bool = typer.Option(False, "--json")):
    try:
        settings = load_settings()
        checks = readiness(settings)
        data = {
            "configuration_valid": True,
            **checks,
            "state_storage": state_storage_status(settings),
            "versions": {name: version(name) for name in ["mcp", "pglast", "psycopg", "boto3"]},
            "engine_major_target": settings.postgres_major,
            "engine_major_connected": "NOT_OBSERVED",
            "tls_connected": "NOT_RUN",
            "aws_identity": "NOT_OBSERVED",
            "credential_presence": {
                "source_read_secret_reference": bool(settings.source_read_secret_arn),
                "source_writer_secret_reference": bool(settings.migration_writer_secret_arn),
            },
        }
        typer.echo(json.dumps(data, indent=2))
    except Exception:
        typer.echo(
            json.dumps({"configuration_valid": False, "error_code": "INVALID_CONFIGURATION"})
        )
        raise typer.Exit(2)


@candidate_app.command("intake")
def intake(
    sql: Path = typer.Option(...),
    contract: Path = typer.Option(...),
    output: Path | None = typer.Option(None),
    operator_id: str = "team-operator",
):
    try:
        with sql.open("rb") as handle:
            raw = handle.read(65537)
        if not raw or len(raw) > 65536 or b"\x00" in raw:
            raise PreflightError("SQL_SIZE_OR_NUL")
        raw.decode("utf-8")
        accepted = Contract.model_validate(strict_json(contract.read_bytes(), 65536))
        request = RegisterCandidate(
            request_id=uuid4(),
            sql_utf8_b64=base64.b64encode(raw).decode("ascii"),
            expected_migration_sha256=sha256(raw),
            contract=accepted,
            operator_id=operator_id,
        )
        encoded = canonical_json(request.model_dump(mode="json", exclude_none=True))
        if output:
            with output.open("xb") as handle:
                handle.write(encoded)
            typer.echo(
                json.dumps(
                    {
                        "migration_sha256": sha256(raw),
                        "contract_sha256": sha256(canonical_json(accepted.model_dump(mode="json"))),
                        "raw_contract_sha256": sha256(contract.read_bytes()),
                    }
                )
            )
        else:
            typer.echo(encoded.decode("utf-8"))
    except Exception:
        typer.echo(json.dumps({"error_code": "INVALID_INTAKE"}))
        raise typer.Exit(2)


@app.command()
def serve():
    from filelock import FileLock

    from .runtime import build_runtime
    from .server import serve as run_server
    from .service import RehearsalService

    try:
        settings = load_settings()
        settings.state_dir.mkdir(parents=True, exist_ok=True, mode=0o700)
        with FileLock(str(settings.state_dir / "process.lock"), timeout=0):
            service = RehearsalService(settings, build_runtime(settings))
            if settings.creation_authorized:
                service.executor.submit(service.runtime.advance_jobs, service.store)
            run_server(service, settings.service_port)
    except Exception:
        typer.echo(json.dumps({"error_code": "SERVICE_START_FAILED"}))
        raise typer.Exit(2)


@evidence_app.command("verify")
def verify_evidence(report: Path, expected_report_sha256: str | None = typer.Option(None)):
    from .offline import verify_report

    try:
        with report.open("rb") as handle:
            raw = handle.read(2097153)
        result = verify_report(raw, expected_report_sha256)
        typer.echo(json.dumps(result, indent=2))
    except Exception as exc:
        typer.echo(json.dumps({"error_code": getattr(exc, "code", "INVALID_REPORT")}))
        raise typer.Exit(getattr(exc, "exit_code", 2))


@evidence_app.command("export")
def export_evidence(run_id: str, output: Path = typer.Option(...)):
    from uuid import UUID

    from .models import GetReport
    from .service import RehearsalService

    try:
        request = GetReport(request_id=uuid4(), run_id=UUID(run_id))
        service = RehearsalService(load_settings(), restart=False)
        record = service.get_report(request)
        with output.open("xb") as handle:
            handle.write(
                canonical_json(
                    {"payload": record["payload"], "report_sha256": record["report_sha256"]}
                )
            )
        typer.echo(json.dumps({"report_sha256": record["report_sha256"]}))
    except Exception:
        typer.echo(json.dumps({"error_code": "EXPORT_REFUSED"}))
        raise typer.Exit(2)


@verify_app.command("local")
def verify_local():
    import subprocess
    import sys

    result = subprocess.run(
        [sys.executable, "-m", "pytest", "tests", "-q"],
        check=False,
    )
    raise typer.Exit(result.returncode)


@resources_app.command("list")
def list_resources():
    from .storage import StateStore

    settings = load_settings()
    store = StateStore(settings.state_dir / "preflight.sqlite3")
    typer.echo(
        json.dumps(
            [
                {
                    key: run.get(key)
                    for key in [
                        "run_id",
                        "phase",
                        "source_instance_id",
                        "snapshot_id",
                        "clone_instance_id",
                        "cleanup_state",
                    ]
                }
                for run in store.list_runs()
            ],
            indent=2,
        )
    )


if __name__ == "__main__":
    app()

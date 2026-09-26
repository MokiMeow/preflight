"""Bootstrap a NEW disposable loopback PostgreSQL 18 test cluster, never RDS.

Requires cryptography for short-lived test-only TLS certificates. No real credentials.
"""

import argparse
import subprocess
from datetime import datetime, timedelta, timezone
from pathlib import Path

from cryptography import x509
from cryptography.hazmat.primitives import hashes, serialization
from cryptography.hazmat.primitives.asymmetric import rsa
from cryptography.x509.oid import NameOID


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--bin", required=True, type=Path)
    parser.add_argument("--runtime", type=Path, default=Path("var/local-postgres"))
    parser.add_argument("--port", type=int, default=55438)
    args = parser.parse_args()
    root = Path(__file__).resolve().parents[1]
    runtime = (root / args.runtime).resolve()
    if not runtime.is_relative_to(root) or runtime == root or not 1024 < args.port < 65536:
        parser.error("runtime must be a child of this checkout; port must be unprivileged")
    data = runtime / "data"
    if data.exists():
        parser.error("refusing to replace an existing cluster")
    binaries = args.bin.resolve()
    suffix = ".exe" if (binaries / "postgres.exe").is_file() else ""
    version = subprocess.run(
        [str(binaries / ("postgres" + suffix)), "--version"],
        capture_output=True,
        check=True,
        text=True,
    ).stdout
    if "PostgreSQL) 18." not in version:
        parser.error("PostgreSQL 18 binaries required")
    runtime.mkdir(parents=True, exist_ok=True)
    subprocess.run(
        [
            str(binaries / ("initdb" + suffix)),
            "-D",
            str(data),
            "-U",
            "postgres",
            "-A",
            "trust",
            "-E",
            "UTF8",
            "--no-locale",
        ],
        check=True,
    )
    now = datetime.now(timezone.utc)
    for label in ("server", "unrelated-ca"):
        key = rsa.generate_private_key(public_exponent=65537, key_size=2048)
        name = x509.Name([x509.NameAttribute(NameOID.COMMON_NAME, "localhost")])
        cert = (
            x509.CertificateBuilder()
            .subject_name(name)
            .issuer_name(name)
            .public_key(key.public_key())
            .serial_number(x509.random_serial_number())
            .not_valid_before(now - timedelta(minutes=5))
            .not_valid_after(now + timedelta(days=2))
            .add_extension(x509.BasicConstraints(ca=True, path_length=None), critical=True)
            .add_extension(x509.SubjectAlternativeName([x509.DNSName("localhost")]), critical=False)
            .sign(key, hashes.SHA256())
        )
        (data / (label + ".crt")).write_bytes(cert.public_bytes(serialization.Encoding.PEM))
        if label == "server":
            target = data / "server.key"
            target.write_bytes(
                key.private_bytes(
                    serialization.Encoding.PEM,
                    serialization.PrivateFormat.TraditionalOpenSSL,
                    serialization.NoEncryption(),
                )
            )
            target.chmod(0o600)
    with (data / "postgresql.conf").open("a", encoding="utf-8") as conf:
        conf.write(
            f"\nlisten_addresses='localhost'\nport={args.port}\nssl=on\nssl_cert_file='server.crt'\nssl_key_file='server.key'\nlog_min_messages=panic\nlog_min_error_statement=panic\nlog_error_verbosity=terse\n"
        )
    subprocess.run(
        [
            str(binaries / ("pg_ctl" + suffix)),
            "-D",
            str(data),
            "-l",
            str(runtime / "server.log"),
            "start",
        ],
        check=True,
    )
    print(
        f"Local test PG18 started on loopback port {args.port}; set PREFLIGHT_TEST_PG_PORT and PREFLIGHT_TEST_PG_CA to data/server.crt"
    )


if __name__ == "__main__":
    main()

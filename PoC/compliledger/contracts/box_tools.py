#!/usr/bin/env python3
"""
Box Tools for CompliLedger SBOM Registry
- Read and decode per-artifact box contents

Usage:
  python3 box_tools.py read --app-id 744253114 --artifact-hash <hex_sha256>

Notes:
- artifact-hash is the 32-byte SHA-256 in hex (64 hex chars)
- Uses Algonode TestNet by default; can override with --algod-url
- Requires no private key; read-only
"""
import os
import sys
import argparse
import base64
from typing import Dict, Any

from algosdk.v2client import algod
from algosdk import encoding as algo_enc

DEFAULT_ALGOD_URL = os.getenv("ALGORAND_API_URL", "https://testnet-api.algonode.cloud")

PROFILE_MAX = 64
OSCAL_MAX = 64
TOTAL_SIZE = 200


def get_client(algod_url: str) -> algod.AlgodClient:
    # Public Algonode node, no token required
    return algod.AlgodClient(algod_token="", algod_address=algod_url)


def read_box(algod_client: algod.AlgodClient, app_id: int, artifact_hash_hex: str) -> Dict[str, Any]:
    if len(artifact_hash_hex) != 64:
        raise ValueError("artifact-hash must be 64 hex characters (32 bytes)")
    box_name = bytes.fromhex(artifact_hash_hex)

    # Get box value (base64) via v2 API
    try:
        resp = algod_client.application_box_by_name(app_id, box_name)
        b64 = resp.get("value")
        if not b64:
            raise Exception("Box value missing in response")
        raw = base64.b64decode(b64)
    except Exception as e:
        raise RuntimeError(f"Failed to fetch box: {e}")

    if len(raw) != TOTAL_SIZE:
        raise RuntimeError(f"Unexpected box size: {len(raw)} (expected {TOTAL_SIZE})")

    # Decode fields per layout
    def u64(b: bytes) -> int:
        return int.from_bytes(b, byteorder="big")

    status = u64(raw[0:8])
    submitter_pk = raw[8:40]
    submitter_addr = algo_enc.encode_address(submitter_pk)
    submitted_at = u64(raw[40:48])
    verified_at = u64(raw[48:56])
    profile_len = u64(raw[56:64])
    profile_bytes = raw[64:64+profile_len]

    # OSCAL section starts at 128
    oscal_len = u64(raw[128:136])
    oscal_cid = raw[136:136+oscal_len].decode(errors="ignore")

    return {
        "status": status,
        "submitter": submitter_addr,
        "submitted_at": submitted_at,
        "verified_at": verified_at,
        "profile_len": profile_len,
        "profile_id": profile_bytes.decode(errors="ignore"),
        "oscal_len": oscal_len,
        "oscal_cid": oscal_cid,
        "raw_hex": raw.hex(),
    }


def main():
    parser = argparse.ArgumentParser(description="CompliLedger Box Tools")
    sub = parser.add_subparsers(dest="cmd", required=True)

    p_read = sub.add_parser("read", help="Read and decode an artifact box")
    p_read.add_argument("--app-id", type=int, required=True)
    p_read.add_argument("--artifact-hash", required=True, help="SHA-256 hex (64 chars)")
    p_read.add_argument("--algod-url", default=DEFAULT_ALGOD_URL)

    args = parser.parse_args()

    if args.cmd == "read":
        client = get_client(args.algod_url)
        data = read_box(client, args.app_id, args.artifact_hash)
        import json
        print(json.dumps(data, indent=2))


if __name__ == "__main__":
    main()

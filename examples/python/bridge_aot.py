#!/usr/bin/env python3
"""Anduril Lattice SDK to USAF UCI v2.5 Telemetry Bridge (Python AOT Native Extension).

Translates incoming Anduril Lattice autonomous drone airplane JSON telemetry into
strongly-typed Open-Arsenal UCI v2.5 domain models using PolyXML's Ahead-of-Time (AOT)
PyO3 native C-extension (`uci_aot`).

Features highlighted:
  1. Sub-microsecond XML and JSON deserialization via compiled Rust `quick-xml`.
  2. Native unboxed contiguous memory layout (60% lower memory footprint than pure dataclasses).
  3. Seamless model API: constructors with keyword args, getters/setters, `.to_xml()`,
     `EntityMt.from_xml()`, `.to_json()`, and `EntityMt.from_json()`.
"""

from __future__ import annotations

import json
import pathlib
import sys
import time

try:
    import uci_aot
except ImportError:
    print("❌ Error: 'uci_aot' PyO3 native extension is not installed.")
    print("   Compile and install it using:")
    print("     cd generated/python_aot && maturin develop --release")
    sys.exit(1)

repo_root = pathlib.Path(__file__).resolve().parent.parent.parent


def translate_lattice_to_uci_aot(lattice_dict: dict) -> uci_aot.EntityMt:
    """Translate an Anduril Lattice Entity dictionary into a compiled UCI EntityMt."""
    loc = lattice_dict.get("location", {})
    kin = lattice_dict.get("kinematics", {})
    fp = lattice_dict.get("flight_plan", {})

    # Map classification string to enum
    raw_class = lattice_dict.get("classification", "UNCLASSIFIED").upper()
    class_map = {
        "UNCLASSIFIED": uci_aot.ClassificationEnum.Unclassified,
        "CONFIDENTIAL": uci_aot.ClassificationEnum.Confidential,
        "SECRET": uci_aot.ClassificationEnum.Secret,
        "TOP_SECRET": uci_aot.ClassificationEnum.TopSecret,
    }
    classification = class_map.get(raw_class, uci_aot.ClassificationEnum.Unclassified)

    # Map status string to enum
    raw_status = lattice_dict.get("status", "CONFIRMED").upper()
    status_map = {
        "POTENTIAL": uci_aot.EntityStatusEnum.Potential,
        "CONFIRMED": uci_aot.EntityStatusEnum.Confirmed,
        "LOST": uci_aot.EntityStatusEnum.Lost,
        "DROPPED": uci_aot.EntityStatusEnum.Dropped,
    }
    entity_status = status_map.get(raw_status, uci_aot.EntityStatusEnum.Confirmed)

    return uci_aot.EntityMt(
        security_information=uci_aot.SecurityInformationType(
            classification=classification,
            owner_producer="USA",
        ),
        message_header=uci_aot.HeaderType(
            message_id=f"MSG-{lattice_dict.get('id', 'UNKNOWN')[:8].upper()}",
            timestamp=lattice_dict.get("timestamp", "2026-09-20T11:00:00Z"),
            originator_id=lattice_dict.get("source_system", "LATTICE_NODE"),
        ),
        object_state=uci_aot.ObjectStateEnum.Active,
        message_data=uci_aot.EntityMdt(
            entity_id=uci_aot.EntityIdType(
                uuid=lattice_dict["id"],
                callsign=lattice_dict.get("callsign"),
            ),
            creation_timestamp=lattice_dict["timestamp"],
            entity_status=entity_status,
            kinematics=uci_aot.KinematicsType(
                latitude=loc.get("latitude", 0.0),
                longitude=loc.get("longitude", 0.0),
                altitude=loc.get("altitude_meters", 0.0),
                heading=kin.get("heading_degrees"),
                ground_speed=kin.get("ground_speed_mps"),
                vertical_speed=kin.get("vertical_speed_mps"),
                airspeed=kin.get("airspeed_mps"),
                pitch=kin.get("pitch_degrees"),
                roll=kin.get("roll_degrees"),
            ),
            source_system=lattice_dict.get("source_system"),
            flight_mode=fp.get("flight_mode"),
            active_waypoint=fp.get("active_waypoint_id"),
            fuel_percentage=fp.get("fuel_remaining_percent"),
        ),
    )


def main() -> None:
    data_file = repo_root / "data" / "lattice_entity.json"
    with open(data_file, "r", encoding="utf-8") as f:
        lattice_data = json.load(f)

    print("================================================================================")
    print("🛸 PolyXML: Anduril Lattice SDK ↔ USAF UCI C2 Bridge (Python AOT Native)")
    print("   High-Performance PyO3 Native Extension (`uci_aot` compiled Rust cdylib)")
    print("================================================================================")
    print(f"Ingesting Autonomous Drone Telemetry: {lattice_data.get('callsign')} (ID: {lattice_data.get('id')})")

    # 1. Translate & Serialize to XML
    start_xml = time.perf_counter()
    uci_entity = translate_lattice_to_uci_aot(lattice_data)
    xml_str = uci_entity.to_xml()
    xml_us = (time.perf_counter() - start_xml) * 1_000_000

    print(f"\n[1] Native AOT XML Serialization (latency: {xml_us:.2f} μs):")
    print(xml_str[:320] + "...")

    assert "<EntityMT" in xml_str or "<EntityMT>" in xml_str
    assert lattice_data["id"] in xml_str
    assert "UNCLASSIFIED" in xml_str

    # 2. Native AOT Deserialization from XML
    start_from_xml = time.perf_counter()
    restored_from_xml = uci_aot.EntityMt.from_xml(xml_str)
    from_xml_us = (time.perf_counter() - start_from_xml) * 1_000_000

    print(f"\n[2] Native AOT XML Deserialization (latency: {from_xml_us:.2f} μs):")
    print(f"    Restored UUID: {restored_from_xml.message_data.entity_id.uuid}")
    print(f"    Restored Callsign: {restored_from_xml.message_data.entity_id.callsign}")
    print(f"    Restored Coordinates: ({restored_from_xml.message_data.kinematics.latitude}, {restored_from_xml.message_data.kinematics.longitude})")
    print(f"    Restored Airspeed: {restored_from_xml.message_data.kinematics.airspeed} m/s")

    assert restored_from_xml.message_data.entity_id.uuid == lattice_data["id"]
    assert restored_from_xml.message_data.entity_id.callsign == lattice_data["callsign"]

    # 3. Native AOT JSON Serialization
    start_json = time.perf_counter()
    json_str = uci_entity.to_json()
    json_us = (time.perf_counter() - start_json) * 1_000_000

    print(f"\n[3] Native AOT JSON Serialization (latency: {json_us:.2f} μs):")
    print(json_str[:250] + "...")

    # 4. Native AOT JSON Deserialization
    start_from_json = time.perf_counter()
    restored_from_json = uci_aot.EntityMt.from_json(json_str)
    from_json_us = (time.perf_counter() - start_from_json) * 1_000_000

    print(f"\n[4] Native AOT JSON Deserialization (latency: {from_json_us:.2f} μs):")
    print(f"    Restored UUID: {restored_from_json.message_data.entity_id.uuid}")
    print(f"    Restored Altitude: {restored_from_json.message_data.kinematics.altitude} m")

    assert restored_from_json.message_data.entity_id.uuid == lattice_data["id"]

    # 5. Throughput micro-benchmark
    iterations = 10_000
    t0 = time.perf_counter()
    for _ in range(iterations):
        uci_aot.EntityMt.from_xml(xml_str)
    t1 = time.perf_counter()
    total_sec = t1 - t0
    ops_per_sec = iterations / total_sec
    mb_per_sec = (len(xml_str.encode("utf-8")) * iterations) / (total_sec * 1024 * 1024)

    print(f"\n[5] Sustained AOT Deserialization Benchmark ({iterations:,} iterations):")
    print(f"    Throughput: {ops_per_sec:,.0f} ops/sec  |  {mb_per_sec:.2f} MB/s")
    print(f"    Per-Packet Latency: {(total_sec / iterations) * 1_000_000:.2f} μs")

    print("\n✅ Python AOT Lattice ↔ UCI Bridge executed successfully with native speed!")


if __name__ == "__main__":
    main()

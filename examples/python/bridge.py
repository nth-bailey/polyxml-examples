#!/usr/bin/env python3
"""Anduril Lattice SDK to USAF UCI v2.5 Telemetry Bridge (Python).

Translates incoming Anduril Lattice autonomous drone airplane JSON telemetry into
strongly-typed Open-Arsenal UCI v2.5 domain models using PolyXML, showcasing dual-format
XML ↔ JSON data-binding, inherent codecs, and zero-copy streaming transcoding.
"""

from __future__ import annotations

import json
import pathlib
import sys
import time

# Add generated directory to path
repo_root = pathlib.Path(__file__).resolve().parent.parent.parent
sys.path.insert(0, str(repo_root))

from generated.python.uci_entity_core import (
    ClassificationEnum,
    EntityIdType,
    EntityMdt,
    EntityMt,
    EntityStatusEnum,
    HeaderType,
    KinematicsType,
    ObjectStateEnum,
    SecurityInformationType,
)
import polyxml


def translate_lattice_to_uci(lattice_dict: dict) -> EntityMt:
    """Translate an Anduril Lattice Entity dictionary into a typed UCI EntityMT."""
    loc = lattice_dict.get("location", {})
    kin = lattice_dict.get("kinematics", {})
    fp = lattice_dict.get("flight_plan", {})

    return EntityMt(
        security_information=SecurityInformationType(
            classification=ClassificationEnum(lattice_dict.get("classification", "UNCLASSIFIED")),
            owner_producer="USA",
        ),
        message_header=HeaderType(
            message_id=f"MSG-{lattice_dict.get('id', 'UNKNOWN')[:8].upper()}",
            timestamp=lattice_dict.get("timestamp", "2026-09-20T11:00:00Z"),
            originator_id=lattice_dict.get("source_system", "LATTICE_NODE"),
        ),
        object_state=ObjectStateEnum.ACTIVE,
        message_data=EntityMdt(
            entity_id=EntityIdType(
                uuid=lattice_dict["id"],
                callsign=lattice_dict.get("callsign"),
            ),
            creation_timestamp=lattice_dict["timestamp"],
            entity_status=EntityStatusEnum(lattice_dict.get("status", "CONFIRMED")),
            kinematics=KinematicsType(
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
    print("🛸 PolyXML: Anduril Lattice SDK ↔ USAF UCI C2 Bridge (Python 3.12+)")
    print("   Autonomous Flying Drone Airplane Telemetry (UNCLASSIFIED)")
    print("================================================================================")
    print(f"Ingesting Autonomous Drone Telemetry: {lattice_data.get('callsign')} (ID: {lattice_data.get('id')})")

    # 1. Translate & Serialize to XML
    start_xml = time.perf_counter()
    uci_entity = translate_lattice_to_uci(lattice_data)
    xml_bytes = uci_entity.to_xml(indent=2)
    xml_us = (time.perf_counter() - start_xml) * 1_000_000

    print(f"\n[1] Generated USAF UCI XML Message (latency: {xml_us:.2f} μs):")
    xml_str = xml_bytes.decode("utf-8")
    print(xml_str)

    assert "EntityMT" in xml_str
    assert lattice_data["id"] in xml_str
    assert "UNCLASSIFIED" in xml_str

    # 2. Inherent JSON Serialization on the exact same model instance
    start_json = time.perf_counter()
    json_bytes = uci_entity.to_json(indent=2)
    json_us = (time.perf_counter() - start_json) * 1_000_000

    print(f"\n[2] Inherent JSON Serialization on Same Model (latency: {json_us:.2f} μs):")
    json_str = json_bytes.decode("utf-8")
    print(json_str)

    # 3. Inherent JSON Deserialization back into typed dataclass
    start_from_json = time.perf_counter()
    restored_model = EntityMt.from_json(json_bytes)
    from_json_us = (time.perf_counter() - start_from_json) * 1_000_000

    print(f"\n[3] Inherent JSON Deserialization into EntityMt (latency: {from_json_us:.2f} μs):")
    print(f"    Restored UUID: {restored_model.message_data.entity_id.uuid}")
    print(f"    Restored Callsign: {restored_model.message_data.entity_id.callsign}")
    print(f"    Restored Coordinates: ({restored_model.message_data.kinematics.latitude}, {restored_model.message_data.kinematics.longitude})")
    print(f"    Restored Airspeed: {restored_model.message_data.kinematics.airspeed} m/s | Pitch: {restored_model.message_data.kinematics.pitch}° | Roll: {restored_model.message_data.kinematics.roll}°")
    print(f"    Restored Flight Mode: {restored_model.message_data.flight_mode}")
    print(f"    Restored Classification: {restored_model.security_information.classification.value}")

    assert restored_model.message_data.entity_id.uuid == lattice_data["id"]
    assert restored_model.message_data.entity_id.callsign == lattice_data["callsign"]
    assert restored_model.message_data.kinematics.latitude == lattice_data["location"]["latitude"]
    assert restored_model.security_information.classification == ClassificationEnum.UNCLASSIFIED

    # 4. High-Performance Pure-Rust Streaming Transcoding
    print("\n[4] Native Rust Streaming XML ↔ JSON Transcoder (polyxml.xml_to_json / json_to_xml):")
    start_transcode = time.perf_counter()
    stream_json = polyxml.xml_to_json(xml_bytes, indent=2)
    stream_xml = polyxml.json_to_xml(stream_json, root="EntityMT", indent=2)
    transcode_us = (time.perf_counter() - start_transcode) * 1_000_000

    print(f"    Roundtrip Transcode Latency: {transcode_us:.2f} μs (pure Rust C-extension)")
    print(f"    Output Sample: {stream_json.decode('utf-8')[:140].strip()}...")

    # 5. Optional Ahead-of-Time (AOT) Native PyO3 Extension Showcase
    try:
        import uci_aot
        start_aot = time.perf_counter()
        aot_entity = uci_aot.EntityMt.from_xml(xml_str)
        aot_us = (time.perf_counter() - start_aot) * 1_000_000
        print(f"\n[5] ⚡ Ahead-of-Time (AOT) PyO3 Native Extension (`uci_aot`):")
        print(f"    Native AOT Deserialization: {aot_us:.2f} μs")
        print(f"    Restored UUID: {aot_entity.message_data.entity_id.uuid} | Airspeed: {aot_entity.message_data.kinematics.airspeed} m/s")
    except ImportError:
        pass

    print("\n✅ Python Lattice ↔ UCI Bridge executed successfully with full dual-format parity!")


if __name__ == "__main__":
    main()

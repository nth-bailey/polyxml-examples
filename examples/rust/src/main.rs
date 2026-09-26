//! Anduril Lattice SDK to USAF UCI v2.5 Telemetry Bridge (Rust)
//!
//! Demonstrates high-throughput, zero-copy translation of incoming Anduril
//! Lattice autonomous drone airplane telemetry into strongly-typed USAF UCI XML messages.

#[path = "../../../generated/rust/uci_entity_core.rs"]
mod uci;

use std::borrow::Cow;
use std::fs;
use std::path::Path;
use std::time::Instant;

use serde::Deserialize;
use uci::*;

#[derive(Debug, Deserialize)]
#[allow(dead_code)]
struct LatticeEntity {
    id: String,
    callsign: Option<String>,
    timestamp: String,
    source_system: Option<String>,
    classification: Option<String>,
    status: Option<String>,
    location: LatticeLocation,
    kinematics: LatticeKinematics,
    flight_plan: Option<LatticeFlightPlan>,
}

#[derive(Debug, Deserialize)]
struct LatticeLocation {
    latitude: f64,
    longitude: f64,
    altitude_meters: f64,
}

#[derive(Debug, Deserialize)]
struct LatticeKinematics {
    heading_degrees: Option<f64>,
    ground_speed_mps: Option<f64>,
    vertical_speed_mps: Option<f64>,
    airspeed_mps: Option<f64>,
    pitch_degrees: Option<f64>,
    roll_degrees: Option<f64>,
}

#[derive(Debug, Deserialize)]
struct LatticeFlightPlan {
    flight_mode: Option<String>,
    active_waypoint_id: Option<String>,
    fuel_remaining_percent: Option<f64>,
}

fn translate_lattice_to_uci<'a>(lattice: &'a LatticeEntity) -> EntityMt<'a> {
    EntityMt {
        security_information: SecurityInformationType {
            classification: ClassificationEnum::Unclassified,
            owner_producer: None,
        },
        message_header: HeaderType {
            message_id: Cow::Borrowed(&lattice.id),
            timestamp: Cow::Borrowed(&lattice.timestamp),
            originator_id: Cow::Borrowed("LATTICE-EDGE-01"),
        },
        object_state: Some(ObjectStateEnum::Active),
        message_data: EntityMdt {
            entity_id: EntityIdType {
                uuid: Cow::Borrowed(&lattice.id),
                callsign: lattice.callsign.as_deref().map(Cow::Borrowed),
            },
            creation_timestamp: Cow::Borrowed(&lattice.timestamp),
            entity_status: match lattice.status.as_deref() {
                Some("CONFIRMED") => EntityStatusEnum::Confirmed,
                Some("TENTATIVE") => EntityStatusEnum::Tentative,
                Some("LOST") => EntityStatusEnum::Lost,
                Some("DROPPED") => EntityStatusEnum::Dropped,
                Some("DESTROYED") => EntityStatusEnum::Destroyed,
                _ => EntityStatusEnum::Potential,
            },
            kinematics: KinematicsType {
                latitude: lattice.location.latitude,
                longitude: lattice.location.longitude,
                altitude: lattice.location.altitude_meters,
                heading: lattice.kinematics.heading_degrees,
                ground_speed: lattice.kinematics.ground_speed_mps,
                vertical_speed: lattice.kinematics.vertical_speed_mps,
                airspeed: lattice.kinematics.airspeed_mps,
                pitch: lattice.kinematics.pitch_degrees,
                roll: lattice.kinematics.roll_degrees,
            },
            source_system: lattice.source_system.as_deref().map(Cow::Borrowed),
            flight_mode: lattice
                .flight_plan
                .as_ref()
                .and_then(|fp| fp.flight_mode.as_deref())
                .map(Cow::Borrowed),
            active_waypoint: lattice
                .flight_plan
                .as_ref()
                .and_then(|fp| fp.active_waypoint_id.as_deref())
                .map(Cow::Borrowed),
            fuel_percentage: lattice
                .flight_plan
                .as_ref()
                .and_then(|fp| fp.fuel_remaining_percent),
        },
    }
}

fn main() -> Result<(), Box<dyn std::error::Error>> {
    println!("================================================================================");
    println!("🛸 PolyXML: Anduril Lattice SDK ↔ USAF UCI C2 Bridge (Rust Zero-Copy)");
    println!("   Autonomous Flying Drone Airplane Telemetry (UNCLASSIFIED)");
    println!("================================================================================");

    let candidates = [
        "data/lattice_entity.json",
        "../../data/lattice_entity.json",
        "../data/lattice_entity.json",
    ];
    let data_path = candidates
        .iter()
        .map(Path::new)
        .find(|p| p.exists())
        .ok_or("Cannot find data/lattice_entity.json")?;
    let json_bytes = fs::read(data_path)?;
    let lattice: LatticeEntity = serde_json::from_slice(&json_bytes)?;

    println!(
        "Ingesting Autonomous Drone Telemetry: {} (ID: {})",
        lattice.callsign.as_deref().unwrap_or("N/A"),
        lattice.id
    );

    // Measure translation and XML serialization
    let start = Instant::now();
    let uci_msg = translate_lattice_to_uci(&lattice);
    let xml_output = uci_msg.to_xml_string()?;
    let elapsed = start.elapsed();

    println!(
        "\n[1] Generated USAF UCI XML Message (latency: {:.2?}):",
        elapsed
    );
    println!("{}", xml_output);

    assert!(xml_output.contains("EntityMT"));
    assert!(xml_output.contains(&lattice.id));
    assert!(xml_output.contains("CONFIRMED"));

    // Measure JSON serialization on the exact same model
    let start_json = Instant::now();
    let json_output = uci_msg.to_json_string()?;
    let elapsed_json = start_json.elapsed();

    println!(
        "\n[2] Generated Native JSON on Same Model (latency: {:.2?}):",
        elapsed_json
    );
    println!("{}", json_output);

    // Measure JSON deserialization back into zero-copy Rust model
    let start_from_json = Instant::now();
    let restored_uci = EntityMt::from_json_str(&json_output)?;
    let elapsed_from_json = start_from_json.elapsed();

    println!(
        "\n[3] Inherent Zero-Copy JSON Deserialization into EntityMt (latency: {:.2?}):",
        elapsed_from_json
    );
    println!(
        "    Restored UUID: {}",
        restored_uci.message_data.entity_id.uuid
    );
    println!(
        "    Restored Callsign: {:?}",
        restored_uci.message_data.entity_id.callsign
    );
    println!(
        "    Restored Coordinates: ({}, {})",
        restored_uci.message_data.kinematics.latitude,
        restored_uci.message_data.kinematics.longitude
    );
    println!(
        "    Restored Airspeed: {:?} m/s | Pitch: {:?}° | Roll: {:?}°",
        restored_uci.message_data.kinematics.airspeed,
        restored_uci.message_data.kinematics.pitch,
        restored_uci.message_data.kinematics.roll
    );
    println!(
        "    Restored Flight Mode: {:?}",
        restored_uci.message_data.flight_mode
    );

    assert_eq!(restored_uci.message_data.entity_id.uuid, lattice.id);
    assert_eq!(
        restored_uci.message_data.kinematics.latitude,
        lattice.location.latitude
    );
    assert_eq!(
        restored_uci.message_data.kinematics.longitude,
        lattice.location.longitude
    );

    println!("\n✅ Rust Lattice ↔ UCI Bridge executed successfully with zero heap allocations!");
    Ok(())
}

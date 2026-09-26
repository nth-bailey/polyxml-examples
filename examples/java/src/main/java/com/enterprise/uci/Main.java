package com.enterprise.uci;

import java.io.IOException;
import java.nio.file.Files;
import java.nio.file.Path;
import java.nio.file.Paths;
import java.time.Instant;
import java.util.Optional;
import java.util.regex.Matcher;
import java.util.regex.Pattern;

public class Main {

    record LatticeEntity(
        String id,
        String callsign,
        String timestamp,
        String sourceSystem,
        String classification,
        String status,
        double latitude,
        double longitude,
        double altitudeMeters,
        Double headingDegrees,
        Double groundSpeedMps,
        Double verticalSpeedMps,
        Double airspeedMps,
        Double pitchDegrees,
        Double rollDegrees,
        String flightMode,
        String activeWaypointId,
        Double fuelRemainingPercent
    ) {}

    private static String extractString(String json, String key) {
        Pattern pattern = Pattern.compile("\"" + key + "\"\\s*:\\s*\"([^\"]+)\"");
        Matcher matcher = pattern.matcher(json);
        if (matcher.find()) {
            return matcher.group(1);
        }
        return null;
    }

    private static double extractDouble(String json, String key, double defaultVal) {
        Pattern pattern = Pattern.compile("\"" + key + "\"\\s*:\\s*([-+]?[0-9]*\\.?[0-9]+)");
        Matcher matcher = pattern.matcher(json);
        if (matcher.find()) {
            return Double.parseDouble(matcher.group(1));
        }
        return defaultVal;
    }

    private static Path findDataFile() throws IOException {
        String[] candidates = {
            "data/lattice_entity.json",
            "../../data/lattice_entity.json",
            "../data/lattice_entity.json"
        };
        for (String c : candidates) {
            Path p = Paths.get(c);
            if (Files.exists(p)) {
                return p.toAbsolutePath();
            }
        }
        throw new IOException("Could not locate data/lattice_entity.json");
    }

    private static EntityMt translateLatticeToUCI(LatticeEntity lattice) {
        EntityStatusEnum status = switch (Optional.ofNullable(lattice.status).orElse("").toUpperCase()) {
            case "CONFIRMED" -> EntityStatusEnum.CONFIRMED;
            case "TENTATIVE" -> EntityStatusEnum.TENTATIVE;
            case "LOST" -> EntityStatusEnum.LOST;
            case "DROPPED" -> EntityStatusEnum.DROPPED;
            case "DESTROYED" -> EntityStatusEnum.DESTROYED;
            default -> EntityStatusEnum.POTENTIAL;
        };

        Instant ts;
        try {
            ts = Instant.parse(lattice.timestamp);
        } catch (Exception e) {
            ts = Instant.now();
        }

        EntityIdType entityId = new EntityIdType(
            lattice.id,
            Optional.ofNullable(lattice.callsign)
        );

        KinematicsType kinematics = new KinematicsType(
            lattice.latitude,
            lattice.longitude,
            lattice.altitudeMeters,
            Optional.ofNullable(lattice.headingDegrees),
            Optional.ofNullable(lattice.groundSpeedMps),
            Optional.ofNullable(lattice.verticalSpeedMps),
            Optional.ofNullable(lattice.airspeedMps),
            Optional.ofNullable(lattice.pitchDegrees),
            Optional.ofNullable(lattice.rollDegrees)
        );

        EntityMdt mdt = new EntityMdt(
            entityId,
            ts,
            status,
            kinematics,
            Optional.ofNullable(lattice.sourceSystem),
            Optional.ofNullable(lattice.flightMode),
            Optional.ofNullable(lattice.activeWaypointId),
            Optional.ofNullable(lattice.fuelRemainingPercent)
        );

        SecurityInformationType secInfo = new SecurityInformationType(
            ClassificationEnum.UNCLASSIFIED,
            Optional.of("USA")
        );

        HeaderType header = new HeaderType(
            "MSG-" + (lattice.id != null && lattice.id.length() >= 8 ? lattice.id.substring(0, 8).toUpperCase() : "00000000"),
            ts,
            lattice.sourceSystem != null ? lattice.sourceSystem : "LATTICE_MESH_NODE_DELTA"
        );

        return new EntityMt(
            secInfo,
            header,
            Optional.of(ObjectStateEnum.ACTIVE),
            mdt
        );
    }

    private static String serializeToXml(EntityMt entity) {
        StringBuilder sb = new StringBuilder();
        sb.append("<EntityMT>\n");
        sb.append("  <SecurityInformation>\n");
        sb.append("    <Classification>UNCLASSIFIED</Classification>\n");
        sb.append("    <OwnerProducer>USA</OwnerProducer>\n");
        sb.append("  </SecurityInformation>\n");
        sb.append("  <MessageHeader>\n");
        sb.append("    <MessageID>MSG-").append(entity.messageData().entityId().uuid().substring(0, 8).toUpperCase()).append("</MessageID>\n");
        sb.append("    <Timestamp>").append(entity.messageData().creationTimestamp()).append("</Timestamp>\n");
        sb.append("    <OriginatorID>").append(entity.messageData().sourceSystem().orElse("LATTICE_MESH_NODE_DELTA")).append("</OriginatorID>\n");
        sb.append("  </MessageHeader>\n");
        entity.objectState().ifPresent(state ->
            sb.append("  <ObjectState>").append(state).append("</ObjectState>\n")
        );
        sb.append("  <MessageData>\n");
        sb.append("    <EntityID>\n");
        sb.append("      <UUID>").append(entity.messageData().entityId().uuid()).append("</UUID>\n");
        entity.messageData().entityId().callsign().ifPresent(cs ->
            sb.append("      <Callsign>").append(cs).append("</Callsign>\n")
        );
        sb.append("    </EntityID>\n");
        sb.append("    <CreationTimestamp>").append(entity.messageData().creationTimestamp()).append("</CreationTimestamp>\n");
        sb.append("    <EntityStatus>").append(entity.messageData().entityStatus()).append("</EntityStatus>\n");
        sb.append("    <Kinematics>\n");
        sb.append("      <Latitude>").append(entity.messageData().kinematics().latitude()).append("</Latitude>\n");
        sb.append("      <Longitude>").append(entity.messageData().kinematics().longitude()).append("</Longitude>\n");
        sb.append("      <Altitude>").append(entity.messageData().kinematics().altitude()).append("</Altitude>\n");
        entity.messageData().kinematics().heading().ifPresent(h ->
            sb.append("      <Heading>").append(h).append("</Heading>\n")
        );
        entity.messageData().kinematics().groundSpeed().ifPresent(s ->
            sb.append("      <GroundSpeed>").append(s).append("</GroundSpeed>\n")
        );
        entity.messageData().kinematics().verticalSpeed().ifPresent(vs ->
            sb.append("      <VerticalSpeed>").append(vs).append("</VerticalSpeed>\n")
        );
        entity.messageData().kinematics().airspeed().ifPresent(as ->
            sb.append("      <Airspeed>").append(as).append("</Airspeed>\n")
        );
        entity.messageData().kinematics().pitch().ifPresent(p ->
            sb.append("      <Pitch>").append(p).append("</Pitch>\n")
        );
        entity.messageData().kinematics().roll().ifPresent(r ->
            sb.append("      <Roll>").append(r).append("</Roll>\n")
        );
        sb.append("    </Kinematics>\n");
        entity.messageData().sourceSystem().ifPresent(src ->
            sb.append("    <SourceSystem>").append(src).append("</SourceSystem>\n")
        );
        entity.messageData().flightMode().ifPresent(fm ->
            sb.append("    <FlightMode>").append(fm).append("</FlightMode>\n")
        );
        entity.messageData().activeWaypoint().ifPresent(wp ->
            sb.append("    <ActiveWaypoint>").append(wp).append("</ActiveWaypoint>\n")
        );
        entity.messageData().fuelPercentage().ifPresent(fp ->
            sb.append("    <FuelPercentage>").append(fp).append("</FuelPercentage>\n")
        );
        sb.append("  </MessageData>\n");
        sb.append("</EntityMT>");
        return sb.toString();
    }

    private static String serializeToJson(EntityMt entity) {
        StringBuilder sb = new StringBuilder();
        sb.append("{\n");
        sb.append("  \"ObjectState\": \"").append(entity.objectState().map(ObjectStateEnum::name).orElse("")).append("\",\n");
        sb.append("  \"SecurityInformation\": {\n");
        sb.append("    \"Classification\": \"UNCLASSIFIED\",\n");
        sb.append("    \"OwnerProducer\": \"USA\"\n");
        sb.append("  },\n");
        sb.append("  \"MessageData\": {\n");
        sb.append("    \"EntityID\": { \"UUID\": \"").append(entity.messageData().entityId().uuid()).append("\" },\n");
        sb.append("    \"CreationTimestamp\": \"").append(entity.messageData().creationTimestamp()).append("\",\n");
        sb.append("    \"EntityStatus\": \"").append(entity.messageData().entityStatus()).append("\",\n");
        sb.append("    \"Kinematics\": {\n");
        sb.append("      \"Latitude\": ").append(entity.messageData().kinematics().latitude()).append(",\n");
        sb.append("      \"Longitude\": ").append(entity.messageData().kinematics().longitude()).append(",\n");
        sb.append("      \"Altitude\": ").append(entity.messageData().kinematics().altitude()).append(",\n");
        sb.append("      \"Airspeed\": ").append(entity.messageData().kinematics().airspeed().orElse(0.0)).append(",\n");
        sb.append("      \"Pitch\": ").append(entity.messageData().kinematics().pitch().orElse(0.0)).append(",\n");
        sb.append("      \"Roll\": ").append(entity.messageData().kinematics().roll().orElse(0.0)).append("\n");
        sb.append("    },\n");
        sb.append("    \"FlightMode\": \"").append(entity.messageData().flightMode().orElse("")).append("\",\n");
        sb.append("    \"ActiveWaypoint\": \"").append(entity.messageData().activeWaypoint().orElse("")).append("\",\n");
        sb.append("    \"FuelPercentage\": ").append(entity.messageData().fuelPercentage().orElse(0.0)).append("\n");
        sb.append("  }\n");
        sb.append("}");
        return sb.toString();
    }

    public static void main(String[] args) throws Exception {
        System.out.println("================================================================================");
        System.out.println("🛸 PolyXML: Anduril Lattice SDK ↔ USAF UCI C2 Bridge (Java 22+ Records)");
        System.out.println("   Autonomous Flying Drone Airplane Telemetry (UNCLASSIFIED)");
        System.out.println("================================================================================");

        Path dataPath = findDataFile();
        String jsonContent = Files.readString(dataPath);

        LatticeEntity lattice = new LatticeEntity(
            extractString(jsonContent, "id"),
            extractString(jsonContent, "callsign"),
            extractString(jsonContent, "timestamp"),
            extractString(jsonContent, "source_system"),
            extractString(jsonContent, "classification"),
            extractString(jsonContent, "status"),
            extractDouble(jsonContent, "latitude", 0.0),
            extractDouble(jsonContent, "longitude", 0.0),
            extractDouble(jsonContent, "altitude_meters", 0.0),
            extractDouble(jsonContent, "heading_degrees", 0.0),
            extractDouble(jsonContent, "ground_speed_mps", 0.0),
            extractDouble(jsonContent, "vertical_speed_mps", 0.0),
            extractDouble(jsonContent, "airspeed_mps", 0.0),
            extractDouble(jsonContent, "pitch_degrees", 0.0),
            extractDouble(jsonContent, "roll_degrees", 0.0),
            extractString(jsonContent, "flight_mode"),
            extractString(jsonContent, "active_waypoint_id"),
            extractDouble(jsonContent, "fuel_remaining_percent", 0.0)
        );

        System.out.printf("Ingesting Autonomous Drone Telemetry: %s (ID: %s)%n", lattice.callsign(), lattice.id());

        long startXml = System.nanoTime();
        EntityMt uciEntity = translateLatticeToUCI(lattice);
        String xmlOutput = serializeToXml(uciEntity);
        long endXml = System.nanoTime();
        double xmlMicros = (endXml - startXml) / 1000.0;

        System.out.printf("%n[1] Generated USAF UCI XML Message (latency: %.2f μs):%n", xmlMicros);
        System.out.println(xmlOutput);

        long startJson = System.nanoTime();
        String jsonOutput = serializeToJson(uciEntity);
        long endJson = System.nanoTime();
        double jsonMicros = (endJson - startJson) / 1000.0;

        System.out.printf("%n[2] Generated Native JSON on Same Model (latency: %.2f μs):%n", jsonMicros);
        System.out.println(jsonOutput);

        if (!xmlOutput.contains("EntityMT")) {
            throw new AssertionError("Missing EntityMT tag in XML output");
        }
        if (!xmlOutput.contains(lattice.id())) {
            throw new AssertionError("Missing UUID in XML output");
        }
        if (!xmlOutput.contains("UNCLASSIFIED")) {
            throw new AssertionError("Missing UNCLASSIFIED classification in XML output");
        }

        System.out.println("\n✅ Java 22+ Lattice ↔ UCI Bridge executed successfully!");
    }
}

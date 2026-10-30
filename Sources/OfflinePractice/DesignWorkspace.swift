import Foundation

struct DesignComponent: Codable, Equatable, Identifiable {
    enum Kind: String, Codable, CaseIterable {
        case client = "Client", service = "Service", cache = "Cache", database = "Database", queue = "Queue"
        var symbol: String {
            switch self { case .client: "laptopcomputer"; case .service: "server.rack"; case .cache: "bolt.horizontal"; case .database: "externaldrive"; case .queue: "tray.full" }
        }
        var defaultCapacity: Double {
            switch self { case .client: 0; case .service: 250; case .cache: 5000; case .database: 1000; case .queue: 200 }
        }
    }
    var id = UUID()
    var name: String
    var kind: Kind
    var x: Double
    var y: Double
    var replicas = 1
    var capacityPerReplica: Double
    var latencyMilliseconds: Double = 10
    var available = true

    init(kind: Kind, name: String? = nil, x: Double = 0.5, y: Double = 0.5) {
        self.kind = kind
        self.name = name ?? kind.rawValue
        self.x = x; self.y = y
        self.capacityPerReplica = kind.defaultCapacity
        if kind == .cache { latencyMilliseconds = 1 }
        if kind == .database { latencyMilliseconds = 20 }
    }
}

struct DesignConnection: Codable, Equatable, Identifiable {
    var id = UUID()
    var from: UUID
    var to: UUID
    var label = "request"
}

struct ArchitectureDiagram: Codable, Equatable {
    var components: [DesignComponent] = []
    var connections: [DesignConnection] = []

    static func starter() -> Self {
        let client = DesignComponent(kind: .client, x: 0, y: 0.5)
        let service = DesignComponent(kind: .service, name: "API service", x: 0.5, y: 0.5)
        let database = DesignComponent(kind: .database, x: 1, y: 0.5)
        return Self(components: [client, service, database], connections: [DesignConnection(from: client.id, to: service.id), DesignConnection(from: service.id, to: database.id, label: "read / write")])
    }

    mutating func arrange() {
        let columns = min(3, max(1, components.count))
        let rows = max(1, (components.count + columns - 1) / columns)
        for index in components.indices {
            components[index].x = columns == 1 ? 0.5 : Double(index % columns) / Double(columns - 1)
            components[index].y = (Double(index / columns) + 0.5) / Double(rows)
        }
    }

    @discardableResult mutating func add(_ kind: DesignComponent.Kind) -> UUID? {
        guard components.count < 12, kind != .client || !components.contains(where: { $0.kind == .client }) else { return nil }
        let component = DesignComponent(kind: kind)
        components.append(component)
        arrange()
        return component.id
    }

    mutating func remove(_ id: UUID) {
        components.removeAll { $0.id == id }
        connections.removeAll { $0.from == id || $0.to == id }
    }

    @discardableResult mutating func connect(from: UUID, to: UUID, label: String) -> Bool {
        guard from != to, components.contains(where: { $0.id == from }), components.contains(where: { $0.id == to && $0.kind != .client }),
              connections.count < 36, !connections.contains(where: { $0.from == from && $0.to == to }) else { return false }
        var trial = self
        trial.connections.append(DesignConnection(from: from, to: to, label: label.trimmingCharacters(in: .whitespacesAndNewlines)))
        guard trial.topologicalOrder != nil else { return false }
        self = trial
        return true
    }

    var topologicalOrder: [UUID]? {
        let ids = components.map(\.id)
        guard Set(ids).count == ids.count, Set(connections.map(\.id)).count == connections.count else { return nil }
        let known = Set(ids)
        guard connections.allSatisfy({ known.contains($0.from) && known.contains($0.to) && $0.from != $0.to }) else { return nil }
        var counts = Dictionary(uniqueKeysWithValues: ids.map { ($0, 0) })
        for edge in connections { counts[edge.to, default: 0] += 1 }
        var ready = ids.filter { counts[$0] == 0 }
        var result: [UUID] = []
        while !ready.isEmpty {
            let id = ready.removeFirst()
            result.append(id)
            for edge in connections where edge.from == id {
                counts[edge.to, default: 0] -= 1
                if counts[edge.to] == 0 { ready.append(edge.to) }
            }
        }
        return result.count == ids.count ? result : nil
    }
}

struct DesignScenario: Codable, Equatable {
    var requestsPerSecond: Double = 200
    var readPercent: Double = 80
    var cacheHitPercent: Double = 80
    var durationSeconds: Double = 60
}

struct DesignTradeoff: Codable, Equatable, Identifiable {
    var id = UUID()
    var decision = ""
    var alternative = ""
    var benefit = ""
    var cost = ""
    var justification = ""
}

struct DesignStageResult: Codable, Equatable, Identifiable {
    var id: UUID
    let name: String
    let kind: DesignComponent.Kind
    let incoming: Double
    let capacity: Double
    let utilization: Double?
    let completed: Double
    let backlog: Double
    let available: Bool
    let latencyMilliseconds: Double?
}

struct DesignSimulationResult: Codable, Equatable {
    let valid: Bool
    let completedPerSecond: Double
    let uncachedPathMilliseconds: Double?
    let stages: [DesignStageResult]
    let observations: [String]
    var constrainedStages: Int { stages.filter { !$0.available || ($0.utilization ?? 0) >= 1 }.count }
}

struct DesignExperiment: Codable, Equatable, Identifiable {
    var id = UUID()
    var date = Date()
    let name: String
    let diagram: ArchitectureDiagram
    let scenario: DesignScenario
    let result: DesignSimulationResult
}

struct DesignWorkspace: Codable, Equatable {
    var diagram = ArchitectureDiagram.starter()
    var scenario = DesignScenario()
    var requirements = ""
    var capacityReasoning = ""
    var dataModel = ""
    var requestFlow = ""
    var failureModes = ""
    var tradeoffs: [DesignTradeoff] = []
    var experiments: [DesignExperiment] = []
    var writtenSections: Int { [requirements, capacityReasoning, dataModel, requestFlow, failureModes].filter { !$0.trimmingCharacters(in: .whitespacesAndNewlines).isEmpty }.count }
}

// A defined educational flow model, not a cloud benchmark or architecture correctness judge.
enum DesignSimulation {
    static func run(diagram: ArchitectureDiagram, scenario: DesignScenario) -> DesignSimulationResult {
        func invalid(_ message: String) -> DesignSimulationResult {
            DesignSimulationResult(valid: false, completedPerSecond: 0, uncachedPathMilliseconds: nil, stages: [], observations: [message])
        }
        guard scenario.requestsPerSecond.isFinite, (0...1_000_000_000).contains(scenario.requestsPerSecond),
              scenario.readPercent.isFinite, (0...100).contains(scenario.readPercent),
              scenario.cacheHitPercent.isFinite, (0...100).contains(scenario.cacheHitPercent),
              scenario.durationSeconds.isFinite, (1...86_400).contains(scenario.durationSeconds) else {
            return invalid("Use a finite nonnegative request rate, percentages from 0 to 100, and a duration of 1–86,400 seconds.")
        }
        guard !diagram.components.isEmpty, diagram.components.count <= 12, let order = diagram.topologicalOrder else {
            return invalid("Use up to 12 components in a forward request flow without cycles. Response arrows are implicit.")
        }
        let clients = diagram.components.filter { $0.kind == .client }
        guard clients.count == 1, let client = clients.first, !diagram.connections.contains(where: { $0.to == client.id }) else {
            return invalid("Use exactly one client as the source of the request flow.")
        }
        let nodes = Dictionary(uniqueKeysWithValues: diagram.components.map { ($0.id, $0) })
        let outgoing = Dictionary(grouping: diagram.connections, by: \.from)
        for component in diagram.components where component.kind != .client {
            guard (1...32).contains(component.replicas), component.capacityPerReplica.isFinite,
                  (1...10_000_000).contains(component.capacityPerReplica), component.latencyMilliseconds.isFinite,
                  (0...60_000).contains(component.latencyMilliseconds) else {
                return invalid("Each processing component needs 1–32 replicas, a per-replica capacity of 1–10,000,000 requests/s, and a latency of 0–60,000 ms.")
            }
        }
        var reached: Set<UUID> = [client.id]
        for id in order where reached.contains(id) {
            for edge in outgoing[id] ?? [] { reached.insert(edge.to) }
        }
        guard reached.count > 1 else { return invalid("Connect the client to at least one processing component.") }
        var demand: [UUID: Double] = [client.id: scenario.requestsPerSecond]
        var stages: [DesignStageResult] = []
        var ownFraction: [UUID: Double] = [:]
        var latency: [UUID: Double] = [:]
        var finiteLatency = true
        var observations: [String] = []
        let bypass = scenario.readPercent / 100 * scenario.cacheHitPercent / 100
        for id in order where reached.contains(id) {
            let node = nodes[id]!
            let incoming = demand[id] ?? 0
            let capacity = node.kind == .client ? incoming : node.available ? Double(node.replicas) * node.capacityPerReplica : 0
            let completed = node.available ? min(incoming, capacity) : 0
            ownFraction[id] = incoming == 0 ? 1 : completed / incoming
            let utilization = node.kind == .client || capacity == 0 ? nil : incoming / capacity
            let backlog = node.kind == .queue ? max(0, incoming - capacity) * scenario.durationSeconds : 0
            let stageLatency: Double?
            if node.kind == .client { stageLatency = 0 }
            else if !node.available || (utilization ?? 0) >= 1 || node.kind == .queue {
                stageLatency = incoming == 0 ? 0 : nil
            } else { stageLatency = incoming == 0 ? 0 : node.latencyMilliseconds / (1 - (utilization ?? 0)) }
            if node.kind != .client {
                stages.append(DesignStageResult(id: id, name: node.name, kind: node.kind, incoming: incoming, capacity: capacity,
                                               utilization: utilization, completed: completed, backlog: backlog, available: node.available,
                                               latencyMilliseconds: stageLatency))
                if !node.available { observations.append("\(node.name) is unavailable; its incoming work cannot be processed.") }
                else if let utilization, utilization >= 1 { observations.append("\(node.name) has no capacity headroom. Add replicas, reduce load, or change the request path.") }
                if node.kind == .queue { observations.append("\(node.name) adds \(Int(min(backlog, Double(Int.max) / 2))) pending jobs over this scenario. Queue waiting time is not modeled.") }
            }
            if stageLatency == nil { finiteLatency = false }
            let totalLatency = (latency[id] ?? 0) + (stageLatency ?? 0)
            latency[id] = totalLatency
            for edge in outgoing[id] ?? [] {
                let forwarded = node.kind == .cache ? completed * (1 - bypass) : completed
                demand[edge.to, default: 0] += forwarded
                latency[edge.to] = max(latency[edge.to] ?? 0, totalLatency)
            }
        }
        var success: [UUID: Double] = [:]
        for id in order.reversed() where reached.contains(id) {
            let children = (outgoing[id] ?? []).map { success[$0.to] ?? 1 }
            let downstream = children.min() ?? 1
            let fraction = nodes[id]?.kind == .cache && !children.isEmpty ? bypass + (1 - bypass) * downstream : downstream
            success[id] = (ownFraction[id] ?? 1) * fraction
        }
        if reached.count != diagram.components.count { observations.append("Disconnected components are excluded from this experiment.") }
        if observations.isEmpty { observations.append("The modeled components have capacity headroom. This does not establish a production SLA.") }
        return DesignSimulationResult(valid: true, completedPerSecond: scenario.requestsPerSecond * (success[client.id] ?? 0),
                                      uncachedPathMilliseconds: finiteLatency ? latency.values.max() ?? 0 : nil,
                                      stages: stages, observations: observations)
    }
}

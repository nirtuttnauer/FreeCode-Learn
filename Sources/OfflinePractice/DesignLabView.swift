import SwiftUI

struct DesignLabView: View {
    @Bindable var store: Store
    @ViewState private var tab = "Diagram"
    @ViewState private var selected: UUID?
    @ViewState private var from: UUID?
    @ViewState private var to: UUID?
    @ViewState private var connectionLabel = "request"
    @ViewState private var connectionError = ""
    @ViewState private var undo: [ArchitectureDiagram] = []
    @ViewState private var redo: [ArchitectureDiagram] = []

    private var draft: DesignWorkspace { store.workspace.design ?? DesignWorkspace() }
    private var model: DesignSimulationResult { DesignSimulation.run(diagram: draft.diagram, scenario: draft.scenario) }
    private var selectedComponent: DesignComponent? { draft.diagram.components.first { $0.id == selected } }

    var body: some View {
        VStack(alignment: .leading, spacing: 0) {
            VStack(alignment: .leading, spacing: 7) {
                Label(store.record.status == "Solved" ? "Component code checks passed" : "Component code checks not yet passed", systemImage: store.record.status == "Solved" ? "checkmark.circle" : "circle")
                    .font(.callout).foregroundStyle(store.record.status == "Solved" ? FreeCodeTheme.accent : FreeCodeTheme.secondary)
                Text("Diagrams, model estimates, and written reasoning are ungraded.").font(.caption).foregroundStyle(FreeCodeTheme.secondary)
            }.padding(16)
            WorkspaceTabs(label: "Architecture lab", options: ["Diagram", "Experiments", "Review"], selection: $tab).padding(.horizontal, 16)
            Divider()
            ScrollView {
                VStack(alignment: .leading, spacing: 20) {
                    if tab == "Diagram" { diagramEditor }
                    else if tab == "Experiments" { experiments }
                    else { review }
                }.padding(16)
            }
        }
        .background(FreeCodeTheme.surface)
        .disabled(store.running)
        .onAppear { selected = draft.diagram.components.first?.id }
    }

    private var diagramEditor: some View {
        VStack(alignment: .leading, spacing: 16) {
            HStack(spacing: 12) {
                Menu {
                    ForEach(DesignComponent.Kind.allCases, id: \.self) { kind in
                        Button(kind.rawValue, systemImage: kind.symbol) {
                            editDiagram { diagram in selected = diagram.add(kind) }
                        }.disabled(draft.diagram.components.count >= 12 || (kind == .client && draft.diagram.components.contains { $0.kind == .client }))
                    }
                } label: { Label("Add component", systemImage: "plus") }.menuStyle(.borderlessButton).fixedSize()
                Button { editDiagram { $0.arrange() } } label: { Image(systemName: "square.grid.3x3") }
                    .help("Arrange components").accessibilityLabel("Arrange components")
                Spacer()
                Button {
                    guard let previous = undo.popLast() else { return }
                    redo.append(draft.diagram)
                    update(\.diagram, previous)
                } label: { Image(systemName: "arrow.uturn.backward") }.disabled(undo.isEmpty).help("Undo diagram change").accessibilityLabel("Undo diagram change")
                Button {
                    guard let next = redo.popLast() else { return }
                    undo.append(draft.diagram)
                    update(\.diagram, next)
                } label: { Image(systemName: "arrow.uturn.forward") }.disabled(redo.isEmpty).help("Redo diagram change").accessibilityLabel("Redo diagram change")
            }.controlSize(.small)
            ArchitectureCanvas(diagram: draft.diagram, stages: model.stages, selection: $selected, beginDrag: { rememberDiagram() }, move: { id, x, y in
                var diagram = draft.diagram
                guard let index = diagram.components.firstIndex(where: { $0.id == id }) else { return }
                diagram.components[index].x = min(1, max(0, x))
                diagram.components[index].y = min(1, max(0, y))
                update(\.diagram, diagram)
            })
            Text("Select a component to edit it. Drag to move it, or use its position sliders. Arrows model forward requests; responses are implicit.")
                .font(.caption).foregroundStyle(FreeCodeTheme.secondary)
            if let node = selectedComponent { componentEditor(node) }
            Divider()
            Text("Request flow").font(.headline)
            VStack(alignment: .leading, spacing: 10) {
                HStack {
                    Picker("From", selection: $from) {
                        Text("Choose source").tag(UUID?.none)
                        ForEach(draft.diagram.components) { Text($0.name).tag(Optional($0.id)) }
                    }
                    Picker("To", selection: $to) {
                        Text("Choose destination").tag(UUID?.none)
                        ForEach(draft.diagram.components.filter { $0.kind != .client }) { Text($0.name).tag(Optional($0.id)) }
                    }
                }
                HStack {
                    TextField("Connection label", text: $connectionLabel).textFieldStyle(.roundedBorder)
                    Button("Connect") {
                        guard let from, let to else { return }
                        var diagram = draft.diagram
                        if diagram.connect(from: from, to: to, label: connectionLabel) {
                            editDiagram { $0 = diagram }
                            connectionError = ""
                        } else { connectionError = "Use different components and a new forward connection without a cycle. Responses are implicit." }
                    }.disabled(from == nil || to == nil || from == to)
                }
                if !connectionError.isEmpty { Text(connectionError).font(.caption).foregroundStyle(.orange) }
                ForEach(draft.diagram.connections) { edge in
                    HStack {
                        let source = draft.diagram.components.first { $0.id == edge.from }?.name ?? "Component"
                        let destination = draft.diagram.components.first { $0.id == edge.to }?.name ?? "Component"
                        Text("\(source) → \(destination)").font(.callout)
                        Text(edge.label).font(.caption).foregroundStyle(FreeCodeTheme.secondary).lineLimit(1)
                        Spacer()
                        Button { editDiagram { $0.connections.removeAll { $0.id == edge.id } } } label: { Image(systemName: "xmark") }
                            .buttonStyle(.plain).accessibilityLabel("Remove connection from \(source) to \(destination)")
                    }
                }
            }
        }
    }

    private func componentEditor(_ node: DesignComponent) -> some View {
        VStack(alignment: .leading, spacing: 12) {
            Text("Component settings").font(.headline)
            TextField("Component name", text: componentBinding(node.id, \.name)).textFieldStyle(.roundedBorder)
            if node.kind != .client {
                Toggle("Available in simulation", isOn: componentBinding(node.id, \.available))
                Stepper("Replicas: \(node.replicas)", value: componentBinding(node.id, \.replicas), in: 1...32)
                numberField("Capacity per replica (requests/s)", value: componentBinding(node.id, \.capacityPerReplica))
                numberField("Base latency (ms)", value: componentBinding(node.id, \.latencyMilliseconds))
            }
            HStack {
                Text("Horizontal").font(.caption).frame(width: 65, alignment: .leading)
                Slider(value: componentBinding(node.id, \.x), in: 0...1).accessibilityLabel("Horizontal position")
            }
            HStack {
                Text("Vertical").font(.caption).frame(width: 65, alignment: .leading)
                Slider(value: componentBinding(node.id, \.y), in: 0...1).accessibilityLabel("Vertical position")
            }
            Button("Remove component", role: .destructive) { editDiagram { $0.remove(node.id) }; selected = nil }
                .controlSize(.small).help("Removes this component and its connections. Undo diagram restores them.")
        }
    }

    private var experiments: some View {
        VStack(alignment: .leading, spacing: 18) {
            Text("Test your assumptions").font(.title3.weight(.semibold))
            Text("Change load, cache behavior, replicas, or component availability. Compare saved runs to explain the tradeoff.")
                .font(.callout).foregroundStyle(FreeCodeTheme.secondary)
            numberField("Incoming requests/s", value: scenarioBinding(\.requestsPerSecond))
            numberField("Reads (%)", value: scenarioBinding(\.readPercent))
            numberField("Cache hits among reads (%)", value: scenarioBinding(\.cacheHitPercent))
            numberField("Duration (seconds)", value: scenarioBinding(\.durationSeconds))
            Button("Run & save experiment", systemImage: "play.fill") { store.saveDesignExperiment() }
                .buttonStyle(.borderedProminent).foregroundStyle(FreeCodeTheme.actionText).disabled(!model.valid)
            simulationResult(model)
            DisclosureGroup("Model assumptions and formulas") {
                Text("This is a defined educational model, not a benchmark. Traffic is steady and replicas balance perfectly. Every forward arrow receives the source’s processed rate; fan-out copies work. Each cache bypasses read_fraction × hit_fraction of downstream work. A stage processes min(incoming, replicas × capacity). Queue growth is max(0, incoming − capacity) × duration. Below saturation, path latency uses base_latency ÷ (1 − utilization), summed on the longest reached path. Saturation, failures, or queues make that latency estimate unavailable. Network behavior, sharding, consistency, tail latency, and retries are not simulated.")
                    .font(.caption).foregroundStyle(FreeCodeTheme.secondary).padding(.top, 8)
            }.font(.callout)
            Divider()
            Text("Saved experiments").font(.headline)
            if draft.experiments.isEmpty {
                Text("Save a baseline, change one assumption, then save another run.").font(.callout).foregroundStyle(FreeCodeTheme.secondary)
            }
            ForEach(Array(draft.experiments.enumerated().reversed()), id: \.element.id) { index, experiment in
                DisclosureGroup {
                    Text("\(experiment.scenario.requestsPerSecond, specifier: "%.0f") incoming requests/s · \(experiment.scenario.durationSeconds, specifier: "%.0f") seconds")
                        .font(.caption).foregroundStyle(FreeCodeTheme.secondary)
                    if index > 0 {
                        let delta = experiment.result.completedPerSecond - draft.experiments[index - 1].result.completedPerSecond
                        Text("\(delta, specifier: "%+.1f") modeled completed requests/s versus the preceding experiment").font(.caption)
                    }
                    simulationResult(experiment.result)
                    Button("Restore this setup") {
                        rememberDiagram()
                        var next = draft
                        next.diagram = experiment.diagram
                        next.scenario = experiment.scenario
                        store.updateDesign(next)
                        selected = next.diagram.components.first?.id
                    }.controlSize(.small)
                } label: {
                    HStack {
                        Text(experiment.name).font(.callout.weight(.medium))
                        Spacer()
                        Text("\(experiment.result.completedPerSecond, specifier: "%.1f") requests/s").font(.caption.monospacedDigit()).foregroundStyle(FreeCodeTheme.secondary)
                    }
                }
            }
        }
    }

    private func simulationResult(_ result: DesignSimulationResult) -> some View {
        VStack(alignment: .leading, spacing: 12) {
            if result.valid {
                HStack {
                    Text("Completed work (model)").font(.callout)
                    Spacer()
                    Text("\(result.completedPerSecond, specifier: "%.1f") requests/s").font(.callout.monospacedDigit().weight(.semibold))
                }
                HStack {
                    Text("Path estimate").font(.callout)
                    Spacer()
                    Text(result.uncachedPathMilliseconds.map { String(format: "%.1f ms", $0) } ?? "Unavailable").font(.callout.monospacedDigit())
                }
                ForEach(result.stages) { stage in
                    VStack(alignment: .leading, spacing: 5) {
                        HStack {
                            Text(stage.name).font(.callout.weight(.medium))
                            Spacer()
                            Text(stage.available ? stage.utilization.map { String(format: "%.0f%% load", $0 * 100) } ?? "No capacity" : "Unavailable")
                                .font(.caption.monospacedDigit()).foregroundStyle(!stage.available || (stage.utilization ?? 0) >= 1 ? Color.orange : FreeCodeTheme.secondary)
                        }
                        Text("\(stage.incoming, specifier: "%.1f") incoming · \(stage.capacity, specifier: "%.1f") capacity · \(stage.completed, specifier: "%.1f") processed requests/s")
                            .font(.caption).foregroundStyle(FreeCodeTheme.secondary)
                        if stage.kind == .queue { Text("\(stage.backlog, specifier: "%.0f") pending jobs after this run").font(.caption) }
                    }
                }
            }
            ForEach(Array(result.observations.enumerated()), id: \.offset) { _, note in
                Label(note, systemImage: result.valid ? "info.circle" : "exclamationmark.triangle").font(.caption).foregroundStyle(FreeCodeTheme.secondary)
            }
        }.padding(14).background(FreeCodeTheme.editor, in: RoundedRectangle(cornerRadius: 6))
    }

    private var review: some View {
        VStack(alignment: .leading, spacing: 20) {
            Text("Explain the design").font(.title3.weight(.semibold))
            Text("\(draft.writtenSections) of 5 reasoning sections have notes. This is your review, not an automatic grade.").font(.caption).foregroundStyle(FreeCodeTheme.secondary)
            reviewField("Requirements & constraints", hint: "Who uses this system? Define scope, correctness, latency, and availability targets.", key: \.requirements)
            reviewField("Capacity reasoning", hint: "Estimate traffic, concurrency, storage, and headroom. Relate your saved experiments to those estimates.", key: \.capacityReasoning)
            reviewField("Data model", hint: "Describe records, keys, indexes, retention, and consistency requirements.", key: \.dataModel)
            reviewField("Request flow", hint: "Walk through a read and a write using your diagram. Identify synchronous and asynchronous boundaries.", key: \.requestFlow)
            reviewField("Failure & recovery", hint: "What fails first? Explain timeouts, retries, idempotency, backpressure, and recovery.", key: \.failureModes)
            Divider()
            HStack {
                Text("Decisions & tradeoffs").font(.headline)
                Spacer()
                Button("Add decision", systemImage: "plus") {
                    var next = draft; next.tradeoffs.append(DesignTradeoff()); store.updateDesign(next)
                }.controlSize(.small)
            }
            if draft.tradeoffs.isEmpty { Text("Record an alternative, what your choice gains, and what it gives up.").font(.callout).foregroundStyle(FreeCodeTheme.secondary) }
            ForEach(draft.tradeoffs) { decision in
                VStack(alignment: .leading, spacing: 12) {
                    HStack {
                        Text("Decision").font(.callout.weight(.semibold))
                        Spacer()
                        Button { var next = draft; next.tradeoffs.removeAll { $0.id == decision.id }; store.updateDesign(next) } label: { Image(systemName: "trash") }
                            .buttonStyle(.plain).accessibilityLabel("Remove decision")
                    }
                    decisionField("Chosen approach", id: decision.id, key: \.decision)
                    decisionField("Alternative", id: decision.id, key: \.alternative)
                    decisionField("Benefit", id: decision.id, key: \.benefit)
                    decisionField("Cost / limitation", id: decision.id, key: \.cost)
                    decisionField("Why this tradeoff fits the requirements", id: decision.id, key: \.justification)
                    Divider()
                }
            }
        }
    }

    private func reviewField(_ title: String, hint: String, key: WritableKeyPath<DesignWorkspace, String>) -> some View {
        VStack(alignment: .leading, spacing: 8) {
            Text(title).font(.headline)
            Text(hint).font(.caption).foregroundStyle(FreeCodeTheme.secondary)
            TextEditor(text: Binding(get: { draft[keyPath: key] }, set: { update(key, $0) }))
                .font(.body).scrollContentBackground(.hidden).padding(8).frame(minHeight: 85)
                .background(FreeCodeTheme.editor, in: RoundedRectangle(cornerRadius: 6))
                .overlay { RoundedRectangle(cornerRadius: 6).strokeBorder(FreeCodeTheme.border) }
                .accessibilityLabel(title)
        }
    }
    private func decisionField(_ title: String, id: UUID, key: WritableKeyPath<DesignTradeoff, String>) -> some View {
        TextField(title, text: Binding(get: { draft.tradeoffs.first { $0.id == id }?[keyPath: key] ?? "" }, set: { text in
            var next = draft
            if let index = next.tradeoffs.firstIndex(where: { $0.id == id }) { next.tradeoffs[index][keyPath: key] = text; store.updateDesign(next) }
        }), axis: .vertical).textFieldStyle(.roundedBorder).lineLimit(1...4).accessibilityLabel(title)
    }
    private func numberField(_ title: String, value: Binding<Double>) -> some View {
        HStack {
            Text(title).font(.callout)
            Spacer()
            TextField(title, value: value, format: .number).textFieldStyle(.roundedBorder).frame(width: 110).multilineTextAlignment(.trailing).accessibilityLabel(title)
        }
    }
    private func scenarioBinding(_ key: WritableKeyPath<DesignScenario, Double>) -> Binding<Double> {
        Binding(get: { draft.scenario[keyPath: key] }, set: { value in var next = draft; next.scenario[keyPath: key] = value; store.updateDesign(next) })
    }
    private func componentBinding<Value>(_ id: UUID, _ key: WritableKeyPath<DesignComponent, Value>) -> Binding<Value> {
        let original = draft.diagram.components.first { $0.id == id }![keyPath: key]
        return Binding(get: { draft.diagram.components.first { $0.id == id }?[keyPath: key] ?? original }, set: { value in
            editDiagram { diagram in if let index = diagram.components.firstIndex(where: { $0.id == id }) { diagram.components[index][keyPath: key] = value } }
        })
    }
    private func update<Value>(_ key: WritableKeyPath<DesignWorkspace, Value>, _ value: Value) {
        var next = draft; next[keyPath: key] = value; store.updateDesign(next)
    }
    private func rememberDiagram() { undo.append(draft.diagram); if undo.count > 60 { undo.removeFirst() }; redo = [] }
    private func editDiagram(_ edit: (inout ArchitectureDiagram) -> Void) {
        var next = draft.diagram; edit(&next)
        guard next != draft.diagram else { return }
        rememberDiagram(); update(\.diagram, next)
    }
}

private struct ArchitectureCanvas: View {
    let diagram: ArchitectureDiagram
    let stages: [DesignStageResult]
    @Binding var selection: UUID?
    let beginDrag: () -> Void
    let move: (UUID, Double, Double) -> Void
    @ViewState private var dragID: UUID?
    @ViewState private var dragOrigin: CGPoint = .zero

    private var canvasHeight: CGFloat { max(260, CGFloat((diagram.components.count + 2) / 3) * 110) }
    var body: some View {
        GeometryReader { proxy in
            let width = max(490, proxy.size.width)
            ScrollView(.horizontal) {
                ZStack {
                    Canvas { context, _ in
                        for edge in diagram.connections {
                            if let source = diagram.components.first(where: { $0.id == edge.from }), let destination = diagram.components.first(where: { $0.id == edge.to }) {
                                let a = point(source, width: width), b = point(destination, width: width)
                                let dx = b.x - a.x, dy = b.y - a.y
                                let horizontal = abs(dx) >= abs(dy)
                                let start = CGPoint(x: a.x + (horizontal ? (dx >= 0 ? 67 : -67) : 0), y: a.y + (horizontal ? 0 : (dy >= 0 ? 35 : -35)))
                                let end = CGPoint(x: b.x - (horizontal ? (dx >= 0 ? 67 : -67) : 0), y: b.y - (horizontal ? 0 : (dy >= 0 ? 35 : -35)))
                                var path = Path(); path.move(to: start); path.addLine(to: end)
                                context.stroke(path, with: .color(FreeCodeTheme.secondary), lineWidth: 1.5)
                                let angle = atan2(end.y-start.y, end.x-start.x)
                                var arrow = Path(); arrow.move(to: end)
                                arrow.addLine(to: CGPoint(x: end.x-8*cos(angle-0.5), y: end.y-8*sin(angle-0.5)))
                                arrow.addLine(to: CGPoint(x: end.x-8*cos(angle+0.5), y: end.y-8*sin(angle+0.5))); arrow.closeSubpath()
                                context.fill(arrow, with: .color(FreeCodeTheme.secondary))
                            }
                        }
                    }.accessibilityHidden(true)
                    ForEach(diagram.components) { node in
                        Button { selection = node.id } label: {
                            VStack(spacing: 5) {
                                Label(node.name.isEmpty ? node.kind.rawValue : node.name, systemImage: node.kind.symbol)
                                    .font(.system(size: 12, weight: .semibold)).lineLimit(1)
                                Text(node.kind == .client ? "Request source" : node.available ? "\(node.replicas) × \(node.capacityPerReplica, specifier: "%.0f") req/s" : "Unavailable")
                                    .font(.system(size: 11)).foregroundStyle(node.available ? FreeCodeTheme.secondary : Color.orange)
                            }.frame(width: 134, height: 70)
                                .background(FreeCodeTheme.surface, in: RoundedRectangle(cornerRadius: 8))
                                .overlay { RoundedRectangle(cornerRadius: 8).strokeBorder(selection == node.id ? FreeCodeTheme.accent : FreeCodeTheme.border, lineWidth: selection == node.id ? 2 : 1) }
                        }
                        .buttonStyle(.plain).position(point(node, width: width))
                        .accessibilityLabel("\(node.name), \(node.kind.rawValue), \(node.available ? "available" : "unavailable")")
                        .accessibilityAddTraits(selection == node.id ? .isSelected : [])
                        .simultaneousGesture(DragGesture(minimumDistance: 4).onChanged { value in
                            if dragID != node.id { dragID = node.id; dragOrigin = CGPoint(x: node.x, y: node.y); selection = node.id; beginDrag() }
                            move(node.id, dragOrigin.x + value.translation.width / (width - 150), dragOrigin.y + value.translation.height / (canvasHeight - 100))
                        }.onEnded { _ in dragID = nil })
                    }
                    if diagram.components.isEmpty { Text("Add a client and processing components to start.").font(.callout).foregroundStyle(FreeCodeTheme.secondary) }
                }.frame(width: width, height: canvasHeight)
            }
        }.frame(height: canvasHeight)
            .background(FreeCodeTheme.editor, in: RoundedRectangle(cornerRadius: 8))
            .overlay { RoundedRectangle(cornerRadius: 8).strokeBorder(FreeCodeTheme.border) }
    }
    private func point(_ node: DesignComponent, width: CGFloat) -> CGPoint {
        CGPoint(x: 75 + node.x * (width - 150), y: 50 + node.y * (canvasHeight - 100))
    }
}

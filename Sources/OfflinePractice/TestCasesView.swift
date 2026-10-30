import SwiftUI

struct TestCasesView: View {
    @Bindable var store: Store
    @ViewState<Bool> private var confirmExamples = false

    private var cases: Binding<[TestCaseDraft]> {
        Binding(get: { store.workspace.testCaseDrafts ?? [] }, set: store.updateTestCases)
    }

    var body: some View {
        VStack(alignment: .leading, spacing: 0) {
            HStack {
                Text("\(cases.wrappedValue.count) test cases").font(.caption).foregroundStyle(.secondary)
                Spacer()
                Button("Load examples") { confirmExamples = true }
                Button("Add case", systemImage: "plus") {
                    var next = cases.wrappedValue
                    next.append(TestCaseDraft(arguments: [], expected: TestValueDraft(.null)))
                    store.updateTestCases(next)
                }.disabled(store.workspace.testCaseDrafts == nil || cases.wrappedValue.count >= 50)
            }.controlSize(.small).padding(12)
            Divider()
            if store.workspace.testCaseDrafts == nil {
                ContentUnavailableView("Saved tests need attention", systemImage: "exclamationmark.triangle", description: Text("The existing test data was preserved. Load examples to replace it with editable cases."))
            } else {
                ScrollView {
                    LazyVStack(alignment: .leading, spacing: 16) {
                        ForEach(cases) { test in
                            VStack(alignment: .leading, spacing: 12) {
                                HStack {
                                    Text("Case \((cases.wrappedValue.firstIndex { $0.id == test.wrappedValue.id } ?? 0) + 1)").font(.headline)
                                    Spacer()
                                    Button("Remove case", systemImage: "trash") {
                                        store.updateTestCases(cases.wrappedValue.filter { $0.id != test.wrappedValue.id })
                                    }.labelStyle(.iconOnly).help("Remove this test case")
                                }
                                ForEach(test.arguments) { argument in
                                    HStack(alignment: .top) {
                                        TestValueField(title: inputName(test: test.wrappedValue, argument: argument.wrappedValue), value: argument)
                                        Button("Remove input", systemImage: "minus.circle") {
                                            test.arguments.wrappedValue.removeAll { $0.id == argument.wrappedValue.id }
                                        }.labelStyle(.iconOnly).help("Remove this input").padding(.top, 3)
                                    }
                                }
                                Button("Add input", systemImage: "plus.circle") {
                                    test.arguments.wrappedValue.append(TestValueDraft(.integer(0)))
                                }.controlSize(.small)
                                Divider()
                                TestValueField(title: "Expected output", value: test.expected)
                                Toggle("Compare arrays in any order", isOn: test.unordered).font(.caption)
                            }.padding(14).background(FreeCodeTheme.editor, in: RoundedRectangle(cornerRadius: 6))
                        }
                        if cases.wrappedValue.isEmpty {
                            Text("Add a case or load the question’s examples to get started.").foregroundStyle(.secondary)
                        }
                        if let error = store.testCaseError {
                            Label(error, systemImage: "exclamationmark.triangle").font(.caption).foregroundStyle(.orange)
                        }
                        Text("Choose a type for each value. Arrays use brackets, for example [2, 7, 11, 15]. Text values do not need quotes.")
                            .font(.caption).foregroundStyle(.secondary)
                    }.padding(14)
                }
            }
        }
        .disabled(store.running)
        .confirmationDialog("Replace test cases with the question’s examples?", isPresented: $confirmExamples) {
            Button("Load examples", role: .destructive, action: store.loadExampleTests)
        } message: { Text("Your current custom test cases will be replaced.") }
    }

    private func inputName(test: TestCaseDraft, argument: TestValueDraft) -> String {
        let index = test.arguments.firstIndex { $0.id == argument.id } ?? 0
        let input = store.problem?.samples.first?.input ?? ""
        let regex = try? NSRegularExpression(pattern: #"(?:^|,\s*)([A-Za-z_][A-Za-z_0-9]*)\s*="#)
        let names = regex?.matches(in: input, range: NSRange(input.startIndex..., in: input)).compactMap { match in
            Range(match.range(at: 1), in: input).map { String(input[$0]) }
        } ?? []
        return names.indices.contains(index) ? names[index] : "Input \(index + 1)"
    }
}

private struct TestValueField: View {
    let title: String
    @Binding var value: TestValueDraft

    var body: some View {
        VStack(alignment: .leading, spacing: 6) {
            HStack {
                Text(title).font(.callout.weight(.medium))
                Spacer()
                Picker("\(title) type", selection: $value.kind) {
                    ForEach(TestValueDraft.Kind.allCases, id: \.self) { Text($0.rawValue).tag($0) }
                }.labelsHidden().fixedSize().controlSize(.small)
            }
            if value.kind == .boolean {
                Toggle("\(title) is true", isOn: Binding(get: { value.text == "true" }, set: { value.text = $0 ? "true" : "false" }))
                    .toggleStyle(.checkbox)
            } else if value.kind == .null {
                Text("null").font(.body.monospaced()).foregroundStyle(.secondary)
            } else {
                TextField(title, text: $value.text, axis: .vertical)
                    .font(.system(size: 12, design: .monospaced)).lineLimit(1...8).textFieldStyle(.roundedBorder)
                    .accessibilityLabel(title)
            }
            if (try? value.value()) == nil {
                Text("Enter a valid \(value.kind.rawValue.lowercased()) value.").font(.caption).foregroundStyle(.orange)
            }
        }
        .onChange(of: value.kind) { _, kind in
            switch kind {
            case .number: value.text = "0"
            case .boolean: value.text = "false"
            case .array: value.text = "[]"
            case .object: value.text = "{}"
            case .null: value.text = "null"
            case .string: break
            }
        }
    }
}

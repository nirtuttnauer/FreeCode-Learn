import SwiftUI

struct PersonalListsView: View {
    @Bindable var store: Store
    @Environment(\.dismiss) private var dismiss
    @ViewState private var name = ""
    @ViewState private var editingID: String?
    @ViewState private var deleting: CustomList?
    @ViewState private var addCurrent = true
    @ViewState private var message = ""
    @FocusState private var nameFocused: Bool

    private var currentQuestion: Int? { store.section == .problems ? store.selection : nil }

    var body: some View {
        VStack(alignment: .leading, spacing: 20) {
            HStack {
                Text("My lists").font(.title2.weight(.semibold))
                Spacer()
                Button("Done") { dismiss() }.keyboardShortcut(.cancelAction)
            }
            Text("Organize questions your way. Lists stay on this Mac alongside your saved work.")
                .font(.callout).foregroundStyle(.secondary)
            VStack(alignment: .leading, spacing: 10) {
                Text(editingID == nil ? "New list" : "Rename list").font(.headline)
                HStack {
                    TextField("List name", text: $name).textFieldStyle(.roundedBorder).focused($nameFocused).onSubmit(save)
                    Button(editingID == nil ? "Create" : "Save", action: save)
                        .disabled(name.trimmingCharacters(in: .whitespacesAndNewlines).isEmpty || store.running || !store.customListsReadable)
                }
                if editingID == nil, currentQuestion != nil {
                    Toggle("Add the current question", isOn: $addCurrent).font(.callout)
                }
                if editingID != nil {
                    Button("Cancel rename") { editingID = nil; name = "" }.controlSize(.small)
                }
                if !message.isEmpty { Text(message).font(.caption).foregroundStyle(.secondary) }
                if !store.customListsReadable {
                    Text("Saved lists need recovery before they can be edited. The original file has been preserved.")
                        .font(.callout).foregroundStyle(.secondary)
                }
            }
            Divider()
            if store.customLists.isEmpty {
                ContentUnavailableView("No personal lists yet", systemImage: "text.badge.plus", description: Text("Try “Interview prep” or “Revisit later”."))
            } else {
                ScrollView {
                    LazyVStack(alignment: .leading, spacing: 16) {
                        ForEach(store.customLists) { list in
                            HStack(spacing: 12) {
                                VStack(alignment: .leading, spacing: 4) {
                                    Text(list.name).font(.headline).lineLimit(2)
                                    Text("\(list.questionIDs.count) questions").font(.caption).foregroundStyle(.secondary)
                                }
                                Spacer()
                                Button("Open") { store.choosePlan(list.id); dismiss() }.disabled(store.running)
                                Button { editingID = list.id; name = list.name; nameFocused = true; message = "" } label: { Image(systemName: "pencil") }
                                    .help("Rename \(list.name)").accessibilityLabel("Rename \(list.name)")
                                Button(role: .destructive) { deleting = list } label: { Image(systemName: "trash") }
                                    .help("Delete \(list.name)").accessibilityLabel("Delete \(list.name)")
                            }
                        }
                    }
                }
            }
            if let error = store.error {
                Text(error).font(.callout).foregroundStyle(.red).textSelection(.enabled)
            }
        }
        .padding(24).frame(width: 480, height: 500)
        .background(FreeCodeTheme.surface).foregroundStyle(FreeCodeTheme.text).tint(FreeCodeTheme.accent)
        .onAppear { nameFocused = true }
        .confirmationDialog("Delete “\(deleting?.name ?? "")”?", isPresented: Binding(get: { deleting != nil }, set: { if !$0 { deleting = nil } })) {
            Button("Delete list", role: .destructive) {
                if let list = deleting, store.deleteCustomList(list.id) {
                    if editingID == list.id { editingID = nil; name = "" }
                    message = "List deleted. Your questions, code, and progress are kept."
                }
                deleting = nil
            }
        } message: { Text("Only this list is removed. Questions, saved code, and progress are kept.") }
    }

    private func save() {
        if let id = editingID {
            guard store.renameCustomList(id, to: name) else { return }
            message = "List renamed."
        } else {
            guard store.createCustomList(name, adding: addCurrent ? currentQuestion : nil) != nil else { return }
            message = "List created. Use Lists on any question to add more."
        }
        name = ""
        editingID = nil
    }
}

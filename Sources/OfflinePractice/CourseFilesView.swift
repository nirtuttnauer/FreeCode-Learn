import SwiftUI

struct CourseFilesView: View {
    @Bindable var store: Store
    @ViewState private var filename = ""
    @ViewState private var fileAction = "new"
    @ViewState private var editingFile = false
    @ViewState private var deletingFile = false

    var body: some View {
        VStack(alignment: .leading, spacing: 8) {
            HStack {
                Picker("Workspace file", selection: Binding(get: { store.workspace.selectedFile ?? "" }, set: store.selectCourseFile)) {
                    ForEach(store.courseFileNames, id: \.self) { name in Text(name).tag(name) }
                }.labelsHidden().accessibilityLabel("Workspace file").disabled(store.running)
                Menu {
                    Button("New file…") { filename = ""; fileAction = "new"; editingFile = true }
                    Button("Rename file…") { filename = store.activeFilename; fileAction = "rename"; editingFile = true }
                    Button("Delete file…", role: .destructive) { deletingFile = true }
                    Divider()
                    Button("Export workspace…", action: store.exportCourseWorkspace)
                } label: { Image(systemName: "doc.badge.plus") }.disabled(store.running).accessibilityLabel("Manage workspace files")
            }
            HStack(spacing: 12) {
                Menu("Explore & check") {
                    Button("Run demonstration") { run("demo") }
                    Button("Run my tests") { run("learner") }
                    Button("Check types") { run("typecheck") }
                    Button("Lint files") { run("lint") }
                    Button("Run benchmarks") { run("benchmark") }
                }.disabled(store.running)
                Text("Shared module files · required checks grade this step")
                    .font(.caption).foregroundStyle(FreeCodeTheme.secondary).lineLimit(2)
            }
        }.padding(.horizontal, 16).padding(.vertical, 10)
        .alert(fileAction == "new" ? "New workspace file" : "Rename workspace file", isPresented: $editingFile) {
            TextField("Relative file name", text: $filename)
            Button("Cancel", role: .cancel) {}
            Button(fileAction == "new" ? "Create" : "Rename") { store.editCourseFile(fileAction, name: filename) }
        } message: { Text("Use a relative path, such as src/package/helpers.py or test_learner.py.") }
        .confirmationDialog("Delete \(store.activeFilename)?", isPresented: $deletingFile) {
            Button("Delete file", role: .destructive) { store.editCourseFile("delete", name: "") }
        } message: { Text("This removes the file from this workspace. Export a copy first if you need to keep it.") }
    }

    private func run(_ action: String) {
        store.courseAction = action
        store.run()
    }
}

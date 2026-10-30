import AppKit
import Foundation

extension Store {
    var isCourseExercise: Bool { problem?.course != nil }
    var courseFileNames: [String] { (workspace.files ?? [:]).keys.sorted() }

    func selectCourseFile(_ name: String) {
        guard !running, workspace.files?[name] != nil else { return }
        let old = workspace.selectedFile ?? activeFilename
        let code = workspace.code
        workspace.files?[old] = code
        workspace.selectedFile = name
        workspace.code = workspace.files?[name] ?? ""
        saveNow()
    }

    func validCourseFilename(_ name: String) -> Bool {
        let parts = name.split(separator: "/", omittingEmptySubsequences: false)
        return !name.isEmpty && name.count <= 240 && !name.contains("\\") && parts.allSatisfy { !$0.isEmpty && !$0.hasPrefix(".") }
            && ["py", "md", "toml", "json", "txt", "html", "sql", "yaml", "yml", "css", "svg"].contains((name as NSString).pathExtension)
            && !["checks", "trusted", "course-internal"].contains(String(parts.first ?? ""))
            && !courseFileNames.contains { $0.hasPrefix(name + "/") || name.hasPrefix($0 + "/") }
    }

    func editCourseFile(_ action: String, name: String) {
        guard !running, isCourseExercise else { return }
        let name = name.trimmingCharacters(in: .whitespacesAndNewlines)
        if action != "delete" {
            guard validCourseFilename(name), workspace.files?[name] == nil, courseFileNames.count < 200 else {
                error = "Choose a new relative source or documentation file name, such as src/package/helpers.py. Hidden and parent paths are not allowed."
                return
            }
        }
        let old = workspace.selectedFile ?? problem?.course?.entrypoint ?? ""
        if action == "delete" || action == "rename" {
            guard old != problem?.course?.entrypoint else { error = "Keep the required entry file. You can edit its contents."; return }
        }
        let code = workspace.code
        workspace.files?[old] = code
        if action == "new" { workspace.files?[name] = "" }
        if action == "rename" {
            let text = workspace.files?.removeValue(forKey: old)
            workspace.files?[name] = text
        }
        if action == "delete" { workspace.files?.removeValue(forKey: old) }
        let next = action == "delete" ? problem?.course?.entrypoint ?? "" : name
        workspace.selectedFile = next
        workspace.code = workspace.files?[next] ?? ""
        edited()
        saveNow()
    }

    func exportCourseWorkspace() {
        guard saveNow(), let files = workspace.files else { return }
        let panel = NSOpenPanel()
        panel.canChooseDirectories = true; panel.canChooseFiles = false; panel.canCreateDirectories = true
        panel.prompt = "Export workspace"
        guard panel.runModal() == .OK, let parent = panel.url else { return }
        let target = parent.appendingPathComponent("Python Engineer-" + UUID().uuidString.prefix(8))
        do {
            for (name, text) in files {
                guard validExportPath(name) else { throw CocoaError(.fileWriteInvalidFileName) }
                let path = target.appendingPathComponent(name)
                try FileManager.default.createDirectory(at: path.deletingLastPathComponent(), withIntermediateDirectories: true)
                try text.write(to: path, atomically: true, encoding: .utf8)
            }
            NSWorkspace.shared.activateFileViewerSelecting([target])
        } catch { self.error = "Workspace export failed: \(error.localizedDescription)" }
    }

    func replaceCurrentStarter() {
        if let course = problem?.course {
            do {
                let url = libraryURL.appendingPathComponent("learning/\(course.courseID ?? "python-engineer")/\(course.workspaceID).json")
                let starters = try JSONDecoder().decode([String: String].self, from: Data(contentsOf: url))
                workspace.code = starters[activeFilename] ?? ""
            } catch { self.error = "Starter files could not load: \(error.localizedDescription)"; return }
        } else {
            workspace.code = workspace.mode == "program" ? language.program : problem?.starters[language.rawValue] ?? language.program
        }
        edited()
    }

    private func validExportPath(_ name: String) -> Bool {
        !name.hasPrefix("/") && !name.contains("\\") && name.split(separator: "/", omittingEmptySubsequences: false).allSatisfy { !$0.isEmpty && !$0.hasPrefix(".") }
    }
}

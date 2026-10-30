import AppKit
import Foundation
import Observation

@MainActor @Observable
final class Store {
    let libraryURL: URL
    let scriptsURL: URL
    let workURL: URL
    var catalog: [ProblemSummary] = []
    var problem: Problem?
    var selection: Int? = nil
    var language: Language = .python
    var workspace = Workspace()
    var progress: [String: ProgressRecord] = [:]
    var notes = ""
    var search = ""
    var difficulty = "All difficulties"
    var topic = "All topics"
    var filter = "All problems"
    var error: String?
    var saveMessage = "Saved"
    var showCoverage = false
    var showReset = false
    var showResetAccount = false
    var activity: [Activity] = []
    var latestBackup: URL?
    var studyPlans: [StudyPlan] = []
    var selectedPlan = "all"
    var section: PracticeSection = .problems
    var customLists: [CustomList] = []
    var customListsReadable = true
    var learningCatalog: [ProblemSummary] = []
    var learningCourses: [LearningCourse] = []
    var selectedCourse = ""
    var courseSteps: [String: CourseExercise] = [:]
    var courseAction = "check"
    var result: RunResult?
    var running = false
    var statementTab = "Description"
    var consoleTab = "Results"
    private var saveTask: Task<Void, Never>?
    private var process: Process?
    private var loading = false
    private var activeKey: String?

    init(workDirectory: URL? = nil, libraryDirectory: URL? = nil) {
        let root = URL(fileURLWithPath: FileManager.default.currentDirectoryPath)
        let resources = Bundle.main.resourceURL ?? root
        libraryURL = libraryDirectory ?? ((FileManager.default.fileExists(atPath: resources.appendingPathComponent("data/learning/courses.json").path) || FileManager.default.fileExists(atPath: resources.appendingPathComponent("data/catalog.json").path))
            ? resources.appendingPathComponent("data") : root.appendingPathComponent("data"))
        scriptsURL = FileManager.default.fileExists(atPath: resources.appendingPathComponent("scripts/runner.py").path)
            ? resources.appendingPathComponent("scripts") : root.appendingPathComponent("scripts")
        if let workDirectory {
            workURL = workDirectory
        } else if let override = ProcessInfo.processInfo.environment["OFFLINE_PRACTICE_WORK_DIR"] {
            workURL = URL(fileURLWithPath: override)
        } else {
            workURL = FileManager.default.urls(for: .applicationSupportDirectory, in: .userDomainMask)[0].appendingPathComponent("OfflinePractice")
        }
        do {
            try FileManager.default.createDirectory(at: workURL, withIntermediateDirectories: true)
            if FileManager.default.fileExists(atPath: libraryURL.appendingPathComponent("catalog.json").path) {
                catalog = try JSONDecoder().decode([ProblemSummary].self, from: Data(contentsOf: libraryURL.appendingPathComponent("catalog.json")))
            }
            let learningURL = libraryURL.appendingPathComponent("learning")
            if FileManager.default.fileExists(atPath: learningURL.appendingPathComponent("courses.json").path) {
                learningCourses = try JSONDecoder().decode([LearningCourse].self, from: Data(contentsOf: learningURL.appendingPathComponent("courses.json")))
                learningCatalog = try JSONDecoder().decode([ProblemSummary].self, from: Data(contentsOf: learningURL.appendingPathComponent("catalog.json")))
                selectedCourse = learningCourses.first?.id ?? ""
            }
            for folder in (try? FileManager.default.contentsOfDirectory(at: learningURL, includingPropertiesForKeys: nil)) ?? [] {
                let courseManifest = folder.appendingPathComponent("manifest.json")
                if FileManager.default.fileExists(atPath: courseManifest.path) {
                    let steps = try JSONDecoder().decode(CourseManifest.self, from: Data(contentsOf: courseManifest)).steps
                    guard Set(courseSteps.keys).isDisjoint(with: steps.keys) else { throw CocoaError(.fileReadCorruptFile) }
                    courseSteps.merge(steps) { previous, _ in previous }
                }
            }
            if catalog.isEmpty { section = .learning; selectedCourse = learningCourses.first { $0.id == "python-engineer" }?.id ?? selectedCourse }
            let listsFile = workURL.appendingPathComponent("custom-lists.json")
            if FileManager.default.fileExists(atPath: listsFile.path) {
                do { customLists = try JSONDecoder().decode([CustomList].self, from: Data(contentsOf: listsFile)) }
                catch {
                    customListsReadable = false
                    self.error = "Your personal lists could not be read and have been preserved on disk. Restore custom-lists.json from a backup before editing lists. \(error.localizedDescription)"
                }
            }
            let plansURL = libraryURL.appendingPathComponent("playlists.json")
            if FileManager.default.fileExists(atPath: plansURL.path) {
                studyPlans = try JSONDecoder().decode([StudyPlan].self, from: Data(contentsOf: plansURL))
            }
            let progressFile = workURL.appendingPathComponent("progress.json")
            if FileManager.default.fileExists(atPath: progressFile.path) {
                progress = try JSONDecoder().decode([String: ProgressRecord].self, from: Data(contentsOf: progressFile))
                for (id, step) in courseSteps where progress[id]?.status == "Solved" && progress[id]?.courseVersion != step.version {
                    progress[id]?.status = "In progress"
                }
            }
            let activityFile = workURL.appendingPathComponent("activity.json")
            if FileManager.default.fileExists(atPath: activityFile.path) {
                activity = try JSONDecoder().decode([Activity].self, from: Data(contentsOf: activityFile))
            }
            if let saved = Language(rawValue: UserDefaults.standard.string(forKey: "language") ?? "") { language = saved }
            let last = UserDefaults.standard.integer(forKey: "lastProblem")
            if learningCatalog.contains(where: { $0.id == last }) { section = .learning; selectedCourse = learningCourses.first { $0.questionIDs.contains(last) }?.id ?? selectedCourse }
            select((catalog + learningCatalog).contains { $0.id == last } ? last : catalog.first?.id ?? activeCourse?.questionIDs.first ?? learningCatalog.first?.id)
        } catch { self.error = "Could not load the local library or saved progress: \(error.localizedDescription)" }
    }

    var filtered: [ProblemSummary] {
        let query = search.trimmingCharacters(in: .whitespacesAndNewlines)
        let ids = section == .learning ? activeCourse?.questionIDs ?? [] : activePlan?.questionIDs ?? activeCustomList?.questionIDs
        let order = Dictionary((ids ?? []).enumerated().map { ($0.element, $0.offset) }, uniquingKeysWith: { first, _ in first })
        let matches = currentCatalog.filter { p in
            (ids == nil || order[p.id] != nil) &&
            (section != .problems || selectedPlan != "sql" || p.tags.contains("Database")) &&
            (query.isEmpty || p.title.localizedCaseInsensitiveContains(query) || String(p.id) == query || p.tags.contains { $0.localizedCaseInsensitiveContains(query) }) &&
            (difficulty == "All difficulties" || p.difficulty == difficulty) &&
            (topic == "All topics" || p.tags.contains(topic)) &&
            (filter == "All problems" || (filter == "Favorites" ? progress[String(p.id)]?.favorite == true : filter == "Premium" ? p.premium : (progress[String(p.id)]?.status ?? "Unstarted") == filter))
        }
        return ids == nil ? matches : matches.sorted { (order[$0.id] ?? .max) < (order[$1.id] ?? .max) }
    }
    var currentCatalog: [ProblemSummary] { section == .learning ? learningCatalog : catalog }
    var currentActivity: [Activity] { let ids = Set(currentCatalog.map(\.id)); return activity.filter { ids.contains($0.problemID) } }
    var topics: [String] { Array(Set(currentCatalog.flatMap(\.tags))).sorted() }
    var solved: Int { catalog.filter { progress[String($0.id)]?.status == "Solved" }.count }
    var currentSolved: Int { currentCatalog.filter { progress[String($0.id)]?.status == "Solved" }.count }
    var activePlan: StudyPlan? { section == .problems ? studyPlans.first { $0.id == selectedPlan } : nil }
    var activeCustomList: CustomList? { section == .problems ? customLists.first { $0.id == selectedPlan } : nil }
    var activeCourse: LearningCourse? { section == .learning ? learningCourses.first { $0.id == selectedCourse } : nil }
    var isSystemDesign: Bool { section == .learning && problem?.tags.contains("System design") == true }
    var lessonIndex: Int? { selection.flatMap { activeCourse?.questionIDs.firstIndex(of: $0) } }
    var nextIncompleteLesson: Int? { activeCourse?.questionIDs.first { progress[String($0)]?.status != "Solved" } }
    func canMoveLesson(_ offset: Int) -> Bool {
        guard !running, let course = activeCourse, let lessonIndex else { return false }
        return course.questionIDs.indices.contains(lessonIndex + offset)
    }
    func choosePlan(_ id: String) {
        guard !running, saveNow() else { return }
        section = .problems
        selectedPlan = id
        clearFiltersAndSelect()
    }
    func chooseSection(_ next: PracticeSection) {
        guard !running, section != next, saveNow() else { return }
        section = next
        clearFiltersAndSelect()
    }
    func chooseCourse(_ id: String) {
        guard !running, saveNow() else { return }
        selectedCourse = id
        clearFiltersAndSelect()
    }
    func clearFiltersAndSelect() {
        search = ""
        difficulty = "All difficulties"
        topic = "All topics"
        filter = "All problems"
        let first = section == .learning ? filtered.first { progress[String($0.id)]?.status != "Solved" } ?? filtered.first : filtered.first
        if let first { select(first.id) }
        else if saveNow() { activeKey = nil; selection = nil; problem = nil; notes = "" }
    }
    func moveLesson(_ offset: Int) {
        guard !running, let course = activeCourse, let selection,
              let index = course.questionIDs.firstIndex(of: selection),
              course.questionIDs.indices.contains(index + offset), saveNow() else { return }
        search = ""; difficulty = "All difficulties"; topic = "All topics"; filter = "All problems"
        select(course.questionIDs[index + offset])
    }
    func resumeLearning() {
        guard section == .learning, !running, saveNow() else { return }
        clearFiltersAndSelect()
    }
    func updateDesign(_ design: DesignWorkspace) {
        guard isSystemDesign, activeKey != nil, !running else { return }
        workspace.design = design
        if record.status == "Unstarted" {
            var updated = record
            updated.status = "In progress"
            progress[String(selection ?? 0)] = updated
        }
        edited(affectsSolution: false)
    }
    @discardableResult func saveDesignExperiment() -> Bool {
        guard let design = workspace.design, isSystemDesign, !running else { return false }
        let result = DesignSimulation.run(diagram: design.diagram, scenario: design.scenario)
        guard result.valid else { return false }
        var next = design
        next.experiments.append(DesignExperiment(name: "Experiment \(next.experiments.count + 1)", diagram: design.diagram, scenario: design.scenario, result: result))
        updateDesign(next)
        return saveNow()
    }
    var record: ProgressRecord { progress[String(selection ?? 0)] ?? ProgressRecord() }
    var activeFilename: String { workspace.selectedFile ?? "\(problem?.slug ?? "solution").\(language.ext)" }
    var key: String? { problem?.course.map { "course-\($0.workspaceID)-python" } ?? selection.map { "\($0)-\(language.rawValue)" } }

    func select(_ id: Int?) {
        guard id != selection || problem == nil else { return }
        guard saveNow() else { return }
        do {
            guard let id else { return }
            let learning = learningCatalog.contains { $0.id == id }
            let next = try JSONDecoder().decode(Problem.self, from: Data(contentsOf: libraryURL.appendingPathComponent("\(learning ? "learning/" : "")problems/\(id).json")))
            loading = true
            selection = id
            problem = next
            if learning { language = .python }
            else if next.tags.contains("Database") { language = .sql }
            else if language == .sql { language = .python }
            notes = progress[String(id)]?.notes ?? ""
            result = nil
            loadWorkspace()
            UserDefaults.standard.set(id, forKey: "lastProblem")
            loading = false
        } catch { self.error = "Could not open question: \(error.localizedDescription)"; loading = false }
    }

    func changeLanguage(_ next: Language) {
        guard next != language, saveNow() else { return }
        loading = true
        language = next
        UserDefaults.standard.set(next.rawValue, forKey: "language")
        loadWorkspace()
        result = nil
        loading = false
    }

    func loadWorkspace() {
        guard let key, let problem else { return }
        activeKey = key
        let url = workURL.appendingPathComponent(key + ".json")
        if FileManager.default.fileExists(atPath: url.path) {
            do { workspace = try JSONDecoder().decode(Workspace.self, from: Data(contentsOf: url)) }
            catch { self.error = "Saved code could not be read. It has been preserved on disk. \(error.localizedDescription)"; activeKey = nil }
        } else {
            let template = problem.starters[language.rawValue]
            workspace = Workspace(code: template ?? language.program, tests: sampleTests(), stdin: language == .sql ? problem.sqlSetup ?? "-- Add CREATE TABLE and INSERT statements here.\n" : "", mode: language == .sql ? "sql" : template == nil ? "program" : "function")
            if let course = problem.course {
                do {
                    let url = libraryURL.appendingPathComponent("learning/\(course.courseID ?? "python-engineer")/\(course.workspaceID).json")
                    workspace.files = try JSONDecoder().decode([String: String].self, from: Data(contentsOf: url))
                    workspace.selectedFile = course.entrypoint
                    workspace.code = workspace.files?[course.entrypoint] ?? ""
                    workspace.mode = "course"
                } catch { self.error = "Course workspace could not load: \(error.localizedDescription)"; activeKey = nil }
            }
        }
        if workspace.testCaseDrafts == nil {
            workspace.testCaseDrafts = try? TestCaseDraft.decode(workspace.tests)
        }
        if isSystemDesign && workspace.design == nil { workspace.design = DesignWorkspace() }
    }

    var testCaseError: String? {
        guard workspace.mode == "function" else { return nil }
        do {
            let cases = try workspace.testCaseDrafts ?? TestCaseDraft.decode(workspace.tests)
            guard (1...50).contains(cases.count) else { throw TestCaseError.caseCount }
            _ = try TestCaseDraft.encode(cases)
            return nil
        } catch { return error.localizedDescription }
    }

    func updateTestCases(_ cases: [TestCaseDraft]) {
        workspace.testCaseDrafts = cases
        if let encoded = try? TestCaseDraft.encode(cases) { workspace.tests = encoded }
        edited()
    }

    func loadExampleTests() {
        workspace.tests = sampleTests()
        workspace.testCaseDrafts = try? TestCaseDraft.decode(workspace.tests)
        edited()
    }

    func sampleTests() -> String {
        guard let problem else { return "[]" }
        let cases: [JSONValue] = problem.samples.compactMap { sample in
            guard let args = sample.args else { return nil }
            // JSON null decodes to nil for Optional<JSONValue>.
            return .object(["args": .array(args), "expected": sample.expected ?? .null])
        }
        let encoder = JSONEncoder()
        encoder.outputFormatting = [.prettyPrinted, .sortedKeys, .withoutEscapingSlashes]
        return (try? String(data: encoder.encode(cases), encoding: .utf8)) ?? "[]"
    }

    func edited(affectsSolution: Bool = true) {
        guard !loading, activeKey != nil else { return }
        saveMessage = "Saving…"
        if affectsSolution {
            if let course = problem?.course {
                let code = workspace.code
                if let name = workspace.selectedFile { workspace.files?[name] = code }
                for (id, step) in courseSteps where step.workspaceID == course.workspaceID && progress[id] != nil {
                    progress[id]?.status = "In progress"
                }
            }
            var updated = record
            updated.status = "In progress"
            progress[String(selection ?? 0)] = updated
        }
        saveTask?.cancel()
        saveTask = Task { [weak self] in
            do { try await Task.sleep(for: .milliseconds(450)) } catch { return }
            self?.saveNow()
        }
    }

    @discardableResult func saveNow() -> Bool {
        saveTask?.cancel()
        guard !loading, let activeKey else { return true }
        do {
            let code = workspace.code
            if let name = workspace.selectedFile { workspace.files?[name] = code }
            var updated = record
            updated.notes = notes
            var nextProgress = progress
            nextProgress[String(selection ?? 0)] = updated
            let encoder = JSONEncoder()
            try encoder.encode(workspace).write(to: workURL.appendingPathComponent(activeKey + ".json"), options: .atomic)
            try encoder.encode(nextProgress).write(to: workURL.appendingPathComponent("progress.json"), options: .atomic)
            try encoder.encode(activity).write(to: workURL.appendingPathComponent("activity.json"), options: .atomic)
            progress = nextProgress
            saveMessage = "Saved"
            return true
        } catch {
            saveMessage = "Save failed"
            self.error = "Could not save your work. Keep this window open and check disk permissions. \(error.localizedDescription)"
            return false
        }
    }

    func toggleFavorite() {
        var next = record
        next.favorite.toggle()
        progress[String(selection ?? 0)] = next
        saveNow()
    }

    func run() {
        guard !running, let problem, saveNow() else { return }
        if let testCaseError { self.error = testCaseError; return }
        do {
            let submitted = workspace
            let runURL = workURL.appendingPathComponent("runs/\(UUID().uuidString)")
            try FileManager.default.createDirectory(at: runURL, withIntermediateDirectories: true)
            var request: [String: String] = ["language": language.rawValue, "code": workspace.code,
                "mode": workspace.mode, "stdin": workspace.stdin, "tests": workspace.tests,
                "reference": problem.references[language.rawValue] ?? workspace.code]
            if let files = workspace.files {
                request["courseStep"] = String(problem.id)
                request["courseFiles"] = String(decoding: try JSONEncoder().encode(files), as: UTF8.self)
                request["courseAction"] = courseAction
                courseAction = "check"
            }
            let gradesSubmission = problem.course == nil || request["courseAction"] == "check"
            let requestURL = runURL.appendingPathComponent("request.json")
            try JSONEncoder().encode(request).write(to: requestURL)
            let outputURL = runURL.appendingPathComponent("result.json")
            FileManager.default.createFile(atPath: outputURL.path, contents: nil)
            let output = try FileHandle(forWritingTo: outputURL)
            let task = Process()
            let runtimes = scriptsURL.deletingLastPathComponent().appendingPathComponent("runtimes")
            #if arch(arm64)
            let runtimeArchitecture = "arm64"
            #else
            let runtimeArchitecture = "x86_64"
            #endif
            task.executableURL = Bundle.main.bundleIdentifier == "local.offlinepractice.mac" || FileManager.default.fileExists(atPath: runtimes.path)
                ? runtimes.appendingPathComponent("\(runtimeArchitecture)/python/bin/python3")
                : URL(fileURLWithPath: "/usr/bin/python3")
            task.arguments = ["-I", "-B", scriptsURL.appendingPathComponent("runner.py").path, "--request", requestURL.path]
            task.currentDirectoryURL = scriptsURL.deletingLastPathComponent()
            task.standardOutput = output
            task.standardError = output
            let runProblemID = problem.id
            let runLanguage = language.rawValue
            let runMode = workspace.mode
            task.terminationHandler = { [weak self] finished in
                let status = finished.terminationStatus
                Task { @MainActor in
                    try? output.close()
                    guard let self else { return }
                    self.running = false
                    self.process = nil
                    if status == 130 || status == 15 {
                        self.result = RunResult(success: false, message: "Stopped", output: "The local run was stopped.", cases: [], duration: nil)
                        self.activity.append(Activity(problemID: runProblemID, language: runLanguage, mode: runMode, success: false, passed: 0, total: 0, duration: nil, stopped: true))
                    } else {
                        do {
                            let decoded = try JSONDecoder().decode(RunResult.self, from: Data(contentsOf: outputURL))
                            if self.selection == runProblemID { self.result = decoded }
                            self.updateProgressAfterRun(decoded, problemID: runProblemID, language: runLanguage, submitted: submitted)
                            self.activity.append(Activity(problemID: runProblemID, language: runLanguage, mode: runMode, success: decoded.success, passed: decoded.cases?.filter(\.passed).count ?? 0, total: decoded.cases?.count ?? 0, duration: decoded.duration))
                        } catch {
                            self.result = RunResult(success: false, message: "Runner could not start", output: "\(error.localizedDescription)\nReinstall PracticeCode from the full disk image if a bundled runtime is missing.", cases: [], duration: nil)
                        }
                    }
                    self.saveNow()
                    // Only ephemeral request/results live here; saved work is elsewhere.
                    try? FileManager.default.removeItem(at: runURL)
                }
            }
            try task.run()
            process = task
            running = true
            result = nil
            consoleTab = "Results"
            if gradesSubmission {
                var updated = record
                updated.status = "In progress"
                progress[String(problem.id)] = updated
            }
        } catch { self.error = "Could not start local runner: \(error.localizedDescription)" }
    }

    func updateProgressAfterRun(_ result: RunResult, problemID: Int, language: String, submitted: Workspace) {
        guard selection == problemID, self.language.rawValue == language,
              workspace.code == submitted.code, workspace.tests == submitted.tests,
              workspace.files == submitted.files,
              workspace.mode == submitted.mode, testCaseError == nil else { return }
        var updated = progress[String(problemID)] ?? ProgressRecord()
        let cases = result.cases ?? []
        if submitted.mode == "course" {
            guard let check = result.course, check.graded else { return }
            let step = courseSteps[String(problemID)]
            updated.status = result.success && !cases.isEmpty && cases.allSatisfy(\.passed)
                && check.workspaceID == step?.workspaceID && check.checkGroup == step?.checkGroup && check.version == step?.version ? "Solved" : "In progress"
            updated.courseVersion = step?.version
            progress[String(problemID)] = updated
            return
        }
        let expectedCount = (try? TestCaseDraft.decode(submitted.tests).count) ?? 0
        updated.status = submitted.mode == "function" && result.success && !cases.isEmpty &&
            cases.count == expectedCount && cases.allSatisfy(\.passed) ? "Solved" : "In progress"
        progress[String(problemID)] = updated
    }
    func stop() { process?.terminate() }

    func resetAccount() {
        guard !running, saveNow() else { return }
        saveTask?.cancel()
        let manager = FileManager.default
        let stamp = ISO8601DateFormatter().string(from: Date()).replacingOccurrences(of: ":", with: "-")
        let backup = workURL.appendingPathComponent("backups/\(stamp)-\(UUID().uuidString.prefix(8))")
        var moved: [(URL, URL)] = []
        do {
            try manager.createDirectory(at: backup, withIntermediateDirectories: true)
            let files = try manager.contentsOfDirectory(at: workURL, includingPropertiesForKeys: nil)
                .filter { $0.lastPathComponent != "backups" }
            for file in files {
                let destination = backup.appendingPathComponent(file.lastPathComponent)
                try manager.moveItem(at: file, to: destination)
                moved.append((file, destination))
            }
        } catch {
            var rollbackErrors: [String] = []
            for (original, destination) in moved.reversed() {
                do { try manager.moveItem(at: destination, to: original) }
                catch { rollbackErrors.append(error.localizedDescription) }
            }
            self.error = "Reset could not finish. Your files were preserved. Backup: \(backup.path). \(error.localizedDescription) \(rollbackErrors.joined(separator: "; "))"
            return
        }
        // Detach the old workspace before selecting a fresh problem, preventing an old-code autosave.
        activeKey = nil
        progress = [:]
        activity = []
        customLists = []
        customListsReadable = true
        notes = ""
        result = nil
        selection = nil
        problem = nil
        workspace = Workspace()
        language = .python
        search = ""
        topic = "All topics"
        difficulty = "All difficulties"
        filter = "All problems"
        selectedPlan = "all"
        section = catalog.isEmpty ? .learning : .problems
        selectedCourse = learningCourses.first?.id ?? ""
        statementTab = "Description"
        consoleTab = "Results"
        latestBackup = backup
        UserDefaults.standard.set(language.rawValue, forKey: "language")
        select((catalog.first ?? learningCatalog.first)?.id)
        saveNow()
    }

    func exportCode() {
        let panel = NSSavePanel()
        panel.nameFieldStringValue = activeFilename
        if panel.runModal() == .OK, let url = panel.url {
            do { try workspace.code.write(to: url, atomically: true, encoding: .utf8) }
            catch { self.error = "Export failed: \(error.localizedDescription)" }
        }
    }
}

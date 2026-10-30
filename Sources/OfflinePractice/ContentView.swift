import AppKit
import SwiftUI

// This SDK also exports a State macro; select the property wrapper explicitly.
typealias ViewState<Value> = SwiftUI.State<Value>

struct ContentView: View {
    @Bindable var store: Store
    @FocusState private var searchFocused: Bool
    @Environment(\.openWindow) private var openWindow
    @Environment(\.openSettings) private var openSettings
    @AppStorage("workspaceLayout") private var layout = "split"
    @AppStorage("consoleExpanded") private var consoleExpanded = true
    @ViewState<NavigationSplitViewVisibility> private var columnVisibility = .all
    @ViewState private var showPersonalLists = false
    @ViewState private var showFilters = false
    @ViewState private var showTrackDetails = false
    @AppStorage("systemDesignWorkspace") private var designTab = "Code"

    var body: some View {
        NavigationSplitView(columnVisibility: $columnVisibility) {
            sidebar
                .navigationSplitViewColumnWidth(min: 245, ideal: 270, max: 360)
        } detail: {
            if let problem = store.problem {
                if layout == "question" {
                    statement(problem).modifier(PaneSurface()).padding(10)
                } else if layout == "code" {
                    coding(problem).modifier(PaneSurface()).padding(10)
                } else {
                    HSplitView {
                        statement(problem).frame(minWidth: 320, idealWidth: 510).modifier(PaneSurface())
                        coding(problem).frame(minWidth: 400, idealWidth: 660).modifier(PaneSurface())
                    }.padding(10)
                }
            } else {
                ContentUnavailableView("Your practice library", systemImage: "books.vertical", description: Text("Select a question to start practicing."))
            }
        }
        .background(FreeCodeTheme.workspace)
        .foregroundStyle(FreeCodeTheme.text)
        .tint(FreeCodeTheme.accent)
        .safeAreaInset(edge: .bottom, spacing: 0) {
            if let course = store.activeCourse, let index = store.lessonIndex {
                HStack(spacing: 16) {
                    Button { store.moveLesson(-1) } label: { Label("Previous lesson", systemImage: "arrow.left") }
                        .disabled(!store.canMoveLesson(-1)).help("Previous lesson · ⌥⌘←")
                    Spacer()
                    Text("Step \(index + 1) of \(course.questionIDs.count)").font(.callout.monospacedDigit()).foregroundStyle(FreeCodeTheme.secondary)
                    Spacer()
                    Button { store.moveLesson(1) } label: { Label("Next lesson", systemImage: "arrow.right") }
                        .buttonStyle(.borderedProminent).foregroundStyle(FreeCodeTheme.actionText).disabled(!store.canMoveLesson(1)).help("Next lesson · ⌥⌘→")
                }.controlSize(.regular).padding(.horizontal, 20).padding(.vertical, 12).background(FreeCodeTheme.sidebar)
            }
        }
        .toolbar {
            ToolbarItem(placement: .navigation) {
                Text(store.activeCourse.map { "Learning  /  \($0.name)" } ?? "Problems")
                    .font(.callout).foregroundStyle(FreeCodeTheme.secondary).lineLimit(1)
            }
            ToolbarItem(placement: .automatic) { Spacer() }
            ToolbarItemGroup(placement: .primaryAction) {
                Button { openWindow(id: "statistics") } label: { Image(systemName: "chart.bar") }
                    .help("Statistics").accessibilityLabel("Statistics")
                Button { if let next = store.filtered.randomElement() { store.select(next.id) } } label: { Image(systemName: "shuffle") }
                    .disabled(store.running || store.filtered.isEmpty)
                    .help("Random question").accessibilityLabel("Random question")
                Button { openSettings() } label: { Image(systemName: "gearshape") }
                    .help("Settings · ⌘,").accessibilityLabel("Settings")
            }
        }
        .background {
            Button("") { searchFocused = true }.keyboardShortcut("f", modifiers: .command).hidden()
        }
        .sheet(isPresented: $store.showCoverage) { CoverageView(store: store) }
        .sheet(isPresented: $showPersonalLists) { PersonalListsView(store: store) }
        .alert("PracticeCode", isPresented: Binding(get: { store.error != nil }, set: { if !$0 { store.error = nil } })) {
            Button("OK") { store.error = nil }
        } message: { Text(store.error ?? "") }
        .confirmationDialog("Replace the current code with the starter?", isPresented: $store.showReset) {
            Button("Replace code", role: .destructive) {
                store.replaceCurrentStarter()
            }
        } message: { Text("This replaces the code for this question and language. Your other solutions are kept.") }
        .onAppear { columnVisibility = layout == "split" ? .all : .detailOnly }
        .onChange(of: layout) { _, value in
            columnVisibility = value == "split" ? .all : .detailOnly
            if value == "code" { consoleExpanded = false }
        }
        .onChange(of: store.running) { _, running in
            if running {
                if layout == "question" { layout = "split" }
                designTab = "Code"
                consoleExpanded = true
            }
        }
        .frame(minWidth: layout == "split" ? 1050 : 620, minHeight: 680)
        .toolbarBackground(FreeCodeTheme.workspace, for: .windowToolbar)
        .toolbarBackground(.visible, for: .windowToolbar)
        .tint(FreeCodeTheme.accent)
    }

    private var sidebar: some View {
        VStack(spacing: 0) {
            VStack(alignment: .leading, spacing: 12) {
                HStack(spacing: 10) {
                    Image(nsImage: NSApplication.shared.applicationIconImage).resizable().frame(width: 30, height: 30)
                    Text("PracticeCode").font(.system(size: 22, weight: .semibold)).tracking(-0.6)
                }.padding(.bottom, 5)
                VStack(spacing: 5) {
                    if !store.catalog.isEmpty { destination(.problems, symbol: "doc.text") }
                    destination(.learning, symbol: "book.closed")
                }
                searchField
                if store.section == .learning {
                    if let course = store.activeCourse {
                        HStack {
                            Picker("Track", selection: Binding(get: { store.selectedCourse }, set: store.chooseCourse)) {
                                ForEach(store.learningCourses) { Text($0.name).tag($0.id) }
                            }.labelsHidden().disabled(store.running)
                            Button { showTrackDetails.toggle() } label: { Image(systemName: "info.circle") }
                                .buttonStyle(.plain).accessibilityLabel("Track details")
                                .popover(isPresented: $showTrackDetails) { Text(course.summary).font(.callout).padding(20).frame(width: 320) }
                        }
                        let completed = course.questionIDs.filter { store.progress[String($0)]?.status == "Solved" }.count
                        HStack {
                            Text("\(completed) / \(course.questionIDs.count) completed").font(.caption.monospacedDigit()).foregroundStyle(FreeCodeTheme.secondary)
                            Spacer()
                            Button("Resume") { store.resumeLearning() }.controlSize(.small).disabled(store.running)
                        }
                        ProgressView(value: Double(completed), total: Double(max(1, course.questionIDs.count))).controlSize(.small)
                    }
                } else {
                    Picker("Collection", selection: Binding(get: { store.selectedPlan }, set: store.choosePlan)) {
                        Text("All questions").tag("all")
                        Text("All SQL questions").tag("sql")
                        Section("My lists") {
                            ForEach(store.customLists) { Text($0.name).tag($0.id) }
                        }
                        Section("LeetCode study plans") {
                            ForEach(store.studyPlans) { plan in Text(plan.name).tag(plan.id) }
                        }
                    }.controlSize(.small).disabled(store.running)
                    Button("Manage my lists…", systemImage: "text.badge.plus") { showPersonalLists = true }
                        .controlSize(.small).disabled(store.running)
                    if let list = store.activeCustomList {
                        Text("\(list.questionIDs.count) questions · Your personal list").font(.caption).foregroundStyle(.secondary)
                    }
                }
                if let plan = store.activePlan {
                    let solved = plan.questionIDs.filter { store.progress[String($0)]?.status == "Solved" }.count
                    Text("\(solved) of \(plan.questionIDs.count) downloaded entries solved").font(.caption).foregroundStyle(.secondary)
                    if let note = plan.membershipNote {
                        Text(note).font(.caption2).foregroundStyle(.secondary)
                    }
                }
            }.padding(.horizontal, 16).padding(.top, 18).padding(.bottom, 14)
            Divider()
            let problems = store.filtered
            if problems.isEmpty {
                if let list = store.activeCustomList, list.questionIDs.isEmpty {
                    ContentUnavailableView("Your list is empty", systemImage: "text.badge.plus", description: Text("Browse the problem library and use Lists on a question to add it here."))
                        .frame(maxHeight: .infinity)
                    Button("Browse all problems") { store.choosePlan("all") }.padding()
                } else if let plan = store.activePlan, plan.questionIDs.isEmpty {
                    ContentUnavailableView("Question list unavailable", systemImage: "list.bullet.rectangle", description: Text("The public source does not expose this playlist’s membership. Use All questions to practice from the full local library."))
                        .frame(maxHeight: .infinity)
                } else {
                    ContentUnavailableView.search(text: store.search).frame(maxHeight: .infinity)
                }
                Button("Clear filters") {
                    store.clearFiltersAndSelect()
                }.padding()
            } else {
                List(selection: Binding(get: { store.selection }, set: { if !store.running { store.select($0) } })) {
                    if let groups = store.activeCourse?.groups ?? store.activePlan?.groups {
                        ForEach(groups) { group in
                            let ids = Set(group.questionIDs)
                            let rows = problems.filter { ids.contains($0.id) }
                            if !rows.isEmpty {
                                Section(group.name) {
                                    ForEach(rows) { p in
                                        ProblemRow(problem: p, progress: store.progress[String(p.id)], number: store.section == .learning ? (store.activeCourse?.questionIDs.firstIndex(of: p.id)).map { $0 + 1 } : p.id).tag(p.id)
                                            .listRowBackground(store.selection == p.id ? FreeCodeTheme.selection : Color.clear)
                                    }
                                }
                            }
                        }
                    } else {
                        ForEach(problems) { p in
                            ProblemRow(problem: p, progress: store.progress[String(p.id)], number: p.id).tag(p.id)
                                            .listRowBackground(store.selection == p.id ? FreeCodeTheme.selection : Color.clear)
                        }
                    }
                }.listStyle(.sidebar).scrollContentBackground(.hidden)
                    .background(FreeCodeTheme.sidebar).tint(FreeCodeTheme.selection)
            }
            Divider()
            HStack(spacing: 6) {
                Image(systemName: "checkmark.circle").foregroundStyle(FreeCodeTheme.accent)
                Text("\(store.currentSolved) \(store.section == .learning ? "completed" : "solved")")
                Spacer()
                Text("\(problems.count) shown").foregroundStyle(.secondary)
            }.font(.caption).foregroundStyle(FreeCodeTheme.secondary).padding(.horizontal, 16).padding(.vertical, 12)
        }.background(FreeCodeTheme.sidebar)
    }

    private func destination(_ section: PracticeSection, symbol: String) -> some View {
        Button { store.chooseSection(section) } label: {
            HStack(spacing: 10) {
                Image(systemName: symbol).frame(width: 18)
                Text(section.rawValue).font(.system(size: 14, weight: store.section == section ? .semibold : .regular))
                Spacer()
            }.padding(.horizontal, 10).padding(.vertical, 9)
                .background(store.section == section ? FreeCodeTheme.selection : .clear, in: RoundedRectangle(cornerRadius: 6))
                .contentShape(Rectangle())
        }.buttonStyle(.plain).accessibilityAddTraits(store.section == section ? .isSelected : [])
    }

    private var searchField: some View {
        HStack(spacing: 8) {
            HStack(spacing: 7) {
                Image(systemName: "magnifyingglass").foregroundStyle(FreeCodeTheme.secondary)
                TextField(store.section == .learning ? "Search lessons…" : "Search problems…", text: $store.search)
                    .textFieldStyle(.plain).focused($searchFocused).accessibilityLabel(store.section == .learning ? "Search lessons" : "Search problems")
                if !store.search.isEmpty {
                    Button { store.search = "" } label: { Image(systemName: "xmark.circle.fill") }
                        .buttonStyle(.plain).accessibilityLabel("Clear search")
                }
            }.padding(9).background(FreeCodeTheme.editor, in: RoundedRectangle(cornerRadius: 6))
                .overlay { RoundedRectangle(cornerRadius: 6).strokeBorder(FreeCodeTheme.border) }
            Button { showFilters.toggle() } label: {
                Image(systemName: hasFilters ? "line.3.horizontal.decrease.circle.fill" : "slider.horizontal.3")
                    .foregroundStyle(hasFilters ? FreeCodeTheme.accent : FreeCodeTheme.secondary)
            }.buttonStyle(.plain).help(hasFilters ? "Filters are active" : "Search and filters").accessibilityLabel("Search and filters")
                .popover(isPresented: $showFilters) { filterControls.padding(20).frame(width: 300) }
        }
    }
    private var hasFilters: Bool { store.difficulty != "All difficulties" || store.topic != "All topics" || store.filter != "All problems" }
    private var filterControls: some View {
        VStack(alignment: .leading, spacing: 16) {
            Text("Filter \(store.section == .learning ? "lessons" : "problems")").font(.headline)
            Picker("Difficulty", selection: $store.difficulty) {
                ForEach(["All difficulties", "Easy", "Medium", "Hard"], id: \.self) { Text($0) }
            }
            Picker("Progress", selection: $store.filter) {
                Text(store.section == .learning ? "All lessons" : "All problems").tag("All problems")
                ForEach(["Unstarted", "In progress", "Solved", "Favorites"], id: \.self) { Text($0) }
                if store.section == .problems { Text("Premium").tag("Premium") }
            }
            Picker("Topic", selection: $store.topic) {
                Text("All topics").tag("All topics")
                ForEach(store.topics, id: \.self) { Text($0) }
            }
            Button("Clear filters") { store.clearFiltersAndSelect() }
        }.foregroundStyle(FreeCodeTheme.text)
    }

    private func statement(_ p: Problem) -> some View {
        VStack(spacing: 0) {
            HStack {
                WorkspaceTabs(label: "Problem content", options: ["Description", "Solutions", "Notes"], selection: $store.statementTab)
                Spacer()
                Button { layout = layout == "question" ? "split" : "question" } label: {
                    Image(systemName: layout == "question" ? "arrow.down.right.and.arrow.up.left" : "arrow.up.left.and.arrow.down.right")
                }.buttonStyle(.plain).accessibilityLabel(layout == "question" ? "Restore both panels" : "Focus on question")
            }.padding(.horizontal, 18)
            Divider()
            VStack(alignment: .leading, spacing: 13) {
                HStack(alignment: .firstTextBaseline) {
                    Text(store.section == .learning ? p.title : "\(p.id). \(p.title)").font(.system(size: 23, weight: .semibold)).tracking(-0.4).textSelection(.enabled)
                    Spacer(minLength: 6)
                    if store.section == .problems {
                        Menu {
                            ForEach(store.customLists) { list in
                                Button { store.toggleMembership(in: list.id, questionID: p.id) } label: {
                                    Label(list.name, systemImage: list.questionIDs.contains(p.id) ? "checkmark" : "plus")
                                }
                            }
                            Divider()
                            Button("Manage my lists…") { showPersonalLists = true }
                        } label: { Label("Lists", systemImage: "text.badge.plus") }
                        .menuStyle(.borderlessButton).fixedSize()
                        .help("Add or remove this question from your personal lists")
                        .disabled(store.running || !store.customListsReadable)
                    }
                    Button(action: store.toggleFavorite) {
                        Image(systemName: store.record.favorite ? "star.fill" : "star")
                            .foregroundStyle(store.record.favorite ? Color.orange : .secondary)
                    }.buttonStyle(.plain).help(store.record.favorite ? "Remove from favorites" : "Add to favorites")
                        .accessibilityLabel(store.record.favorite ? "Remove from favorites" : "Add to favorites")
                }
                HStack(spacing: 12) {
                    Text(p.difficulty).font(.callout.weight(.medium)).foregroundStyle(difficultyColor(p.difficulty))
                    if p.premium { Label("Premium", systemImage: "lock.open").font(.caption).foregroundStyle(.secondary) }
                    Spacer()
                    Label(store.record.status, systemImage: store.record.status == "Solved" ? "checkmark.circle.fill" : store.record.status == "In progress" ? "circle.lefthalf.filled" : "circle")
                        .font(.caption).foregroundStyle(store.record.status == "Solved" ? FreeCodeTheme.accent : FreeCodeTheme.secondary)
                        .help("Editing starts progress. Passing all configured function tests marks this solution solved.")
                }
                ScrollView(.horizontal, showsIndicators: false) {
                    HStack(spacing: 6) {
                        ForEach(p.tags, id: \.self) { tag in
                            Button(tag) { store.topic = tag }
                                .buttonStyle(.plain).font(.caption).foregroundStyle(FreeCodeTheme.secondary)
                                .padding(.horizontal, 8).padding(.vertical, 4).background(FreeCodeTheme.editor, in: RoundedRectangle(cornerRadius: 4))
                        }
                    }
                }
            }.padding(.horizontal, 24).padding(.top, 24).padding(.bottom, 12)
            if !p.missingImages.isEmpty && store.statementTab == "Description" {
                Label("\(p.missingImages.count) diagram\(p.missingImages.count == 1 ? " is" : "s are") unavailable in the source archive. The question text is saved locally.", systemImage: "photo.badge.exclamationmark")
                    .font(.caption).foregroundStyle(.secondary).padding(.horizontal, 24).padding(.bottom, 12)
            }
            if store.statementTab == "Description" {
                StatementView(html: p.statement, root: store.libraryURL, identity: p.id)
            } else if store.statementTab == "Solutions" {
                VStack(alignment: .leading, spacing: 12) {
                    if store.isCourseExercise && store.record.status == "Unstarted" {
                        Text("Try the exercise first").font(.headline)
                        Text("Make an attempt before opening the worked implementation.").foregroundStyle(.secondary)
                    } else {
                    Text("\(store.section == .learning ? "Worked" : "Reference") solution · \(store.language.title)").font(.headline)
                    Text(store.section == .learning ? "A worked implementation for this lesson. Compare your approach after attempting the exercise." : "Community reference from Doocs. Your own code stays in the editor alongside it.").font(.callout).foregroundStyle(.secondary)
                    if store.language == .sql {
                        Text("SQL references use the source dialect, usually MySQL. Adapt dialect-specific syntax before running in SQLite.").font(.caption).foregroundStyle(.secondary)
                    }
                    if let reference = p.references[store.language.rawValue] {
                        CodeEditor(text: .constant(reference), editable: false, identity: "ref-\(p.id)-\(store.language.rawValue)", commentPrefix: store.language.commentPrefix)
                    } else {
                        ContentUnavailableView("No reference in \(store.language.title)", systemImage: "doc.text", description: Text("Try another language. The question remains available offline."))
                    }
                    }
                }.padding(20)
            } else {
                VStack(alignment: .leading, spacing: 10) {
                    Text("Your notes").font(.headline)
                    Text("Approach, complexity, and things to revisit.").font(.callout).foregroundStyle(.secondary)
                    TextEditor(text: Binding(get: { store.notes }, set: { store.notes = $0; store.edited(affectsSolution: false) })).font(.body).padding(8).background(.background)
                }.padding(20)
            }
            Divider()
            HStack {
                Text(store.section == .learning ? "PracticeCode lesson" : "Statement: LeetCode · Archive: Doocs").font(.caption).foregroundStyle(FreeCodeTheme.secondary)
                Spacer()
                if let url = URL(string: p.sourceURL) {
                    Link(store.section == .learning ? "Further reading" : "Source", destination: url).font(.caption).help("Open the source in your browser (requires internet)")
                }
            }.padding(.horizontal, 20).padding(.vertical, 10)
        }
    }

    private func coding(_ p: Problem) -> some View {
        VStack(spacing: 0) {
            HStack {
                if store.isSystemDesign {
                    WorkspaceTabs(label: "System design workspace", options: ["Code", "Architecture"], selection: $designTab)
                } else { Text("Code").font(.headline).padding(.vertical, 13) }
                Spacer()
                if !store.isSystemDesign || designTab == "Code" {
                    if store.running {
                        ProgressView().controlSize(.small)
                        Button("Stop", systemImage: "stop.fill", action: store.stop)
                            .keyboardShortcut(".", modifiers: .command)
                    } else {
                        Button(action: store.run) {
                            Label(store.isCourseExercise ? "Run required checks" : store.language == .sql ? "Run query" : "Run code", systemImage: "play.fill")
                        }
                        .buttonStyle(RunCodeStyle())
                        .disabled(store.problem == nil || store.testCaseError != nil)
                        .help(store.testCaseError ?? "Run local tests · ⌘Return")
                    }
                }
                Button { layout = layout == "code" ? "split" : "code" } label: {
                    Image(systemName: layout == "code" ? "arrow.down.right.and.arrow.up.left" : "arrow.up.left.and.arrow.down.right")
                }.buttonStyle(.plain).accessibilityLabel(layout == "code" ? "Restore both panels" : "Focus on code")
            }.padding(.horizontal, 16)
            Divider()
            if store.isSystemDesign && designTab == "Architecture" {
                DesignLabView(store: store).id(store.key)
            } else if consoleExpanded {
                VSplitView {
                    codePane(p)
                    console
                }
            } else {
                codePane(p)
                Divider()
                Button { consoleExpanded = true } label: {
                    HStack {
                        Label("Show tests & results", systemImage: "chevron.up")
                        Spacer()
                        if let error = store.testCaseError {
                            Text(error).foregroundStyle(.orange).lineLimit(1)
                        } else if let result = store.result {
                            Text(result.message).foregroundStyle(.secondary).lineLimit(1)
                        }
                    }.font(.caption).padding(.horizontal, 16).padding(.vertical, 10).contentShape(Rectangle())
                }.buttonStyle(.plain)
            }
        }
    }

    private func codePane(_ p: Problem) -> some View {
        VStack(spacing: 0) {
            HStack {
                Picker("Language", selection: Binding(get: { store.language }, set: store.changeLanguage)) {
                    ForEach(store.section == .learning ? [.python] : Language.allCases) { Text($0.title).tag($0) }
                }.labelsHidden().fixedSize().disabled(store.running)
                Spacer()
                Text(store.activeFilename).font(.caption.monospaced()).foregroundStyle(FreeCodeTheme.secondary).lineLimit(1)
                Menu {
                    Button("Toggle Line Comment", systemImage: "text.bubble") {
                        NSApp.sendAction(#selector(CommentingTextView.toggleLineComment(_:)), to: nil, from: nil)
                    }
                    Divider()
                    Button("Export code…", action: store.exportCode)
                    Button("Replace with starter…") { store.showReset = true }
                } label: { Image(systemName: "ellipsis") }.menuStyle(.borderlessButton).fixedSize()
            }.padding(.horizontal, 16).padding(.vertical, 12)
            Divider()
            if store.isCourseExercise {
                CourseFilesView(store: store)
            } else { HStack {
                Text("Execution").font(.caption).foregroundStyle(FreeCodeTheme.secondary)
                Spacer()
                if store.language == .sql {
                    Text("SQLite · in-memory database").font(.caption).foregroundStyle(.secondary)
                } else {
                    Picker("Execution mode", selection: Binding(get: { store.workspace.mode }, set: { store.workspace.mode = $0; store.edited() })) {
                        Text("Function tests").tag("function")
                        Text("Full program").tag("program")
                    }.labelsHidden().fixedSize().controlSize(.small).disabled(store.running)
                }
            }.padding(.horizontal, 16).padding(.vertical, 6).background(FreeCodeTheme.editor) }
            CodeEditor(text: Binding(get: { store.workspace.code }, set: { store.workspace.code = $0; store.edited() }), identity: (store.key ?? "") + (store.workspace.selectedFile ?? ""), commentPrefix: store.language.commentPrefix)
            Divider()
            HStack {
                Image(systemName: "internaldrive").font(.caption2)
                Text(store.saveMessage)
                Spacer()
                Text("\(store.workspace.code.components(separatedBy: "\n").count) lines").monospacedDigit()
                Text("UTF-8")
            }.font(.caption2).foregroundStyle(.secondary).padding(.horizontal, 16).padding(.vertical, 7)
        }.frame(minHeight: 250).background(FreeCodeTheme.editor)
    }

    private var console: some View {
        VStack(spacing: 0) {
            HStack {
                let inputTitle = store.isCourseExercise ? "Required checks" : store.language == .sql ? "Schema & data" : store.workspace.mode == "function" ? "Test cases" : "Standard input"
                WorkspaceTabs(label: "Console content", options: [inputTitle, "Results"], selection: Binding(get: { store.consoleTab == "Input" ? inputTitle : "Results" }, set: { store.consoleTab = $0 == "Results" ? "Results" : "Input" }))
                Spacer()
                Button { consoleExpanded = false } label: { Image(systemName: "chevron.down") }
                    .buttonStyle(.plain).help("Minimize tests and results").accessibilityLabel("Minimize tests and results")
            }.padding(.horizontal, 16)
            Divider()
            if store.consoleTab == "Input" {
                if store.isCourseExercise {
                    VStack(alignment: .leading, spacing: 10) {
                        Text("Required checks").font(.headline)
                        Text("Each step runs its bundled pytest checks against your shared workspace. Checks are read-only. Create test_learner.py to add your own tests, then choose Run my tests.")
                        Text("Demonstrations, lint, benchmarks and written reflections do not complete a step.").foregroundStyle(.secondary)
                    }.font(.callout).padding(18)
                } else if store.workspace.mode == "function" {
                    TestCasesView(store: store)
                } else {
                    VStack(alignment: .leading, spacing: 0) {
                        if store.language == .sql {
                            Text("SQLite dialect. Review the example schema and seed data before running. MySQL-specific syntax may need adaptation.")
                                .font(.caption).foregroundStyle(.secondary).padding(12)
                        }
                        CodeEditor(text: Binding(get: { store.workspace.stdin }, set: { store.workspace.stdin = $0; store.edited() }), fontSize: 12, identity: "stdin-\(store.key ?? "")", commentPrefix: store.language == .sql ? "--" : nil)
                    }
                }
            } else {
                results
            }
        }.frame(minHeight: 210, idealHeight: 300)
    }

    @ViewBuilder private var results: some View {
        if store.running {
            VStack(spacing: 12) {
                ProgressView()
                Text("Running on your Mac…").font(.callout)
                Text("Compiling if needed. Each run has a time limit.").font(.caption).foregroundStyle(.secondary)
            }.frame(maxWidth: .infinity, maxHeight: .infinity)
        } else if let result = store.result {
            ScrollView {
                VStack(alignment: .leading, spacing: 14) {
                    HStack {
                        Label(result.message, systemImage: result.success ? "checkmark.circle.fill" : "exclamationmark.circle.fill")
                            .font(.headline).foregroundStyle(result.success ? Color.green : Color.orange)
                        Spacer()
                        if let duration = result.duration { Text(String(format: "%.2f s", duration)).font(.caption.monospacedDigit()).foregroundStyle(.secondary) }
                    }
                    ForEach(result.cases ?? []) { c in
                        VStack(alignment: .leading, spacing: 6) {
                            Label(store.isCourseExercise ? "\(c.passed ? "Passed" : "Failed") · \(c.input)" : "Case \(c.index) · \(c.passed ? "Passed" : "Different output")", systemImage: c.passed ? "checkmark" : "xmark")
                                .font(.callout.weight(.medium))
                            Text("Arguments: \(c.input)").foregroundStyle(.secondary)
                            if !c.passed { Text("Expected: \(c.expected)") }
                            Text("Returned: \(c.actual)")
                        }.font(.system(size: 12, design: .monospaced)).textSelection(.enabled)
                        Divider()
                    }
                    if !result.output.isEmpty {
                        Text(result.output).font(.system(size: 12, design: .monospaced)).textSelection(.enabled)
                    }
                    Text(store.isSystemDesign ? "These checks assess the component code. Diagrams, experiments, and written tradeoffs are a separate, ungraded design review." : store.section == .learning ? "These checks assess this lesson’s executable contract. Your written reasoning is ungraded." : "Results cover the local cases you supplied. They do not certify acceptance by LeetCode's private judge.")
                        .font(.caption).foregroundStyle(.secondary)
                }.padding(18).frame(maxWidth: .infinity, alignment: .leading)
            }
        } else {
            VStack(alignment: .leading, spacing: 12) {
                Label("Ready when you are", systemImage: "play.circle").font(.headline)
                Text(store.isCourseExercise ? "Implement this step in its module or project files, then run the required checks. Open Explore & check for demonstrations and your own tests." : store.language == .sql ? "Write your query, review the example tables under Schema & data, then run it against a fresh local SQLite database." : store.workspace.mode == "function" ? "Implement the function, review the example cases, then run them locally." : "Write a complete program, add standard input, and run it locally.")
                    .font(.callout).foregroundStyle(.secondary)
                HStack(spacing: 12) {
                    Button(store.isCourseExercise ? "About required checks" : store.language == .sql ? "Review schema & data" : store.workspace.mode == "function" ? "Review test cases" : "Edit standard input") { store.consoleTab = "Input" }
                    Text("⌘ Return to run").font(.caption).foregroundStyle(.secondary)
                }
            }.padding(24).frame(maxWidth: .infinity, maxHeight: .infinity, alignment: .leading)
        }
    }
}

private struct ProblemRow: View {
    let problem: ProblemSummary
    let progress: ProgressRecord?
    let number: Int?
    var body: some View {
        HStack(alignment: .top, spacing: 9) {
            Image(systemName: progress?.status == "Solved" ? "checkmark.circle.fill" : progress?.status == "In progress" ? "circle.lefthalf.filled" : "circle")
                .font(.system(size: 12)).foregroundStyle(progress?.status == "Solved" ? FreeCodeTheme.accent : FreeCodeTheme.secondary)
                .frame(width: 13).padding(.top, 3)
            VStack(alignment: .leading, spacing: 5) {
                Text(number.map { "\($0). \(problem.title)" } ?? problem.title).font(.system(size: 13, weight: .medium)).lineLimit(2).foregroundStyle(FreeCodeTheme.text)
                HStack(spacing: 7) {
                    Text(problem.difficulty).foregroundStyle(difficultyColor(problem.difficulty))
                    if problem.premium { Image(systemName: "lock.open").accessibilityLabel("Premium question") }
                    if progress?.favorite == true { Image(systemName: "star.fill").foregroundStyle(.orange).accessibilityLabel("Favorite") }
                }.font(.system(size: 11)).foregroundStyle(FreeCodeTheme.secondary)
            }
            Spacer(minLength: 0)
        }.padding(.vertical, 6).accessibilityElement(children: .combine)
    }
}

@MainActor func difficultyColor(_ value: String) -> Color {
    switch value { case "Easy": FreeCodeTheme.easy; case "Medium": FreeCodeTheme.medium; case "Hard": FreeCodeTheme.hard; default: FreeCodeTheme.secondary }
}

struct CoverageView: View {
    let store: Store
    var dismissible = true
    @Environment(\.dismiss) private var dismiss
    private var coverage: [String: Any] {
        guard let data = try? Data(contentsOf: store.libraryURL.appendingPathComponent("coverage.json")),
              let value = try? JSONSerialization.jsonObject(with: data) as? [String: Any] else { return [:] }
        return value
    }
    var body: some View {
        VStack(alignment: .leading, spacing: 18) {
            HStack {
                Label("Your offline library", systemImage: "internaldrive").font(.title2.weight(.semibold))
                Spacer()
                if dismissible { Button("Done") { dismiss() }.keyboardShortcut(.defaultAction) }
            }
            Grid(alignment: .leading, horizontalSpacing: 24, verticalSpacing: 12) {
                GridRow { Text("Learning courses").foregroundStyle(.secondary); Text("\(store.learningCourses.count)").monospacedDigit() }
                GridRow { Text("Learning steps").foregroundStyle(.secondary); Text("\(store.learningCatalog.count)").monospacedDigit() }
                if !store.catalog.isEmpty {
                GridRow { Text("Questions").foregroundStyle(.secondary); Text("\(store.catalog.count)").monospacedDigit() }
                GridRow { Text("Premium included").foregroundStyle(.secondary); Text("\(store.catalog.filter(\.premium).count)").monospacedDigit() }
                GridRow { Text("SQL questions").foregroundStyle(.secondary); Text("\(store.catalog.filter { $0.tags.contains("Database") }.count)").monospacedDigit() }
                GridRow { Text("Official study plans").foregroundStyle(.secondary); Text("\(store.studyPlans.count)").monospacedDigit() }
                GridRow { Text("Complete membership snapshots").foregroundStyle(.secondary); Text("\(coverage["completeStudyPlans"] as? Int ?? 0) of \(store.studyPlans.count)").monospacedDigit() }
                GridRow { Text("Source index gaps").foregroundStyle(.secondary); Text("\((coverage["missingFromSourceIndex"] as? [Int] ?? []).count)").monospacedDigit() }
                GridRow { Text("Unavailable diagrams").foregroundStyle(.secondary); Text("\((coverage["unavailableImages"] as? [Any] ?? []).count) referenced image URLs").monospacedDigit() }
                GridRow { Text("Source revision").foregroundStyle(.secondary); Text(String((coverage["sourceCommit"] as? String ?? "Unknown").prefix(12))).font(.system(.body, design: .monospaced)) }
                GridRow { Text("Downloaded").foregroundStyle(.secondary); Text(String((coverage["importedAt"] as? String ?? "Unknown").prefix(10))) }
                }
            }
            Divider()
            if store.catalog.isEmpty {
                Text("Original courses and all required Python packages are bundled for offline study. App and course code: MIT. Lesson prose and diagrams: CC BY 4.0, attributed to Nir Tuttnauer.")
                Text("Required checks verify the named local scenarios. Demonstrations, benchmark timings, written reflections and deployment are ungraded.").foregroundStyle(.secondary)
            } else {
            Text("All \(store.catalog.count) question IDs match LeetCode’s official main problem catalog at the recorded check time, including \(store.catalog.filter(\.premium).count) premium questions. No missing or extra IDs were found.")
            Text("All statement diagrams are bundled locally. LeetCode’s private test suite and online judge are not included.")
                .foregroundStyle(.secondary)
            Text("All 18 study-plan membership lists are saved with sections and question order, including Apple, TikTok, premium topic sections, and JavaScript bonus challenges. Public archive entries were checked against official counts and public memberships. Source details are in the coverage report.")
                .font(.callout).foregroundStyle(.secondary)
            }
            HStack {
                Button("Reveal saved work") { NSWorkspace.shared.selectFile(nil, inFileViewerRootedAtPath: store.workURL.path) }
                Button("Reveal coverage report") { NSWorkspace.shared.activateFileViewerSelecting([store.libraryURL.appendingPathComponent("coverage.json")]) }
            }
            Text(store.catalog.isEmpty ? "PracticeCode · Python Engineer · Original learning content" : "Problem statements belong to LeetCode. Community archive and references: Doocs, CC BY-SA 4.0. This app is independent of LeetCode.")
                .font(.caption).foregroundStyle(.secondary)
        }.padding(28).frame(width: 600).textSelection(.enabled)
    }
}

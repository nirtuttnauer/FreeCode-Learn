import AppKit
import SwiftUI

@main
struct OfflinePracticeApp: App {
    @NSApplicationDelegateAdaptor(AppDelegate.self) private var delegate
    private let store = Store()
    @AppStorage("appearanceMode") private var appearanceMode = "system"
    @AppStorage("workspaceLayout") private var layout = "split"
    private var preferredAppearance: ColorScheme? { appearanceMode == "dark" ? .dark : appearanceMode == "light" ? .light : nil }
    var body: some Scene {
        WindowGroup("FreeCode") {
            ContentView(store: store)
                .preferredColorScheme(preferredAppearance)
                .onAppear { delegate.store = store; NSApp.setActivationPolicy(.regular); NSApp.activate(ignoringOtherApps: true) }
        }
        .defaultSize(width: 1480, height: 940)
        .windowStyle(.hiddenTitleBar)
        .commands {
            CommandMenu("Learning") {
                Button("Previous lesson") { store.moveLesson(-1) }.keyboardShortcut(.leftArrow, modifiers: [.command, .option]).disabled(!store.canMoveLesson(-1))
                Button("Next lesson") { store.moveLesson(1) }.keyboardShortcut(.rightArrow, modifiers: [.command, .option]).disabled(!store.canMoveLesson(1))
            }
            CommandGroup(after: .sidebar) {
                Menu("Focus panels") {
                    Button("Show both panels") { layout = "split" }
                    Button("Focus question") { layout = "question" }
                    Button("Focus code") { layout = "code" }
                }

            }
            CommandGroup(after: .textEditing) {
                Button("Toggle Line Comment") {
                    NSApp.sendAction(#selector(CommentingTextView.toggleLineComment(_:)), to: nil, from: nil)
                }.keyboardShortcut("/", modifiers: .command)
            }
            CommandGroup(replacing: .saveItem) {
                Button("Save") { store.saveNow() }.keyboardShortcut("s", modifiers: .command)
                Button("Export code…", action: store.exportCode).keyboardShortcut("s", modifiers: [.command, .shift])
                Divider()
                Button(store.language == .sql ? "Run query" : "Run code", action: store.run)
                    .keyboardShortcut(.return, modifiers: .command)
                    .disabled(store.running || store.problem == nil || store.testCaseError != nil)
            }
        }
        Settings {
            SettingsView(store: store).preferredColorScheme(preferredAppearance)
        }
        Window("Statistics", id: "statistics") {
            StatisticsView(store: store)
                .preferredColorScheme(preferredAppearance)
        }.defaultSize(width: 820, height: 720)
    }
}

@MainActor final class AppDelegate: NSObject, NSApplicationDelegate {
    weak var store: Store?
    func applicationShouldTerminate(_ sender: NSApplication) -> NSApplication.TerminateReply {
        guard store?.saveNow() != false else { return .terminateCancel }
        store?.stop()
        return .terminateNow
    }
    func applicationShouldTerminateAfterLastWindowClosed(_ sender: NSApplication) -> Bool { true }
}

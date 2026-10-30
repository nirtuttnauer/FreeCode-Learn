import SwiftUI

struct SettingsView: View {
    let store: Store
    @AppStorage("appearanceMode") private var appearanceMode = "system"
    var body: some View {
        ScrollView {
            VStack(alignment: .leading, spacing: 0) {
                VStack(alignment: .leading, spacing: 12) {
                    Text("Appearance").font(.headline)
                    Picker("Appearance", selection: $appearanceMode) {
                        Text("System").tag("system")
                        Text("Light").tag("light")
                        Text("Dark").tag("dark")
                    }.pickerStyle(.segmented).labelsHidden()
                    Text("System follows your macOS appearance.")
                        .font(.caption).foregroundStyle(FreeCodeTheme.secondary)
                }.padding(28)
                Divider()
                CoverageView(store: store, dismissible: false)
            }
        }
        .frame(width: 640, height: 720)
        .background(FreeCodeTheme.surface).foregroundStyle(FreeCodeTheme.text).tint(FreeCodeTheme.accent)
    }
}

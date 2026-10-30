import AppKit
import SwiftUI

@MainActor enum FreeCodeTheme {
    private static func color(_ light: UInt32, _ dark: UInt32) -> NSColor {
        func rgb(_ hex: UInt32) -> NSColor {
            NSColor(srgbRed: Double((hex >> 16) & 255) / 255, green: Double((hex >> 8) & 255) / 255, blue: Double(hex & 255) / 255, alpha: 1)
        }
        let day = rgb(light), night = rgb(dark)
        return NSColor(name: nil) { $0.bestMatch(from: [.darkAqua, .aqua]) == .darkAqua ? night : day }
    }
    static let workspaceColor = color(0xEDF1F5, 0x0A121C)
    static let sidebarColor = color(0xF1F5F8, 0x0C1722)
    static let surfaceColor = color(0xFFFFFF, 0x17232F)
    static let editorColor = color(0xFCFDFE, 0x0D151F)
    static let textColor = color(0x172B3A, 0xECF2F7)
    static let secondaryColor = color(0x526575, 0xA6B7C7)
    static let accentColor = color(0x11654F, 0x85F1D0)
    static let borderColor = color(0xCFD9E2, 0x2B3D4C)
    static let selectionColor = color(0xDDEFEA, 0x153B3D)
    static let keywordColor = color(0x743C97, 0xE7A9F5)
    static let stringColor = color(0x206C51, 0x9BDABF)
    static let numberColor = color(0x8A4E16, 0xEBC784)
    static let easy = Color(nsColor: color(0x166643, 0x79DCAC))
    static let medium = Color(nsColor: color(0x87510E, 0xF4CA7B))
    static let hard = Color(nsColor: color(0xA82F46, 0xF49AAC))
    static let actionText = Color(nsColor: color(0xFFFFFF, 0x0B201D))
    static let workspace = Color(nsColor: workspaceColor)
    static let sidebar = Color(nsColor: sidebarColor)
    static let surface = Color(nsColor: surfaceColor)
    static let editor = Color(nsColor: editorColor)
    static let text = Color(nsColor: textColor)
    static let secondary = Color(nsColor: secondaryColor)
    static let accent = Color(nsColor: accentColor)
    static let border = Color(nsColor: borderColor)
    static let selection = Color(nsColor: selectionColor)
    static let radius: CGFloat = 8
}

struct WorkspaceTabs: View {
    let label: String
    let options: [String]
    @Binding var selection: String
    var body: some View {
        HStack(spacing: 20) {
            ForEach(options, id: \.self) { option in
                Button { selection = option } label: {
                    VStack(spacing: 10) {
                        Text(option).font(.system(size: 13, weight: selection == option ? .semibold : .regular))
                            .foregroundStyle(selection == option ? FreeCodeTheme.text : FreeCodeTheme.secondary)
                        Capsule().fill(selection == option ? FreeCodeTheme.accent : .clear).frame(height: 2)
                    }.padding(.top, 13).contentShape(Rectangle())
                }
                .buttonStyle(.plain).fixedSize(horizontal: true, vertical: false)
                .accessibilityLabel(option)
                .accessibilityAddTraits(selection == option ? .isSelected : [])
                .onMoveCommand { direction in
                    guard let index = options.firstIndex(of: selection) else { return }
                    let next = direction == .left ? index - 1 : direction == .right ? index + 1 : index
                    if options.indices.contains(next) { selection = options[next] }
                }
            }
        }.accessibilityElement(children: .contain).accessibilityLabel(label)
    }
}

struct PaneSurface: ViewModifier {
    func body(content: Content) -> some View {
        content.background(FreeCodeTheme.surface)
            .clipShape(RoundedRectangle(cornerRadius: FreeCodeTheme.radius))
            .overlay { RoundedRectangle(cornerRadius: FreeCodeTheme.radius).strokeBorder(FreeCodeTheme.border, lineWidth: 1) }
    }
}

struct RunCodeStyle: ButtonStyle {
    @Environment(\.colorScheme) private var colorScheme
    @Environment(\.isEnabled) private var enabled
    func makeBody(configuration: Configuration) -> some View {
        configuration.label.font(.system(size: 13, weight: .semibold))
            .padding(.horizontal, 14).padding(.vertical, 8)
            .foregroundStyle(colorScheme == .dark ? FreeCodeTheme.accent : FreeCodeTheme.actionText)
            .background((colorScheme == .dark ? FreeCodeTheme.selection : FreeCodeTheme.accent).opacity(configuration.isPressed ? 0.9 : 1), in: RoundedRectangle(cornerRadius: 6))
            .opacity(enabled ? 1 : 0.45)
    }
}

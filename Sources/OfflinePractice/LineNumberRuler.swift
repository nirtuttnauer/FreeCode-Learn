import AppKit

@MainActor final class LineNumberRuler: NSRulerView {
    weak var textView: NSTextView?
    override var isFlipped: Bool { true }

    init(textView: NSTextView, scrollView: NSScrollView) {
        self.textView = textView
        super.init(scrollView: scrollView, orientation: .verticalRuler)
        clientView = textView
        ruleThickness = 42
        scrollView.contentView.postsBoundsChangedNotifications = true
        NotificationCenter.default.addObserver(self, selector: #selector(refresh(_:)), name: NSView.boundsDidChangeNotification, object: scrollView.contentView)
        setAccessibilityElement(false)
    }
    required init(coder: NSCoder) { fatalError("Not used") }
    deinit { NotificationCenter.default.removeObserver(self) }
    @objc private func refresh(_ note: Notification) { needsDisplay = true }
    override func viewDidChangeEffectiveAppearance() { super.viewDidChangeEffectiveAppearance(); needsDisplay = true }

    override func drawHashMarksAndLabels(in rect: NSRect) {
        FreeCodeTheme.editorColor.setFill()
        NSBezierPath(rect: bounds).fill()
        guard let textView, let layout = textView.layoutManager else { return }
        let text = textView.string as NSString
        let attributes: [NSAttributedString.Key: Any] = [.font: NSFont.monospacedDigitSystemFont(ofSize: 11, weight: .regular), .foregroundColor: FreeCodeTheme.secondaryColor]
        var offset = 0, number = 1
        while offset < text.length {
            let glyph = layout.glyphIndexForCharacter(at: offset)
            let line = layout.lineFragmentRect(forGlyphAt: glyph, effectiveRange: nil)
            let y = convert(NSPoint(x: 0, y: line.minY + textView.textContainerInset.height), from: textView).y
            if y > bounds.maxY { break }
            if y + line.height >= bounds.minY {
                let label = String(number) as NSString
                let width = label.size(withAttributes: attributes).width
                label.draw(at: NSPoint(x: ruleThickness - width - 10, y: y), withAttributes: attributes)
            }
            offset = NSMaxRange(text.lineRange(for: NSRange(location: offset, length: 0)))
            number += 1
        }
        if text.length == 0 || textView.string.hasSuffix("\n") {
            let y = convert(NSPoint(x: 0, y: layout.extraLineFragmentRect.minY + textView.textContainerInset.height), from: textView).y
            let label = String(number) as NSString
            label.draw(at: NSPoint(x: ruleThickness - label.size(withAttributes: attributes).width - 10, y: y), withAttributes: attributes)
        }
    }
}

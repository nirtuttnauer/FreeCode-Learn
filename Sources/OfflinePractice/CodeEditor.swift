import AppKit
import SwiftUI

struct CodeEditor: NSViewRepresentable {
    @Binding var text: String
    var editable = true
    var fontSize: CGFloat = 13
    var identity = ""
    var commentPrefix: String? = nil

    func makeCoordinator() -> Coordinator { Coordinator(self) }
    func makeNSView(context: Context) -> NSScrollView {
        let scroll = NSScrollView()
        let editor = CommentingTextView()
        editor.commentPrefix = commentPrefix
        editor.isRichText = false
        editor.isAutomaticQuoteSubstitutionEnabled = false
        editor.isAutomaticDashSubstitutionEnabled = false
        editor.isAutomaticTextReplacementEnabled = false
        editor.isAutomaticSpellingCorrectionEnabled = false
        editor.isContinuousSpellCheckingEnabled = false
        editor.isGrammarCheckingEnabled = false
        editor.isEditable = editable
        editor.allowsUndo = true
        editor.font = .monospacedSystemFont(ofSize: fontSize, weight: .regular)
        editor.backgroundColor = FreeCodeTheme.editorColor
        editor.textColor = FreeCodeTheme.textColor
        editor.insertionPointColor = FreeCodeTheme.accentColor
        editor.setAccessibilityElement(true)
        editor.setAccessibilityLabel(editable ? "Code editor" : "Reference code")
        editor.textContainerInset = NSSize(width: 16, height: 18)
        let paragraph = NSMutableParagraphStyle()
        paragraph.lineSpacing = 5
        paragraph.tabStops = []
        paragraph.defaultTabInterval = ("    " as NSString).size(withAttributes: [.font: editor.font!]).width
        editor.defaultParagraphStyle = paragraph
        editor.isHorizontallyResizable = true
        editor.isVerticallyResizable = true
        editor.autoresizingMask = [.width]
        editor.textContainer?.containerSize = NSSize(width: CGFloat.greatestFiniteMagnitude, height: CGFloat.greatestFiniteMagnitude)
        editor.textContainer?.widthTracksTextView = false
        editor.delegate = context.coordinator
        context.coordinator.editor = editor
        scroll.hasVerticalScroller = true
        scroll.hasHorizontalScroller = true
        scroll.autohidesScrollers = true
        scroll.drawsBackground = true
        scroll.backgroundColor = FreeCodeTheme.editorColor
        scroll.documentView = editor
        let ruler = LineNumberRuler(textView: editor, scrollView: scroll)
        scroll.hasVerticalRuler = true
        scroll.verticalRulerView = ruler
        scroll.rulersVisible = true
        context.coordinator.ruler = ruler
        return scroll
    }
    func updateNSView(_ scroll: NSScrollView, context: Context) {
        guard let editor = scroll.documentView as? NSTextView else { return }
        context.coordinator.parent = self
        (editor as? CommentingTextView)?.commentPrefix = commentPrefix
        editor.isEditable = editable
        if context.coordinator.identity != identity {
            context.coordinator.identity = identity
            editor.string = text
            editor.undoManager?.removeAllActions()
            editor.setSelectedRange(NSRange(location: 0, length: 0))
            editor.scrollToBeginningOfDocument(nil)
            scroll.contentView.scroll(to: .zero)
            scroll.reflectScrolledClipView(scroll.contentView)
            context.coordinator.highlight(editor)
        } else if editor.string != text {
            editor.string = text
            context.coordinator.highlight(editor)
        }
    }
    @MainActor final class Coordinator: NSObject, NSTextViewDelegate {
        var parent: CodeEditor
        var identity = ""
        weak var editor: NSTextView?
        weak var ruler: NSRulerView?
        private let editorUndo = UndoManager()
        init(_ parent: CodeEditor) {
            self.parent = parent
            super.init()
            for name in [NSNotification.Name.NSUndoManagerDidUndoChange, NSNotification.Name.NSUndoManagerDidRedoChange] {
                NotificationCenter.default.addObserver(self, selector: #selector(synchronizeUndo), name: name, object: editorUndo)
            }
        }
        deinit { NotificationCenter.default.removeObserver(self) }
        func undoManager(for view: NSTextView) -> UndoManager? { editorUndo }
        @objc private func synchronizeUndo() {
            guard let editor, parent.editable else { return }
            parent.text = editor.string
            highlight(editor)
            ruler?.needsDisplay = true
        }
        func textDidChange(_ notification: Notification) {
            guard let editor = notification.object as? NSTextView else { return }
            parent.text = editor.string
            highlight(editor)
            ruler?.needsDisplay = true
        }
        func textView(_ textView: NSTextView, doCommandBy commandSelector: Selector) -> Bool {
            if commandSelector == #selector(NSResponder.insertTab(_:)) {
                textView.insertText("    ", replacementRange: textView.selectedRange())
                return true
            }
            if commandSelector == #selector(NSResponder.insertNewline(_:)) {
                let ns = textView.string as NSString
                let line = ns.lineRange(for: NSRange(location: textView.selectedRange().location, length: 0))
                let prefix = ns.substring(with: NSRange(location: line.location, length: textView.selectedRange().location - line.location))
                let indent = String(prefix.prefix(while: { $0 == " " || $0 == "\t" }))
                let extra = prefix.trimmingCharacters(in: .whitespaces).hasSuffix(":") || prefix.trimmingCharacters(in: .whitespaces).hasSuffix("{") ? "    " : ""
                textView.insertText("\n" + indent + extra, replacementRange: textView.selectedRange())
                return true
            }
            return false
        }
        func highlight(_ view: NSTextView) {
            guard let storage = view.textStorage, storage.length < 200_000 else { return }
            let range = NSRange(location: 0, length: storage.length)
            storage.beginEditing()
            storage.addAttribute(.foregroundColor, value: FreeCodeTheme.textColor, range: range)
            let patterns: [(String, NSColor)] = [
                (#"\b(class|def|return|if|else|elif|for|while|in|import|from|as|try|except|raise|pass|break|continue|True|False|None|var|let|const|function|new|throw|public|private|static|void|int|long|double|boolean|bool|using|namespace|include|auto|struct|switch|case|true|false|null|this|self)\b"#, FreeCodeTheme.keywordColor),
                (#"\b\d+(\.\d+)?\b"#, FreeCodeTheme.numberColor),
                (#"(?i)\b(SELECT|FROM|WHERE|JOIN|LEFT|RIGHT|INNER|OUTER|ON|AS|AND|OR|NOT|NULL|GROUP|BY|ORDER|HAVING|LIMIT|WITH|CASE|WHEN|THEN|ELSE|END|COUNT|SUM|AVG|MIN|MAX|DISTINCT|CREATE|TABLE|INSERT|INTO|VALUES)\b"#, FreeCodeTheme.keywordColor),
                (#"\"([^\"\\]|\\.)*\"|'([^'\\]|\\.)*'"#, FreeCodeTheme.stringColor),
                (#"(?m)(//[^\n]*|#[^\n]*|--[^\n]*)"#, FreeCodeTheme.secondaryColor)
            ]
            for (pattern, color) in patterns {
                guard let regex = try? NSRegularExpression(pattern: pattern) else { continue }
                for match in regex.matches(in: view.string, range: range) {
                    storage.addAttribute(.foregroundColor, value: color, range: match.range)
                }
            }
            storage.endEditing()
        }
    }
}

@MainActor final class CommentingTextView: NSTextView {
    var commentPrefix: String?

    @objc func toggleLineComment(_ sender: Any?) {
        guard isEditable, let commentPrefix,
              let change = LineComments.toggle(string, selection: selectedRange(), prefix: commentPrefix) else { return }
        insertText(change.replacement, replacementRange: change.range)
        setSelectedRange(change.selection)
        undoManager?.setActionName("Toggle Line Comment")
    }
}

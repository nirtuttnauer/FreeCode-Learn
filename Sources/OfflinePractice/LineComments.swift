import Foundation

struct LineCommentChange {
    let range: NSRange
    let replacement: String
    let selection: NSRange
}

enum LineComments {
    static func toggle(_ text: String, selection: NSRange, prefix: String) -> LineCommentChange? {
        let source = text as NSString
        guard selection.location <= source.length, NSMaxRange(selection) <= source.length, !prefix.isEmpty else { return nil }
        let start = source.lineRange(for: NSRange(location: selection.location, length: 0)).location
        let last = selection.length > 0 ? NSMaxRange(selection) - 1 : selection.location
        let end = NSMaxRange(source.lineRange(for: NSRange(location: last, length: 0)))
        let range = NSRange(location: start, length: end - start)
        let content = source.substring(with: range)
        var lines = content.components(separatedBy: "\n")
        if content.hasSuffix("\n") { lines.removeLast() }
        var offset = start
        var candidates: [(location: Int, tail: String)] = []
        for line in lines {
            let indent = String(line.prefix { $0 == " " || $0 == "\t" })
            let tail = String(line.dropFirst(indent.count))
            if !tail.trimmingCharacters(in: .whitespacesAndNewlines).isEmpty || lines.count == 1 {
                candidates.append((offset + (indent as NSString).length, tail))
            }
            offset += (line as NSString).length + 1
        }
        guard !candidates.isEmpty else { return nil }
        let uncomment = candidates.allSatisfy { $0.tail.hasPrefix(prefix) }
        let edits: [(location: Int, removed: Int, inserted: String)] = candidates.map { line in
            let removed = uncomment ? (prefix as NSString).length + (line.tail.dropFirst(prefix.count).hasPrefix(" ") ? 1 : 0) : 0
            return (line.location, removed, uncomment ? "" : prefix + " ")
        }
        let result = NSMutableString(string: content)
        for edit in edits.reversed() {
            result.replaceCharacters(in: NSRange(location: edit.location - start, length: edit.removed), with: edit.inserted)
        }
        func mapped(_ boundary: Int, afterInsertion: Bool) -> Int {
            var delta = 0
            for edit in edits {
                let added = (edit.inserted as NSString).length
                if boundary > edit.location || (boundary == edit.location && afterInsertion) {
                    if boundary < edit.location + edit.removed { return edit.location + delta + added }
                    delta += added - edit.removed
                }
            }
            return boundary + delta
        }
        let selectedStart = mapped(selection.location, afterInsertion: selection.length == 0)
        let selectedEnd = mapped(NSMaxRange(selection), afterInsertion: true)
        return LineCommentChange(range: range, replacement: result as String,
                                 selection: NSRange(location: selectedStart, length: max(0, selectedEnd - selectedStart)))
    }
}

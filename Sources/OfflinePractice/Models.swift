import Foundation

struct ProblemSummary: Codable, Identifiable, Hashable, Sendable {
    let id: Int
    let title: String
    let slug: String
    let difficulty: String
    let premium: Bool
    let tags: [String]
}

enum JSONValue: Codable, Sendable, Equatable {
    case null, bool(Bool), integer(Int64), number(Double), string(String), array([JSONValue]), object([String: JSONValue])
    init(from decoder: any Decoder) throws {
        let c = try decoder.singleValueContainer()
        if c.decodeNil() { self = .null }
        else if let v = try? c.decode(Bool.self) { self = .bool(v) }
        else if let v = try? c.decode(Int64.self) { self = .integer(v) }
        else if let v = try? c.decode(Double.self) { self = .number(v) }
        else if let v = try? c.decode(String.self) { self = .string(v) }
        else if let v = try? c.decode([JSONValue].self) { self = .array(v) }
        else { self = .object(try c.decode([String: JSONValue].self)) }
    }
    func encode(to encoder: any Encoder) throws {
        var c = encoder.singleValueContainer()
        switch self {
        case .null: try c.encodeNil()
        case .bool(let v): try c.encode(v)
        case .integer(let v): try c.encode(v)
        case .number(let v): try c.encode(v)
        case .string(let v): try c.encode(v)
        case .array(let v): try c.encode(v)
        case .object(let v): try c.encode(v)
        }
    }
}

struct Sample: Codable, Sendable {
    let input: String
    let output: String
    let args: [JSONValue]?
    let expected: JSONValue?
}

struct Problem: Codable, Sendable {
    let id: Int
    let title: String
    let slug: String
    let url: String
    let difficulty: String
    let tags: [String]
    let premium: Bool
    let statement: String
    let references: [String: String]
    let starters: [String: String]
    let samples: [Sample]
    let sourceURL: String
    let missingImages: [String]
    let sqlSetup: String?
    var course: CourseExercise? = nil
}

enum Language: String, CaseIterable, Codable, Identifiable {
    case python, javascript, cpp, java, sql
    var id: String { rawValue }
    var commentPrefix: String { self == .python ? "#" : self == .sql ? "--" : "//" }
    var title: String {
        switch self { case .python: "Python"; case .javascript: "JavaScript"; case .cpp: "C++"; case .java: "Java"; case .sql: "SQL (SQLite)" }
    }
    var ext: String {
        switch self { case .python: "py"; case .javascript: "js"; case .cpp: "cpp"; case .java: "java"; case .sql: "sql" }
    }
    var program: String {
        switch self {
        case .sql: "-- Write your SQLite query here.\n"
        case .python: "import sys\n\ndef main():\n    data = sys.stdin.read()\n    # Write your solution here.\n    print(data.strip())\n\nif __name__ == '__main__':\n    main()\n"
        case .javascript: "const fs = require('fs');\nconst input = fs.readFileSync(0, 'utf8');\n\n// Write your solution here.\nconsole.log(input.trim());\n"
        case .cpp: "#include <iostream>\n#include <string>\n#include <vector>\n#include <algorithm>\nusing namespace std;\n\nint main() {\n    // Read stdin and write your answer to stdout.\n    string line;\n    while (getline(cin, line)) cout << line << '\\n';\n    return 0;\n}\n"
        case .java: "import java.util.*;\n\npublic class Main {\n    public static void main(String[] args) {\n        Scanner in = new Scanner(System.in);\n        // Read stdin and write your answer to stdout.\n        while (in.hasNextLine()) System.out.println(in.nextLine());\n    }\n}\n"
        }
    }
}

struct Workspace: Codable {
    var code: String = ""
    var tests: String = "[]"
    var stdin: String = ""
    var mode: String = "function"
    var testCaseDrafts: [TestCaseDraft]?
    var design: DesignWorkspace?
    var files: [String: String]?
    var selectedFile: String?
}

struct TestValueDraft: Codable, Equatable, Identifiable {
    enum Kind: String, Codable, CaseIterable {
        case number = "Number", string = "Text", boolean = "Boolean", array = "Array", object = "Object", null = "Null"
    }
    var id = UUID()
    var kind: Kind
    var text: String

    init(_ value: JSONValue) {
        switch value {
        case .string(let text): kind = .string; self.text = text; return
        case .integer, .number: kind = .number
        case .bool: kind = .boolean
        case .array: kind = .array
        case .object: kind = .object
        case .null: kind = .null
        }
        text = String(decoding: (try? JSONEncoder().encode(value)) ?? Data(), as: UTF8.self)
    }

    func value() throws -> JSONValue {
        if kind == .string { return .string(text) }
        if kind == .null { return .null }
        let decoded = try JSONDecoder().decode(JSONValue.self, from: Data(text.utf8))
        switch (kind, decoded) {
        case (.number, .integer), (.number, .number), (.boolean, .bool), (.array, .array), (.object, .object): return decoded
        default: throw TestCaseError.invalidValue(kind.rawValue)
        }
    }
}

enum TestCaseError: LocalizedError {
    case invalidValue(String), invalidCase, caseCount
    var errorDescription: String? {
        switch self {
        case .invalidValue(let kind): "Enter a valid \(kind.lowercased()) value."
        case .invalidCase: "Saved test cases need inputs and an expected output."
        case .caseCount: "Add between 1 and 50 test cases."
        }
    }
}

struct TestCaseDraft: Codable, Equatable, Identifiable {
    var id = UUID()
    var arguments: [TestValueDraft]
    var expected: TestValueDraft
    var unordered = false
    var extraFields: [String: JSONValue] = [:]

    static func decode(_ text: String) throws -> [Self] {
        let values = try JSONDecoder().decode([[String: JSONValue]].self, from: Data(text.utf8))
        return try values.map { fields in
            guard case .array(let arguments) = fields["args"], let expected = fields["expected"] else { throw TestCaseError.invalidCase }
            var extra = fields
            ["args", "expected", "unordered"].forEach { extra.removeValue(forKey: $0) }
            return Self(arguments: arguments.map(TestValueDraft.init), expected: TestValueDraft(expected),
                        unordered: fields["unordered"] == .bool(true), extraFields: extra)
        }
    }

    static func encode(_ cases: [Self]) throws -> String {
        let values: [[String: JSONValue]] = try cases.map { test in
            var fields = test.extraFields
            fields["args"] = .array(try test.arguments.map { try $0.value() })
            fields["expected"] = try test.expected.value()
            if test.unordered { fields["unordered"] = .bool(true) }
            return fields
        }
        let encoder = JSONEncoder()
        encoder.outputFormatting = [.prettyPrinted, .sortedKeys]
        return String(decoding: try encoder.encode(values), as: UTF8.self)
    }
}

struct ProgressRecord: Codable {
    var status: String = "Unstarted"
    var favorite: Bool = false
    var notes: String = ""
    var courseVersion: String?
}

struct RunResult: Codable {
    let success: Bool
    let message: String
    let output: String
    let cases: [CaseResult]?
    let duration: Double?
    var course: CourseCheckReport? = nil
}

struct CaseResult: Codable, Identifiable {
    let index: Int
    let passed: Bool
    let actual: String
    let expected: String
    let input: String
    var id: Int { index }
}

struct Activity: Codable, Identifiable {
    var id = UUID()
    let problemID: Int
    let language: String
    let mode: String
    let success: Bool
    let passed: Int
    let total: Int
    let duration: Double?
    var date = Date()
    var stopped = false
}

struct StudyPlan: Codable, Identifiable {
    let id: String
    let name: String
    let sourceURL: String
    let groups: [StudyGroup]
    let membershipNote: String?
    var questionIDs: [Int] { groups.flatMap(\.questionIDs) }
}

struct StudyGroup: Codable, Identifiable {
    let name: String
    let questionIDs: [Int]
    var id: String { "\(name):\(questionIDs.first ?? 0)" }
}

enum PracticeSection: String, CaseIterable, Identifiable {
    case problems = "Problems", learning = "Learning"
    var id: String { rawValue }
}

struct CustomList: Codable, Identifiable, Equatable {
    var id = "custom-" + UUID().uuidString
    var name: String
    var questionIDs: [Int] = []
}

struct LearningCourse: Codable, Identifiable {
    let id: String
    let name: String
    let summary: String
    let groups: [StudyGroup]
    var questionIDs: [Int] { groups.flatMap(\.questionIDs) }
}

struct CourseExercise: Codable, Sendable {
    let workspaceID: String
    let entrypoint: String
    let checkGroup: String
    let version: String
    var courseID: String? = nil
}

struct CourseCheckReport: Codable, Sendable {
    let workspaceID: String
    let checkGroup: String
    let version: String
    let fingerprint: String
    let graded: Bool
    let action: String
}

struct CourseManifest: Decodable {
    let steps: [String: CourseExercise]
}

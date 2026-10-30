import Foundation

struct DifficultyProgress: Identifiable {
    let name: String
    let total: Int
    let solved: Int
    var remaining: Int { total - solved }
    var id: String { name }
}

struct CompletedTasks: Identifiable {
    let name: String
    let count: Int
    var id: String { name }
}

struct PracticeDay: Identifiable {
    let date: Date
    let runs: Int
    let inRange: Bool
    var id: Date { date }
    var intensity: Int {
        switch runs { case 0: 0; case 1: 1; case 2...3: 2; case 4...7: 3; default: 4 }
    }
}

struct PracticeStatistics {
    let difficulties: [DifficultyProgress]
    let taskTypes: [CompletedTasks]
    let weeks: [[PracticeDay]]
    let recentRuns: Int
    let activeDays: Int
    let streak: Int

    init(catalog: [ProblemSummary], progress: [String: ProgressRecord], activity: [Activity],
         now: Date = Date(), calendar: Calendar = .current) {
        let solved = catalog.filter { progress[String($0.id)]?.status == "Solved" }
        difficulties = ["Easy", "Medium", "Hard"].map { name in
            DifficultyProgress(name: name, total: catalog.filter { $0.difficulty == name }.count,
                               solved: solved.filter { $0.difficulty == name }.count)
        }
        let kinds = Dictionary(grouping: solved) { problem in
            if problem.tags.contains("LLM engineering") { return "LLM engineering" }
            if problem.tags.contains("System design") { return "System design" }
            if problem.tags.contains("Database") { return "SQL" }
            if problem.tags.contains("Pandas") { return "Pandas" }
            if problem.tags.contains("JavaScript") { return "JavaScript" }
            return "Algorithms"
        }
        let learning = catalog.contains { $0.id < 0 }
        taskTypes = (learning ? ["LLM engineering", "System design"] : ["Algorithms", "SQL", "Pandas", "JavaScript"]).map { CompletedTasks(name: $0, count: kinds[$0]?.count ?? 0) }

        let today = calendar.startOfDay(for: now)
        let yearAgo = calendar.date(byAdding: .year, value: -1, to: today)!
        let firstDay = calendar.date(byAdding: .day, value: 1, to: yearAgo)!
        // Sunday-first columns match the contribution-calendar convention.
        let firstSunday = calendar.date(byAdding: .day, value: 1 - calendar.component(.weekday, from: firstDay), to: firstDay)!
        let lastSaturday = calendar.date(byAdding: .day, value: 7 - calendar.component(.weekday, from: today), to: today)!
        let recorded = activity.filter { $0.date <= now }
        let runsByDay = Dictionary(grouping: recorded) { calendar.startOfDay(for: $0.date) }.mapValues(\.count)
        let numberOfDays = calendar.dateComponents([.day], from: firstSunday, to: lastSaturday).day! + 1
        let days = (0..<numberOfDays).map { offset in
            let date = calendar.date(byAdding: .day, value: offset, to: firstSunday)!
            let inRange = date >= firstDay && date <= today
            return PracticeDay(date: date, runs: inRange ? runsByDay[date] ?? 0 : 0, inRange: inRange)
        }
        weeks = stride(from: 0, to: days.count, by: 7).map { Array(days[$0..<min($0 + 7, days.count)]) }
        recentRuns = days.reduce(0) { $0 + $1.runs }
        activeDays = days.filter { $0.runs > 0 }.count
        var cursor = today
        if runsByDay[cursor] == nil { cursor = calendar.date(byAdding: .day, value: -1, to: cursor)! }
        var count = 0
        while runsByDay[cursor] != nil {
            count += 1
            cursor = calendar.date(byAdding: .day, value: -1, to: cursor)!
        }
        streak = count
    }
}

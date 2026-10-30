import AppKit
import Charts
import SwiftUI

struct StatisticsView: View {
    @Bindable var store: Store

    @AppStorage("statisticsBreakdown") private var breakdown = "difficulty"

    private var statistics: PracticeStatistics {
        PracticeStatistics(catalog: store.currentCatalog, progress: store.progress, activity: store.currentActivity)
    }
    private var attempted: Int {
        store.currentCatalog.filter { (store.progress[String($0.id)]?.status ?? "Unstarted") != "Unstarted" }.count
    }

    var body: some View {
        let stats = statistics
        ScrollView {
            VStack(alignment: .leading, spacing: 26) {
                VStack(alignment: .leading, spacing: 7) {
                    Text(store.section == .learning ? "Your learning, on this Mac" : "Your practice, on this Mac").font(.largeTitle.weight(.semibold))
                    Text("Progress updates automatically: editing starts a question, and passing all configured function tests marks it solved.").foregroundStyle(.secondary)
                }
                HStack(alignment: .top, spacing: 36) {
                    metric(store.section == .learning ? "Completed" : "Solved", value: store.currentSolved, suffix: "of \(store.currentCatalog.count)")
                    metric("Attempted", value: attempted, suffix: "distinct questions")
                    metric("Local runs", value: store.currentActivity.count, suffix: "\(stats.activeDays) active day\(stats.activeDays == 1 ? "" : "s") in 12 months")
                    metric("Current streak", value: stats.streak, suffix: "days with a run")
                }
                Divider()
                activityCalendar(stats)
                Divider()
                completedChart(stats)
                Divider()
                difficultyTable(stats)
                Divider()
                VStack(alignment: .leading, spacing: 12) {
                    Text("Recent runs").font(.title3.weight(.semibold))
                    if store.currentActivity.isEmpty {
                        Text("No runs recorded yet.").foregroundStyle(.secondary)
                    } else {
                        Grid(alignment: .leading, horizontalSpacing: 18, verticalSpacing: 12) {
                            GridRow {
                                Text("Question").font(.caption).foregroundStyle(.secondary)
                                Text("Language").font(.caption).foregroundStyle(.secondary)
                                Text("Result").font(.caption).foregroundStyle(.secondary)
                                Text("When").font(.caption).foregroundStyle(.secondary)
                            }
                            ForEach(Array(store.currentActivity.suffix(10).reversed())) { run in
                                GridRow {
                                    Text(store.currentCatalog.first { $0.id == run.problemID }?.title ?? "Question").lineLimit(2).frame(maxWidth: .infinity, alignment: .leading)
                                    Text(Language(rawValue: run.language)?.title ?? run.language).foregroundStyle(.secondary)
                                    Text(run.stopped ? "Stopped" : run.total > 0 ? "\(run.passed)/\(run.total) tests" : run.success ? "Finished" : "Error")
                                        .foregroundStyle(run.success ? Color.primary : Color.secondary)
                                    Text(run.date, style: .relative).foregroundStyle(.secondary)
                                }.font(.callout)
                            }
                        }
                    }
                }
                Divider()
                VStack(alignment: .leading, spacing: 12) {
                    Text("Local account").font(.title3.weight(.semibold))
                    Text("Start fresh by resetting saved code, personal lists, custom tests, notes, favorites, progress, and run history across Problems and Learning. The question library and learning tracks stay available.")
                        .font(.callout).foregroundStyle(.secondary)
                    Button("Reset local account…", role: .destructive) { store.showResetAccount = true }
                        .disabled(store.running)
                    if store.running { Text("Stop the active run before resetting.").font(.caption).foregroundStyle(.secondary) }
                    if let backup = store.latestBackup {
                        HStack {
                            Label("Fresh start complete. Recovery backup saved.", systemImage: "checkmark.circle")
                            Button("Reveal backup") { NSWorkspace.shared.activateFileViewerSelecting([backup]) }
                        }.font(.caption)
                    }
                }
            }.padding(30)
        }
        .frame(minWidth: 720, minHeight: 580)
        .background(FreeCodeTheme.surface).foregroundStyle(FreeCodeTheme.text).tint(FreeCodeTheme.accent)
        .confirmationDialog("Reset your local account?", isPresented: $store.showResetAccount) {
            Button("Reset and start fresh", role: .destructive, action: store.resetAccount)
            Button("Cancel", role: .cancel) {}
        } message: {
            Text("Saved code, tests, notes, favorites, progress, and statistics will be cleared from the active account. A recovery backup will be kept on this Mac. The question library stays available.")
        }
    }

    private func activityCalendar(_ stats: PracticeStatistics) -> some View {
        VStack(alignment: .leading, spacing: 12) {
            HStack {
                Text("Activity").font(.title3.weight(.semibold))
                Spacer()
                Text("Last 12 months").font(.caption).foregroundStyle(.secondary)
            }
            Text("\(stats.recentRuns) local runs across \(stats.activeDays) active day\(stats.activeDays == 1 ? "" : "s")")
                .font(.callout).foregroundStyle(.secondary)
            ScrollView(.horizontal, showsIndicators: false) {
                HStack(alignment: .top, spacing: 6) {
                    VStack(spacing: 3) {
                        Text(" ").frame(height: 16)
                        ForEach(0..<7) { day in
                            Text([1: "Mon", 3: "Wed", 5: "Fri"][day] ?? "")
                                .font(.system(size: 9)).foregroundStyle(.secondary).frame(width: 26, height: 10)
                        }
                    }
                    HStack(alignment: .top, spacing: 3) {
                        ForEach(stats.weeks.indices, id: \.self) { index in
                            VStack(spacing: 3) {
                                Text(index == 0 ? stats.weeks[index][0].date.formatted(.dateTime.month(.abbreviated)) : monthLabel(stats.weeks[index])).font(.system(size: 10)).foregroundStyle(.secondary)
                                    .fixedSize().frame(width: 10, height: 16, alignment: .leading)
                                ForEach(stats.weeks[index]) { day in
                                    RoundedRectangle(cornerRadius: 2)
                                        .fill(day.inRange ? activityColor(day.intensity) : .clear)
                                        .frame(width: 10, height: 10)
                                        .help(day.inRange ? "\(day.date.formatted(date: .complete, time: .omitted)): \(day.runs) local runs" : "")
                                        .accessibilityLabel(day.inRange ? "\(day.date.formatted(date: .complete, time: .omitted)), \(day.runs) local runs" : "")
                                        .accessibilityHidden(!day.inRange)
                                }
                            }
                        }
                    }
                }.padding(.vertical, 4).padding(.trailing, 20)
            }
            HStack(spacing: 5) {
                Text("Includes successful, failed, and stopped runs.").font(.caption).foregroundStyle(.secondary)
                Spacer()
                Text("Less").font(.caption2).foregroundStyle(.secondary)
                ForEach(0..<5) { level in
                    RoundedRectangle(cornerRadius: 2).fill(activityColor(level)).frame(width: 10, height: 10)
                        .help(["No runs", "1 run", "2–3 runs", "4–7 runs", "8 or more runs"][level])
                }
                Text("More").font(.caption2).foregroundStyle(.secondary)
            }
        }
    }

    private func completedChart(_ stats: PracticeStatistics) -> some View {
        let groups = breakdown == "type" ? stats.taskTypes : stats.difficulties.map { CompletedTasks(name: $0.name, count: $0.solved) }
        let total = groups.reduce(0) { $0 + $1.count }
        return VStack(alignment: .leading, spacing: 16) {
            HStack {
                Text("Completed questions").font(.title3.weight(.semibold))
                Spacer()
                Picker("Break down completed questions", selection: $breakdown) {
                    Text("Difficulty").tag("difficulty")
                    Text("Task type").tag("type")
                }.pickerStyle(.segmented).labelsHidden().fixedSize()
            }
            HStack(spacing: 32) {
                Group {
                    if total == 0 {
                        Circle().stroke(.quaternary, lineWidth: 22).padding(12)
                    } else {
                        Chart(groups.filter { $0.count > 0 }) { group in
                            SectorMark(angle: .value("Solved", group.count), innerRadius: .ratio(0.7), angularInset: 2)
                                .cornerRadius(3).foregroundStyle(categoryColor(group.name))
                                .accessibilityLabel(group.name)
                                .accessibilityValue("\(group.count) solved, \(Int((Double(group.count) / Double(total) * 100).rounded())) percent")
                        }.chartLegend(.hidden)
                    }
                }
                .frame(width: 190, height: 190)
                .overlay {
                    VStack(spacing: 3) {
                        Text(total, format: .number).font(.system(size: 30, weight: .semibold, design: .rounded))
                        Text("solved").font(.caption).foregroundStyle(.secondary)
                    }.allowsHitTesting(false)
                }
                VStack(alignment: .leading, spacing: 14) {
                    ForEach(groups) { group in
                        HStack(spacing: 9) {
                            Circle().fill(categoryColor(group.name)).frame(width: 9, height: 9)
                            Text(group.name).font(.callout)
                            Spacer()
                            Text(group.count, format: .number).font(.callout.monospacedDigit().weight(.medium))
                            Text(total == 0 ? "0%" : "\(Int((Double(group.count) / Double(total) * 100).rounded()))%")
                                .font(.caption.monospacedDigit()).foregroundStyle(.secondary).frame(width: 42, alignment: .trailing)
                        }.accessibilityElement(children: .combine)
                    }
                    if total == 0 {
                        Text("Pass all configured function tests to complete your first question.").font(.caption).foregroundStyle(.secondary)
                    }
                }.frame(maxWidth: .infinity)
            }
            Text(store.section == .learning ? "Counts completed lessons once each, grouped by difficulty or learning track. Problem statistics are separate." : "Counts currently solved questions once each. Task types follow the library’s SQL, Pandas, JavaScript, and algorithm categories.")
                .font(.caption).foregroundStyle(.secondary)
        }
    }

    private func difficultyTable(_ stats: PracticeStatistics) -> some View {
        VStack(alignment: .leading, spacing: 14) {
            Text("Remaining by difficulty").font(.title3.weight(.semibold))
            Grid(alignment: .leading, horizontalSpacing: 28, verticalSpacing: 12) {
                GridRow {
                    Text("Difficulty").frame(maxWidth: .infinity, alignment: .leading)
                    Text("Solved")
                    Text("Remaining")
                    Text("Total")
                }.font(.caption).foregroundStyle(.secondary)
                ForEach(stats.difficulties) { level in
                    GridRow {
                        HStack(spacing: 8) {
                            Circle().fill(difficultyColor(level.name)).frame(width: 8, height: 8)
                            Text(level.name).fontWeight(.medium)
                        }.accessibilityElement(children: .ignore)
                            .accessibilityLabel("\(level.name): \(level.solved) solved, \(level.remaining) remaining, \(level.total) total")
                        Text(level.solved, format: .number).accessibilityHidden(true)
                        Text(level.remaining, format: .number).fontWeight(.semibold).accessibilityHidden(true)
                        Text(level.total, format: .number).foregroundStyle(.secondary).accessibilityHidden(true)
                    }.font(.callout.monospacedDigit())
                }
            }
            Text("Remaining includes questions that are unstarted or in progress.").font(.caption).foregroundStyle(.secondary)
        }
    }

    private func monthLabel(_ week: [PracticeDay]) -> String {
        guard let first = week.first, Calendar.current.component(.day, from: first.date) <= 7 else { return "" }
        return first.date.formatted(.dateTime.month(.abbreviated))
    }

    private func activityColor(_ intensity: Int) -> Color {
        intensity == 0 ? Color.gray.opacity(0.15) : Color.green.opacity([0, 0.25, 0.45, 0.7, 1][intensity])
    }

    private func categoryColor(_ name: String) -> Color {
        switch name {
        case "Easy", "Medium", "Hard": difficultyColor(name)
        case "SQL": .purple
        case "Pandas": .teal
        case "JavaScript": .orange
        case "LLM engineering": .purple
        case "System design": .blue
        default: .blue
        }
    }

    private func metric(_ title: String, value: Int, suffix: String) -> some View {
        VStack(alignment: .leading, spacing: 6) {
            Text(title).font(.callout).foregroundStyle(.secondary)
            Text(value, format: .number).font(.system(size: 28, weight: .semibold, design: .rounded)).monospacedDigit()
            Text(suffix).font(.caption).foregroundStyle(.secondary)
        }.frame(maxWidth: .infinity, alignment: .leading)
    }
}

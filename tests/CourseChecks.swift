import AppKit
import Foundation

@main struct CourseChecks {
    @MainActor static func main() throws {
        let manager=FileManager.default
        let root=manager.temporaryDirectory.appendingPathComponent("CourseChecks-\(UUID().uuidString)")
        defer { try? manager.removeItem(at: root) }
        let store=Store(workDirectory:root.appendingPathComponent("personal"))
        precondition(store.error == nil, store.error ?? "")
        let course=store.learningCourses.first { $0.id == "python-engineer" }!
        store.chooseSection(.learning)
        store.chooseCourse(course.id)
        precondition(store.isCourseExercise && store.workspace.mode == "course")
        let first=store.selection!
        let entry=store.activeFilename
        store.workspace.code += "\n# persisted course work\n"
        store.edited();precondition(store.saveNow())
        store.moveLesson(1)
        precondition(store.workspace.code.contains("# persisted course work"))
        store.editCourseFile("new",name:"test_learner.py")
        store.workspace.code="def test_local():\n    assert True\n";store.edited();precondition(store.saveNow())
        store.selectCourseFile(entry)
        precondition(store.workspace.code.contains("# persisted course work"))
        store.editCourseFile("new",name:"../escape.py")
        precondition(store.error != nil);store.error=nil
        store.select(first)
        let step=store.problem!.course!
        let submitted=store.workspace
        let proof=CourseCheckReport(workspaceID:step.workspaceID,checkGroup:step.checkGroup,version:step.version,fingerprint:"fixture",graded:true,action:"check")
        let result=RunResult(success:true,message:"Passed",output:"",cases:[CaseResult(index:1,passed:true,actual:"ok",expected:"ok",input:"named test")],duration:0,course:proof)
        store.updateProgressAfterRun(result,problemID:first,language:"python",submitted:submitted)
        precondition(store.record.status == "Solved")
        store.moveLesson(1);store.workspace.code += "\n# changed shared file\n";store.edited()
        precondition(store.progress[String(first)]?.status == "In progress")
        store.select(first)
        store.updateProgressAfterRun(result,problemID:first,language:"python",submitted:submitted)
        precondition(store.record.status == "In progress")
        precondition(store.saveNow())
        let restarted=Store(workDirectory:root.appendingPathComponent("personal"))
        restarted.select(first)
        precondition(restarted.workspace.files?["test_learner.py"] != nil)
        restarted.resetAccount()
        precondition(restarted.latestBackup != nil)
        let publicData=URL(fileURLWithPath:CommandLine.arguments[1])
        let publicStore=Store(workDirectory:root.appendingPathComponent("public"),libraryDirectory:publicData)
        precondition(publicStore.error == nil,publicStore.error ?? "")
        precondition(publicStore.catalog.isEmpty && publicStore.section == .learning)
        precondition(publicStore.learningCatalog.contains { $0.id == publicStore.selection })
        publicStore.chooseCourse("python-engineer")
        precondition(publicStore.isCourseExercise)
        print("PASS: native course persistence, shared files, stale results, reset recovery and public startup")
    }
}

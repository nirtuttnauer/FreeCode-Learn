import Foundation

extension Store {
    private func validListName(_ name: String, excluding id: String? = nil) -> String? {
        let trimmed = name.trimmingCharacters(in: .whitespacesAndNewlines)
        guard !trimmed.isEmpty, trimmed.count <= 80 else {
            error = "Give your list a name between 1 and 80 characters."
            return nil
        }
        guard !customLists.contains(where: { $0.id != id && $0.name.localizedCaseInsensitiveCompare(trimmed) == .orderedSame }) else {
            error = "A list named “\(trimmed)” already exists. Choose another name."
            return nil
        }
        return trimmed
    }

    @discardableResult private func saveLists(_ next: [CustomList]) -> Bool {
        guard !running, customListsReadable else { return false }
        do {
            try JSONEncoder().encode(next).write(to: workURL.appendingPathComponent("custom-lists.json"), options: .atomic)
            customLists = next
            error = nil
            return true
        } catch {
            self.error = "Could not save your lists. Your previous lists are kept. Check disk permissions. \(error.localizedDescription)"
            return false
        }
    }

    @discardableResult func createCustomList(_ name: String, adding questionID: Int? = nil) -> String? {
        guard let name = validListName(name) else { return nil }
        let questions = questionID.flatMap { id in catalog.contains { $0.id == id } ? id : nil }.map { [$0] } ?? []
        let list = CustomList(name: name, questionIDs: questions)
        return saveLists(customLists + [list]) ? list.id : nil
    }

    @discardableResult func renameCustomList(_ id: String, to name: String) -> Bool {
        guard let name = validListName(name, excluding: id), let index = customLists.firstIndex(where: { $0.id == id }) else { return false }
        var next = customLists
        next[index].name = name
        return saveLists(next)
    }

    @discardableResult func deleteCustomList(_ id: String) -> Bool {
        guard customLists.contains(where: { $0.id == id }), saveNow(), saveLists(customLists.filter { $0.id != id }) else { return false }
        if selectedPlan == id { choosePlan("all") }
        return true
    }

    func toggleMembership(in id: String, questionID: Int) {
        guard catalog.contains(where: { $0.id == questionID }), let index = customLists.firstIndex(where: { $0.id == id }), saveNow() else { return }
        var next = customLists
        if next[index].questionIDs.contains(questionID) { next[index].questionIDs.removeAll { $0 == questionID } }
        else { next[index].questionIDs.append(questionID) }
        guard saveLists(next) else { return }
        if selectedPlan == id && !next[index].questionIDs.contains(selection ?? 0) { clearFiltersAndSelect() }
    }
}

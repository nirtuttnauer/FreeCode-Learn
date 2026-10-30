import AppKit
import SwiftUI
import WebKit
import UniformTypeIdentifiers

@MainActor final class OfflineContent: NSObject, WKURLSchemeHandler {
    let root: URL
    var document = ""
    init(root: URL) { self.root = root }
    func webView(_ webView: WKWebView, start task: any WKURLSchemeTask) {
        guard let url = task.request.url else { return }
        do {
            let data: Data
            let mime: String
            if url.host == "statement" {
                data = Data(document.utf8)
                mime = "text/html"
            } else if url.host == "assets" {
                let filename = url.lastPathComponent
                guard filename.range(of: "^[a-f0-9]{24}\\.[a-zA-Z0-9]+$", options: .regularExpression) != nil else {
                    throw URLError(.noPermissionsToReadFile)
                }
                data = try Data(contentsOf: root.appendingPathComponent("assets").appendingPathComponent(filename))
                mime = UTType(filenameExtension: url.pathExtension)?.preferredMIMEType ?? "application/octet-stream"
            } else { throw URLError(.unsupportedURL) }
            task.didReceive(URLResponse(url: url, mimeType: mime, expectedContentLength: data.count, textEncodingName: mime == "text/html" ? "utf-8" : nil))
            task.didReceive(data)
            task.didFinish()
        } catch { task.didFailWithError(error) }
    }
    func webView(_ webView: WKWebView, stop task: any WKURLSchemeTask) {}
}

struct StatementView: NSViewRepresentable {
    let html: String
    let root: URL
    let identity: Int
    @Environment(\.colorScheme) private var colorScheme

    func makeCoordinator() -> Coordinator { Coordinator(root: root) }
    func makeNSView(context: Context) -> WKWebView {
        let config = WKWebViewConfiguration()
        config.setURLSchemeHandler(context.coordinator.content, forURLScheme: "offline")
        config.websiteDataStore = .nonPersistent()
        config.defaultWebpagePreferences.allowsContentJavaScript = false
        let view = WKWebView(frame: .zero, configuration: config)
        view.navigationDelegate = context.coordinator
        view.setValue(false, forKey: "drawsBackground")
        return view
    }
    func updateNSView(_ view: WKWebView, context: Context) {
        let dark = colorScheme == .dark
        let key = "\(identity)-\(dark)"
        guard context.coordinator.key != key else { return }
        context.coordinator.key = key
        let foreground = dark ? "#ecf2f7" : "#172b3a"
        let secondary = dark ? "#a6b7c7" : "#526575"
        let code = dark ? "#0d151f" : "#edf3f6"
        context.coordinator.content.document = """
        <!doctype html><html><head><meta charset="utf-8">
        <meta http-equiv="Content-Security-Policy" content="default-src 'none'; img-src offline: data:; style-src 'unsafe-inline'; script-src 'none'; connect-src 'none'; frame-src 'none'; form-action 'none'; base-uri 'none'">
        <meta name="color-scheme" content="\(dark ? "dark" : "light")">
        <style>
        *{box-sizing:border-box}body{margin:0;padding:18px 24px 40px;font:15px/1.75 -apple-system,BlinkMacSystemFont,sans-serif;color:\(foreground);overflow-wrap:anywhere}
        p{margin:0 0 17px}h3{margin:26px 0 12px;font-size:16px;font-weight:600}h2{font-size:19px;margin:26px 0 12px}strong{font-weight:600}code{font:12.5px/1.6 ui-monospace,Menlo,monospace;background:\(code);padding:2px 5px;border-radius:4px}
        pre{white-space:pre-wrap;overflow-wrap:anywhere;font:12.5px/1.8 ui-monospace,Menlo,monospace;background:\(code);padding:16px;border-radius:8px;margin:12px 0 24px}
        pre code{padding:0}ul,ol{padding-left:22px;margin:8px 0 24px}li{padding-bottom:5px}img{display:block;max-width:100%;height:auto;margin:16px 0;border-radius:4px}
        a{color:\(dark ? "#85f1d0" : "#11654f");text-underline-offset:3px}table{border-collapse:collapse;max-width:100%;display:block;overflow:auto}td,th{padding:7px;border:1px solid \(secondary)}
        ::selection{background:\(dark ? "#20584c" : "#cdeadd")}*:focus-visible{outline:2px solid \(dark ? "#85f1d0" : "#11654f");outline-offset:3px}
        </style></head><body>\(html)</body></html>
        """
        view.load(URLRequest(url: URL(string: "offline://statement/\(identity)")!))
    }

    @MainActor final class Coordinator: NSObject, WKNavigationDelegate {
        let content: OfflineContent
        var key = ""
        init(root: URL) { content = OfflineContent(root: root) }
        func webView(_ webView: WKWebView, decidePolicyFor action: WKNavigationAction) async -> WKNavigationActionPolicy {
            if action.request.url?.scheme == "offline" {
                return .allow
            } else {
                // Remote links and scripts never navigate inside the local statement view.
                return .cancel
            }
        }
    }
}

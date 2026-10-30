// swift-tools-version: 6.2
import PackageDescription

let package = Package(
    name: "OfflinePractice",
    platforms: [.macOS(.v14)],
    targets: [
        .executableTarget(name: "OfflinePractice", path: "Sources/OfflinePractice")
    ],
    swiftLanguageModes: [.v6]
)

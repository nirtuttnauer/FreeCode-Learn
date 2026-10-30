#!/bin/zsh
set -euo pipefail
cd "${0:A:h:h}"
mkdir -p .cache
export CLANG_MODULE_CACHE_PATH="$PWD/.cache/clang-modules"
python3 scripts/stage_content.py --profile public --destination .cache/course-public-data
swiftc -parse-as-library -swift-version 6 Sources/OfflinePractice/Models.swift Sources/OfflinePractice/DesignWorkspace.swift Sources/OfflinePractice/Store.swift Sources/OfflinePractice/PersonalLists.swift Sources/OfflinePractice/PracticeStatistics.swift Sources/OfflinePractice/CourseWorkspace.swift tests/CourseChecks.swift -o .cache/course-checks
.cache/course-checks .cache/course-public-data

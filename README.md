# Swift Agent Skills

An unofficial Codex plugin that bundles four MIT-licensed Swift agent skills created by [Paul Hudson (@twostraws)](https://github.com/twostraws).

## Included skills

### SwiftUI Pro

Reviews SwiftUI code for modern APIs, maintainability, performance, design, and accessibility. [View the original SwiftUI Agent Skill](https://github.com/twostraws/SwiftUI-Agent-Skill).

### SwiftData Pro

Writes and reviews SwiftData code, including models, queries, predicates, relationships, migrations, indexing, and CloudKit constraints. [View the original SwiftData Agent Skill](https://github.com/twostraws/SwiftData-Agent-Skill).

### Swift Concurrency Pro

Reviews Swift concurrency code for actor isolation, structured concurrency, cancellation, async streams, continuations, and common race-condition patterns. [View the original Swift Concurrency Agent Skill](https://github.com/twostraws/Swift-Concurrency-Agent-Skill).

### Swift Testing Pro

Writes and reviews tests using Swift Testing, including async tests, parameterized tests, assertions, test organization, and XCTest migration. [View the original Swift Testing Agent Skill](https://github.com/twostraws/Swift-Testing-Agent-Skill).

## Upstream synchronization

The `Sync upstream skills` GitHub Actions workflow checks all four repositories daily and can also be run manually. It copies only each skill's canonical `SKILL.md`, references, assets, and OpenAI metadata, then validates the complete plugin. When upstream content changes, the workflow opens or updates a pull request for review rather than changing `main` silently.

## License and attribution

The bundled skills were created by Paul Hudson and remain available under the MIT License. The required copyright and permission notice is preserved in [LICENSE](LICENSE), with a copy for each bundled skill under [`licenses/`](licenses/). Exact upstream repositories and bundled commit hashes are recorded in [ATTRIBUTION.md](ATTRIBUTION.md).

This packaging repository is unofficial and is not maintained or endorsed by Paul Hudson.

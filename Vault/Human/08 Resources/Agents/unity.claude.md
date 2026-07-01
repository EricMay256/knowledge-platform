---
CreatedAt: 2026-06-28T16:51:19Z
LastUpdated: 2026-07-01T01:18:47Z
Type: Resource
Status:
tags:
aliases:
---

# Unity C\# Development Conventions

This project is a Unity application written in C\#. Follow these conventions unless explicitly directed otherwise. When something is ambiguous, ask before assuming.

## Code style

### Regions and structure

- Use `#region x` / `#endregion`, not `// REGION:` or `//----x` comments. C\# has native region syntax; use it.
- Group members in this order within a class: serialized fields, private fields, properties, Unity lifecycle methods (Awake, Start, OnEnable, Update, etc.), public methods, private methods, nested types.
- Unity lifecycle methods go in calling order, not alphabetical.

### Naming

- PascalCase for types, methods, properties, public fields, constants.
- camelCase for local variables and parameters.
- `_camelCase` for private fields (leading underscore). Do not prefix with `m_`.
- Serialized private fields use `[SerializeField] private` with `_camelCase`, not public fields. Public mutable fields are not idiomatic in modern Unity C\#.
- Interfaces prefixed with `I` (e.g., `IDamageable`).
- Async methods suffixed with `Async` only when there is also a sync version or when the async nature is non-obvious from context.

### Language features

- Prefer `var` for local variables when the type is obvious from the right-hand side. Use explicit types when it aids readability.
- Use expression-bodied members for trivial getters and one-line methods.
- Use pattern matching, switch expressions, target-typed `new()`, and other modern C\# features where they improve clarity.
- Nullable reference types are enabled. Annotate accordingly. Do not suppress nullability warnings without a reason in a comment.
- Use `nameof()` instead of string literals for member references.

### Braces and formatting

- Allman braces (opening brace on its own line) for types, methods, properties.
- Same-line braces are acceptable for single-line lambdas and simple property accessors.
- Always use braces for control flow, even single-line `if` bodies.
- Prefer early returns over deep nesting.

## Unity-specific conventions

### Component design

- Prefer composition over inheritance. Build behaviour from small, focused MonoBehaviours rather than deep class hierarchies.
- A MonoBehaviour should have one responsibility. If a script is doing two unrelated things, split it.
- Reference other components via `[SerializeField]` and assignment in the Inspector when possible. Use `GetComponent<T>()` in `Awake()` only when Inspector wiring is impractical.
- Cache references in `Awake()` or `Start()`; do not call `GetComponent` in `Update()`.
- Use `[RequireComponent(typeof(T))]` when a script depends on another component on the same GameObject.

### Lifecycle and execution

- `Awake()` for self-initialization (cache references, set up internal state).
- `Start()` for initialization that depends on other objects being awake.
- `OnEnable()` / `OnDisable()` for subscribing/unsubscribing to events. Always pair them. Never subscribe in `Awake()` or `Start()` alone.
- Avoid `Update()` for things that do not need per-frame work. Use coroutines, `InvokeRepeating`, or event-driven patterns where appropriate.
- For physics-related updates, use `FixedUpdate()`. For input that should not miss frames, use `Update()`. For post-physics camera work, use `LateUpdate()`.

### Async and concurrency

- Prefer `async`/`await` with UniTask over coroutines for new code, if UniTask is in the project. If only standard Unity is available, coroutines are fine for Unity-aware async work. If the circumstances are unclear, don’t assume, ask.
- Do not use `Task.Run` or thread-pool work for Unity API calls — Unity APIs are main-thread-only and will throw or behave incorrectly off-thread.
- Always handle cancellation via `CancellationToken` for any async operation that could outlive its component (use `this.GetCancellationTokenOnDestroy()` with UniTask, or equivalent).

### Allocation and performance

- Avoid allocations in `Update()` and other per-frame methods. No LINQ, no string concatenation, no `new` of reference types in hot paths.
- Use object pooling for frequently spawned/destroyed objects.
- Cache `WaitForSeconds` instances rather than allocating per coroutine yield.
- Prefer `TryGetComponent` over `GetComponent` followed by null check, unless there is a corresponding `RequireComponent`
- Be aware of `transform.position` triggering matrix recalculation on assignment; cache and modify locally where it matters.

### Serialization

- Serialized fields should be `[SerializeField] private` with a backing field rather than public fields, unless there is a specific reason for public access.
- Use `[Tooltip]` for any serialized field whose purpose is not obvious from its name.
- Use `[Header]` and `[Space]` to organize the Inspector for non-trivial components.
- ScriptableObjects for shared, designer-editable data. Do not use them as runtime singletons unless that is genuinely the right pattern.

### Project structure

- Scripts go under `Assets/Scripts/` organized by feature, not by type. Avoid folders named "Managers" or "Utilities" as catch-alls.
- Use assembly definitions (`.asmdef`) to enforce module boundaries. Each feature folder gets its own assembly when it grows beyond a few scripts.
- Editor-only scripts go in `Editor/` subfolders or in assemblies marked Editor-only.
- Tests go in `Tests/` subfolders with their own `.asmdef` referencing the Unity Test Framework.

### Editor scripts and tooling

- Editor scripts use the `UnityEditor` namespace and must be in `Editor/` folders or Editor-only assemblies. Reference them only from other Editor code.
- Use `[MenuItem]` for one-off tools; use custom Editor windows (`EditorWindow`) for tools used repeatedly.
- For programmatic scene/prefab construction, prefer `PrefabUtility` and `EditorSceneManager` APIs over hand-editing YAML.

## Testing approach

- Unit tests for pure logic (no MonoBehaviour dependencies) using NUnit through Unity Test Framework. Test files in `Tests/EditMode/`.
- Play mode tests for behaviour that requires Unity runtime, in `Tests/PlayMode/`. Keep these minimal — they are slow.
- Do not generate tests for trivial getters, Unity lifecycle methods, or Inspector-wired references. Test behaviour, not plumbing.
- When writing testable logic, separate pure C\# from MonoBehaviour where possible. A MonoBehaviour can be a thin shell over a plain-C\# class that holds the testable logic.
- If a test would require extensive mocking of Unity APIs, that is usually a sign the production code should be refactored rather than the test being elaborate.

## Dependencies and external code

- Do not add new packages, NuGet references, or Unity Asset Store assets without flagging the addition explicitly and explaining why.
- When suggesting a third-party solution, note whether you have direct knowledge of it or are reasoning from general reputation.
- Prefer Unity Package Manager packages over Asset Store assets when both are available — UPM packages version-control cleanly.
- If a problem can be solved with built-in Unity APIs reasonably well, do not reach for a third-party package.

## Error handling

- Use `Debug.LogError` for genuine errors that should not happen in production.
- Use `Debug.LogWarning` for recoverable issues worth investigating.
- Use `Debug.Log` sparingly. Do not generate log statements as a substitute for proper error handling.
- For services that may fail (network calls, file I/O, parsing), return result types or use try/catch with specific exception types — not `catch (Exception)`.
- For player-facing failure modes, the game should fail gracefully and visibly, not silently log and continue.

## Comments and documentation

- XML doc comments (`///`) to provide usage hints to developers. Ensure thorough documentation on public APIs in library-style code (e.g., a service or SDK). For internal gameplay code, prefer self-documenting names over heavy comments.
- Inline comments explain *why*, not *what*. If the comment describes what the code does, the code should be clearer instead.
- Do not generate boilerplate "Constructor" or "Properties" comments.
- Do not insert TODO comments unless explicitly asked.

## Things to avoid

- Singletons via static instance fields. If shared state is needed, prefer ScriptableObjects, dependency injection, or a service locator pattern. If a singleton is genuinely needed, flag it for review.
- `FindObjectOfType` and `GameObject.Find` outside of editor scripts and one-time initialization. They are slow and brittle. In most cases, one find result can be cached and reused.
- Public mutable fields on MonoBehaviours.
- Coroutines that capture `this` and run for the lifetime of the scene without explicit cancellation.
- Magic numbers in gameplay code. Use serialized fields, constants, or ScriptableObject values.
- Catching `Exception` without rethrowing or logging — silent failure in Unity is particularly hard to debug.

## When generating code

- Provide complete, runnable scripts. Do not leave method bodies as `// TODO` or stub them out unless explicitly asked for a sketch.
- When proposing a non-trivial design, briefly explain the trade-off considered before writing code.
- Flag where a suggestion is idiomatic vs. a pragmatic shortcut. Idiomatic Unity C\# is the default; if you are recommending something for speed of iteration rather than long-term cleanliness, say so.
- If the user's existing code uses a pattern that conflicts with these conventions, follow the existing pattern in that file but flag the conflict for discussion.
- When unsure whether a project uses a specific package (UniTask, Zenject, Cinemachine, etc.), ask before assuming.

## Unity version considerations

- This project targets Unity \[VERSION\]. Some APIs differ across versions; flag where a suggestion is version-specific.
- Prefer modern Unity APIs (Input System over old Input, UI Toolkit over IMGUI for new editor UI, Addressables over Resources) unless the project already uses the older equivalent.
- Prefer Canvas based runtime UI

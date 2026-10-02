# midnight-shell — Full Workspace Map & Reverse-Engineered QML Curriculum

Analysis of `/home/aman/midnight-shell`, a fork of **caelestia-shell** (remote origin: `https://github.com/dim-ghub/midnight-shell`, branch `main`, 3082 commits). The shell runs on this machine via `caelestia shell -d` → `qs -c caelestia -d`, with user config at `/home/aman/.config/caelestia/`.

This document has two phases:

- **Phase 1** — a complete workspace map of the codebase so you can navigate it confidently.
- **Phase 2** — a reverse-engineered QML curriculum (10 steps) that teaches you, from zero QML, exactly the concepts this codebase uses, in dependency order, ending with you building one real widget for the taskbar.

---

# Phase 1 — Workspace Map

## 1. Directory tree

```
/home/aman/midnight-shell/
├── shell.qml                  # ENTRY POINT — instantiated by quickshell
├── bldit.lua                  # build/install helper (Lua, mirrors the repo's build script)
├── flake.nix / flake.lock     # Nix dev/build env
├── scripts/                   # developer utilities (one-off + lint)
│   ├── qml-lint-conventions.py    # coding-convention checker over QML files
│   ├── replace_footer.py          # one-off: hardcoded /home/dim/... path, DO NOT RUN
│   └── replace_xhr.py             # one-off: hardcoded /home/dim/... path, DO NOT RUN
├── assets/
│   ├── dino/                  # offline "no internet" dino animation sprites
│   ├── google-sans-flex/      # bundled GoogleSansFlex font (see Config.font)
│   ├── scripts/
│   │   ├── orion_search.py        # playwright-based web search for the AI assistant
│   │   └── parse_keybinds.lua     # parses hyprland keybinds.lua for the nexus module
│   ├── sounds/                # notification/OSD sounds
│   ├── wallpapers/            # bundled wallpapers
│   ├── shimeji/               # desktop mascot sprites
│   └── wrap_term_launch.sh    # wraps terminal launches; cats ~/.local/state/caelestia/sequences.txt
├── extras/version.cpp         # version stamp for the plugin
├── plugin/                    # C++ extension library (adds types QML cannot express)
│   ├── CMakeLists.txt
│   └── src/Caelestia/
│       ├── Config/            # GlobalConfig, Tokens, Config (attached), MonitorConfigManager
│       ├── Internal/          # HyprExtras, HyprDevices, HyprKeyboard, VisualiserBars, ...
│       ├── Services/          # Cpu, Gpu, Memory, Storage, DiskInfo, CavaProvider, ...
│       ├── Images/            # IUtils (dominant-colour extraction etc.)
│       ├── Models/            # FileSystemModel, FileSystemEntry
│       └── ...                # core exports: CUtils, Toaster, AppDb, Requests, Qalculator
├── components/                # REUSABLE UI building blocks
│   ├── containers/            # StyledWindow, StyledListView, ...
│   ├── controls/              # ButtonBase, IconButton, TextButton, Menu, StyledSwitch, ...
│   ├── effects/               # ColouredIcon, Colouriser, ...
│   ├── images/                # IconImage wrappers
│   ├── misc/                  # CustomShortcut, Ref, ...
│   └── widgets/               # misc larger widgets
├── utils/                     # small helper singletons (Icons, Paths, Strings, SysInfo, ...)
├── services/                  # QML singletons wrapping Quickshell/Caelestia services
│   └── ... (27 files: Hypr, Time, ShellState, Visibilities, Screens, Colours, Audio, ...)
├── modules/                   # THE SHELL'S MODULES (bars, drawers, launcher, etc.)
│   ├── bar/                   # the taskbar — Phase 1 §4
│   ├── drawers/               # per-screen content windows (hosts BarWrapper + panels)
│   ├── launcher/              # app launcher (search, calc, emoji, clipboard, windows)
│   ├── nexus/                 # settings/About UI (newer, still growing)
│   ├── lock/                  # lock screen
│   ├── session/               # session/boot splash
│   ├── sidebar/               # control center (notifications, toggles, media)
│   ├── notifications/         # OSD + notification popup window
│   ├── osd/                   # on-screen display (volume/brightness)
│   ├── shell/                 # ShellRoot helpers
│   ├── shimeji/               # desktop mascot
│   └── ...                    # ServiceLoader.qml, GSFLoader.qml, Shortcuts.qml, etc.
└── nix/                       # nix packaging glue
```

**Import-path rule (critical):** Quickshell turns directories under the config root into importable modules. A directory `modules/bar/` becomes `import qs.modules.bar`. So:

- `modules/bar/Bar.qml` is `import qs.modules.bar` → used as `Bar`
- `modules/bar/components/Clock.qml` is `import qs.modules.bar.components` → `Clock`
- `modules/bar/components/status/LockStatus.qml` is `import qs.modules.bar.components.status` → `LockStatus`
- `modules/bar/popouts/Wrapper.qml` is `import qs.modules.bar.popouts`
- Top-level `components/`, `services/`, `utils/` are `import qs.components`, `import qs.services`, `import qs.utils`.

There are only **2 qmldir files** in the whole repo (`modules/nexus/pages/background/qmldir` and `.../pages/hyprland/qmldir`) because the rest rely on directory-based import resolution.

## 2. Entry point & boot flow

Everything starts from **`shell.qml`** at the repo root. Its top-level object is a `ShellRoot` (a Quickshell built-in that hosts everything a desktop shell can show, including per-screen layers).

Order of operations (roughly, top-to-bottom in the file):

1. **`ShellRoot`** is the root. Its `Binding` sets `ShellState.shellRoot` so any service can find it.
2. **`ConfigToasts`** (`modules/ConfigToasts.qml`) — a singleton-ish loader that pops a small toast on config errors.
3. **`GSFLoader`** (`modules/GSFLoader.qml`) — loads Google Sans Flex via `FontLoader` (drives `Tokens.font`).
4. **`ServiceLoader`** (`modules/ServiceLoader.qml`) — a scope that instantiates every `pragma Singleton` service so they initialize once and start emitting change signals.
5. **`Background`** — the wallpaper layer.
6. **`Drawers`** (`modules/drawers/Drawers.qml`) — a `Variants` + `Scope` per screen that creates one **`ContentWindow`** (`modules/drawers/ContentWindow.qml`) per monitor. `ContentWindow` contains the `BarWrapper` and the various panels (sidebar, osd, etc.).
7. **`AreaPicker`**, **`Lock`** (lock screen), **`PolkitModule`** (polkit dialogs), **`Shimeji`** (mascot), **`BadAppleOverlay`**, **`DesktopLyricsOverlay`**.
8. **`Shortcuts`** (`modules/Shortcuts.qml`) — a scope that instantiates every `CustomShortcut` (the repo's registry of global keybinds → the `caelestia:*` IPC events).
9. Several forced service inits exposed as properties: `DiscordRPC`, `GameMode`, `PipManager`, `SystemTray`, `BatteryMonitor`, `IdleMonitors`, `BluetoothReconnect`.

> ⚠️ **Version skew:** the *installed* shell at `/etc/xdg/quickshell/caelestia/shell.qml` is an **older copy** than this repo. It is missing `PolkitModule`, `Shimeji`, `BadAppleOverlay`, `DesktopLyricsOverlay`, `BluetoothReconnect`, the forced `DiscordRPC`/`GameMode`/`PipManager`/`SystemTray` init, and runs with `settings.watchFiles: false`. **Anything you run on this machine right now reflects the installed copy, not the repo.** See §8.

## 3. Component & dependency graph

### 3.1 QML ↔ C++ split
Quickshell QML only reaches into the system through C++ types. Two sources of C++ types:

- **Quickshell built-ins** (from `/usr/lib/qt6/qml/Quickshell/`):
  - core: `Scope`, `Variants`, `ScriptModel`, `ShellRoot`, `ShellScreen`, `Singleton`, `SystemClock`, `PersistentProperties`, `BoundComponent`, `LazyLoader`
  - Io: `IpcHandler`, `Process`, `StdioCollector`, `FileView`, `Socket`
  - Hyprland: `GlobalShortcut`
  - Services: `Hyprland`, `SystemTray`, `Mpris`, `UPower`, `Pipewire` (`PwNode`), `Networking` (NetworkManager), `Notifications`, etc. (wrapped by `qs.services.*`)
- **Caelestia plugin** (from `/usr/lib/qt6/qml/Caelestia/`), exported as:
  - `Caelestia.Config` — `Config` (attached), `GlobalConfig` (singleton), `Tokens` (singleton), `TokenConfig`, `MonitorConfigManager`
  - `Caelestia.Components` — `LazyListView`, `ButtonRow`, `WavyLine`
  - `Caelestia.Internal` — `HyprExtras`, `HyprDevices`, `HyprKeyboard`, `VisualiserBars`, `SparklineItem`, `CircularBuffer`, ...
  - `Caelestia.Services` — `CavaProvider`, `BeatTracker`, `Cpu`, `Gpu`, `Memory`, `Storage`, `DiskInfo`, `ServiceRef`, `Lyrics`, `SessionManager`, `UsageFmt`
  - `Caelestia` core — `CUtils`, `Toaster`, `AppDb`, `Requests`, `ImageAnalyser`, `Qalculator`
  - `Caelestia.Images` — `IUtils`
  - `Caelestia.Models` — `FileSystemModel`, `FileSystemEntry`

### 3.2 The dependency direction
- `shell.qml` imports `qs.components`, `qs.services`, `qs.utils`, and specific modules.
- Every module imports `qs.services` (state), `qs.components` (UI), `Caelestia.Config` (config/tokens), `Quickshell` (core), `QtQuick` (base).
- Widgets under `modules/bar/components/*` are consumed by `Bar.qml` through the **entry system** (§4), not by direct instantiation.

### 3.3 Services layer (the 27 QML singletons)
Each file in `services/` is a `pragma Singleton` object that wraps a lower-level service:

| File | Wraps | Purpose |
|---|---|---|
| `Hypr.qml` | Quickshell Hyprland service | workspaces, toplevels, keyboard, `Hypr.monitorFor(screen)`, `dispatch()`, caps/num lock |
| `Time.qml` | `SystemClock` | wall-clock time (`Time.string`) |
| `ShellState.qml` | internal | per-screen `ScreenState` store; `ShellState.forScreen(s)`, `forActive(s)` |
| `Visibilities.qml` | `ShellState` | **mostly backwards-compat stubs** forwarding to ShellState |
| `Screens.qml` | `GlobalConfig` + `ShellState` | enumerates enabled monitors (`Screens.array`), filtered by `GlobalConfig.forScreen(s.name).enabled` |
| `Colours.qml` | M3Palette/M3TPalette + ImageAnalyser | Material 3 palette, light/dark, `Colours.layer()`, transparency from wall luminance |
| `Audio.qml` | Pipewire `PwNode` | volume/mute per sink/source; aliases `Audio.cava`, `Audio.beatTracker` |
| `Players.qml` | Mpris | active media player (used by Spotify widget) |
| `Notifs.qml` | Quickshell notif daemon | notification model, DND state |
| `Brightness.qml` | BrightnessDevice | backlight control |
| `Nmcli.qml` / `VPN.qml` | NetworkManager CLI | wifi/ethernet/VPN state |
| `Wallpapers.qml` / `Weather.qml` / ... | misc | wall sources, weather data |

Most of these are consumed inside modules by reading properties, e.g. `Hypr.workspaces[0].isActive`, `Time.string`, `Notifs.dnd`.

## 4. Bar deep dive

### 4.1 Layering: ContentWindow → BarWrapper → Bar
- `modules/drawers/ContentWindow.qml` creates one `BarWrapper` per monitor inside a `StyledWindow` (a `PanelWindow` with WlrLayershell namespace) positioned per `Config.bar.position` (left/right/top/bottom).
- `modules/bar/BarWrapper.qml` handles **visibility**: `ScreenState.visible`, `exclusiveZone` (so Hyprland reserves space), autohide when `Config.bar.persistent === false`, and exclusion via `Strings.testRegexList(Config.bar.excludedScreens, screen.name)`.
- `modules/bar/Bar.qml` is the layout. It has three **`EntrySection`**s: `start`, `center`, `end`.

### 4.2 The entry system (most important thing to understand)
Entries are **not hardcoded**. `Bar.qml` reads config:

```
Config.bar.entries.start.values   →  ScriptModel { values: ... }
```

`Config.bar.entries` is a `ConfigList` (see `plugin/src/Caelestia/Config/barconfig.hpp`, `configlist.hpp`). Each entry has an `id`. The bar renders each entry via:

- `ScriptModel { values: <ids> }` — the array of entry ids.
- `EntryWrapper` — per-item wrapper that looks up which **component** to instantiate.
- `DelegateChooser` / `EntryChooser` — maps `role: "id"` → the right widget component (Clock, Workspaces, Tray, StatusIcons, Dock, ActiveWindow, Spotify, Power, OsIcon, ...).

Default sections (from `barconfig.hpp` defaults):
- `start`: `["logo", "workspaces"]`
- `center`: `["activeWindow"]`
- `end`: `["tray", "clock", "statusIcons", "power"]`

The user's live config (`/home/aman/.config/caelestia/shell.json`) does not override `entries`, so they run the defaults; it *does* set `bar.showOnHover: true`, `bar.persistent: false`, `bar.clock.background: false`, `bar.scrollActions.*: true`, and a special `secret` workspace icon.

The bar also does `entryAt(x)` (hit-testing), `closeTray()`, `checkPopout()`, and `handleWheel` (scrolling over sections → volume/brightness via `scrollActions`).

### 4.3 Popouts
When you click an entry, a popout appears:

- `modules/bar/popouts/Wrapper.qml` — the window; animates and switches between **content**, **winfo** (window info), and **nexus** views.
- `modules/bar/popouts/Content.qml` — picks the right popout content for the active entry id (activewindow, network, wirelesspassword, tray, statusicons, spotify, dockhover, dockcontext, kblayout, etc.).
- `modules/bar/popouts/PopoutState.qml` — shared state: `currentName`, `currentSection`, `dockModel`, `sidebarOpen`.

This is a **section-aware push/merge** system (the fork's recent commit "split taskbar entries into start/center/end sections and make popout push/merge section-aware"): popouts know which section they were launched from.

### 4.4 Widget-by-widget data sources
| Widget | File | Data source |
|---|---|---|
| Clock | `modules/bar/components/Clock.qml` | `Time` singleton + `SystemClock`; `MaterialIcon` + `StyledText` |
| Workspaces | `components/workspaces/Workspaces.qml`, `Workspace.qml`, `SpecialWorkspaces.qml`, `ActiveIndicator.qml` | `Hypr.workspaces`, `Hypr.activeWsId`, `groupOffset`; `GridLayout` + Loader-based indicators |
| Tray | `components/Tray.qml`, `TrayItem.qml` | `SystemTray` service, `Quickshell.Services.SystemTray`, `QsMenuOpener`, `Icons.getTrayIcon`, `ColouredIcon` |
| StatusIcons | `components/StatusIcons.qml` + `components/status/*` | `ScriptModel` over `[lock, battery, bluetooth, notifs, peripheralBattery]`; `collapsed()` logic (e.g. lock hidden unless caps/num lock via `Hypr.capsLock`) |
| Dock | `components/Dock.qml` | `dockModel` (ListModel of favourite apps); `saveNewOrder()` writes `GlobalConfig.launcher.favouriteApps` |
| ActiveWindow | `components/ActiveWindow.qml` | `Hypr.activeToplevel.title`; width capped against bar section widths |
| Spotify | `components/Spotify.qml` | `Players.active` (Mpris) + `ServiceRef` on `Audio.cava` for the visualiser |
| Power | `components/Power.qml` | `SessionManager`/`Logind` actions; contains a "cursed workaround" (see §8) |
| GithubActivity | `components/GithubActivity.qml` | `GithubStore` (singleton) fetching from GitHub API |
| OsIcon | `components/OsIcon.qml` | static logo, opens launcher/nexus |

## 5. State & data flow

### 5.1 Three layers of state
1. **Config (C++ persisted)** — `GlobalConfig` reads `~/.config/caelestia/shell.json` (plus `monitors/<name>/shell.json` per-monitor overrides). It is a tree of `ConfigObject`s; each `CONFIG_PROPERTY(type, name, default)` creates a Q_PROPERTY with change notification. Hot reload via `QFileSystemWatcher` + a **50 ms debounce** in `rootconfig.cpp` — editing `shell.json` live-updates the shell.
2. **Runtime service state (QML singletons)** — e.g. `Time.string`, `Hypr.workspaces`, `Screens.array`. These push change signals; QML bindings re-evaluate.
3. **UI state (QML objects)** — e.g. `PopoutState`, `ScreenState.launcher`, `ScreenState.sidebar`. These are plain objects whose properties are bound to by widgets.

### 5.2 Per-monitor configuration — the `Config` attached property
`Config` (from `Caelestia.Config`) is a **QQuickAttachedPropertyPropagator**. Setting `Config.screen` on a container makes every descendant read `Config.<field>` for *that screen's* overrides; unset → global defaults. `MonitorConfigManager` holds the per-screen `ConfigObject`s. `BarWrapper`/`ContentWindow` set `Config.screen: screen.name` at the window root.

### 5.3 Per-screen UI state — `ShellState` / `ScreenState`
`ShellState.forScreen(screen)` returns a `ScreenState` (via `Variants` keyed by screen) with booleans like `launcher`, `sidebar`, `visible`, `popout`, `notification`. Widgets bind to `screenState.xxx`; `ShellState.forActive(screen)` resolves the "active" monitor.

### 5.4 Binding chain example (Clock)
```
shell.json → GlobalConfig.bar.clock.showDate
              ↓ (CONFIG_PROPERTY notify)
Tokens.font.clock  ← Tokens (singleton) ← AppearanceTokens ← GlobalConfig.appearance.font
              ↓
Clock.qml: StyledText { text: Time.string; font: Tokens.font.clock; visible: Config.bar.clock.showDate }
```

## 6. Styling & theming

### 6.1 Colours (Material 3 from your wallpaper)
`services/Colours.qml` (singleton):
- `Colours.palette` — `M3Palette` for the current theme; `.m3primary`, `.m3surfaceContainer`, `.m3onSurface`, `.m3outline`, etc.
- `Colours.tPalette` — the transparent variant.
- `Colours.light` — bool (light/dark scheme).
- `Colours.layer("level")` — layered background colour helper.
- `Colours.transparency` — derived from `wallLuminance` (via `ImageAnalyser`): light/dark walls get different opacities.

### 6.2 Tokens (design system in C++)
`Tokens` is a singleton built from `Config.appearance`: `Tokens.padding.*`, `Tokens.spacing.*`, `Tokens.rounding.*`, `Tokens.sizes.*`, `Tokens.anim.durations.*` + easing curves, and fonts: `Tokens.font.body.medium`, `Tokens.font.label.small`, `Tokens.font.icon.medium`, etc. See `appearanceconfig.hpp` + `font.hpp`.

**Font builders** are the clever part: `Tokens.font.body.builders.small.scale(1.1).build()` produces a derived `QFont` (see `fontbuilder.hpp`). Material icons use `Tokens.font.icon` with `fill`/`grade` properties (material symbols variable font).

### 6.3 Building blocks
- `StyledRect` — rounded, coloured container (uses `Colours.layer`).
- `StyledText` — themed text (renderType NativeRendering; animates text changes).
- `MaterialIcon` — icon glyph from `Tokens.font.icon`.
- `StateLayer` — MouseArea with an animated ripple; the repo's primary click target (see `components/StateLayer.qml` and `components/controls/ButtonBase.qml`).
- `Anim` — `NumberAnimation` wrapper; `Anim.Type` enum maps to `Tokens.anim.*` durations/easings; used everywhere instead of raw `NumberAnimation`.
- `ColouredIcon` — `IconImage` + `Colouriser` effect + `ImageAnalyser` for tinting tray/status icons.

## 7. Non-QML glue

### 7.1 Launch chain
- `~/.config/hypr/hyprland/execs.lua` runs `caelestia shell -d` at login.
- `/usr/bin/caelestia` is a **Python CLI** (`caelestia-cli` 1.1.2). `caelestia shell` builds and runs the real command: **`qs -c caelestia -d`**. The `-c caelestia` flag makes Quickshell load the shell package named `caelestia` from its config search path — on this machine that resolves to the **installed copy at `/etc/xdg/quickshell/caelestia/`** (the repo must be installed/copied there to run, see §8). The directory structure of that package *is* the `qs.*` import mapping. Separately, the shell's **runtime user config** (the JSON the C++ plugin reads, hot-reloaded) lives at `~/.config/caelestia/` (`shell.json`, `monitors/`, `hypr-vars.lua`, ...).

### 7.2 IPC
- **Shell → Hyprland:** via `GlobalShortcut` (Quickshell) registered by `CustomShortcut` (`components/misc/CustomShortcut.qml`, `appid: "caelestia"`). Keybinds in `~/.config/hypr/hyprland/keybinds.lua` dispatch `hl.dsp.global("caelestia:launcher")` etc.; `Shortcuts.qml` receives them.
- **External → Shell:** `qs -c caelestia ipc call <Handler>.<method> ...` → `IpcHandler` (Quickshell.Io) routes to repo-defined handlers (e.g. toggling launcher/sidebar).

### 7.3 Other scripts
- `bldit.lua` — build/install helper; removes legacy lib copies before installing the plugin.
- `assets/scripts/orion_search.py` — playwright+firefox DuckDuckGo search for the AI assistant in the sidebar.
- `assets/scripts/parse_keybinds.lua` — parses the user's hyprland keybinds (with auto-mocking lua) for the nexus/keybinds page.
- `assets/wrap_term_launch.sh` — terminal launcher wrapper; cats `~/.local/state/caelestia/sequences.txt`.
- `scripts/qml-lint-conventions.py` — convention linter (used by the repo's tooling).
- **`scripts/replace_footer.py` & `replace_xhr.py`** — one-off edits to `/home/dim/...` absolute paths (the upstream dev's machine); **not runnable, don't touch**.

## 8. Unfinished / fragile things

### 8.1 ⚠️ Installed shell is older than the repo (version skew) — full diff
`diff /etc/xdg/quickshell/caelestia/shell.qml /home/aman/midnight-shell/shell.qml` shows the running copy **lacks**:
- `PolkitModule` (polkit auth dialogs)
- `Shimeji` (desktop mascot)
- `BadAppleOverlay`, `DesktopLyricsOverlay`
- `BluetoothReconnect`
- Forced init of `DiscordRPC`, `GameMode`, `PipManager`, `SystemTray`
- `settings.watchFiles: true` (running copy has `false` → config hot-reload is **off** on this machine)

**Consequences:** the code you read in the repo may not match what runs; new features (and the `watchFiles` reload behaviour you'll rely on while learning) are absent. If you want a clean baseline, reinstall from the repo (or set `watchFiles: true` in the installed config).

### 8.2 `Visibilities.qml` is a compatibility stub
Most getters/setters just forward to `ShellState`. Old code (`Visibilities.getForActive().sidebar`) still works, but new code should use `ShellState`/`ScreenState` directly. Don't copy the legacy pattern.

### 8.3 "Cursed workaround" in `modules/bar/components/Power.qml`
The Power widget contains a commented `// cursed workaround` — a hack to get a UI behaviour right (upstream acknowledged). Read it, learn the *why*, don't replicate.

### 8.4 Scripts with hardcoded upstream paths
`scripts/replace_footer.py` and `replace_xhr.py` point at `/home/dim/...` and will fail (or write to the wrong place) here. Ignore them.

### 8.5 Copy-paste risk patterns (learn them before you use them)
- **`parent?.x`** (optional chaining) — used liberally; valid in QML's JS but errors if you assume plain `parent.x`.
- **`for (const x of array)`** — fine in QML JS.
- **`Quickshell.iconPath(icon, fallback)`** — required for theme-correct icons; a raw `source:` string breaks.
- **Font building** — `Tokens.font.body.builders.small.scale(1.1).build()`: the `.build()` call is easy to forget.
- **`ScriptModel`/`DelegateChooser` roles** — entries match on `role: "id"`; a typo silently renders nothing.
- **Per-screen Config** — a widget outside a `Config.screen` scope silently reads *global* values.

### 8.6 Misc
- `GitHubActivity`/`GithubStore` poll the network — no caching strategy visible.
- `modules/launcher` has several "states" (apps/actions/calc/scheme/variant/emoji/clipboard/windows) driven by `DelegateChooser` + `State` on a `ListView` — the single most instructive example of state-driven delegates in the repo.
- There is **no manifest file** (no `qtquickshell.json`) — Quickshell's `-c caelestia` flag auto-derives the `qs.*` import paths from the shell package's directory structure. This is why the repo tree itself is the mapping.

---

# Phase 2 — QML Curriculum (Reverse-Engineered From This Repo)

**How to use this.** You know Python/Bash/Lua and Hyprland config; you know *nothing* about QML. Every step below teaches exactly the concept the shell uses, points you at the exact repo file(s) that demonstrate it, and sets you a **standalone project** to build in one sitting. There are **no starter code/solutions** — only goal, constraints, and 2–3 hints. When you're done, run the **checkpoint** (self-test) before moving on. Order is by *dependency*, not difficulty.

Recommended workspace for your practice projects: `~/qml-lab/<project>/main.qml`, launched with `qs -p .` (run from inside the project dir). The repo's own entry is `qs -c caelestia -d`.

---

## PHASE A — Foundations

### Step 1 — QML item tree, properties, and the JS engine

**Concept:** A QML file declares a tree of *items*. Every object has *properties*; you bind a property to another with a JavaScript expression that re-evaluates whenever its inputs change. Handlers like `onClicked` are JS. Types come from *imports* (`import QtQuick` gives you `Item`, `Rectangle`, `Text`, etc.).

**Read in the repo:**
- `components/controls/IconButton.qml` — the whole file is a study in property aliasing (`property alias icon: label.text`) and property expressions (`font: type === IconButton.Filled ? ... : ...`).
- `modules/bar/components/Clock.qml` — how a widget binds text and visibility to service values.
- `components/misc/Ref.qml` — a tiny 10-line file showing `property int` + `Component.onDestruction` (lifetime).

**Standalone project:** A 150×150 `Rectangle` whose colour changes when you click it; show a `Text` in the corner whose text always shows the current colour name, and a second `Text` counting total clicks. Root must be a plain `Item`/`Rectangle`.

- Goal: master properties, bindings, and one mouse handler.
- Constraints: no `if/else` in JS for the count text (use string concatenation); the colour must be chosen by a *property binding*, not set imperatively.
- Hints: `import QtQuick`; `MouseArea` with `anchors.fill: parent`; a JS array of colours; `onClicked` + `onCountChanged`.

**Checkpoint:** Explain in one sentence why `text: count` updates automatically, but `onClicked: text = count` (setting text inside a handler) is a different mechanism. What is the difference between a *binding* and an *assignment*?

### Step 2 — Shell windows, screen anchoring, and layout

**Concept:** A real desktop shell draws on screen through **windows**. `PanelWindow` (Quickshell) is a layer-shell window; `StyledWindow` (repo) wraps it and sets the WlrLayershell namespace + `anchors`/`exclusiveZone`. Inside a window you compose `Row`/`Column`/`Grid` and `anchors`. The screen is exposed as `screen` (a `ShellScreen`) with `name`, `geometry`.

**Read in the repo:**
- `components/containers/StyledWindow.qml` — the wrapper every window uses.
- `modules/bar/BarWrapper.qml` — per-screen visibility, `exclusiveZone`, positioning (top/bottom/left/right).
- `modules/drawers/ContentWindow.qml` — instantiates BarWrapper inside a StyledWindow, per `screen`.
- `modules/bar/Bar.qml` — the `Row`/`GridLayout` layout and section widths.

**Standalone project:** A bar window along the bottom of the primary screen, `40px` tall, containing a `Row` with a `Rectangle` (dot), a `Text` (your name), and a `Text` (screen name from `screen.name`). `exclusiveZone` must make Hyprland reserve the strip. Add a small gap at the bottom-right where a second window (a 100×100 popup `Rectangle`) appears when you click the dot.

- Goal: put pixels on screen in a shell context; understand layers/anchors.
- Constraints: the bar must span the full width; the popup must be a *separate* `PanelWindow`; no hardcoded pixel sizes for the bar width.
- Hints: `Quickshell.ShellRoot`+`ShellScreen` are involved (`Root.screen`); `StyledWindow`/`PanelWindow` have `anchors` + `exclusiveZone`; use `screen.name`.

**Checkpoint:** What is `exclusiveZone`, and what happens if a window's `exclusiveZone` is 0? Why does BarWrapper need `screen.name` (hint: per-screen config)?

### Step 3 — Components & theming: StyledRect, StyledText, MaterialIcon, Colours, Tokens

**Concept:** The shell never styles raw `Rectangle`/`Text`. It uses **components** that pull colours/fonts from the design system: `StyledRect` (Colours.layer), `StyledText` (Tokens.font), `MaterialIcon` (Tokens.font.icon + fill/grade), `StateLayer` (ripple), and `Anim` (tokens-driven animation). Theming is *two singletons*: `Colours` (Material 3 palette) and `Tokens` (padding/spacing/rounding/sizes/fonts/durations).

**Read in the repo:**
- `components/controls/IconButton.qml` (already read in Step 1) — the full expression of the theme system.
- `components/controls/ButtonBase.qml` and `components/StateLayer.qml` — how `isToggle`, `checked`, ripple work.
- `components/StyledRect.qml`, `components/StyledText.qml`, `components/MaterialIcon.qml`.
- `services/Colours.qml` + `plugin/src/Caelestia/Config/appearanceconfig.hpp` + `tokens.hpp` — where the values come from.

**Standalone project:** A "theme card": a `StyledRect` 220×90 with a `MaterialIcon`, a `StyledText` title, and a `StateLayer` that is a toggle (tapping flips a boolean that switches the card's background between `Colours.palette.m3primary` and `m3surfaceContainer`, animating via `Anim`).

- Goal: stop using raw shapes/text; use the theme system by hand.
- Constraints: `font: Tokens.font.body.medium` and spacing from `Tokens.spacing.*`; the icon's `fill` must animate between 0 and 1; no hardcoded hex colours.
- Hints: import `qs.components`, `Caelestia.Config`; `Tokens.font.icon.medium` for the icon; `Colours.palette.m3primary` etc.

**Checkpoint:** What does `Colours.layer("...")` give you vs `Colours.palette.m3...`? Why is `font: Tokens.font.body.medium` different from `font.pixelSize: 14`?

---

## PHASE B — Layout & Data

### Step 4 — Lists & models: ScriptModel, Repeater, ListView, DelegateChooser

**Concept:** The bar doesn't write widgets one by one; it drives them from **models**. `ScriptModel` (Quickshell) turns a JS array into a QML model. `Repeater` renders N delegates; `ListView` adds scrolling/selection; `DelegateChooser` picks the delegate based on a *role* (`role: "id"`). Delegates are separate `Component`s, not inline.

**Read in the repo:**
- `modules/bar/Bar.qml` — `ScriptModel` + `DelegateChooser`/`EntryChooser` + `EntryWrapper` (`start/center/end` sections).
- `modules/bar/components/StatusIcons.qml` — `ScriptModel` over an array of status entry objects.
- `modules/launcher/AppList.qml` — the masterclass: `ListView` + `ScriptModel`, `state`-switched `delegate`, `add/remove/move` transitions, `preferredHighlightBegin/End`.
- `modules/launcher/items/AppItem.qml` — a delegate receiving `modelData` (`required property DesktopEntry modelData`).

**Standalone project:** A vertical `ListView` of 20 numbers where each row is a `StyledText`. Above it a `Row` of 3 `IconButton`s ("All / Even / Odd") that switch the model (via a different `ScriptModel` binding) to show all/even/odd. Clicking a row toggles a favourite star at its right.

- Goal: models, roles, delegates, and `modelData`.
- Constraints: the filter must be one expression producing an array; the delegate must be a separate `Component`; no `Repeater` (use `ListView`).
- Hints: `ScriptModel { values: myJsArray }`; in the delegate use `required property int modelData`; `ListView` has `model`, `delegate`, `currentIndex`.

**Checkpoint:** What is the difference between `Repeater` and `ListView` (delegates are lazily instantiated in one of them)? What does `DelegateChooser`'s `role` refer to, and what does `EntryWrapper` do for a bar entry?

### Step 5 — Wiring a new bar entry from config end-to-end

**Concept:** Real bar entries come from `Config.bar.entries.<section>.values` — a `ConfigList` of `{id, ...}`. Adding a widget = adding an entry id to that list (defaults live in C++: `plugin/src/Caelestia/Config/barconfig.hpp`), then making the bar know how to instantiate it (`DelegateChooser` mapping in `Bar.qml`). This is the "make your own taskbar" superpower.

**Read in the repo:**
- `plugin/src/Caelestia/Config/barconfig.hpp` — the entry defaults (`start/center/end`), plus `BarClock`, `BarWorkspaces` (`specialWorkspaceIcons`, `windowIcons`), `BarScrollActions`.
- `plugin/src/Caelestia/Config/configlist.hpp` — how `ConfigList` exposes `values`, `itemAt`, `loaded`.
- `modules/bar/Bar.qml` — the `DelegateChooser`/`EntryChooser` `role: "id"` mapping and `EntryWrapper`.
- `/home/aman/.config/caelestia/shell.json` — your live config (`bar.showOnHover`, `bar.clock.background`, ...).

**Standalone project:** Using the installed shell, edit `~/.config/caelestia/shell.json` to *reorder* the bar entries (move `clock` from `end` to `start`) and change the `bar.clock.showDate` value. Observe live. Then (as a stretch) create a **copy** of the Clock widget in the repo as a new component and wire it as a new entry id.

- Goal: understand the entry pipeline without touching C++.
- Constraints: `watchFiles: true` must be set (repo default; the installed copy has it off — enable it first, see Phase 1 §8); config edits only.
- Hints: `Config.bar.entries.end` and `.start` are arrays of `{"id": "..."}`; `ScriptModel { values: Config.bar.entries.start.values }`; each entry needs a matching case in the `DelegateChooser`.

**Checkpoint:** If you add `"id": "myWidget"` to `start` but `DelegateChooser` has no branch for it, what renders? What is the *single line of config* that turns on config hot-reload?

---

## PHASE C — State & Services

### Step 6 — Service singletons & the Hyprland API

**Concept:** QML singletons (`pragma Singleton`) are global objects shared by every window. The repo wraps system APIs in `services/*.qml`; the most important is `Hypr.qml` (workspaces, toplevels, keyboard). A widget binds to service properties and updates automatically because Quickshell services emit change notifications.

**Read in the repo:**
- `services/Hypr.qml` — the wrapper: `Hypr.workspaces`, `Hypr.activeWsId`, `Hypr.activeToplevel`, `Hypr.monitorFor(screen)`, `Hypr.dispatch(...)`, caps/num lock.
- `services/ShellState.qml` + `Visibilities.qml` — per-screen UI state.
- `services/Time.qml` — trivially small; a perfect first read.
- `modules/bar/components/workspaces/Workspaces.qml` + `Workspace.qml` — consumers of `Hypr.*`.

**Standalone project:** A widget (in a `StyledWindow`) showing a row of dots, one per workspace of the current monitor; the active workspace's dot is filled and sized larger; clicking a dot dispatches `hyprctl` switch-to-workspace via `Hypr.dispatch`. Auto-updates when the workspace changes.

- Goal: consume a live system service through bindings.
- Constraints: no polling/timers; dot state must be pure bindings to `Hypr.workspaces`/`Hypr.activeWsId`; per-screen (use `screen.name`).
- Hints: `Hypr.workspaces` is a list with `.isActive`/`.screen`/`.id`; `Hypr.dispatch("workspace", id)`; iterate with a `Repeater`.

**Checkpoint:** What happens to your widget's bindings if the user switches workspace *without* you restarting? Why do singletons solve cross-window sharing that instance properties can't?

### Step 7 — Interactivity, popouts & IPC

**Concept:** Click targets are `StateLayer`/`MouseArea`; popouts are *separate windows* controlled by shared state (`PopoutState`); global keybinds arrive as events via `GlobalShortcut`/`CustomShortcut` (`appid: "caelestia"`), and external tools can poke the shell over `IpcHandler` (`qs -c caelestia ipc call ...`). Tray menus use `QsMenuOpener`.

**Read in the repo:**
- `components/misc/CustomShortcut.qml` — wraps `GlobalShortcut`.
- `modules/Shortcuts.qml` — the registry; see how `caelestia:launcher` etc. map to actions.
- `modules/bar/popouts/PopoutState.qml`, `Wrapper.qml`, `Content.qml` — the popout state machine.
- `modules/bar/components/TrayItem.qml` — `QsMenuOpener` for tray right-click menus.
- `plugin/src/Caelestia/IpcHandler` (grep `ipc`) + `modules/sidebar` toggles (e.g. `Visibilities.getForActive().sidebar`) — the toggle path.

**Standalone project:** A bar entry (a `MaterialIcon` button) that opens a popout window. The popout shows 3 `IconButton`s; clicking one closes the popout *and* toggles a boolean in a shared `PopoutState`-like object. Register a `CustomShortcut` (e.g. `SUPER+O`) that toggles the popout. Then trigger it externally with `qs -c caelestia ipc call <yourHandler>.<method>`.

- Goal: click → state → separate window; keybinds; IPC.
- Constraints: the popout must be a separate `StyledWindow`; open/close via a *shared* object both windows bind to; the shortcut must work from anywhere.
- Hints: `QsMenuOpener` only for menus; use `anchors`/`screen` for popout placement; `CustomShortcut` sets `appid` and `action`.

**Checkpoint:** How does a popout "know" which entry opened it? Why must the popout state live outside the popout window itself?

### Step 8 — The C++ config engine: Config attached, GlobalConfig, Tokens, hot reload

**Concept:** The shell's config is a C++ tree (`CONFIG_PROPERTY` macro → Q_PROPERTY + notify). `GlobalConfig` is the singleton root; `Tokens` is the derived design-system singleton; `Config` is the **attached** property that gives per-screen overrides (`Config.screen: screen.name`) and propagates to children. Editing `shell.json` triggers `QFileSystemWatcher` → 50 ms debounce → `ConfigObject` property updates → QML bindings re-run.

**Read in the repo (C++, skim, don't implement):**
- `plugin/src/Caelestia/Config/config.hpp` — `GlobalConfig` sub-objects (`bar`, `appearance`, `services`, `launcher`, ...).
- `plugin/src/Caelestia/Config/configattached.hpp` — the attached `Config` property and `sourceChanged`.
- `plugin/src/Caelestia/Config/configobject.hpp` — `CONFIG_PROPERTY` macro + change detection.
- `plugin/src/Caelestia/Config/rootconfig.cpp` — the watcher + 50 ms debounce reload.
- `plugin/src/Caelestia/Config/barconfig.hpp` — a concrete config object with defaults (you saw it in Step 5).

**Standalone project:** Take your Step 7 popout and add a *config-driven* property: a boolean `myWidget.fancy` in a copied config header... **(don't modify the repo — instead)** simulate per-screen config in pure QML: create an attached-like object (`QtObject` with `sourceChanged`-style notify) and make the popout's colour depend on it; then flip it from a `Connections` on a `Timer` to confirm the binding chain re-evaluates.

- Goal: understand *why* widgets read config through attached properties rather than globals, and how a JSON edit reaches a binding.
- Constraints: read-only on the repo; you may write a throwaway `main.qml` lab file; the colour must update live without a restart.
- Hints: QML attached objects are just `QQuickAttachedPropertyPropagator`; `QtObject { property bool fancy: false }` + `Connections`; `Config.screen` on a root makes children read per-screen.

**Checkpoint:** Explain the full chain from a JSON edit to a widget repaint (file → watcher → debounce → property notify → binding). Why is 50 ms debounce important (hint: your editor saves once, but writes can be split)?

---

## PHASE D — Milestone

### Step 9 — MILESTONE: build one real widget for the taskbar

You now know everything needed to build a **performance/status chip** — the recommended first real widget. It shows CPU + RAM usage with a small sparkline and a coloured fill that shifts with load.

**Read in the repo (the tools you'll lean on):**
- `Caelestia.Services` — `Cpu`, `Memory`, `UsageFmt` (exists: `plugin/src/Caelestia/Services/`), plus `SparklineItem` / `CircularBuffer` in `Caelestia.Internal` (the shell's own performance widgets use these).
- `modules/bar/components/status/LockStatus.qml` and `BatteryStatus.qml` — the *pattern* for a status entry (how they read their service and report `collapsed`).
- `modules/bar/components/StatusIcons.qml` — how entries are aggregated.
- `modules/bar/components/ActiveWindow.qml` — sizing a bar widget against section widths.
- `plugin/src/Caelestia/Config/barconfig.hpp` — where you'd register a new entry default.

**Project goal:** Add a new taskbar widget "perf chip" that:
1. Polls/draws CPU% and RAM% (via `Cpu`/`Memory`/`UsageFmt` — bindings, not timers where possible).
2. Shows a tiny sparkline of recent CPU samples (`CircularBuffer` + `SparklineItem` or a `Repeater` of rects).
3. Colours its fill by threshold (e.g. green < 50%, orange < 80%, red above) using `Colours.palette.m3...`.
4. Is *added to the actual bar* by registering it as an entry (default or via `shell.json` `bar.entries.*`).
5. Has a popout on click showing larger readouts (reuse Step 7's pattern).

**Constraints:** It must be a status-style entry (works in `StatusIcons`), must read from the real `Caelestia.Services`, must be theme-correct (no hardcoded colours), must animate (use `Anim`), and must survive config hot-reload.

**Hints:** start from `BatteryStatus.qml` as a template and swap the service; `UsageFmt` may already format the text for you; check how `BatteryStatus` reports `collapsed()` so your chip hides itself when space is tight.

**Why this widget (vs alternatives):**
- *Performance chip* (chosen): self-contained — the services already exist in the plugin, so you write ~100 lines of QML and zero C++; it exercises bindings, thresholds, sparkline data, and popouts — every concept from Steps 1–8.
- *Keyboard layout indicator*: also small, but needs `HyprKeyboard`/`HyprDevices` device-watching logic and keybind-aware popout — more edge cases for a first widget.
- *Weather chip*: simple, but depends on the external `Weather` service/provider and needs network-state handling; worse "success feedback" for a first build.

**Checkpoint:** Your widget must render on all three bar sections when moved between them via config, without code changes.

### Step 10 — Polish: State/Transitions, Anim, Behavior, and debugging

**Concept:** Real polish comes from the shell's animation grammar. `State` + `PropertyChanges` describe modes; `Transition` describes the tween between modes; `Anim` (tokens-driven `NumberAnimation`) is the tween; `Behavior on` animates a property every time it changes. Debugging tools: `qmllint` (run the repo's `scripts/qml-lint-conventions.py`), the `watchFiles: true` live-reload, and printing from JS.

**Read in the repo:**
- `modules/launcher/AppList.qml` — the exhaustive `states`/`transitions`/`add`/`remove`/`move` set (re-read with fresh eyes).
- `modules/bar/popouts/Wrapper.qml` — animating between content/winfo/nexus views.
- `components/controls/ButtonBase.qml` / `StateLayer.qml` — ripple + press states.
- `components/effects/ColouredIcon.qml` — `Behavior`/`Anim` on icon state.

**Standalone project:** Take your Step 9 perf chip and add: a `State` machine for "compact / expanded" (popout view), a `Behavior on color` when crossing thresholds, a fade+slide `Transition` on popout open/close, and a subtle idle animation. Then run the repo's lint script on your QML and fix every finding.

- Goal: make the widget feel native to this shell.
- Constraints: every animation duration/easing from `Tokens.anim.*`; no magic numbers for timings; lint must pass clean.
- Hints: `Anim { type: Anim.DefaultEffects }`; `Behavior on x { Anim {} }`; `Transition { Anim { property: "y" } }`.

**Checkpoint:** Explain why `Behavior` on a *bound* property vs a `Transition` on a `State` change behave differently, and which one you used for threshold colour shifts.

---

## Milestone recap
After Steps 1–10 you will have: read the entire relevant surface of this repo, rebuilt its core patterns from scratch, and shipped a real, configurable, animated, lint-clean taskbar widget — the same "add an entry" workflow the shell itself uses for Clock/Workspaces/StatusIcons.

---

*Written for the midnight-shell fork (running shell: installed copy at `/etc/xdg/quickshell/caelestia`, which is older than the repo — see Phase 1 §8).*

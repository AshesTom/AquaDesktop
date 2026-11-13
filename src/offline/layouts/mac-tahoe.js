// MacTahoe Liquid KDE — macOS Tahoe-style layout
// Top menu bar (flush) + bottom dock (floating, large icons)
// Applied per-screen so multi-monitor setups get a matching bar + dock on
// every display, not just the primary one.

// ── remove existing panels ──────────────────────
var old = panels();
var launcherPresets = {};
var dockPresetRevisions = {};
var dockPresetCategories = {};
var dockIconChoices = {};
for (var p = 0; p < old.length; p++) {
    var widgets = old[p].widgetIds;
    for (var w = 0; w < widgets.length; w++) {
        var widget = old[p].widgetById(widgets[w]);
        if (widget && widget.type === "org.kde.mac.tahoe.liquid.icontasks") {
            widget.currentConfigGroup = ["General"];
            dockIconChoices[old[p].screen] = widget.readConfig("macOSDockIcons", false);
            dockPresetRevisions[old[p].screen] = Number(widget.readConfig("dockPresetRevision", 0));
            dockPresetCategories[old[p].screen] = widget.readConfig("dockPresetCategories", []);
        }
        if (widget && widget.type === "org.kde.mac-tahoe-liquid-kde.launcher") {
            widget.currentConfigGroup = ["General"];
            var preset = Number(widget.readConfig("launcherPreset", 0));
            if (preset === 1 || preset === 2) {
                launcherPresets[old[p].screen] = preset;
            }
        }
    }
}
for (var i = 0; i < old.length; i++) {
    old[i].remove();
}

for (var screen = 0; screen < screenCount; screen++) {
    // ── top menu bar ────────────────────────────────
    // Top bar, flush panel with applets-only floating. floatingApplets=1 is
    // reasserted via plasmashellrc after layout apply and every theme switch.
    if (typeof mttkdeTopPanel === "undefined" || mttkdeTopPanel) {
    var bar = new Panel("org.kde.panel");
    bar.location = "top";
    bar.screen = screen;
    bar.lengthMode = "fill";
    bar.floating = false;
    bar.hiding = "none";
    bar.height = 32;

    // Panel Colorizer hides the continuous native panel background. Its only
    // panel layer is Tahoe's dark veil, a gradient fading to nothing at the
    // bar's bottom edge; do not add widget color layers or a solid panel
    // color: with applets-only floating they render as a full-width gray
    // strip plus dark blocks behind individual applets.
    var colorizer = bar.addWidget("luisbocanegra.panel.colorizer");
    if (colorizer) {
        colorizer.currentConfigGroup = ["General"];
        colorizer.writeConfig("globalSettings", JSON.stringify({
            "nativePanel": {
                "background": { "enabled": false, "opacity": 0, "shadow": false },
                "floatingDialogs": true
            },
            // Tahoe's dark veil behind the menu bar (theme_switch.TOP_BAR_SCRIM).
            "panel": { "normal": {"enabled": true, "backgroundColor": {"enabled": true, "sourceType": 5, "alpha": 1, "gradient": {"orientation": 1, "stops": [{"color": "#33000000", "position": 0}, {"color": "#2b000000", "position": 0.45}, {"color": "#12000000", "position": 0.8}, {"color": "#00000000", "position": 1}]}}} },
            // White menu bar text and icons (theme_switch.TOP_BAR_FOREGROUND).
            "widgets": { "normal": { "enabled": true, "backgroundColor": { "enabled": false }, "foregroundColor": { "enabled": true, "sourceType": 0, "alpha": 1, "custom": "#ffffff" } } },
            "trayWidgets": { "normal": { "enabled": true, "backgroundColor": { "enabled": false }, "foregroundColor": { "enabled": true, "sourceType": 0, "alpha": 1, "custom": "#ffffff" } } }
        }));
        colorizer.currentConfigGroup = ["Configuration"];
        colorizer.writeConfig("hideWidget", "true");
    }

    bar.addWidget("org.kde.mac.tahoe.liquid.globalmenu");
    bar.addWidget("org.kde.plasma.panelspacer");

    // Now Playing: the macOS play button, right before the tray icons; it
    // hides itself while nothing plays.
    bar.addWidget("org.kde.mac-tahoe-liquid-kde.nowplaying");

    // system tray — macOS style: its applets stay hidden for their shortcuts
    // and notifications, the menu bar extras below stand in for them, as
    // macOS keeps the rest in Control Center. Our tray has no overflow
    // arrow (its other items open as a macOS menu from the Control Center);
    // Plasma's when the fork is not installed.
    var tray = bar.addWidget(knownWidgetTypes.indexOf("org.kde.mac.tahoe.liquid.systemtray") >= 0
        ? "org.kde.mac.tahoe.liquid.systemtray" : "org.kde.plasma.systemtray");
    tray.currentConfigGroup = ["General"];

    // shown = always visible, hidden = inside arrow, auto = KDE decides
    tray.writeConfig("shownItems", "");
    tray.writeConfig("hiddenItems", "org.kde.plasma.battery,org.kde.plasma.networkmanagement,org.kde.plasma.clipboard,org.kde.plasma.devicenotifier,org.kde.plasma.manage-inputmethod,org.kde.plasma.mediacontroller,org.kde.mac.tahoe.liquid.notifications,org.kde.plasma.keyboardindicator,org.kde.plasma.weather,org.kde.kscreen,org.kde.plasma.keyboardlayout,org.kde.plasma.printmanager,org.kde.plasma.cameraindicator,org.kde.plasma.vault,org.kde.kdeconnect,org.kde.plasma.bluetooth,org.kde.plasma.brightness,org.kde.plasma.volume,Arch-Update,Cachy-Update,org.kde.discovernotifier,chrome_status_icon_1,discord,plasmashell_microphone,steam,spotify,telegram,slack");
    // 22 px icons on a 38 px pitch, like the macOS menu bar extras.
    tray.writeConfig("iconSpacing", 4);
    // Plasma's notifications applet gives way to the macOS-banner fork;
    // knownItems keeps the stock applet from being re-added on its own.
    tray.writeConfig("extraItems", "org.kde.kdeconnect,org.kde.plasma.bluetooth,org.kde.plasma.cameraindicator,org.kde.plasma.clipboard,org.kde.plasma.devicenotifier,org.kde.plasma.manage-inputmethod,org.kde.plasma.mediacontroller,org.kde.mac.tahoe.liquid.notifications,org.kde.plasma.keyboardindicator,org.kde.plasma.weather,org.kde.kscreen,org.kde.plasma.battery,org.kde.plasma.brightness,org.kde.plasma.keyboardlayout,org.kde.plasma.networkmanagement,org.kde.plasma.volume");
    tray.writeConfig("knownItems", "org.kde.kdeconnect,org.kde.plasma.bluetooth,org.kde.plasma.cameraindicator,org.kde.plasma.clipboard,org.kde.plasma.devicenotifier,org.kde.plasma.manage-inputmethod,org.kde.plasma.mediacontroller,org.kde.mac.tahoe.liquid.notifications,org.kde.plasma.keyboardindicator,org.kde.plasma.weather,org.kde.kscreen,org.kde.plasma.battery,org.kde.plasma.brightness,org.kde.plasma.keyboardlayout,org.kde.plasma.networkmanagement,org.kde.plasma.volume,org.kde.plasma.notifications");

    // Input menu: the keyboard layout's letters in a white box, only
    // while more than one layout is set up (macOS shows it then).
    bar.addWidget("org.kde.mac-tahoe-liquid-kde.keyboard");

    // Sound and Battery: the macOS menu bar extras ("72%" beside the
    // battery glyph), in place of the tray's applets.
    bar.addWidget("org.kde.mac-tahoe-liquid-kde.volume");
    bar.addWidget("org.kde.mac-tahoe-liquid-kde.battery");

    // Wi-Fi: the macOS Wi-Fi menu (plasma-nm underneath).
    bar.addWidget("org.kde.mac-tahoe-liquid-kde.wifi");

    // Spotlight: magnifier that opens KRunner, between the extras and the clock.
    var spotlight = bar.addWidget("org.kde.mac-tahoe-liquid-kde.spotlight");
    // Meta+Space opens it, as Cmd+Space does on macOS (one bar only: a
    // global shortcut belongs to one widget).
    if (spotlight && bar.screen === 0) {
        spotlight.globalShortcut = "Meta+Space";
    }

    // Control Center: the two-toggle glyph between Spotlight and the clock.
    bar.addWidget("org.kde.mac-tahoe-liquid-kde.controlcenter");

    // macOS-style clock: locale-ordered "Mon 5 Oct  14:27"; the stock
    // Digital Clock when ours is not installed.
    var clock = bar.addWidget("org.kde.mac-tahoe-liquid-kde.clock");
    if (!clock) {
        clock = bar.addWidget("org.kde.plasma.digitalclock");
        clock.currentConfigGroup = ["Appearance"];
        clock.writeConfig("autoFontAndSize", "false");
        clock.writeConfig("fontFamily", "SF Pro Text");
        clock.writeConfig("fontSize", 10);
        clock.writeConfig("fontWeight", 500);
        clock.writeConfig("showDate", "true");
        clock.writeConfig("use24hFormat", 1);
        clock.writeConfig("showSeconds", 0);
        clock.writeConfig("dateDisplayFormat", "BesideTime");
        clock.writeConfig("dateFormat", "custom");
        clock.writeConfig("customDateFormat", "ddd d ' | '");
    }

    // ── bottom dock ─────────────────────────────────
    // floating, centered, large icons like macOS
    }
    if (typeof mttkdeDock === "undefined" || mttkdeDock) {
    var dock = new Panel("org.kde.panel");
    dock.location = "bottom";
    dock.screen = screen;
    dock.alignment = "center";
    dock.lengthMode = "fit";
    dock.floating = true;
    // Auto-hide avoids the stuck-visible dodge behavior reported in issue #87.
    dock.hiding = "autohide";
    dock.height = 68;
    // opacity is set to translucent via plasmashellrc after layout apply
    // (JS scripting API does not expose panelOpacity)

    var launcher = dock.addWidget("org.kde.mac-tahoe-liquid-kde.launcher");
    launcher.currentConfigGroup = ["General"];
    launcher.writeConfig("icon", "view-app-grid");
    // macOS keeps Finder first: the "Apps" launcher pinned right after it
    // opens this applet's grid, so its own Dock button is hidden.
    launcher.writeConfig("hiddenInDock", "true");
    // The installer selects the new edition when migrating between editions.
    if (typeof mttkdeLauncherPreset !== "undefined"
            && (mttkdeLauncherPreset === 1 || mttkdeLauncherPreset === 2)) {
        launcher.writeConfig("launcherPreset", mttkdeLauncherPreset);
    } else if (launcherPresets[dock.screen] !== undefined) {
        launcher.writeConfig("launcherPreset", launcherPresets[dock.screen]);
    }

    var tasks = dock.addWidget("org.kde.mac.tahoe.liquid.icontasks");
    tasks.currentConfigGroup = ["General"];
    // Base Dock: use the first installed desktop ID for each application.
    // Existing user pins are restored by layout.py after this layout is created.
    var dockApplications = [
        ["org.kde.dolphin.desktop", "org.gnome.Nautilus.desktop", "thunar.desktop", "pcmanfm-qt.desktop"],
        ["firefox.desktop", "firefox-esr.desktop", "org.mozilla.firefox.desktop", "firefox_firefox.desktop", "chromium.desktop", "chromium-browser.desktop", "google-chrome.desktop", "com.google.Chrome.desktop", "brave-browser.desktop", "com.brave.Browser.desktop", "org.kde.falkon.desktop"],
        ["thunderbird.desktop", "org.mozilla.Thunderbird.desktop", "thunderbird_thunderbird.desktop", "org.kde.kmail2.desktop", "org.gnome.Evolution.desktop", "org.gnome.Geary.desktop"],
        ["org.kde.merkuro.calendar.desktop", "org.kde.korganizer.desktop", "org.gnome.Calendar.desktop"],
        ["org.kde.marknote.desktop", "org.kde.knotes.desktop", "org.gnome.Gnote.desktop", "org.gnome.Notes.desktop", "com.vixalien.sticky.desktop"],
        ["org.kde.gwenview.desktop", "org.gnome.Loupe.desktop", "org.gnome.eog.desktop", "org.xfce.ristretto.desktop", "ristretto.desktop", "nomacs.desktop"],
        ["org.kde.elisa.desktop", "org.gnome.Rhythmbox3.desktop", "org.gnome.Music.desktop", "io.bassi.Amberol.desktop", "org.strawberrymusic.strawberry.desktop", "strawberry.desktop", "clementine.desktop", "audacious.desktop"],
        ["org.kde.haruna.desktop", "org.gnome.Showtime.desktop", "vlc.desktop", "org.videolan.VLC.desktop", "org.gnome.Totem.desktop", "io.github.celluloid_player.Celluloid.desktop", "mpv.desktop", "smplayer.desktop"],
        ["org.kde.discover.desktop", "org.gnome.Software.desktop"],
        ["systemsettings.desktop"]
    ];
    var dockCategories = ["files", "browser", "mail", "calendar", "notes", "photos", "music", "video", "store", "settings"];
    var dockLaunchers = [];
    var resolvedDockCategories = [];
    for (var app = 0; app < dockApplications.length; app++) {
        for (var candidate = 0; candidate < dockApplications[app].length; candidate++) {
            var desktopId = dockApplications[app][candidate];
            if (applicationExists(desktopId)) {
                dockLaunchers.push("applications:" + desktopId);
                resolvedDockCategories.push(dockCategories[app]);
                break;
            }
        }
    }
    // The "Apps" launcher (it opens the Launcher's grid) right after the
    // file manager, as macOS keeps Finder first.
    dockLaunchers.splice(resolvedDockCategories[0] === "files" ? 1 : 0, 0,
        "applications:org.kde.mac-tahoe-liquid-kde.apps.desktop");
    tasks.writeConfig("launchers", dockLaunchers);
    tasks.writeConfig("macOSDockIcons", dockIconChoices[dock.screen] || false);
    tasks.writeConfig("dockPresetRevision", dockPresetRevisions[dock.screen] || 0);
    tasks.writeConfig("dockPresetCategories", dockPresetCategories[dock.screen] || []);

    // The thin divider macOS draws between the apps and the stacks.
    if (!dock.addWidget("org.kde.mac-tahoe-liquid-kde.separator")) {
        dock.addWidget("org.kde.plasma.marginsseparator");
    }
    // macOS Downloads stack.
    dock.addWidget("org.kde.mac-tahoe-liquid-kde.downloads");
    // Minimized windows sit between the stacks and the Trash, one
    // thumbnail per window. The section collapses when nothing is minimized.
    var minimized = dock.addWidget("org.kde.mac.tahoe.liquid.icontasks");
    minimized.currentConfigGroup = ["General"];
    minimized.writeConfig("showOnlyMinimized", "true");
    minimized.writeConfig("groupingStrategy", "0");
    minimized.writeConfig("launchers", "");
    // The Trash must stay last: it widens the glass while the Dock magnifies.
    dock.addWidget("org.kde.mac-tahoe-liquid-kde.trashcan");
}
}

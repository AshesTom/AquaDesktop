// MacTahoe Liquid KDE — macOS Tahoe-style layout
// Top menu bar (flush) + bottom dock (floating, large icons)

// ── remove existing panels ──────────────────────
var old = panels();
var launcherPresets = {};
for (var p = 0; p < old.length; p++) {
    var widgets = old[p].widgetIds;
    for (var w = 0; w < widgets.length; w++) {
        var widget = old[p].widgetById(widgets[w]);
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

// ── top menu bar ────────────────────────────────
// top bar, flush panel with applets-only floating
// (floatingApplets=1 is set via plasmashellrc after layout apply)
var bar = new Panel("org.kde.panel");
bar.location = "top";
bar.screen = 0;
bar.lengthMode = "fill";
bar.floating = false;
bar.hiding = "none";
bar.height = 30;

// panel colorizer: transparent background
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

// system tray — macOS style: only battery (laptops) and Wi-Fi stay in the
// menu bar; Bluetooth, sound and brightness sit behind the expander, the
// way macOS keeps them in Control Center. Colour update notifiers hide too.
// Now Playing: the macOS play button, right before the tray icons; it
// hides itself while nothing plays.
bar.addWidget("org.kde.mac-tahoe-liquid-kde.nowplaying");

// Our tray (no overflow arrow, its other items in a macOS menu opened
// from the Control Center); Plasma's when the fork is not installed.
var tray = bar.addWidget(knownWidgetTypes.indexOf("org.kde.mac.tahoe.liquid.systemtray") >= 0
    ? "org.kde.mac.tahoe.liquid.systemtray" : "org.kde.plasma.systemtray");
tray.currentConfigGroup = ["General"];

// shown = always visible, hidden = inside arrow, auto = KDE decides
tray.writeConfig("shownItems", "");
tray.writeConfig("hiddenItems", "org.kde.plasma.battery,org.kde.plasma.networkmanagement,org.kde.plasma.clipboard,org.kde.plasma.devicenotifier,org.kde.plasma.manage-inputmethod,org.kde.plasma.mediacontroller,org.kde.mac.tahoe.liquid.notifications,org.kde.plasma.keyboardindicator,org.kde.plasma.weather,org.kde.kscreen,org.kde.plasma.keyboardlayout,org.kde.plasma.printmanager,org.kde.plasma.cameraindicator,org.kde.plasma.vault,org.kde.kdeconnect,org.kde.plasma.bluetooth,org.kde.plasma.brightness,org.kde.plasma.volume,Arch-Update,Cachy-Update,org.kde.discovernotifier,chrome_status_icon_1,discord,plasmashell_microphone,steam,spotify,telegram,slack");
// 22 px icons on a 38 px pitch, like the macOS menu bar extras.
tray.writeConfig("iconSpacing", 4);
// Plasma's notifications applet gives way to the macOS-banner fork;
// knownItems keeps the stock applet from
// being re-added on its own.
tray.writeConfig("extraItems", "org.kde.kdeconnect,org.kde.plasma.bluetooth,org.kde.plasma.cameraindicator,org.kde.plasma.clipboard,org.kde.plasma.devicenotifier,org.kde.plasma.manage-inputmethod,org.kde.plasma.mediacontroller,org.kde.mac.tahoe.liquid.notifications,org.kde.plasma.keyboardindicator,org.kde.plasma.weather,org.kde.kscreen,org.kde.plasma.battery,org.kde.plasma.brightness,org.kde.plasma.keyboardlayout,org.kde.plasma.networkmanagement,org.kde.plasma.volume");
tray.writeConfig("knownItems", "org.kde.kdeconnect,org.kde.plasma.bluetooth,org.kde.plasma.cameraindicator,org.kde.plasma.clipboard,org.kde.plasma.devicenotifier,org.kde.plasma.manage-inputmethod,org.kde.plasma.mediacontroller,org.kde.mac.tahoe.liquid.notifications,org.kde.plasma.keyboardindicator,org.kde.plasma.weather,org.kde.kscreen,org.kde.plasma.battery,org.kde.plasma.brightness,org.kde.plasma.keyboardlayout,org.kde.plasma.networkmanagement,org.kde.plasma.volume,org.kde.plasma.notifications");

// Wi-Fi: the macOS Wi-Fi menu (plasma-nm underneath), in place of
// the network applet the tray keeps hidden for its notifications.
// Input menu: the keyboard layout, shown with more than one layout.
bar.addWidget("org.kde.mac-tahoe-liquid-kde.keyboard");
// Sound and Battery: the macOS extras, in place of the tray's applets.
bar.addWidget("org.kde.mac-tahoe-liquid-kde.volume");
bar.addWidget("org.kde.mac-tahoe-liquid-kde.battery");
bar.addWidget("org.kde.mac-tahoe-liquid-kde.wifi");

// Spotlight: magnifier that opens KRunner, between the extras and the clock.
var spotlight = bar.addWidget("org.kde.mac-tahoe-liquid-kde.spotlight");
// Meta+Space opens it, as Cmd+Space does on macOS.
if (spotlight) {
    spotlight.globalShortcut = "Meta+Space";
}

// Control Center: the two-toggle glyph between Spotlight and the clock.
bar.addWidget("org.kde.mac-tahoe-liquid-kde.controlcenter");

// macOS-style clock: system font at its normal size, locale-ordered
// "Mon 5 Oct  14:27". The stock Digital Clock sizes its text from the
// panel height and the screen's physical DPI instead.
var clock = bar.addWidget("org.kde.mac-tahoe-liquid-kde.clock");
if (!clock) {
    clock = bar.addWidget("org.kde.plasma.digitalclock");
    clock.currentConfigGroup = ["Appearance"];
    clock.writeConfig("showDate", "true");
    clock.writeConfig("dateDisplayFormat", "BesideTime");
}

// ── bottom dock ─────────────────────────────────
// floating, centered, large icons like macOS
var dock = new Panel("org.kde.panel");
dock.location = "bottom";
dock.screen = 0;
dock.alignment = "center";
dock.lengthMode = "fit";
dock.floating = true;
// Auto-hide avoids the stuck-visible dodge behavior reported in issue #87.
dock.hiding = "autohide";
// A 71 px macOS Tahoe Dock: the floating background is drawn 1 px inside
// the panel thickness. Icon size and spacing are derived from it by the
// Dock widgets (see the task manager's LayoutMetrics.js).
dock.height = 64;
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
tasks.writeConfig("launchers", "preferred://filemanager,applications:org.kde.mac-tahoe-liquid-kde.apps.desktop,preferred://terminal,preferred://browser,applications:systemsettings.desktop,applications:steam.desktop");

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

// SPDX-License-Identifier: GPL-3.0-or-later
#include "launchersearchpopup.h"

#include <Plasma/Theme>
#include <PlasmaQuick/PlasmaShellWaylandIntegration>
#include <KWindowSystem>
#include <KX11Extras>
#include <QStandardPaths>

LauncherSearchPopup::LauncherSearchPopup()
    : PlasmaQuick::PopupPlasmaWindow(QStandardPaths::locate(QStandardPaths::GenericDataLocation,
                                       QStringLiteral("plasma/desktoptheme/") + Plasma::Theme().themeName()
                                       + QStringLiteral("/dialogs/launcher-search.svgz")).isEmpty()
                                       ? QStringLiteral("dialogs/background")
                                       : QStringLiteral("dialogs/launcher-search"))
{
    setFlags(flags() | Qt::Dialog);
    // Match Plasma's applet role so window effects preserve the SVG capsule.
    if (KWindowSystem::isPlatformX11()) {
        KX11Extras::setType(winId(), NET::AppletPopup);
    } else if (KWindowSystem::isPlatformWayland()) {
        PlasmaShellWaylandIntegration::get(this)->setRole(QtWayland::org_kde_plasma_surface::role_appletpopup);
    }
    connect(this, &QWindow::activeChanged, this, &LauncherSearchPopup::focusChanged);
}

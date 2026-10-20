// SPDX-License-Identifier: GPL-3.0-or-later
#include "launchersearchpopup.h"

#include <Plasma/Theme>
#include <PlasmaQuick/PlasmaShellWaylandIntegration>
#include <KWindowSystem>
#include <KX11Extras>
#include <QEvent>
#include <QScreen>
#include <QStandardPaths>
#include <algorithm>

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
    connect(this, &QWindow::transientParentChanged, this, [this](QWindow *parent) {
        if (m_anchorWindow) {
            m_anchorWindow->removeEventFilter(this);
        }
        m_anchorWindow = parent;
        if (parent && KWindowSystem::isPlatformX11()) {
            parent->installEventFilter(this);
        }
    });
}

bool LauncherSearchPopup::eventFilter(QObject *watched, QEvent *event)
{
    if (watched == m_anchorWindow && isVisible()
        && (event->type() == QEvent::Move || event->type() == QEvent::Resize)) {
        requestUpdate();
    }
    return PlasmaQuick::PopupPlasmaWindow::eventFilter(watched, event);
}

bool LauncherSearchPopup::event(QEvent *event)
{
    const bool handled = PlasmaQuick::PopupPlasmaWindow::event(event);
    // Plasma 6.8 only positions PopupPlasmaWindow on Wayland. Keep the
    // launcher's X11 capsule attached when the parent moves or resizes.
    if (KWindowSystem::isPlatformX11() && isVisible()
        && (event->type() == QEvent::Show || event->type() == QEvent::Resize
            || event->type() == QEvent::UpdateRequest)) {
        const auto anchor = visualParent();
        if (anchor && anchor->window() && anchor->window()->screen()) {
            const QRect available = anchor->window()->screen()->availableGeometry();
            const QPointF topLeft = anchor->mapToGlobal(QPointF(0, 0));
            const int left = qRound(topLeft.x() + (anchor->width() - width()) / 2);
            const int top = qRound(topLeft.y()) - height() - margin();
            setPosition(std::clamp(left, available.left(),
                                   std::max(available.left(), available.right() + 1 - width())),
                        std::clamp(top, available.top(),
                                   std::max(available.top(), available.bottom() + 1 - height())));
        }
    }
    return handled;
}

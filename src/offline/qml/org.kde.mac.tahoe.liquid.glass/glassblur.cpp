/*
    MacTahoe Liquid KDE — GlassBlur: blur behind a popup's glass shapes only.

    SPDX-License-Identifier: GPL-3.0-or-later
*/
#include "glassblur.h"

#include <KWindowEffects>
#include <QPainterPath>
#include <QQuickWindow>
#include <QEvent>

GlassBlur::GlassBlur(QQuickItem *parent)
    : QQuickItem(parent)
{
    // Coalesce bursts of geometry changes into one compositor request.
    m_timer.setSingleShot(true);
    m_timer.setInterval(0);
    connect(&m_timer, &QTimer::timeout, this, &GlassBlur::apply);
    // Plasma's Dialog rewrites the window's blur from its background hints
    // when it shows, gets a new surface or resizes, sometimes well after
    // the event: ask again a few times until it has settled.
    m_settleTimer.setSingleShot(true);
    connect(&m_settleTimer, &QTimer::timeout, this, [this] {
        apply();
        if (m_settlePass < kSettleDelays.size()) {
            m_settleTimer.start(kSettleDelays[m_settlePass++]);
        }
    });
}

GlassBlur::~GlassBlur()
{
    if (m_window && m_maskSet) {
        m_window->setMask(QRegion());
    }
}

QQuickItem *GlassBlur::target() const
{
    return m_target;
}

void GlassBlur::setTarget(QQuickItem *target)
{
    if (m_target == target) {
        return;
    }
    if (m_target) {
        disconnect(m_target, nullptr, this, nullptr);
    }
    m_target = target;
    if (m_target) {
        connect(m_target, &QQuickItem::widthChanged, this, &GlassBlur::update);
        connect(m_target, &QQuickItem::heightChanged, this, &GlassBlur::update);
    }
    Q_EMIT targetChanged();
    update();
}

bool GlassBlur::isActive() const
{
    return m_active;
}

void GlassBlur::setActive(bool active)
{
    if (m_active == active) {
        return;
    }
    m_active = active;
    Q_EMIT activeChanged();
    update();
}

void GlassBlur::update()
{
    m_timer.start();
    m_settlePass = 0;
    m_settleTimer.start(kSettleDelays[m_settlePass++]);
}

void GlassBlur::itemChange(ItemChange change, const ItemChangeData &value)
{
    if (change == ItemSceneChange) {
        watchWindow(value.window);
    }
    QQuickItem::itemChange(change, value);
}

void GlassBlur::watchWindow(QQuickWindow *window)
{
    if (m_window == window) {
        return;
    }
    if (m_window) {
        m_window->removeEventFilter(this);
    }
    m_window = window;
    if (m_window) {
        m_window->installEventFilter(this);
    }
    update();
}

bool GlassBlur::eventFilter(QObject *watched, QEvent *event)
{
    // A new surface (every show of a popup on Wayland), a show, a resize or
    // an expose may come with Plasma's Dialog writing its own blur: ask
    // again once it is done.
    switch (event->type()) {
    case QEvent::PlatformSurface:
    case QEvent::Show:
    case QEvent::Expose:
    case QEvent::Resize:
        update();
        break;
    default:
        break;
    }
    return QQuickItem::eventFilter(watched, event);
}

void GlassBlur::collect(QQuickItem *item, QRegion &region, const QRectF &clip) const
{
    if (!item->isVisible() || item->opacity() <= 0) {
        return;
    }
    // An empty clip is no clip: nothing above clips the item.
    QRectF itemClip = clip;
    if (item->clip()) {
        const QRectF rect = item->mapRectToScene(QRectF(0, 0, item->width(), item->height()));
        itemClip = itemClip.isNull() ? rect : itemClip.intersected(rect);
        if (itemClip.isEmpty()) {
            return;
        }
    }
    const QVariant radius = item->property("glassRadius");
    if (radius.isValid() && radius.toReal() >= 0 && item->width() > 0 && item->height() > 0) {
        const QRectF rect = item->mapRectToScene(QRectF(0, 0, item->width(), item->height()));
        const qreal r = qMin(radius.toReal(), qMin(rect.width(), rect.height()) / 2);
        QPainterPath path;
        path.addRoundedRect(rect, r, r);
        QRegion shape(path.toFillPolygon().toPolygon());
        if (!itemClip.isNull()) {
            shape &= itemClip.toAlignedRect();
        }
        region |= shape;
        // A glass shape's own children are on the glass.
        return;
    }
    const auto children = item->childItems();
    for (QQuickItem *child : children) {
        collect(child, region, itemClip);
    }
}

void GlassBlur::apply()
{
    if (!m_window) {
        return;
    }
    QRegion region;
    if (m_active && m_target) {
        collect(m_target, region, QRectF());
    }
    KWindowEffects::enableBlurBehind(m_window, !region.isEmpty(), region);
    // Clicks outside the glass go to what is under it, as on macOS (on
    // Wayland the mask is the surface's input region).
    if (!region.isEmpty() && m_window->mask() != region) {
        m_window->setMask(region);
        m_maskSet = true;
    } else if (region.isEmpty() && m_maskSet) {
        m_window->setMask(QRegion());
        m_maskSet = false;
    }
    // The blur region is double-buffered: KWin applies it on the surface's
    // next commit. A popup that is not repainting (most of them, once
    // shown) would keep it pending forever, and the glass came up unblurred
    // one time in two. Render a frame so it gets committed.
    m_window->update();
}

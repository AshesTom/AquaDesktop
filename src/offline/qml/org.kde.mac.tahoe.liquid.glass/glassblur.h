/*
    MacTahoe Liquid KDE — GlassBlur: blur behind a popup's glass shapes only.

    SPDX-License-Identifier: GPL-3.0-or-later
*/
#pragma once

#include <QPointer>
#include <QQuickItem>
#include <QRegion>
#include <QTimer>

#include <array>
#include <qqmlregistration.h>

class QQuickWindow;

/*
    Asks the compositor to blur behind every visible item under `target`
    that declares a `glassRadius` property (>= 0): the union of their
    rounded shapes, in window coordinates. Everything else in the window
    stays see-through. Call update() after the shapes move; showing the
    window, resizing the target and toggling `active` update it too.
*/
class GlassBlur : public QQuickItem
{
    Q_OBJECT
    QML_ELEMENT
    Q_PROPERTY(QQuickItem *target READ target WRITE setTarget NOTIFY targetChanged)
    Q_PROPERTY(bool active READ isActive WRITE setActive NOTIFY activeChanged)

public:
    explicit GlassBlur(QQuickItem *parent = nullptr);
    ~GlassBlur() override;

    QQuickItem *target() const;
    void setTarget(QQuickItem *target);
    bool isActive() const;
    void setActive(bool active);

    Q_INVOKABLE void update();

Q_SIGNALS:
    void targetChanged();
    void activeChanged();

protected:
    void itemChange(ItemChange change, const ItemChangeData &value) override;
    bool eventFilter(QObject *watched, QEvent *event) override;

private:
    void apply();
    void watchWindow(QQuickWindow *window);
    void collect(QQuickItem *item, QRegion &region, const QRectF &clip) const;

    QPointer<QQuickItem> m_target;
    QPointer<QQuickWindow> m_window;
    bool m_active = true;
    // The window's input mask is ours: give it back when the glass goes.
    bool m_maskSet = false;
    QTimer m_timer;
    // Later passes: Plasma's Dialog resets the window's blur from its own
    // background hints when it shows or resizes, after our first request.
    QTimer m_settleTimer;
    // Delays (ms) between the later passes, after the immediate one.
    static constexpr std::array<int, 5> kSettleDelays{60, 140, 300, 700, 1200};
    std::size_t m_settlePass = 0;
};

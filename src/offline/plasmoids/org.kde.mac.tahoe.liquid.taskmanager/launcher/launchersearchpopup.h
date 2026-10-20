// SPDX-License-Identifier: GPL-3.0-or-later
#pragma once

#include <PlasmaQuick/PopupPlasmaWindow>
#include <QPointer>
#include <qqmlregistration.h>

// A separate native frame keeps the capsule's glass, input mask and shadow aligned.
class LauncherSearchPopup : public PlasmaQuick::PopupPlasmaWindow
{
    Q_OBJECT
    QML_ELEMENT
    Q_PROPERTY(bool hasFocus READ isActive NOTIFY focusChanged)

public:
    LauncherSearchPopup();
    Q_INVOKABLE void activate() { requestActivate(); }

protected:
    bool event(QEvent *event) override;
    bool eventFilter(QObject *watched, QEvent *event) override;

Q_SIGNALS:
    void focusChanged();

private:
    QPointer<QWindow> m_anchorWindow;
};

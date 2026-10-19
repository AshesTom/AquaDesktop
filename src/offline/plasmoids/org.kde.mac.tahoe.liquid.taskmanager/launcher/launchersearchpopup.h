// SPDX-License-Identifier: GPL-3.0-or-later
#pragma once

#include <PlasmaQuick/PopupPlasmaWindow>
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

Q_SIGNALS:
    void focusChanged();
};

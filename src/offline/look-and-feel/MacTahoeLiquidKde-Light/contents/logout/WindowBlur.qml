/*
    AquaDesktop — the alert's blur, kept in its own file:
    org.kde.mac.tahoe.liquid.glass is a compiled module, and without it the
    Loader in Logout.qml only loses the blur, not the alert.

    SPDX-License-Identifier: GPL-3.0-or-later
*/
import QtQuick

import org.kde.mac.tahoe.liquid.glass as Glass

Glass.GlassBlur {}

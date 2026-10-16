/*
    AquaDesktop — Now Playing glyph (see Glyphs.js).

    SPDX-License-Identifier: GPL-3.0-or-later
*/
import QtQuick

import org.kde.kirigami as Kirigami
import "Glyphs.js" as Glyphs

Image {
    property string glyph
    property color color: Kirigami.Theme.textColor

    source: glyph ? Glyphs.url(glyph, color) : ""
    sourceSize: Qt.size(Math.ceil(width * Screen.devicePixelRatio), Math.ceil(height * Screen.devicePixelRatio))
    fillMode: Image.PreserveAspectFit
    smooth: true
    cache: true
}

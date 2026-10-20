// SPDX-License-Identifier: GPL-2.0-or-later
#pragma once

#include <QPainterPath>
#include <QRegion>
#include <algorithm>
#include <cmath>
#include <limits>
#include <optional>

// Recover a rounded popup's curve from its integer blur region. The shader
// can then fade along the curve instead of exposing the region's stair steps.
inline std::optional<float> roundedBlurRadius(const QRegion &region, const QRect &bounds)
{
    if (region.isEmpty() || region.boundingRect() != bounds || bounds.height() < 4) {
        return std::nullopt;
    }
    const QRect firstRow = region.intersected(QRect(bounds.x(), bounds.y(), bounds.width(), 1)).boundingRect();
    const int inset = firstRow.left() - bounds.left();
    if (inset < 1 || std::abs(bounds.right() - firstRow.right() - inset) > 1) {
        return std::nullopt;
    }
    const int estimate = qRound(inset + 0.5 + std::sqrt(inset));
    const int maximum = std::min(bounds.width(), bounds.height()) / 2;
    std::optional<float> bestRadius;
    qint64 bestError = std::numeric_limits<qint64>::max();
    // SVG alpha masks include partially covered pixels; thresholded masks
    // round differently. Fit nearby curves instead of trusting one scanline.
    for (int radius = std::max(1, estimate - 2); radius <= std::min(maximum, estimate + 3); ++radius) {
        QPainterPath inner, outer, curve;
        // FrameSvg downsamples device-pixel alpha masks to logical pixels.
        // Its SVG arc rasterization can differ from QPainterPath by two
        // pixels, including at 150%, and opposite insets can differ by one.
        inner.addRoundedRect(QRectF(bounds).adjusted(2, 2, -2, -2), std::max(0, radius - 2), std::max(0, radius - 2));
        outer.addRoundedRect(QRectF(bounds).adjusted(-2, -2, 2, 2), radius + 2, radius + 2);
        // Keep holes and custom cutouts outside this rasterization tolerance.
        if (!(QRegion(inner.toFillPolygon().toPolygon()) - region).isEmpty()
            || !(region - QRegion(outer.toFillPolygon().toPolygon())).isEmpty()) {
            continue;
        }
        // A capsule has no straight vertical edge. Prefer its exact
        // half-height curve over a slightly smaller rasterized fit.
        if (radius == maximum) {
            return float(radius);
        }
        curve.addRoundedRect(QRectF(bounds), radius, radius);
        const QRegion difference = region ^ QRegion(curve.toFillPolygon().toPolygon());
        qint64 error = 0;
        for (const QRect &rect : difference) {
            error += qint64(rect.width()) * rect.height();
        }
        if (error < bestError) {
            bestRadius = radius;
            bestError = error;
        }
    }
    return bestRadius;
}

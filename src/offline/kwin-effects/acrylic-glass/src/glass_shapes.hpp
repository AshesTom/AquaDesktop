#pragma once

// AquaDesktop: recover a popover's glass bubbles from its blur region.
//
// A popover asks KWin to blur behind the union of its rounded bubbles
// (org.kde.mac.tahoe.liquid.glass, KSvg frame masks); the protocol carries
// that union as banded rectangles only. Each connected group of rectangles
// is one bubble: its bounding box is the bubble and its corner radius is the
// height of the bands that do not reach the box's left edge yet.

#include <QList>
#include <QRectF>

#include <algorithm>
#include <cmath>
#include <numeric>
#include <vector>

namespace AquaGlass {

struct GlassShape {
    QRectF box;
    qreal radius = 0;
};

inline std::vector<GlassShape> glassShapes(const QList<QRectF> &rects, size_t maxShapes)
{
    const qsizetype n = rects.size();
    std::vector<int> parent(n);
    std::iota(parent.begin(), parent.end(), 0);
    auto find = [&parent](int i) {
        while (parent[i] != i) {
            parent[i] = parent[parent[i]];
            i = parent[i];
        }
        return i;
    };

    // Two rectangles belong to one bubble when they overlap or touch along
    // an edge; corners meeting diagonally do not join two bubbles.
    constexpr qreal slack = 0.5;
    for (qsizetype i = 0; i < n; ++i) {
        const QRectF &a = rects[i];
        for (qsizetype j = i + 1; j < n; ++j) {
            const QRectF &b = rects[j];
            const bool xOverlap = a.left() < b.right() && b.left() < a.right();
            const bool yOverlap = a.top() < b.bottom() && b.top() < a.bottom();
            const bool xTouch = std::abs(a.right() - b.left()) <= slack || std::abs(b.right() - a.left()) <= slack;
            const bool yTouch = std::abs(a.bottom() - b.top()) <= slack || std::abs(b.bottom() - a.top()) <= slack;
            if ((xOverlap && (yOverlap || yTouch)) || (yOverlap && xTouch)) {
                parent[find(int(i))] = find(int(j));
            }
        }
    }

    std::vector<int> roots;
    std::vector<QRectF> boxes;
    for (qsizetype i = 0; i < n; ++i) {
        const int root = find(int(i));
        auto it = std::find(roots.begin(), roots.end(), root);
        if (it == roots.end()) {
            roots.push_back(root);
            boxes.push_back(rects[i]);
        } else {
            QRectF &box = boxes[it - roots.begin()];
            box = box.united(rects[i]);
        }
    }

    std::vector<GlassShape> shapes;
    shapes.reserve(roots.size());
    for (size_t k = 0; k < roots.size(); ++k) {
        const QRectF box = boxes[k];
        // Rows from the top whose leftmost rectangle starts right of the box.
        std::vector<QRectF> members;
        for (qsizetype i = 0; i < n; ++i) {
            if (find(int(i)) == roots[k]) {
                members.push_back(rects[i]);
            }
        }
        std::sort(members.begin(), members.end(), [](const QRectF &a, const QRectF &b) {
            return a.top() < b.top() || (a.top() == b.top() && a.left() < b.left());
        });
        qreal inset = 0;
        for (size_t i = 0; i < members.size();) {
            const qreal top = members[i].top();
            qreal left = members[i].left();
            qreal bottom = members[i].bottom();
            for (; i < members.size() && members[i].top() == top; ++i) {
                left = std::min(left, members[i].left());
                bottom = std::min(bottom, members[i].bottom());
            }
            if (left <= box.left() + slack) {
                break;
            }
            inset = bottom - box.top();
        }
        // A polygonised arc reaches the box edge within half a pixel about
        // sqrt(r) rows early: the bands are r - sqrt(r) high.
        const qreal estimate = inset > 0 ? inset + 0.5 + std::sqrt(inset + 0.25) : 0;
        const qreal radius = std::min(estimate, std::min(box.width(), box.height()) / 2);
        shapes.push_back({box, radius});
    }

    if (shapes.size() > maxShapes) {
        return {};
    }
    // Reading order keeps the shader's first match stable between frames.
    std::sort(shapes.begin(), shapes.end(), [](const GlassShape &a, const GlassShape &b) {
        return a.box.top() < b.box.top() || (a.box.top() == b.box.top() && a.box.left() < b.box.left());
    });
    return shapes;
}

} // namespace AquaGlass

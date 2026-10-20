#pragma once

// AquaDesktop: Liquid Glass for Plasma popovers (LiquidPopups), one lens per
// bubble of the window's blur region (see liquid_shapes.hpp and
// shaders/liquid_core.frag).

#include "liquid_shapes.hpp"

#include <opengl/glshader.h>

#include <QMatrix4x4>
#include <QVector2D>

#include <memory>
#include <vector>

namespace BBDX {

class LiquidPass {
private:
    std::unique_ptr<KWin::GLShader> m_shader;
    int m_mvpMatrixLocation;
    int m_colorMatrixLocation;
    int m_offsetLocation;
    int m_halfpixelLocation;
    int m_rectSizeLocation;
    int m_viewportScaleLocation;
    int m_shapeCountLocation;
    int m_shapesLocation;
    int m_shapeRadiiLocation;
    int m_edgeSizePixelsLocation;
    int m_refractionStrengthLocation;
    int m_refractionNormalPowLocation;
    int m_refractionRGBFringingLocation;
    int m_refractionOffsetStrengthLocation;
    int m_glintStrengthLocation;
    int m_scrimModeLocation;
    int m_scrimCapLocation;
    int m_scrimDecayLocation;

    bool m_enabled{false};
    float m_edgeSizePixels{};
    float m_refractionStrength{};
    float m_normalPow{};
    float m_RGBFringing{};
    float m_offsetStrength{};
    float m_glintStrength{};
    int m_scrimMode{};
    float m_scrimCap{};
    float m_scrimDecay{};

    LiquidPass() = default;

public:
    static constexpr size_t maxShapes = 24;

    static std::unique_ptr<LiquidPass> create();

    void reconfigure();

    /**
     * LiquidPopups is on and the shader loaded.
     */
    bool enabled() const { return m_enabled; }

    void pushShader() const;

    void setParameters(const QMatrix4x4 &projectionMatrix,
                       const QMatrix4x4 &colorMatrix,
                       const QVector2D &halfpixel,
                       float offset,
                       const QVector2D &rectSize,
                       float viewportScale,
                       const std::vector<LiquidShape> &shapes) const;
};

} // namespace BBDX

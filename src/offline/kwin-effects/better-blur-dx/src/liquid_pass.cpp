#include "blurconfig.h"
#include "liquid_pass.hpp"
#include "utils.h"

#include <opengl/glshadermanager.h>

#include <QLoggingCategory>
#include <QVector4D>

#include <algorithm>

Q_LOGGING_CATEGORY(LIQUID_PASS, "kwin_effect_better_blur_dx.liquid_pass", QtInfoMsg)

std::unique_ptr<BBDX::LiquidPass> BBDX::LiquidPass::create() {
    std::unique_ptr<LiquidPass> pass{new LiquidPass};

    pass->m_shader = KWin::ShaderManager::instance()->generateShaderFromFile(
        KWin::ShaderTrait::MapTexture,
        BBDX::shaderFilePath(":/effects/better_blur_dx/shaders/vertex.vert"),
        BBDX::shaderFilePath(":/effects/better_blur_dx/shaders/liquid.frag")
    );

    if (!pass->m_shader) {
        qCWarning(LIQUID_PASS) << BBDX::LOG_PREFIX << "Failed to load liquid pass shader";
        return nullptr;
    }

    auto *shader = pass->m_shader.get();
    pass->m_mvpMatrixLocation = shader->uniformLocation("modelViewProjectionMatrix");
    pass->m_colorMatrixLocation = shader->uniformLocation("colorMatrix");
    pass->m_offsetLocation = shader->uniformLocation("offset");
    pass->m_halfpixelLocation = shader->uniformLocation("halfpixel");
    pass->m_rectSizeLocation = shader->uniformLocation("rectSize");
    pass->m_viewportScaleLocation = shader->uniformLocation("viewportScale");
    pass->m_shapeCountLocation = shader->uniformLocation("shapeCount");
    pass->m_shapesLocation = shader->uniformLocation("shapes");
    pass->m_shapeRadiiLocation = shader->uniformLocation("shapeRadii");
    pass->m_edgeSizePixelsLocation = shader->uniformLocation("edgeSizePixels");
    pass->m_refractionStrengthLocation = shader->uniformLocation("refractionStrength");
    pass->m_refractionNormalPowLocation = shader->uniformLocation("refractionNormalPow");
    pass->m_refractionRGBFringingLocation = shader->uniformLocation("refractionRGBFringing");
    pass->m_refractionOffsetStrengthLocation = shader->uniformLocation("refractionOffsetStrength");
    pass->m_glintStrengthLocation = shader->uniformLocation("glintStrength");
    pass->m_scrimModeLocation = shader->uniformLocation("scrimMode");
    pass->m_scrimCapLocation = shader->uniformLocation("scrimCap");
    pass->m_scrimDecayLocation = shader->uniformLocation("scrimDecay");

    return pass;
}

void BBDX::LiquidPass::reconfigure() {
    auto config = BBDX::BlurConfig::self();
    if (!config) {
        return;
    }

    m_enabled = config->liquidPopups();
    m_edgeSizePixels = std::max(0, config->liquidEdgeSize());
    m_refractionStrength = std::clamp(config->liquidRefractionStrength(), 0, 100) / 100.0f;
    // Tenths, like NextKde's 5.0 normal power.
    m_normalPow = std::max(1, config->liquidNormalPow()) / 10.0f;
    m_RGBFringing = std::clamp(config->liquidRGBFringing(), 0, 100) / 100.0f;
    m_offsetStrength = std::clamp(config->liquidOffsetStrength(), 0, 120) / 10.0f;
    m_glintStrength = std::clamp(config->liquidGlints(), 0, 100) / 100.0f;
    m_scrimMode = std::clamp(config->liquidScrim(), 0, 2);
    m_scrimCap = std::clamp(config->liquidScrimCap(), 0, 100) / 100.0f;
    m_scrimDecay = std::clamp(config->liquidScrimDecay(), 0, 100) / 100.0f;
}

void BBDX::LiquidPass::pushShader() const {
    KWin::ShaderManager::instance()->pushShader(m_shader.get());
}

void BBDX::LiquidPass::setParameters(const QMatrix4x4 &projectionMatrix,
                                     const QMatrix4x4 &colorMatrix,
                                     const QVector2D &halfpixel,
                                     float offset,
                                     const QVector2D &rectSize,
                                     float viewportScale,
                                     const std::vector<LiquidShape> &shapes) const {
    m_shader->setUniform(m_mvpMatrixLocation, projectionMatrix);
    m_shader->setUniform(m_colorMatrixLocation, colorMatrix);
    m_shader->setUniform(m_halfpixelLocation, halfpixel);
    m_shader->setUniform(m_offsetLocation, offset);
    m_shader->setUniform(m_rectSizeLocation, rectSize);
    m_shader->setUniform(m_viewportScaleLocation, viewportScale);

    // GLShader has no array setters: upload through the program directly.
    // The shader is bound (pushShader) when this runs.
    const int count = int(std::min(shapes.size(), maxShapes));
    GLfloat boxes[maxShapes * 4] = {};
    GLfloat radii[maxShapes] = {};
    for (int i = 0; i < count; ++i) {
        const QRectF &box = shapes[i].box;
        boxes[i * 4 + 0] = box.x();
        boxes[i * 4 + 1] = box.y();
        boxes[i * 4 + 2] = box.width();
        boxes[i * 4 + 3] = box.height();
        radii[i] = shapes[i].radius;
    }
    m_shader->setUniform(m_shapeCountLocation, count);
    if (m_shapesLocation >= 0) {
        glUniform4fv(m_shapesLocation, maxShapes, boxes);
    }
    if (m_shapeRadiiLocation >= 0) {
        glUniform1fv(m_shapeRadiiLocation, maxShapes, radii);
    }

    m_shader->setUniform(m_edgeSizePixelsLocation, m_edgeSizePixels);
    m_shader->setUniform(m_refractionStrengthLocation, m_refractionStrength);
    m_shader->setUniform(m_refractionNormalPowLocation, m_normalPow);
    m_shader->setUniform(m_refractionRGBFringingLocation, m_RGBFringing);
    m_shader->setUniform(m_refractionOffsetStrengthLocation, m_offsetStrength);
    m_shader->setUniform(m_glintStrengthLocation, m_glintStrength);
    m_shader->setUniform(m_scrimModeLocation, m_scrimMode);
    m_shader->setUniform(m_scrimCapLocation, m_scrimCap);
    m_shader->setUniform(m_scrimDecayLocation, m_scrimDecay);
}

"""Apply reviewed rendering fixes to the verified Rounded Corners 0.10.0.

Texture orientation detection adapted from upstream PR #547 (5026fab0c93174d22be0b87ccaaa799f7173b066).
SPDX-License-Identifier: GPL-3.0-or-later
"""
from pathlib import Path


_REPLACEMENTS = {
    "src/WindowManager.cpp": (
        ("    // Don't treat docks as windows.", """    // Desktop containment (including edit mode) must never be redirected.
    if (kwindow->isDesktop()) {
        return false;
    }

    // Don't treat docks as windows."""),
    ),
    "src/Window.cpp": (
        ("    return (w->expandedGeometry().isValid() &&", """    return (!w->isDesktop() && !w->isDock() && w->expandedGeometry().isValid() &&"""),
    ),
    "src/Effect.cpp": (
        ('#include <QDebug>', '#include <QDebug>\n#include <QVariant>'),
        ("ShapeCorners::Effect::~Effect()\n{", """ShapeCorners::Effect::~Effect()
{
    for (auto *window : KWin::effects->stackingOrder()) {
        window->setProperty("_mttkde_corner_shape_v1", QVariant());
        window->addRepaintFull();
    }"""),
        ("    // If the shader is not valid or the window is not managed or doesn't need the effect, fall back to default.", """    // Clear stale geometry when excluded, disabled, or changing window type.
    kwindow->setProperty("_mttkde_corner_shape_v1", QVariant());

    // If the shader is not valid or the window is not managed or doesn't need the effect, fall back to default."""),
        ("    // If the window should have rounded corners, adjust the paint and opaque regions.", """    // Share the animated logical geometry with Acrylic Glass for this frame.
    // This is runtime state only: neither effect rewrites the other's settings.
    kwindow->setProperty("_mttkde_corner_shape_v1", QVariantList{
        window->hasRoundCorners() ? double(window->currentConfig.cornerRadius) : 0.0,
        Config::useSquircleShape() ? double(Config::squircleness()) : 0.0});

    // If the window should have rounded corners, adjust the paint and opaque regions."""),
        ("""    if (m_windowManager->addWindow(kwindow)) {
        // Redirect the window and set the shader if it was successfully added.
        redirect(kwindow);
        setShader(kwindow, m_shaderManager.GetShader().get());
    }""", """    // drawWindow redirects only eligible windows, after hasEffect().
    // Eager redirection also captured desktop/edit-mode surfaces (#77).
    m_windowManager->addWindow(kwindow);"""),
    ),
    "src/Shader.cpp": (
        ("} // namespace", """// KWin 6.8's offscreen texture orientation depends on the graphics backend.
#if KWIN_EFFECT_API_VERSION >= 237 && KWIN_PLUGIN_VERSION_NUM >= QT_VERSION_CHECK(6, 7, 90)
    const KWin::ShaderTraits kShaderTraits = KWin::ShaderTrait::MapTexture | KWin::ShaderTrait::RoundedCorners;
#else
    constexpr auto kShaderTraits = KWin::ShaderTrait::MapTexture;
#endif
} // namespace"""),
        ("generateShaderFromFile(KWin::ShaderTrait::MapTexture, QString(),",
         "generateShaderFromFile(kShaderTraits, QString(),"),
    ),
    "src/shaders/shapecorners_qt6_core.frag": (
        ('#include "colormanagement.glsl"', """#ifdef TRAIT_ROUNDED_CORNERS
#if TRAIT_ROUNDED_CORNERS && (__VERSION__ >= 300 || defined(GL_OES_standard_derivatives))
in vec2 position0;
#define HAS_POSITION0
#endif
#endif

#include "colormanagement.glsl\""""),
        ("    vec4 tex = texture(sampler, texcoord0);", """#ifdef HAS_POSITION0
    // Derivatives must be evaluated before any per-fragment branching.
    yInverted = detect_y_inverted();
#endif
    vec4 tex = texture(sampler, texcoord0);"""),
    ),
    "src/shaders/variables.glsl": (
        ("vec2 tex_to_pixel(vec2 texcoord)", """#ifdef HAS_POSITION0
bool yInverted = true;
bool detect_y_inverted()
{
    return dFdx(texcoord0.y) * dFdx(position0.y) + dFdy(texcoord0.y) * dFdy(position0.y) > 0.0;
}
#else
const bool yInverted = false;
#endif

vec2 tex_to_pixel(vec2 texcoord)"""),
        ("(1.0 - texcoord.y) * windowExpandedSize.y",
         "(yInverted ? texcoord.y : 1.0 - texcoord.y) * windowExpandedSize.y"),
        ("    return vec2((pixelcoord.x + windowTopLeft.x) / windowExpandedSize.x,\n"
         "                1.0 - (pixelcoord.y + windowTopLeft.y) / windowExpandedSize.y);",
         "    vec2 uv = (pixelcoord + windowTopLeft) / windowExpandedSize;\n"
         "    return vec2(uv.x, yInverted ? uv.y : 1.0 - uv.y);"),
    ),
}


class CompatibilityError(ValueError):
    """Expose the failed path without coupling the Nix helper to a UI locale."""

    def __init__(self, relative: str):
        self.relative = relative
        super().__init__(f"Rounded Corners compatibility patch does not match {relative}")


def apply(source: Path) -> None:
    """Validate every hunk before writing; reject unexpected or partial sources."""
    updates = {}
    for relative, replacements in _REPLACEMENTS.items():
        path = source / relative
        try:
            text = path.read_text()
        except OSError as exc:
            raise CompatibilityError(relative) from exc
        for old, new in replacements:
            if text.count(new) == 1:
                continue
            if text.count(old) != 1:
                raise CompatibilityError(relative)
            text = text.replace(old, new, 1)
        updates[path] = text
    for path, text in updates.items():
        if path.read_text() != text:
            path.write_text(text)


if __name__ == "__main__":
    import sys
    apply(Path(sys.argv[1]))

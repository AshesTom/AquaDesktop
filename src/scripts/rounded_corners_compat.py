"""Backport texture orientation detection to the verified Rounded Corners 0.10.0.

Adapted from upstream PR #547 (5026fab0c93174d22be0b87ccaaa799f7173b066).
SPDX-License-Identifier: GPL-3.0-or-later
"""
from pathlib import Path


_REPLACEMENTS = {
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


def apply(source: Path) -> None:
    """Validate every hunk before writing; reject unexpected or partial sources."""
    updates = {}
    for relative, replacements in _REPLACEMENTS.items():
        path = source / relative
        text = path.read_text()
        for old, new in replacements:
            if text.count(new) == 1:
                continue
            if text.count(old) != 1:
                raise ValueError(f"Rounded Corners compatibility patch does not match {relative}")
            text = text.replace(old, new, 1)
        updates[path] = text
    for path, text in updates.items():
        if path.read_text() != text:
            path.write_text(text)


if __name__ == "__main__":
    import sys
    apply(Path(sys.argv[1]))

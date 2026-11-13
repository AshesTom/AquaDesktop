// MacTahoe Liquid KDE — Acrylic Glass highlight helpers

#ifndef LIQUIDGLASS_HIGHLIGHT_GLSL
#define LIQUIDGLASS_HIGHLIGHT_GLSL

// Frame-local coordinates grow downwards, independently of texture orientation.
// A thin upper highlight defines the glass edge without a broad painted rim.
float lgRimAngularWeight(vec2 outNorm)
{
    return 0.65 + 0.55 * clamp(-outNorm.y * 0.5 + 0.5, 0.0, 1.0);
}

vec3 lgApplyHighlight(vec3 color, float inside, vec2 outNorm,
                      float highlightWidth, float highlightStrength, bool dockSurface)
{
    float band = max(highlightWidth, 1.0);
    // The Dock catches light at the silhouette; keep the reflection within
    // the pixel-scaled band instead of fading it out at the glass edge.
    float rim = dockSurface
        ? 1.6 * exp(-inside * (2.0 / band))
        : exp(-inside * (3.0 / band)) * smoothstep(0.0, 2.0, inside);
    float intensity = rim * highlightStrength * lgRimAngularWeight(outNorm);
    return mix(color, vec3(0.87, 0.93, 1.0), clamp(intensity, 0.0, 0.95));
}

#endif

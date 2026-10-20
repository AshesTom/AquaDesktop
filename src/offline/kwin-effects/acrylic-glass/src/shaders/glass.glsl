#extension GL_OES_standard_derivatives : enable

#define LG_SAMPLE(tex, coord) texture2D(tex, coord)
#define LG_OUT gl_FragColor

#include "sdf.glsl"
#include "blur.glsl"
#include "distort.glsl"
#include "highlight.glsl"

uniform sampler2D texUnit;
uniform mat4 colorMatrix;
uniform float offset;
uniform vec2 halfpixel;
uniform vec4 box;
uniform vec4 cornerRadius;
uniform float opacity;
uniform float rgbDriftStrength;
uniform float magnifyGlassStrength;
uniform float refractionWidth;
uniform float highlightWidth;
uniform float highlightStrength;
uniform float materialOpacity;
uniform bool dockSurface;
uniform vec2 backgroundSize;
uniform vec4 gradientTop;
uniform vec4 gradientBottom;
uniform bool darkGradientOverlay;

varying vec2 uv;
varying vec2 vertex;

void main(void)
{
    vec2 halfSize = blurSize * 0.5;
    vec2 pos = vertex - box.xy;

    float d = lgRoundedRectDistance(pos, halfSize, cornerRadius);
    float mask = lgRoundedRectCoverage(d);
    if (mask <= 0.0) {
        discard;
    }

    vec2 outNorm = lgRoundedRectNormal(pos, halfSize, cornerRadius);
    float inside = max(-d, 0.0);

    float refrBand = max(refractionWidth * (dockSurface ? 1.5 : 1.0), 1.0);
    float edgeT = smoothstep(-refrBand, 0.0, d);
    // A broader bevel makes the Dock read as clear, thick glass.
    // Both profiles leave the centre undistorted.
    float edgeQ = edgeT * edgeT * (dockSurface ? 1.0 : edgeT);

    vec2 lensUV = uv;
    if (magnifyGlassStrength > 0.0) {
        lensUV = dockSurface
            ? lgDockLensUV(uv, outNorm, blurSize, backgroundSize, magnifyGlassStrength, edgeQ)
            : lgLensUV(uv, magnifyGlassStrength, edgeQ);
    }
    vec2 texel = halfpixel * 2.0;
    vec3 col;
    if (offset > 0.0) {
        col = lgGaussianBlur(texUnit, texel, lensUV, vec2(offset * 3.0));
    } else {
        // Pixel-exact passthrough: snap to texel center so GL_LINEAR returns
        // the underlying texel exactly instead of a sub-pixel bilinear blend.
        vec2 snapped = (floor(lensUV / texel) + 0.5) * texel;
        col = LG_SAMPLE(texUnit, clamp(snapped, 0.0, 1.0)).rgb;
    }
    if (rgbDriftStrength > 0.0) {
        col = lgApplyRgbDrift(texUnit, col, lensUV, outNorm, blurSize, rgbDriftStrength, edgeQ);
    }
    if (highlightStrength > 0.0) {
        col = lgApplyHighlight(col, inside, outNorm, highlightWidth, highlightStrength);
    }

    vec4 surface = vec4(col, 1.0) * colorMatrix;
    if (darkGradientOverlay) {
        // Frame-local geometry keeps top/bottom upright on all backends.
        // Tint changes color only: the bottom retains the same blurred glass.
        float heightFraction = clamp((pos.y + halfSize.y) / max(blurSize.y, 1.0), 0.0, 1.0);
        float t = smoothstep(0.0, 0.5, heightFraction);
        float tintAlpha = mix(gradientTop.a, gradientBottom.a, t);
        vec3 tint = mix(gradientTop.rgb * gradientTop.a, gradientBottom.rgb * gradientBottom.a, t);
        surface.rgb = surface.rgb * (1.0 - tintAlpha) + tint;
    }
    // Keep the bevel covered so refraction does not double the sharp backdrop.
    float coverage = materialOpacity * (dockSurface ? mix(0.8, 1.0, edgeQ) : 1.0);
    LG_OUT = surface * (mask * opacity * coverage);
}

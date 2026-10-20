#version 140

#define LG_SAMPLE(tex, coord) texture(tex, coord)
#define LG_OUT fragColor

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
// AquaDesktop: the lens centre in texture coordinates.
uniform vec2 lensCenter;
uniform float refractionWidth;
uniform float highlightWidth;
uniform float highlightStrength;
uniform float materialOpacity;
uniform vec4 gradientTop;
uniform vec4 gradientBottom;
uniform bool darkGradientOverlay;

in vec2 uv;
in vec2 vertex;
out vec4 fragColor;

void main()
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

    float refrBand = max(refractionWidth, 1.0);
    float edgeT = smoothstep(-refrBand, 0.0, d);
    // Cubic rim concentration — refraction / RGB drift / lens distortion fall
    // off sharply away from the edge, leaving the centre of the glass clean.
    float edgeQ = edgeT * edgeT * edgeT;

    vec2 lensUV = (magnifyGlassStrength > 0.0)
        ? lgLensUV(uv, lensCenter, magnifyGlassStrength, edgeQ)
        : uv;
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
    LG_OUT = surface * (mask * opacity * materialOpacity);
}

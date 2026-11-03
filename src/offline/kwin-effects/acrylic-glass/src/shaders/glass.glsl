uniform vec3 tintColor;
uniform float tintGray;
uniform float tintStrength;
uniform vec2 autoTintAlphaRange;
uniform int autoTintAlpha;

uniform float edgeSizePixels;
uniform float refractionStrength;
uniform float refractionNormalPow;
uniform float refractionRGBFringing;
uniform int physicallyBasedRefraction;

uniform int edgeAA; // 1 = widget-style edge antialiasing
uniform float cornerExponent; // 2.0 = circular corners, > 2.0 = superellipse ("squircle") corners

float roundedRectangleDist(vec2 p, vec2 b, vec4 cornerRadius)
{
    float r = p.x > 0.0
        ? (p.y > 0.0 ? cornerRadius.y : cornerRadius.w)
        : (p.y > 0.0 ? cornerRadius.x : cornerRadius.z);
    if (cornerExponent > 2.001 && r > 0.0) {
        // A superellipse corner of radius r cuts away much less of the box corner than a circle of the
        // same r (n=4: 54%), so it reads as nearly square. Scale r so the diagonal cut matches the circle
        // and the exponent only changes the character of the curve, like Apple's continuous corners.
        float k = 0.2928932 / (1.0 - exp2(-1.0 / cornerExponent));
        r = min(r * k, min(b.x, b.y));
    }

    vec2 q = abs(p) - b + r;
    float inner = min(max(q.x, q.y), 0.0);
    vec2 qc = max(q, 0.0);

    if (cornerExponent <= 2.001 || r <= 0.0) {
        return inner + length(qc) - r;
    }

    // Superellipse corner |x/r|^n + |y/r|^n = 1 (the same curve the macOS widgets use).
    // First-order signed distance: (h - r) / |grad h| with h = (x^n + y^n)^(1/n).
    float n = cornerExponent;
    float h = pow(pow(qc.x, n) + pow(qc.y, n), 1.0 / n);
    vec2 g = pow(qc, vec2(n - 1.0)) / max(pow(h, n - 1.0), 1e-6);
    float gl = max(length(g), 1e-4);
    return inner + (h - r) / (h > 1e-6 ? gl : 1.0);
}

struct GlassFragment {
    vec4 color;
    float dist;
    float concaveFactor;
};

#include "snells-glass.glsl"
#include "rim.glsl"

vec4 roundedRectangle(vec2 fragCoord, vec3 color, vec4 cornerRadius)
{
    vec2 halfblurSize = blurSize * 0.5;
    vec2 p = fragCoord - halfblurSize;
    float dist = roundedRectangleDist(p, halfblurSize, cornerRadius);

    if (dist <= 0.0) {
        return vec4(color, 1.0);
    }

    float s = smoothstep(0.0, 1.0, dist);
    return vec4(color, mix(1.0, 0.0, s));
}

GlassFragment glassRefraction(vec2 position, vec2 halfBlurSize, vec4 cornerRadius, float dist, float concaveFactor)
{
    const float h = 1.0;
    vec2 gradient = vec2(
            roundedRectangleDist(position + vec2(h, 0), halfBlurSize, cornerRadius) - roundedRectangleDist(position - vec2(h, 0), halfBlurSize, cornerRadius),
            roundedRectangleDist(position + vec2(0, h), halfBlurSize, cornerRadius) - roundedRectangleDist(position - vec2(0, h), halfBlurSize, cornerRadius)
    );

    vec2 normal = length(gradient) > 0.0 ? -normalize(gradient) : vec2(0.0, 1.0);

    float finalStrength = min(0.4 * concaveFactor * refractionStrength, 1.0);

    vec2 refractOffsetG = -normal.xy * finalStrength;
    vec2 refractOffsetR = -normal.xy * finalStrength;
    vec2 refractOffsetB = -normal.xy * finalStrength;

    // Different refraction offsets for each color channel
    float fringingFactor = refractionRGBFringing * 0.3;
    if (fringingFactor > 0.0) {
        // Red bends most
        refractOffsetR = -normal.xy * (finalStrength * (1.0 + fringingFactor));
        // Blue bends least
        refractOffsetB = -normal.xy * (finalStrength * (1.0 - fringingFactor));
    }

    vec2 coordR = clamp(uv - refractOffsetR, 0.0, 1.0);
    vec2 coordG = clamp(uv - refractOffsetG, 0.0, 1.0);
    vec2 coordB = clamp(uv - refractOffsetB, 0.0, 1.0);

    vec4 color = vec4(
        texture(texUnit, coordR).r,
        texture(texUnit, coordG).g,
        texture(texUnit, coordB).b,
        texture(texUnit, coordG).a
    );
    return GlassFragment(color, dist, concaveFactor);
}

float adjustedTintStrength(float baseTintStrength, vec3 backgroundColor)
{
    float strength = clamp(baseTintStrength, 0.0, 1.0);

    const vec3 grayscaleWeights = vec3(0.299, 0.587, 0.114);
    float backgroundGray = dot(backgroundColor, grayscaleWeights);

    float finalScale = clamp(abs(backgroundGray - tintGray), 0.0, 1.0);
    float rangedScale = mix(autoTintAlphaRange.x, autoTintAlphaRange.y, finalScale);

    float localStrength = strength * rangedScale;
    float useLocal = step(0.5, float(autoTintAlpha)) * step(0.001, strength);

    return mix(strength, localStrength, useLocal);
}

vec4 glass(vec4 sum, vec4 cornerRadius)
{
    vec2 halfBlurSize = blurSize * 0.5;
    float minHalfSize = min(halfBlurSize.x, halfBlurSize.y);

    vec2 position = uv * blurSize - halfBlurSize.xy;
    float distRaw = roundedRectangleDist(position, halfBlurSize, cornerRadius);

    // With edgeAA the glass is also shaded across a 1px outer feather so the mask can blend it out.
    float feather = edgeAA == 1 ? 1.0 : 0.0;
    if (distRaw >= feather) {
        return sum;
    }
    float dist = min(distRaw, 0.0);

    float minEsp = clamp(edgeSizePixels, 0.1, minHalfSize * 0.9);
    float edgeFactor = 1.0 - clamp(abs(dist) / minEsp, 0.0, 1.0);
    float concaveFactor = 1.0 - sqrt(1.0 - pow(smoothstep(0.0, 1.0, edgeFactor), refractionNormalPow));

    GlassFragment s;
    if (refractionStrength > 0.0) {
        vec4 r = clamp(cornerRadius * 2.0, min(64.0, minHalfSize), min(128.0, minHalfSize));
        s = physicallyBasedRefraction == 0
            ? glassRefraction(position, halfBlurSize, r, dist, concaveFactor)
            : snellsRefraction(position, halfBlurSize, r, minHalfSize, dist, concaveFactor);
    } else {
        s = GlassFragment(sum, dist, concaveFactor);
    }

    vec3 rgb = s.concaveFactor < 1.0 ? glassGlow(position, s) : s.color.rgb;
    vec3 untinted = rgb;
    s.color.rgb = mix(rgb, tintColor, adjustedTintStrength(tintStrength, rgb));
    vec3 final = glassOutline(position, s, untinted);
    if (edgeAA == 1) {
        return vec4(final, 1.0);
    }
    return roundedRectangle(uv * blurSize, final, cornerRadius);
}

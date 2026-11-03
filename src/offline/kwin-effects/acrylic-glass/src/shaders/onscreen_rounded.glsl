#include "sdf.glsl"

uniform sampler2D texUnit;
uniform mat4 colorMatrix;
uniform float offset;
uniform vec2 halfpixel;
uniform vec4 box;
uniform vec4 cornerRadius;
uniform float opacity;
uniform vec2 blurSize;

in vec2 uv;
in vec2 vertex;
#include "oklab.glsl"
#include "glass.glsl"

void main(void)
{
    vec2 halfBlurSize = blurSize * 0.5;
    float minHalfSize = min(halfBlurSize.x, halfBlurSize.y);

    vec2 position = uv * blurSize - halfBlurSize.xy;
    float dist = roundedRectangleDist(position, halfBlurSize, cornerRadius);

    vec4 sum = vec4(0);
    if (dist <= (edgeAA == 1 ? 1.0 : 0.0)) {
        sum = texture(texUnit, uv + vec2(-halfpixel.x * 2.0, 0.0) * offset);
        sum += texture(texUnit, uv + vec2(-halfpixel.x, halfpixel.y) * offset) * 2.0;
        sum += texture(texUnit, uv + vec2(0.0, halfpixel.y * 2.0) * offset);
        sum += texture(texUnit, uv + vec2(halfpixel.x, halfpixel.y) * offset) * 2.0;
        sum += texture(texUnit, uv + vec2(halfpixel.x * 2.0, 0.0) * offset);
        sum += texture(texUnit, uv + vec2(halfpixel.x, -halfpixel.y) * offset) * 2.0;
        sum += texture(texUnit, uv + vec2(0.0, -halfpixel.y * 2.0) * offset);
        sum += texture(texUnit, uv + vec2(-halfpixel.x, -halfpixel.y) * offset) * 2.0;
        sum /= 12.0;
    }

    sum = glass(sum, cornerRadius);

    // vertex is y-down; roundedRectangleDist expects y-up
    float f = roundedRectangleDist(vec2(vertex.x - box.x, -(vertex.y - box.y)), box.zw, cornerRadius);
    if (edgeAA == 1) {
        // Widget-style mask: 1px smoothstep centered on the true edge, on a unit-gradient distance
        sum *= 1.0 - smoothstep(-0.5, 0.5, f);
    } else {
        float df = fwidth(f);
        sum *= 1.0 - clamp(0.5 + f / df, 0.0, 1.0);
    }

    if (useOklabSaturation == 1) {
        sum.rgb = oklabSaturate(sum.rgb, saturation);
    }

    fragColor = sum * colorMatrix * opacity;
}

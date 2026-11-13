// SPDX-License-Identifier: GPL-3.0-or-later
#ifndef LIQUIDGLASS_BLUR_GLSL
#define LIQUIDGLASS_BLUR_GLSL

// Dense 5x5 binomial Gaussian, reconstructed with nine bilinear samples.
// Pair weights 4 + 1 at +/-1.2 texels; the centre has weight 6.
// Increasing tap spacing creates displaced copies of edges, not a wider
// Gaussian. The Kawase pyramid owns the radius; this pass only smooths it.
vec3 lgGaussianBlur(sampler2D texUnit, vec2 texel, vec2 uvCenter)
{
    vec3 total = vec3(0.0);
    for (int y = -1; y <= 1; ++y) {
        for (int x = -1; x <= 1; ++x) {
            float weight = (x == 0 ? 6.0 : 5.0) * (y == 0 ? 6.0 : 5.0);
            vec2 coord = uvCenter + vec2(float(x), float(y)) * texel * 1.2;
            total += LG_SAMPLE(texUnit, clamp(coord, 0.0, 1.0)).rgb * weight;
        }
    }
    return total / 256.0;
}

#endif

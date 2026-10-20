// SPDX-License-Identifier: GPL-3.0-or-later
#ifndef LIQUIDGLASS_BLUR_GLSL
#define LIQUIDGLASS_BLUR_GLSL

// One symmetric Gaussian finish over the Dual Kawase pyramid. Nine taps,
// fixed work, no highlight weighting or alternate box/bokeh kernels.
vec3 lgGaussianBlur(sampler2D texUnit, vec2 texel, vec2 uvCenter, vec2 rect)
{
    vec3 total = vec3(0.0);
    for (int y = -1; y <= 1; ++y) {
        for (int x = -1; x <= 1; ++x) {
            float weight = (x == 0 ? 2.0 : 1.0) * (y == 0 ? 2.0 : 1.0);
            vec2 coord = uvCenter + vec2(float(x), float(y)) * rect * texel * 0.5;
            total += LG_SAMPLE(texUnit, clamp(coord, 0.0, 1.0)).rgb * weight;
        }
    }
    return total / 16.0;
}

#endif

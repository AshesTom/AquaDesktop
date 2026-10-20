// AquaDesktop: Liquid Glass for Plasma popovers, one lens per bubble.
//
// The Snell lens, the body lens, the edge glints and the adaptive scrim are
// ported from NextKde's Glass effect (kwin/glass-effect/src/shaders:
// glass.glsl, snells-glass.glsl, onscreen_rounded.glsl, GPL-3.0). NextKde
// receives each surface's shape through its own Wayland protocol; here the
// shapes are recovered from the window's blur region (liquid_pass.cpp), so
// every bubble of a popover gets its own rim instead of one window-wide lens.

uniform sampler2D texUnit;
uniform mat4 colorMatrix;
uniform float offset;
uniform vec2 halfpixel;

// Logical size of the sampled background (the blur region's bounding box).
uniform vec2 rectSize;
uniform float viewportScale;

#define MAX_SHAPES 24
uniform int shapeCount;
// x, y, width, height in logical pixels, top-left origin.
uniform vec4 shapes[MAX_SHAPES];
uniform float shapeRadii[MAX_SHAPES];

uniform float edgeSizePixels;
uniform float refractionStrength;
uniform float refractionNormalPow;
uniform float refractionRGBFringing;
uniform float refractionOffsetStrength;
uniform float glintStrength;

// 0: no scrim, 1: black, 2: white.
uniform int scrimMode;
uniform float scrimCap;
uniform float scrimDecay;

varying vec2 uv;


float roundedRectangleDist(vec2 p, vec2 b, float r)
{
    vec2 q = abs(p) - b + r;
    return min(max(q.x, q.y), 0.0) + length(max(q, 0.0)) - r;
}

// Analytic gradient of the rounded-box SDF.
vec2 gradSdRoundedBox(vec2 p, vec2 b, float r)
{
    vec2 q = abs(p) - b + r;
    vec2 sgn = sign(p);
    if (q.x > 0.0 && q.y > 0.0) {
        float norm = length(q);
        if (norm > 1e-5)
            return sgn * q / norm;
    }
    if (q.x > 0.0)
        return vec2(sgn.x, 0.0);
    if (q.y > 0.0)
        return vec2(0.0, sgn.y);
    return (q.x > q.y) ? vec2(sgn.x, 0.0) : vec2(0.0, sgn.y);
}

// Logical pixels (top-left origin) to the texture's coordinates (y up).
vec2 toUv(vec2 shiftPx)
{
    return vec2(shiftPx.x, -shiftPx.y) / rectSize;
}

vec4 sampleBlurred(vec2 coord)
{
    vec2 o = halfpixel * offset;
    vec4 sum = texture2D(texUnit, coord + vec2(-o.x * 2.0, 0.0));
    sum += texture2D(texUnit, coord + vec2(-o.x, o.y)) * 2.0;
    sum += texture2D(texUnit, coord + vec2(0.0, o.y * 2.0));
    sum += texture2D(texUnit, coord + vec2(o.x, o.y)) * 2.0;
    sum += texture2D(texUnit, coord + vec2(o.x * 2.0, 0.0));
    sum += texture2D(texUnit, coord + vec2(o.x, -o.y)) * 2.0;
    sum += texture2D(texUnit, coord + vec2(0.0, -o.y * 2.0));
    sum += texture2D(texUnit, coord + vec2(-o.x, -o.y)) * 2.0;
    return sum / 12.0;
}

// Rim colour: white over dark backdrops, the backdrop's own hue lifted over
// bright and colourful ones, a deep gold over very bright ones.
vec3 getHighlightColor(vec3 backgroundColor, float targetBrightness)
{
    const vec3 grayscaleWeights = vec3(0.299, 0.587, 0.114);
    float luminance = dot(backgroundColor, grayscaleWeights);
    float maxComponent = max(max(backgroundColor.r, backgroundColor.g), backgroundColor.b);
    float lumFactor = (luminance * 2.5) / (1.0 + luminance * 2.5);
    float satFactor = (maxComponent * 2.5) / (1.0 + maxComponent * 2.5);
    float colorInfluence = lumFactor * satFactor;
    vec3 hueLifted = (backgroundColor / max(luminance, 0.001)) * targetBrightness;
    return mix(vec3(targetBrightness), hueLifted, colorInfluence);
}

vec3 rimLight(vec3 backdrop)
{
    float lum = dot(backdrop, vec3(0.299, 0.587, 0.114));
    float brightT = smoothstep(0.45, 0.80, lum);
    vec3 whiteRim = mix(vec3(1.0), clamp(getHighlightColor(backdrop, 1.0), 0.0, 1.0), 0.06);
    const vec3 deepGold = vec3(0.46, 0.32, 0.12);
    vec3 darkRim = mix(deepGold, deepGold * clamp(backdrop, 0.0, 1.0), 0.08);
    return mix(whiteRim, darkRim, brightT);
}

// Narrow glints along the top-left and bottom-right edges.
vec3 applyLiquidGlints(vec3 rgb, vec2 position, vec2 halfSize, float radius,
                       float dist, float aa)
{
    vec2 gradient = gradSdRoundedBox(position, halfSize, max(radius, 1.0));
    vec2 outward = length(gradient) > 1e-5 ? normalize(gradient) : vec2(0.0, 1.0);

    float arcDiagonal = clamp(2.0 * abs(outward.x * outward.y), 0.0, 1.0);
    float arcCoverage = smoothstep(0.08, 0.72, arcDiagonal);
    float straightSigma = max(aa * 0.52, 0.62);
    float sigma = mix(straightSigma, max(straightSigma, max(0.72, aa * 0.72)), arcCoverage);
    float darkRimWeight = smoothstep(0.45, 0.80, dot(rgb, vec3(0.299, 0.587, 0.114)));
    float filteredSigma = mix(sigma, sqrt(sigma * sigma + aa * aa / 12.0), darkRimWeight);
    float edgeDistance = max(-dist, 0.0);
    float contourLine = (sigma / filteredSigma)
        * exp(-0.5 * pow((edgeDistance - 1.0) / filteredSigma, 2.0));

    // position.y grows downwards here: the light comes from the top left.
    float xProgress = clamp((position.x + halfSize.x) / max(halfSize.x * 2.0, 1.0) + 0.04, 0.0, 1.0);
    float yProgress = clamp((position.y + halfSize.y) / max(halfSize.y * 2.0, 1.0), 0.0, 1.0);
    float fromLeft = 1.0 - smoothstep(0.0, 1.0, xProgress);
    float fromRight = 1.0 - smoothstep(0.0, 1.0, 1.0 - xProgress);
    float fromTop = 1.0 - smoothstep(0.0, 1.0, yProgress);
    float fromBottom = 1.0 - smoothstep(0.0, 1.0, 1.0 - yProgress);

    float topFacing = pow(max(-outward.y, 0.0), 0.78);
    float leftFacing = pow(max(-outward.x, 0.0), 0.78);
    float bottomFacing = pow(max(outward.y, 0.0), 0.78);
    float rightFacing = pow(max(outward.x, 0.0), 0.78);

    float primaryEnvelope = min(1.0, topFacing * fromLeft + leftFacing * fromTop);
    float secondaryEnvelope = min(1.0, bottomFacing * fromRight + rightFacing * fromBottom);

    float response = smoothstep(0.05, 0.75, clamp(refractionStrength, 0.0, 1.0)) * glintStrength;
    vec3 rim = rimLight(rgb);
    rgb = mix(rgb, rim, clamp(contourLine * primaryEnvelope * 0.60 * response, 0.0, 0.60));
    rgb = mix(rgb, rim, clamp(contourLine * secondaryEnvelope * 0.50 * response, 0.0, 0.50));
    return rgb;
}

// Snell refraction at the rim plus a body lens reaching 40 px inwards.
vec4 snellsRefraction(vec2 position, vec2 halfSize, float radius, float dist,
                      float concaveFactor)
{
    float minHalfSize = min(halfSize.x, halfSize.y);
    float bandWidth = clamp(edgeSizePixels, 0.1, minHalfSize * 0.9);
    const float bodyReachPx = 40.0;
    const float bodyMaxPx = 40.0;
    const float maxLensShiftPx = 48.0;
    const float fixedBevelIntensity = 1.4;
    float ior = 1.0 + refractionStrength;

    float lensRadius = clamp(radius * 2.0, min(64.0, minHalfSize), min(128.0, minHalfSize));
    float epsilon = max(min(bandWidth * 0.75, lensRadius * 0.6), 0.5);
    vec2 smoothGradient = vec2(
        roundedRectangleDist(position + vec2(epsilon, 0.0), halfSize, lensRadius)
            - roundedRectangleDist(position - vec2(epsilon, 0.0), halfSize, lensRadius),
        roundedRectangleDist(position + vec2(0.0, epsilon), halfSize, lensRadius)
            - roundedRectangleDist(position - vec2(0.0, epsilon), halfSize, lensRadius));
    float gradientLength = length(smoothGradient);
    vec2 outwardDir = gradientLength > 0.001 ? smoothGradient / gradientLength : vec2(0.0);

    float normalHeight = concaveFactor * fixedBevelIntensity;
    vec3 glassNormal = normalize(vec3(outwardDir * normalHeight, 1.0));

    // Shifts are counted in texels of the half-resolution capture: two
    // logical pixels each.
    const float pixelPx = 2.0;
    float lensMagnitude = min(concaveFactor * fixedBevelIntensity * 6.0, 10.0);
    vec2 lensShiftPx = -outwardDir * lensMagnitude * pixelPx;

    float interiorDist = max(-dist, 0.0);
    float bodyT = 1.0 - clamp(interiorDist / bodyReachPx, 0.0, 1.0);
    float bodyProfile = 1.0 - sqrt(max(1.0 - bodyT * bodyT, 0.0));
    vec2 sampleDir = -outwardDir;
    vec2 dirAbs = max(abs(sampleDir), vec2(1e-3));
    vec2 roomToEdge = (halfSize - sign(sampleDir) * position) / dirAbs;
    float available = min(roomToEdge.x, roomToEdge.y);
    float bodyMagnitude = min(clamp(refractionOffsetStrength, 0.0, 12.0) * refractionStrength * 6.0, bodyMaxPx);
    bodyMagnitude = min(bodyMagnitude, available / pixelPx * 0.85);
    lensShiftPx -= outwardDir * bodyMagnitude * bodyProfile * pixelPx;

    vec3 refracted = refract(vec3(0.0, 0.0, -1.0), glassNormal, 1.0 / ior);
    vec2 direction = length(refracted.xy) > 0.001 ? normalize(refracted.xy) : vec2(0.0);
    float magnitude = lensMagnitude * refractionStrength;
    vec2 maxShift = vec2(maxLensShiftPx * pixelPx);

    vec2 shiftG = clamp(direction * magnitude * pixelPx + lensShiftPx, -maxShift, maxShift);
    vec4 color = sampleBlurred(clamp(uv + toUv(shiftG), 0.0, 1.0));
    if (refractionRGBFringing > 0.001) {
        float fringe = clamp(refractionRGBFringing, 0.0, 1.0) * 0.3;
        vec2 shiftR = clamp(direction * magnitude * (1.0 + fringe) * pixelPx + lensShiftPx, -maxShift, maxShift);
        vec2 shiftB = clamp(direction * magnitude * (1.0 - fringe) * pixelPx + lensShiftPx, -maxShift, maxShift);
        color.r = sampleBlurred(clamp(uv + toUv(shiftR), 0.0, 1.0)).r;
        color.b = sampleBlurred(clamp(uv + toUv(shiftB), 0.0, 1.0)).b;
    }
    return color;
}

float localLuminance()
{
    // A broad neighbourhood: fine wallpaper detail must not steer the tint.
    vec3 color = vec3(0.0);
    vec2 stepUv = vec2(16.0) / rectSize;
    for (int y = -1; y <= 1; ++y) {
        for (int x = -1; x <= 1; ++x) {
            float weight = (x == 0 ? 2.0 : 1.0) * (y == 0 ? 2.0 : 1.0);
            color += texture2D(texUnit, clamp(uv + vec2(x, y) * stepUv, 0.0, 1.0)).rgb * weight;
        }
    }
    return clamp(dot(color / 16.0, vec3(0.299, 0.587, 0.114)), 0.0, 1.0);
}

vec3 adaptiveScrim(vec3 background, float lum, bool whiteScrim)
{
    float damage = whiteScrim ? 1.0 - lum : lum;
    float floorAlpha = 0.06 * scrimCap;
    float peakAlpha = min(0.9999, max(floorAlpha, min(scrimDecay, scrimCap)));
    float response = pow(damage, 2.0 - scrimDecay);
    float ratio = (1.0 - peakAlpha) / (1.0 - floorAlpha);
    float primaryAlpha = floorAlpha + (peakAlpha - floorAlpha)
        * response / (ratio + (1.0 - ratio) * response);
    float compressed = damage * (1.0 - primaryAlpha);
    float handoff = 1.0 - smoothstep(0.0, 1.0 - peakAlpha, compressed);
    float oppositeCap = min(min(0.10, scrimCap), 0.5 * (1.0 - peakAlpha));
    float oppositeAlpha = oppositeCap * handoff * (scrimCap - primaryAlpha) / max(scrimCap, 0.0001);
    vec3 primaryTint = whiteScrim ? vec3(1.0) : vec3(0.0);
    return mix(mix(background, primaryTint, primaryAlpha), 1.0 - primaryTint, oppositeAlpha);
}

void main(void)
{
    vec2 p = vec2(uv.x, 1.0 - uv.y) * rectSize;

    int index = -1;
    for (int i = 0; i < MAX_SHAPES; ++i) {
        if (i >= shapeCount)
            break;
        vec4 s = shapes[i];
        if (p.x >= s.x && p.y >= s.y && p.x <= s.x + s.z && p.y <= s.y + s.w) {
            index = i;
            break;
        }
    }

    vec4 sum;
    if (index < 0) {
        sum = sampleBlurred(uv) * colorMatrix;
    } else {
        vec4 s = shapes[index];
        vec2 halfSize = 0.5 * s.zw;
        vec2 position = p - (s.xy + halfSize);
        float radius = min(shapeRadii[index], min(halfSize.x, halfSize.y));
        float dist = roundedRectangleDist(position, halfSize, radius);
        // Device pixels per logical pixel: the glints stay a hairline.
        float aa = max(1.0 / max(viewportScale, 0.0001), 0.75);

        float minHalfSize = min(halfSize.x, halfSize.y);
        float minEsp = clamp(edgeSizePixels, 0.1, minHalfSize * 0.9);
        float edgeFactor = 1.0 - clamp(abs(dist) / minEsp, 0.0, 1.0);
        float concaveFactor = 1.0 - sqrt(1.0 - pow(smoothstep(0.0, 1.0, edgeFactor), refractionNormalPow));

        sum = (refractionStrength > 0.0 && dist < 0.0)
            ? snellsRefraction(position, halfSize, radius, dist, concaveFactor)
            : sampleBlurred(uv);
        sum *= colorMatrix;
        if (dist < 0.0)
            sum.rgb = applyLiquidGlints(sum.rgb, position, halfSize, radius, dist, aa);
    }

    if (scrimMode > 0)
        sum.rgb = adaptiveScrim(sum.rgb, localLuminance(), scrimMode == 2);

    gl_FragColor = sum;
}

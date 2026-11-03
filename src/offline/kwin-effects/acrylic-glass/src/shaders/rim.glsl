uniform vec3 glowColor;
uniform float glowStrength;
uniform int edgeLighting;
uniform int rimGlow;
uniform float glowOffset;
uniform int rimGlowColorMix;
uniform int rimSpecular;
uniform float rimSpecularScale;
uniform float rimWidth;
uniform int rimAdaptToRefraction;
uniform float rimAdaptMultiplier;
uniform int cursorRim;
uniform vec2 cursorPos;          // relative to the window center, device px, +y up
uniform float cursorRimRadius;   // device px
uniform float cursorRimStrength; // 0..1 (brightness)
uniform float cursorRimThickness; // edge falloff multiplier
uniform int widgetBorder;
uniform float widgetBorderStrength; // 0..1
uniform float widgetHoverFade;      // 0..1, eased entry of the hover light
uniform float uiScale;              // device pixels per logical pixel

vec3 glassGlow(vec2 position, GlassFragment s)
{
    vec3 outline = s.color.rgb;

    if (edgeLighting == 1) {
        outline += (s.color.rgb * s.concaveFactor);
    }

    return outline;
}

vec3 glowTintFromBackdrop(vec3 glow, vec3 backdrop)
{
    vec3 glowLab = linearToOklab(srgbToLinear(clamp(glow, 0.0, 1.0)));
    vec3 backLab = linearToOklab(srgbToLinear(clamp(backdrop, 0.0, 1.0)));

    float glowChroma = length(glowLab.gb);
    float cap = max(0.30, glowChroma);
    vec2 chroma = glowLab.gb + backLab.gb * 2.0;
    float c = length(chroma);
    if (c > cap) {
        chroma *= cap / c;
        c = cap;
    }

    float added = max(c - glowChroma, 0.0);
    float lum = clamp(glowLab.x + added * (backLab.x - glowLab.x - 0.85), 0.0, 1.0);
    return linearToSrgb(clamp(oklabToLinear(vec3(lum, chroma)), 0.0, 1.0));
}

// Ported from the macOS widgets' liquidglass.frag (cornerSpec + edgeSpec).
// The widget shader works in y-down pixels; p and ndirW below are converted to that space.
vec3 widgetCornerSpec(vec2 p, float depthPx)
{
    float maxStroke = 3.0 * uiScale;
    float feather = 2.0 * uiScale;
    const float SECONDARY_INT = 0.65;

    vec2 b = blurSize * 0.5;
    vec2 restLight = vec2(-b.x, b.y) * 1.2;
    vec2 cursorW = vec2(cursorPos.x, -cursorPos.y);
    bool inside = abs(cursorPos.x) <= b.x && abs(cursorPos.y) <= b.y;
    bool hovering = widgetHoverFade > 0.0 && inside;
    vec2 lightPx = hovering ? mix(restLight, cursorW, widgetHoverFade) : restLight;
    vec2 antiLight = -lightPx;

    float taper = max(blurSize.x, blurSize.y) * 0.7;
    float primaryAtt = exp(-distance(p, lightPx) / taper);
    float secondaryAtt = exp(-distance(p, antiLight) / taper) * SECONDARY_INT;

    float tPx = max(primaryAtt, secondaryAtt) * maxStroke;
    float stroke = 1.0 - smoothstep(tPx - feather, tPx, depthPx);

    float I = stroke * widgetBorderStrength * 0.55;
    return vec3(1.0, 0.98, 0.94) * I;
}

vec3 widgetEdgeSpec(vec2 ndirW, float depthPx)
{
    float lip = 1.0 - smoothstep(0.0, 3.0 * uiScale, max(depthPx, 0.0));
    vec2 lightDir = normalize(vec2(-0.45, 0.90));
    float facing = 0.35 + 0.65 * clamp(dot(ndirW, lightDir) * 0.5 + 0.5, 0.0, 1.0);
    float I = lip * facing * widgetBorderStrength * 0.10;
    return vec3(1.0, 0.98, 0.94) * I;
}

vec3 glassOutline(vec2 position, GlassFragment s, vec3 untinted)
{
    vec3 outline = s.color.rgb;
    vec2 halfSize = blurSize * 0.5;
    float bevelScale = physicallyBasedRefraction == 1 ? refractionBevelIntensity : 1.0;
    float edgeBand = max(clamp(edgeSizePixels, 0.1, min(halfSize.x, halfSize.y) * 0.9) * bevelScale * rimAdaptMultiplier, 0.1);
    float width = rimAdaptToRefraction == 1 ? edgeBand / 3.5 : rimWidth;

    if (rimGlow == 1 && glowStrength > 0.0) {
        vec2 edgeDist = halfSize - abs(position);
        vec2 n = position / halfSize;
        float cornerBlend = min(blurSize.x, blurSize.y) * 0.25;
        float horizontalEdge = smoothstep(-cornerBlend, cornerBlend, edgeDist.x - edgeDist.y);
        vec2 lightPos = vec2(glowOffset, 1.0);
        float pointLight = max(1.0 - smoothstep(0.0, 1.0, distance(n, lightPos)),
                               1.0 - smoothstep(0.0, 1.0, distance(n, -lightPos)));
        float lightWeight = mix(horizontalEdge, pointLight, abs(glowOffset));
        float falloff = exp(s.dist / (2.0 * width));
        if (rimAdaptToRefraction == 1) {
            float edge = 1.0 - clamp(-s.dist / edgeBand, 0.0, 1.0);
            falloff = 1.0 - sqrt(1.0 - pow(smoothstep(0.0, 1.0, edge), refractionNormalPow));
        }
        float glowMask = glowStrength * lightWeight * falloff;
        vec3 tint = rimGlowColorMix == 1 ? glowTintFromBackdrop(glowColor, untinted) : glowColor;
        outline = mix(outline, tint, glowMask);
    }

    if (rimSpecular == 1 && rimSpecularScale > 0.0) {
        vec3 specColor = mix(glowColor, vec3(1.0), 0.8);
        if(glowStrength == 0.0 || dot(glowColor, glowColor) <= 0.0) {
            specColor = vec3(1.0);
        }

        float specWidth = width * rimSpecularScale;
        float edgeMask = smoothstep(0.0, -2.0 * specWidth, s.dist);
        float borderInner = smoothstep(-1.0 * specWidth, -3.0 * specWidth, s.dist);
        float edgeProfile = edgeMask - borderInner;
        float thicknessShadow = pow(edgeProfile, 0.9);
        float shadowMask = smoothstep(blurSize.y * 0.7, -blurSize.y * 0.7, position.y) *
                           smoothstep(blurSize.x * 0.7, -blurSize.x * 0.7, position.x);
        float highlightMask = smoothstep(-blurSize.y * 0.7, blurSize.y * 0.7, position.y) *
                              smoothstep(-blurSize.x * 0.7, blurSize.x * 0.7, position.x);

        outline = mix(outline, specColor, clamp(thicknessShadow * shadowMask, 0.0, 1.0));
        outline = mix(outline, specColor, clamp(thicknessShadow * highlightMask, 0.0, 1.0));
    }

    if (cursorRim == 1 && cursorRimStrength > 0.0) {
        vec3 lightColor = (glowStrength > 0.0 && dot(glowColor, glowColor) > 0.0)
            ? mix(glowColor, vec3(1.0), 0.8)
            : vec3(1.0);

        float r = max(cursorRimRadius, 1.0);
        vec2 toCursor = position - cursorPos;
        float prox = exp(-3.0 * dot(toCursor, toCursor) / (r * r));
        float core = exp(s.dist / (max(cursorRimThickness, 0.05) * width));
        float mask = clamp(prox * core * cursorRimStrength, 0.0, 1.0);
        outline = mix(outline, lightColor, mask);
    }

    if (widgetBorder == 1 && widgetBorderStrength > 0.0) {
        float depthPx = -s.dist;
        vec2 pW = vec2(position.x, -position.y);

        // Outward normal of the shape from the SDF gradient (only needed inside the 3px lip)
        vec2 ndirW = vec2(0.0);
        if (depthPx < 3.0 * uiScale) {
            vec2 e = vec2(0.75);
            vec2 g = vec2(roundedRectangleDist(position + vec2(e.x, 0.0), halfSize, cornerRadius) - roundedRectangleDist(position - vec2(e.x, 0.0), halfSize, cornerRadius),
                          roundedRectangleDist(position + vec2(0.0, e.y), halfSize, cornerRadius) - roundedRectangleDist(position - vec2(0.0, e.y), halfSize, cornerRadius));
            vec2 nUp = length(g) > 1e-4 ? normalize(g) : vec2(0.0);
            ndirW = vec2(nUp.x, -nUp.y);
        }

        outline += widgetEdgeSpec(ndirW, depthPx) + widgetCornerSpec(pW, depthPx);
    }

    return outline;
}

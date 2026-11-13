#version 440

// MacTahoe Liquid KDE — the face of a Liquid Glass bubble, over the blur KWin draws
// behind it. Measured on Apple's macOS Tahoe Control Center image
// (Control.webp, 1.21x): the body is the blurred desktop itself, ringed by
// added light, a bright line along the whole edge, then a glow fading
// inward like the lens of the glass.
//
// The rounded-rectangle SDF comes from liquidglass-kde-widgets'
// liquidglass.frag (jaxparrow07, GPL-3.0). The output is premultiplied:
// the tint over the blur, then the light added with no alpha of its own,
// so the compositor adds it to the desktop and its colour stays the
// desktop's (+45 on every channel at the edge, as measured).
// Rebuild glasssurface.frag.qsb with:
//   qsb --glsl "300 es,330" --hlsl 50 --msl 12 -o glasssurface.frag.qsb glasssurface.frag

layout(location = 0) in vec2 qt_TexCoord0;
layout(location = 0) out vec4 fragColor;

layout(std140, binding = 0) uniform buf {
    mat4  qt_Matrix;
    float qt_Opacity;
    vec2  size;              // widget size in px
    float radius;            // corner radius in px
    float roundness;         // superellipse exponent; 2 = circle
    vec4  tint;              // body tint, straight alpha
    float rimLight;          // light added by the edge line (0..1)
    float rimWidth;          // its width in px
    float glowLight;         // light added just inside it (0..1)
    float glowWidth;         // px over which the glow fades to 1/e
    float hoverLight;        // light added over the whole face on hover
};

vec3 sceneSDFAndNormal(vec2 p) {
    vec2 b = size * 0.5;
    float n = max(roundness, 2.0);
    float r = clamp(radius, 0.0, min(b.x, b.y));

    vec2 q = abs(p) - b + vec2(r);
    float qx = max(q.x, 0.0);
    float qy = max(q.y, 0.0);

    float d;
    vec2 nrm;

    if (qx <= 0.0 && qy <= 0.0) {
        // Interior: nearest silhouette is the straight edge. Level-set
        // slope is 1 already; normal is the axis with the larger q.
        d = max(q.x, q.y) - r;
        nrm = q.x >= q.y ? vec2(1.0, 0.0) : vec2(0.0, 1.0);
    } else if (qx == 0.0) {
        // Top/bottom straight edge past the corner box.
        d = qy - r;
        nrm = vec2(0.0, 1.0);
    } else if (qy == 0.0) {
        // Left/right straight edge past the corner box.
        d = qx - r;
        nrm = vec2(1.0, 0.0);
    } else {
        // Corner wedge: both qx, qy > 0.
        float qxn = pow(qx, n);
        float qyn = pow(qy, n);
        float arc = pow(qxn + qyn, 1.0 / n);
        // ∂arc/∂x = (qx/arc)^(n-1); same for y.
        float gx = pow(qx / arc, n - 1.0);
        float gy = pow(qy / arc, n - 1.0);
        float gradLen = sqrt(gx*gx + gy*gy);
        d   = (arc - r) / max(gradLen, 1e-3);
        nrm = vec2(gx, gy) / max(gradLen, 1e-3);
    }

    // q uses abs(p); flip the normal back to original-space signs.
    nrm *= sign(p + vec2(1e-20));
    return vec3(d, nrm);
}

void main() {
    vec2 p = (qt_TexCoord0 - vec2(0.5)) * size;
    vec3 dn = sceneSDFAndNormal(p);
    float d = dn.x;
    if (d > 1.5) {
        fragColor = vec4(0.0);
        return;
    }
    float depth = max(-d, 0.0);
    float mask = 1.0 - smoothstep(-0.5, 0.5, d);

    // Light from the top left: the whole edge catches it, the top-left and
    // bottom-right stretches a quarter more than the others.
    vec2 lightDir = normalize(vec2(-0.6, -1.0));
    float lit = 0.75 + 0.25 * abs(dot(dn.yz, lightDir));

    // A plateau of rimWidth px, softened over 1 px on each side of its end.
    float edge = 1.0 - smoothstep(max(rimWidth - 1.0, 0.0), rimWidth + 1.0, depth);
    float light = (edge * rimLight + exp(-depth / max(glowWidth, 0.1)) * glowLight) * lit
                + hoverLight;

    fragColor = vec4(tint.rgb * tint.a + vec3(light), tint.a) * mask * qt_Opacity;
}

// SPDX-License-Identifier: GPL-3.0-or-later
#include <QGuiApplication>
#include <QFile>
#include <QImage>
#include <QJsonArray>
#include <QJsonDocument>
#include <QJsonObject>
#include <QMatrix4x4>
#include <QOffscreenSurface>
#include <QOpenGLContext>
#include <QOpenGLBuffer>
#include <QOpenGLFramebufferObject>
#include <QOpenGLFunctions>
#include <QOpenGLShaderProgram>
#include <QOpenGLTexture>
#include <QOpenGLVertexArrayObject>
#include <QVector2D>
#include <QVector4D>
#include <QPainter>
#include <QSvgRenderer>
#include <cstdio>
#include <cstdlib>
#include <functional>
#include <cmath>

static void require(bool ok, const QString &message)
{
    if (!ok) { fprintf(stderr, "%s\n", qPrintable(message)); std::exit(1); }
}

static QByteArray read(const QString &path)
{
    QFile file(path);
    require(file.open(QIODevice::ReadOnly), path);
    return file.readAll();
}

int main(int argc, char **argv)
{
    QGuiApplication app(argc, argv);
    require(argc == 2, QStringLiteral("shader source path required"));
    QSurfaceFormat format;
    format.setVersion(3, 0);
    format.setProfile(QSurfaceFormat::CompatibilityProfile);
    QOpenGLContext context;
    context.setFormat(format);
    require(context.create(), QStringLiteral("OpenGL context unavailable"));
    QOffscreenSurface surface;
    surface.setFormat(context.format());
    surface.create();
    require(context.makeCurrent(&surface), QStringLiteral("makeCurrent failed"));
    auto *gl = context.functions();
    const int width = 192, height = 128;
    QImage backdrop(width, height, QImage::Format_RGBA8888);
    backdrop.fill(QColor(160, 160, 160));
    QOpenGLTexture texture(backdrop);
    texture.setMinMagFilters(QOpenGLTexture::Linear, QOpenGLTexture::Linear);
    texture.setWrapMode(QOpenGLTexture::ClampToEdge);
    QOpenGLFramebufferObject target(width, height);
    const QString root = QString::fromLocal8Bit(argv[1]);
    QImage reference;
    QImage dockReference;
    for (const QString suffix : {QString(), QStringLiteral("_core")}) {
        QOpenGLShaderProgram shader;
        QByteArray fragment = read(root + "/glass" + suffix + ".glsl");
        for (const QString name : {QStringLiteral("sdf"), QStringLiteral("blur"), QStringLiteral("distort"), QStringLiteral("highlight")})
            fragment.replace(("#include \"" + name + ".glsl\"").toUtf8(), read(root + "/" + name + ".glsl"));
        require(shader.addShaderFromSourceCode(QOpenGLShader::Vertex, read(root + "/glass" + suffix + ".vert")), shader.log());
        require(shader.addShaderFromSourceCode(QOpenGLShader::Fragment, fragment), shader.log());
        require(shader.link(), shader.log());
        shader.bind();
        const GLfloat points[] = {0,0, 0,1, 0,height, 0,0, width,0, 1,1, width,height, 1,0};
        QOpenGLVertexArrayObject array;
        require(array.create(), QStringLiteral("vertex array unavailable"));
        array.bind();
        QOpenGLBuffer buffer;
        require(buffer.create() && buffer.bind(), QStringLiteral("vertex buffer unavailable"));
        buffer.allocate(points, sizeof(points));
        shader.enableAttributeArray("position");
        shader.enableAttributeArray("texcoord");
        shader.setAttributeBuffer("position", GL_FLOAT, 0, 2, 4 * sizeof(GLfloat));
        shader.setAttributeBuffer("texcoord", GL_FLOAT, 2 * sizeof(GLfloat), 2, 4 * sizeof(GLfloat));
        QMatrix4x4 projection;
        projection.ortho(0, width, height, 0, -1, 1);
        shader.setUniformValue("modelViewProjectionMatrix", projection);
        shader.setUniformValue("colorMatrix", QMatrix4x4());
        shader.setUniformValue("texUnit", 0);
        shader.setUniformValue("halfpixel", QVector2D(0.5 / width, 0.5 / height));
        shader.setUniformValue("blurSize", QVector2D(width, height));
        shader.setUniformValue("box", QVector4D(width / 2, height / 2, width / 2, height / 2));
        shader.setUniformValue("cornerRadius", QVector4D(20,20,20,20));
        shader.setUniformValue("cornerSquircle", 0.0f);
        shader.setUniformValue("offset", 2.0f);
        shader.setUniformValue("opacity", 1.0f);
        shader.setUniformValue("materialOpacity", 1.0f);
        shader.setUniformValue("centerOpacity", 1.0f);
        shader.setUniformValue("dockSurface", false);
        shader.setUniformValue("backgroundSize", QVector2D(width, height));
        shader.setUniformValue("magnifyGlassStrength", 0.0f);
        shader.setUniformValue("rgbDriftStrength", 0.0f);
        shader.setUniformValue("refractionWidth", 24.0f);
        shader.setUniformValue("highlightWidth", 12.0f);
        shader.setUniformValue("highlightStrength", 0.0f);
        shader.setUniformValue("darkGradientOverlay", false);
        auto render = [&] {
            require(target.bind(), QStringLiteral("FBO failed"));
            gl->glViewport(0, 0, width, height);
            gl->glDisable(GL_BLEND);
            gl->glClearColor(0,0,0,0);
            gl->glClear(GL_COLOR_BUFFER_BIT);
            texture.bind();
            gl->glDrawArrays(GL_TRIANGLE_STRIP, 0, 4);
            gl->glFinish();
            const auto error = gl->glGetError();
            require(error == GL_NO_ERROR, QStringLiteral("OpenGL render error: %1").arg(error));
            return target.toImage();
        };
        auto image = render();
        require(qAlpha(image.pixel(0,0)) == 0, QStringLiteral("corner mask lost"));
        require(std::abs(qRed(image.pixel(96,64)) - 160) <= 1, QStringLiteral("Gaussian must preserve a constant backdrop"));
        shader.setUniformValue("darkGradientOverlay", true);
        shader.setUniformValue("gradientTop", QVector4D(0,0,0,0.38f));
        shader.setUniformValue("gradientBottom", QVector4D(0,0,0,0.02f));
        image = render();
        require(qRed(image.pixel(96,12)) + 40 < qRed(image.pixel(96,115)), QStringLiteral("black gradient must start at the top"));
        require(qAlpha(image.pixel(96,12)) == 255 && qAlpha(image.pixel(96,115)) == 255, QStringLiteral("gradient must not reveal sharp background at the bottom"));
        shader.setUniformValue("gradientTop", QVector4D(0,0,1,0.8f));
        shader.setUniformValue("gradientBottom", QVector4D(1,0,0,0.6f));
        image = render();
        require(qBlue(image.pixel(96,12)) > qRed(image.pixel(96,12)), QStringLiteral("custom top color ignored"));
        require(qRed(image.pixel(96,115)) > qBlue(image.pixel(96,115)), QStringLiteral("custom bottom color ignored"));
        shader.setUniformValue("darkGradientOverlay", false);
        shader.setUniformValue("materialOpacity", 0.5f);
        image = render();
        require(std::abs(qAlpha(image.pixel(96,64)) - 128) <= 1 && std::abs(qRed(image.pixel(96,64)) - 80) <= 1, QStringLiteral("glass output must be premultiplied"));
        shader.setUniformValue("materialOpacity", 1.0f);
        shader.setUniformValue("highlightStrength", 1.0f);
        image = render();
        require(qRed(image.pixel(96,4)) > qRed(image.pixel(96,123)), QStringLiteral("highlight must face upwards"));
        if (reference.isNull()) reference = image;
        else require(reference == image, QStringLiteral("legacy and core shaders differ"));

        shader.setUniformValue("highlightStrength", 0.0f);
        shader.setUniformValue("centerOpacity", 0.65f);
        image = render();
        require(std::abs(qAlpha(image.pixel(96,64)) - 166) <= 1,
                QStringLiteral("Applet centre must reveal the backdrop"));
        require(qAlpha(image.pixel(96,1)) > 250,
                QStringLiteral("Applet transparency must preserve the refracting rim"));
        require(std::abs(qRed(image.pixel(96,64)) - 104) <= 1,
                QStringLiteral("Applet output must remain premultiplied"));

        // Clear Dock glass must bend the backdrop across its bevel without
        // shrinking it along the long axis or displacing the centre.
        shader.setUniformValue("dockSurface", true);
        shader.setUniformValue("centerOpacity", 0.55f);
        shader.setUniformValue("highlightStrength", 0.0f);
        shader.setUniformValue("offset", 0.35f);
        image = render();
        require(std::abs(qAlpha(image.pixel(96,64)) - 140) <= 1,
                QStringLiteral("Dock centre must reveal more of the sharp backdrop"));
        require(qAlpha(image.pixel(96,1)) > 250,
                QStringLiteral("Dock bevel must retain refraction coverage"));
        require(std::abs(qRed(image.pixel(96,64)) - 88) <= 1,
                QStringLiteral("Dock output must remain premultiplied"));
        require(qAlpha(image.pixel(0,0)) == 0, QStringLiteral("Dock corner mask lost"));
        for (int y = 0; y < height; ++y) {
            for (int x = 0; x < width; ++x) {
                backdrop.setPixelColor(x, y, QColor(x, y * 2, 80));
            }
        }
        texture.setData(QOpenGLTexture::RGBA, QOpenGLTexture::UInt8, backdrop.constBits());
        const auto flatDock = render().convertToFormat(QImage::Format_RGBA8888);
        shader.setUniformValue("magnifyGlassStrength", 0.02f);
        const auto bentDock = render().convertToFormat(QImage::Format_RGBA8888);
        require(bentDock.pixel(96,64) == flatDock.pixel(96,64),
                QStringLiteral("Dock centre must remain undistorted"));
        for (const int x : {48, 144}) {
            require(std::abs(qRed(bentDock.pixel(x,4)) - qRed(flatDock.pixel(x,4))) <= 1,
                    QStringLiteral("Dock top edge must not stretch sideways"));
            const int topShift = qGreen(bentDock.pixel(x,4)) - qGreen(flatDock.pixel(x,4));
            const int bottomShift = qGreen(bentDock.pixel(x,123)) - qGreen(flatDock.pixel(x,123));
            require(std::abs(topShift) > 12 && topShift * bottomShift < 0,
                    QStringLiteral("Dock bevel must visibly bend opposite edges inward"));
        }
        if (dockReference.isNull()) dockReference = bentDock;
        else require(dockReference == bentDock, QStringLiteral("Dock differs between shader profiles"));
        shader.setUniformValue("materialOpacity", 0.0f);
        image = render();
        require(qAlpha(image.pixel(96,4)) == 0 && qRed(image.pixel(96,4)) == 0,
                QStringLiteral("Dock must respect disabled material coverage"));
        shader.setUniformValue("dockSurface", false);
        shader.setUniformValue("centerOpacity", 1.0f);
        shader.setUniformValue("materialOpacity", 1.0f);
        shader.setUniformValue("magnifyGlassStrength", 0.0f);
        shader.setUniformValue("offset", 2.0f);

        // Exercise the released preset underneath actual client fills. Checking
        // the effect alone missed the gradient disappearing behind those fills.
        QJsonObject golden;
        for (const auto &entry : QJsonDocument::fromJson(read(root + "/../presets.json")).array()) {
            if (entry.toObject()["id"] == "golden-gate") golden = entry.toObject()["values"].toObject();
        }
        require(!golden.isEmpty(), QStringLiteral("Golden Gate preset missing"));
        const float contrast = golden["Contrast"].toDouble();
        const float shift = (1 - contrast) / 2;
        shader.setUniformValue("colorMatrix", QMatrix4x4(
            contrast,0,0,0, 0,contrast,0,0, 0,0,contrast,0, shift,shift,shift,1));
        shader.setUniformValue("highlightStrength", 0.0f);
        for (const QString end : {QStringLiteral("Top"), QStringLiteral("Bottom")}) {
            const QColor color(golden["Gradient" + end + "Color"].toString());
            const auto uniform = end == "Top" ? "gradientTop" : "gradientBottom";
            shader.setUniformValue(uniform, QVector4D(color.redF(), color.greenF(), color.blueF(),
                                                      golden["Gradient" + end + "Opacity"].toDouble()));
        }
        for (const QColor backdropColor : {QColor(Qt::black), QColor(Qt::white)}) {
            backdrop.fill(backdropColor);
            texture.setData(QOpenGLTexture::RGBA, QOpenGLTexture::UInt8, backdrop.constBits());
            shader.setUniformValue("darkGradientOverlay", true);
            const auto tinted = render();
            shader.setUniformValue("darkGradientOverlay", false);
            const auto untinted = render();
            require(std::abs(qRed(tinted.pixel(96, 0)) - qRed(untinted.pixel(96, 0)) * 0.05) <= 1,
                    QStringLiteral("Golden Gate must start with 95 percent black tint"));
            for (int y = std::ceil(height * 0.5); y < height - 1; ++y) {
                require(tinted.pixel(96, y) == untinted.pixel(96, y),
                        QStringLiteral("Golden Gate tint extends past the first 50 percent"));
            }
            for (const QString mode : {QStringLiteral("Light"), QStringLiteral("Dark")}) {
                for (const QString name : {QStringLiteral("background"), QStringLiteral("launcher-search")}) {
                    QSvgRenderer renderer(root + "/../../../../plasma-theme/MacTahoeLiquidKde-" + mode
                                          + "/dialogs/" + name + ".svgz");
                    require(renderer.isValid(), QStringLiteral("popup surface unavailable"));
                    auto composite = [&](QImage surface) {
                        QPainter painter(&surface);
                        renderer.render(&painter, "center", QRectF(0, 0, width, height));
                        painter.end();
                        return surface;
                    };
                    const auto actual = composite(tinted);
                    const auto control = composite(untinted);
                    if (backdropColor == QColor(Qt::black)) {
                        require(actual == control,
                                mode + " " + name + ": black tint must preserve a black backdrop");
                    } else {
                        require(qRed(actual.pixel(96, 12)) + 8 <= qRed(control.pixel(96, 12)),
                                mode + " " + name + ": upper black tint hidden by client fill");
                        require(qRed(actual.pixel(96, 12)) + 8 <= qRed(actual.pixel(96, 115)),
                                mode + " " + name + ": top/bottom gradient lost");
                    }
                }
            }
        }
        backdrop.fill(QColor(160, 160, 160));
        texture.setData(QOpenGLTexture::RGBA, QOpenGLTexture::UInt8, backdrop.constBits());
        shader.release();
    }
    fprintf(stderr, "Shader colors, orientation, coverage, premultiplication and both profiles verified\n");
}

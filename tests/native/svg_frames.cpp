// SPDX-License-Identifier: GPL-3.0-or-later
#include <KSvg/FrameSvg>
#include <QDir>
#include <QGuiApplication>
#include <QImage>
#include <QPainter>
int main(int argc, char** argv)
{
    QGuiApplication app(argc, argv);
    if (argc != 3)
        return 2;
    const QStringList files = {"dialogs/background", "widgets/tooltip", "widgets/translucentbackground", "widgets/panel-background", "widgets/background"};
    QImage sheet(1000, 520, QImage::Format_ARGB32_Premultiplied);
    sheet.fill(Qt::transparent);
    QPainter painter(&sheet);
    for (int y = 0; y < 520; y += 16)
        for (int x = 0; x < 1000; x += 16)
            painter.fillRect(x, y, 16, 16, ((x / 16 + y / 16) % 2) ? QColor("#49687b") : QColor("#ceb886"));
    int i = 0;
    for (const auto& file : files) {
        KSvg::FrameSvg frame;
        frame.setImagePath(QString(argv[1]) + "/" + file + ".svgz");
        frame.resizeFrame(QSizeF(280, 180));
        if (!frame.isValid())
            return 3;
        const int x = 20 + (i % 3) * 330, y = 40 + (i / 3) * 250;
        painter.setPen(Qt::black);
        painter.drawText(x, y - 12, file);
        painter.drawPixmap(x, y, frame.framePixmap());
        ++i;
    }
    painter.end();
    return sheet.save(argv[2]) ? 0 : 4;
}

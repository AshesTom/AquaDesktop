// SPDX-License-Identifier: GPL-3.0-or-later
// Private-compositor input for the menu capture probe.
#include <KWayland/Client/fakeinput.h>
#include <KWayland/Client/registry.h>
#include <QCoreApplication>
#include <QDBusConnection>
#include <QDBusConnectionInterface>
#include <QDBusReply>
#include <QPointF>
#include <QThread>
#include <memory>
#include <wayland-client.h>

int main(int argc, char** argv)
{
    QCoreApplication app(argc, argv);
    const auto expected = qEnvironmentVariableIntValue("PROBE_COMPOSITOR_PID");
    auto* bus = QDBusConnection::sessionBus().interface();
    if (!bus)
        return 2;
    const QDBusReply<uint> owner = bus->servicePid("org.kde.KWin");
    if (argc != 4 || expected <= 0 || !owner.isValid() || owner.value() != uint(expected)) {
        return 2;
    }
    auto* display = wl_display_connect(nullptr);
    if (!display)
        return 3;
    {
        KWayland::Client::Registry registry;
        std::unique_ptr<KWayland::Client::FakeInput> input;
        QObject::connect(&registry, &KWayland::Client::Registry::fakeInputAnnounced,
            [&](quint32 name, quint32 version) { input.reset(registry.createFakeInput(name, version)); });
        registry.create(display);
        registry.setup();
        wl_display_roundtrip(display);
        if (!input)
            return 4;
        input->authenticate("Menu visual probe", "Input in the verified isolated compositor");
        input->requestPointerMoveAbsolute(QPointF(QString(argv[1]).toDouble(), QString(argv[2]).toDouble()));
        wl_display_roundtrip(display);
        QThread::msleep(100);
        if (QString(argv[3]) == "click") {
            input->requestPointerButtonPress(Qt::LeftButton);
            wl_display_roundtrip(display);
            QThread::msleep(100);
            input->requestPointerButtonRelease(Qt::LeftButton);
        }
        wl_display_roundtrip(display);
    }
    wl_display_disconnect(display);
}

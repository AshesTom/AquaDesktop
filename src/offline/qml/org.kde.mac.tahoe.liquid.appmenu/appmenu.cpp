/*
    AquaDesktop — AppMenu: the active application's menus for the AquaDesktop
    shell's menu bar. The menu import and popup handling follow the Global
    Menu plasmoid (appmenumodel.cpp / appmenuapplet.cpp, from Plasma's
    appmenu applet by Kai Uwe Broulik and Chinmoy Ranjan Pradhan).

    SPDX-License-Identifier: GPL-3.0-or-later
*/
#include "appmenu.h"

#include <KColorScheme>
#include <KLocalizedString>
#include <KUser>
#include <QAction>
#include <QDBusConnection>
#include <QDBusConnectionInterface>
#include <QDBusMessage>
#include <QDBusServiceWatcher>
#include <QGuiApplication>
#include <QIcon>
#include <QKeyEvent>
#include <QMenu>
#include <QMouseEvent>
#include <QProcess>
#include <QQuickWindow>
#include <QScreen>
#include <QStandardPaths>
#include <QTimer>
#include <QWindow>

#include <optional>
#include <utility>

#include <abstracttasksmodel.h>
#include <tasksmodel.h>

#include "dbusmenuimporter.h"

int AppMenu::s_instances = 0;

namespace
{
// Registered while a menu bar exists: apps and KDE's appmenu module take
// it as the sign that a global menu is on screen.
const QString kViewService = QStringLiteral("org.kde.kappmenuview");

constexpr int kWindowMenu = -2;
constexpr int kAppleMenu = -3;

class Importer : public DBusMenuImporter
{
public:
    using DBusMenuImporter::DBusMenuImporter;

protected:
    QIcon iconForName(const QString &name) override
    {
        return QIcon::fromTheme(name);
    }
};

// The shell runs for the whole session, so its widget style may still
// hold the previous appearance's palette after a light/dark switch;
// kdeglobals on disk is always current (as in the Global Menu plasmoid).
void applyActiveColorScheme(QWidget *menu)
{
    QPalette pal = menu->palette();
    const KColorScheme window(QPalette::Active, KColorScheme::Window);
    const KColorScheme view(QPalette::Active, KColorScheme::View);
    const KColorScheme selection(QPalette::Active, KColorScheme::Selection);
    pal.setBrush(QPalette::Window, window.background());
    pal.setBrush(QPalette::WindowText, window.foreground());
    pal.setBrush(QPalette::Base, view.background());
    pal.setBrush(QPalette::Text, view.foreground());
    pal.setBrush(QPalette::ButtonText, window.foreground());
    pal.setBrush(QPalette::Highlight, selection.background());
    pal.setBrush(QPalette::HighlightedText, selection.foreground());
    menu->setPalette(pal);
}
void run(const QString &program)
{
    QProcess::startDetached(program, {});
}

// Queued, so the menu releases its grabs before a confirmation dialog.
void callSessionBus(const QString &service, const QString &path, const QString &interface, const QString &method)
{
    QTimer::singleShot(0, qApp, [=] {
        QDBusConnection::sessionBus().asyncCall(QDBusMessage::createMethodCall(service, path, interface, method));
    });
}
} // namespace

AppMenu::AppMenu(QObject *parent)
    : QObject(parent)
    , m_tasks(new TaskManager::TasksModel(this))
    , m_serviceWatcher(new QDBusServiceWatcher(this))
{
    if (++s_instances == 1) {
        QDBusConnection::sessionBus().interface()->registerService(kViewService,
                                                                   QDBusConnectionInterface::QueueService,
                                                                   QDBusConnectionInterface::DontAllowReplacement);
    }

    using TaskManager::AbstractTasksModel;
    connect(m_tasks, &TaskManager::TasksModel::activeTaskChanged, this, &AppMenu::onActiveWindowChanged);
    connect(m_tasks, &TaskManager::TasksModel::countChanged, this, &AppMenu::onActiveWindowChanged);
    connect(m_tasks, &TaskManager::TasksModel::dataChanged, this,
            [this](const QModelIndex &, const QModelIndex &, const QList<int> &roles) {
                if (roles.isEmpty() || roles.contains(AbstractTasksModel::ApplicationMenuServiceName)
                    || roles.contains(AbstractTasksModel::ApplicationMenuObjectPath)
                    || roles.contains(AbstractTasksModel::AppName)) {
                    onActiveWindowChanged();
                }
            });

    m_serviceWatcher->setConnection(QDBusConnection::sessionBus());
    connect(m_serviceWatcher, &QDBusServiceWatcher::serviceUnregistered, this, [this](const QString &service) {
        if (service == m_service) {
            setMenuSource({}, {});
        }
    });

    onActiveWindowChanged();
}

AppMenu::~AppMenu()
{
    if (--s_instances == 0) {
        QDBusConnection::sessionBus().interface()->unregisterService(kViewService);
    }
}

QString AppMenu::appName() const
{
    const QModelIndex active = m_tasks->activeTask();
    if (!active.isValid()) {
        return {};
    }
    // The shell's own windows (About This Computer) are not an app the
    // user switched to: no name, as the Global Menu does for plasmashell.
    if (m_tasks->data(active, TaskManager::AbstractTasksModel::AppPid).toLongLong() == QCoreApplication::applicationPid()) {
        return {};
    }
    return m_tasks->data(active, TaskManager::AbstractTasksModel::AppName).toString();
}

QStringList AppMenu::titles() const
{
    return m_titles;
}

int AppMenu::currentIndex() const
{
    return m_currentIndex;
}

QQuickItem *AppMenu::buttonRow() const
{
    return m_buttonRow;
}

void AppMenu::setButtonRow(QQuickItem *row)
{
    if (m_buttonRow != row) {
        m_buttonRow = row;
        Q_EMIT buttonRowChanged();
    }
}

void AppMenu::setCurrentIndex(int index)
{
    if (m_currentIndex != index) {
        m_currentIndex = index;
        Q_EMIT currentIndexChanged();
    }
}

void AppMenu::onActiveWindowChanged()
{
    const QModelIndex active = m_tasks->activeTask();
    setMenuSource(m_tasks->data(active, TaskManager::AbstractTasksModel::ApplicationMenuServiceName).toString(),
                  m_tasks->data(active, TaskManager::AbstractTasksModel::ApplicationMenuObjectPath).toString());
    Q_EMIT activeChanged();
}

void AppMenu::setMenuSource(const QString &service, const QString &path)
{
    if (service == m_service && path == m_path) {
        if (m_importer) {
            QMetaObject::invokeMethod(m_importer.get(), qOverload<>(&DBusMenuImporter::updateMenu), Qt::QueuedConnection);
        }
        return;
    }

    close();
    m_service = service;
    m_path = path;
    m_menu.clear();
    m_importer.reset();

    if (service.isEmpty() || path.isEmpty()) {
        m_serviceWatcher->setWatchedServices({});
        scheduleRebuild();
        return;
    }

    m_serviceWatcher->setWatchedServices({service});
    m_importer = std::make_unique<Importer>(service, path);
    connect(m_importer.get(), &DBusMenuImporter::menuUpdated, this, [this](QMenu *menu) {
        // The open menu: the importer put its new entries in the source.
        if (menu == m_source && isOpen()) {
            const auto added = menu->actions();
            for (QAction *action : added) {
                menu->removeAction(action);
                m_proxy->addAction(action);
            }
            m_proxy->adjustSize();
            return;
        }
        if (!m_importer || menu != m_importer->menu()) {
            return;
        }
        m_menu = menu;
        const auto actions = m_menu->actions();
        for (QAction *action : actions) {
            connect(action, &QAction::changed, this, &AppMenu::scheduleRebuild, Qt::UniqueConnection);
            connect(action, &QAction::destroyed, this, &AppMenu::scheduleRebuild, Qt::UniqueConnection);
            // Fill the submenus now, so they open complete at once.
            if (action->menu()) {
                m_importer->updateMenu(action->menu());
            }
        }
        scheduleRebuild();
    });
    // An app asking for one of its menus (Alt+F in a Qt app).
    connect(m_importer.get(), &DBusMenuImporter::actionActivationRequested, this, [this](QAction *action) {
        const int index = visibleActions().indexOf(action);
        if (index >= 0) {
            Q_EMIT requestActivateIndex(index);
        }
    });
    QMetaObject::invokeMethod(m_importer.get(), qOverload<>(&DBusMenuImporter::updateMenu), Qt::QueuedConnection);
    scheduleRebuild();
}

void AppMenu::scheduleRebuild()
{
    if (m_rebuildPending) {
        return;
    }
    m_rebuildPending = true;
    QTimer::singleShot(0, this, &AppMenu::rebuildTitles);
}

QList<QAction *> AppMenu::visibleActions() const
{
    QList<QAction *> result;
    if (!m_menu) {
        return result;
    }
    const auto actions = m_menu->actions();
    for (QAction *action : actions) {
        if (action->isVisible() && !action->isSeparator() && !action->text().isEmpty()) {
            result << action;
        }
    }
    return result;
}

void AppMenu::rebuildTitles()
{
    m_rebuildPending = false;
    QStringList titles;
    const auto actions = visibleActions();
    for (QAction *action : actions) {
        titles << action->text();
    }
    if (titles != m_titles) {
        m_titles = titles;
        Q_EMIT titlesChanged();
    }
}

bool AppMenu::isOpen() const
{
    return m_proxy && m_proxy->isVisible();
}

void AppMenu::giveBack()
{
    if (!m_proxy) {
        return;
    }
    const auto actions = m_proxy->actions();
    for (QAction *action : actions) {
        m_proxy->removeAction(action);
        if (m_source) {
            m_source->addAction(action);
        }
    }
    m_source = nullptr;
}

void AppMenu::lend(QMenu *source)
{
    giveBack();
    m_source = source;
    const auto actions = source->actions();
    for (QAction *action : actions) {
        source->removeAction(action);
        m_proxy->addAction(action);
    }
}

void AppMenu::popup(QMenu *source, int index, QQuickItem *anchor)
{
    if (!source || !anchor || !anchor->window()) {
        return;
    }
    if (!m_proxy) {
        m_proxy = std::make_unique<QMenu>();
        m_proxy->installEventFilter(this);
        m_proxy->setProperty("_breeze_menu_seamless_edges", QVariant::fromValue(Qt::Edges(Qt::TopEdge)));
        connect(m_proxy.get(), &QMenu::aboutToHide, this, [this] {
            setCurrentIndex(-1);
        });
    }

    // Every menu shows in the one proxy, which takes the source's actions:
    // switching menus (pointer or Left / Right) only swaps its contents and
    // moves it. KWin refuses a new grabbing popup opened on a key press.
    // An app menu is asked for its current entries first (AboutToShow,
    // which the source menu never gets now); menuUpdated brings them.
    if (m_importer && source != m_windowMenu.get() && source != m_appleMenu.get()) {
        m_importer->updateMenu(source);
    }
    lend(source);
    applyActiveColorScheme(m_proxy.get());
    m_proxy->setMinimumWidth(0);
    // The Apple menu's width, as in the Global Menu plasmoid.
    if (index == kAppleMenu) {
        m_proxy->setMinimumWidth(m_proxy->sizeHint().width() + 55);
    }

    m_lastPointer = {};
    // Opened by a press: its release comes to the menu next.
    m_skipRelease = QGuiApplication::mouseButtons() != Qt::NoButton;

    QQuickWindow *window = anchor->window();
    // Flush with the bar, under the button's left edge (kept on screen).
    QPoint pos = window->mapToGlobal(anchor->mapToScene(QPointF(0, anchor->height())).toPoint());
    m_proxy->adjustSize();
    if (QScreen *screen = window->screen()) {
        const QRect geo = screen->geometry();
        pos.setX(qBound(geo.x(), pos.x(), geo.x() + geo.width() - m_proxy->width()));
    }

    if (m_proxy->isVisible()) {
        // Wayland: an xdg_popup reposition, a configure round trip later.
        m_proxy->move(pos);
    } else {
        m_proxy->winId();
        m_proxy->windowHandle()->setTransientParent(window);
        m_proxy->popup(pos);
    }
    // QMenu shows nothing for a menu without entries (KWrite's Edit menu
    // with no document).
    setCurrentIndex(m_proxy->isVisible() ? index : -1);
}

void AppMenu::open(int index, QQuickItem *anchor)
{
    const auto actions = visibleActions();
    if (index < 0 || index >= actions.size()) {
        return;
    }
    // Its title clicked again: closed, as on macOS.
    if (m_currentIndex == index && isOpen()) {
        close();
        return;
    }
    QAction *action = actions.at(index);
    if (!action->menu()) {
        // A top-level entry without a submenu acts at once.
        close();
        action->trigger();
        return;
    }
    popup(action->menu(), index, anchor);
}

void AppMenu::openWindowMenu(QQuickItem *anchor)
{
    // Its title clicked again: closed, as on macOS.
    if (m_currentIndex == kWindowMenu && isOpen()) {
        close();
        return;
    }
    const QPersistentModelIndex task(m_tasks->activeTask());
    if (!task.isValid()) {
        return;
    }
    // Its actions may still be lent to the proxy.
    giveBack();
    if (!m_windowMenu) {
        m_windowMenu = std::make_unique<QMenu>();
    }
    QMenu *menu = m_windowMenu.get();
    menu->clear();

    using TaskManager::AbstractTasksModel;
    const auto flag = [this, &task](int role) {
        return m_tasks->data(task, role).toBool();
    };
    TaskManager::TasksModel *tasks = m_tasks;

    QAction *close = menu->addAction(QIcon::fromTheme(QStringLiteral("window-close")), i18n("Close"));
    close->setEnabled(flag(AbstractTasksModel::IsClosable));
    connect(close, &QAction::triggered, tasks, [tasks, task] {
        tasks->requestClose(task);
    });
    menu->addSeparator();

    QAction *minimize = menu->addAction(QIcon::fromTheme(QStringLiteral("window-minimize")), i18n("Minimize"));
    minimize->setEnabled(flag(AbstractTasksModel::IsMinimizable));
    connect(minimize, &QAction::triggered, tasks, [tasks, task] {
        tasks->requestToggleMinimized(task);
    });
    const bool maximized = flag(AbstractTasksModel::IsMaximized);
    QAction *zoom = menu->addAction(QIcon::fromTheme(maximized ? QStringLiteral("window-restore") : QStringLiteral("window-maximize")),
                                    maximized ? i18n("Restore") : i18n("Zoom"));
    zoom->setEnabled(flag(AbstractTasksModel::IsMaximizable));
    connect(zoom, &QAction::triggered, tasks, [tasks, task] {
        tasks->requestToggleMaximized(task);
    });
    menu->addSeparator();

    const bool fullScreen = flag(AbstractTasksModel::IsFullScreen);
    QAction *full = menu->addAction(QIcon::fromTheme(QStringLiteral("view-fullscreen")),
                                    fullScreen ? i18n("Exit Full Screen") : i18n("Enter Full Screen"));
    full->setEnabled(flag(AbstractTasksModel::IsFullScreenable));
    connect(full, &QAction::triggered, tasks, [tasks, task] {
        tasks->requestToggleFullScreen(task);
    });

    popup(menu, kWindowMenu, anchor);
}

void AppMenu::openAppleMenu(QQuickItem *anchor)
{
    // Its title clicked again: closed, as on macOS.
    if (m_currentIndex == kAppleMenu && isOpen()) {
        close();
        return;
    }
    giveBack();
    if (!m_appleMenu) {
        m_appleMenu = std::make_unique<QMenu>();
    }
    QMenu *menu = m_appleMenu.get();
    menu->clear();

    const auto icon = [](const char *name) {
        return QIcon::fromTheme(QString::fromLatin1(name));
    };
    menu->addAction(icon("computer"), i18n("About This Computer"), this, [this] {
        QTimer::singleShot(0, this, &AppMenu::aboutRequested);
    });
    menu->addSeparator();
    menu->addAction(icon("preferences-system"), i18n("System Settings…"), [] {
        run(QStringLiteral("systemsettings"));
    });
    if (!QStandardPaths::findExecutable(QStringLiteral("plasma-discover")).isEmpty()) {
        menu->addAction(icon("software-store-symbolic"), i18n("App Store…"), [] {
            run(QStringLiteral("plasma-discover"));
        });
    }
    menu->addSeparator();
    menu->addAction(icon("dialog-cancel"), i18n("Force Quit…"), [] {
        callSessionBus(QStringLiteral("org.kde.KWin"), QStringLiteral("/KWin"), QStringLiteral("org.kde.KWin"),
                       QStringLiteral("killWindow"));
    });
    menu->addSeparator();
    menu->addAction(icon("system-suspend"), i18n("Sleep"), [] {
        callSessionBus(QStringLiteral("org.kde.Solid.PowerManagement"),
                       QStringLiteral("/org/kde/Solid/PowerManagement/Actions/SuspendSession"),
                       QStringLiteral("org.kde.Solid.PowerManagement.Actions.SuspendSession"), QStringLiteral("suspendToRam"));
    });
    const auto prompt = [](const char *method) {
        callSessionBus(QStringLiteral("org.kde.LogoutPrompt"), QStringLiteral("/LogoutPrompt"),
                       QStringLiteral("org.kde.LogoutPrompt"), QString::fromLatin1(method));
    };
    menu->addAction(icon("system-reboot"), i18n("Restart…"), [prompt] {
        prompt("promptReboot");
    });
    menu->addAction(icon("system-shutdown"), i18n("Shut Down…"), [prompt] {
        prompt("promptShutDown");
    });
    menu->addSeparator();
    menu->addAction(icon("system-lock-screen"), i18n("Lock Screen"), [] {
        callSessionBus(QStringLiteral("org.freedesktop.ScreenSaver"), QStringLiteral("/ScreenSaver"),
                       QStringLiteral("org.freedesktop.ScreenSaver"), QStringLiteral("Lock"));
    });
    const QString firstName = KUser().property(KUser::FullName).toString().section(QLatin1Char(' '), 0, 0);
    menu->addAction(icon("user-identity"), i18n("Log Out %1…", firstName), [prompt] {
        prompt("promptLogout");
    });

    popup(menu, kAppleMenu, anchor);
}

void AppMenu::close()
{
    if (m_proxy) {
        m_proxy->hide();
    }
}

std::optional<int> AppMenu::buttonIndexAt(const QPointF &globalPos) const
{
    if (!m_buttonRow || !m_buttonRow->window()) {
        return std::nullopt;
    }
    const QPointF inRow = m_buttonRow->mapFromScene(m_buttonRow->window()->mapFromGlobal(globalPos));
    QQuickItem *item = m_buttonRow->childAt(inRow.x(), inRow.y());
    if (!item) {
        return std::nullopt;
    }
    bool ok = false;
    const int index = item->property("buttonIndex").toInt(&ok);
    return ok ? std::optional<int>(index) : std::nullopt;
}

bool AppMenu::eventFilter(QObject *watched, QEvent *event)
{
    auto *menu = qobject_cast<QMenu *>(watched);
    if (!menu || menu != m_proxy.get()) {
        return false;
    }

    if (event->type() == QEvent::KeyPress) {
        const int key = static_cast<QKeyEvent *>(event)->key();
        if (key != Qt::Key_Left && key != Qt::Key_Right) {
            return false;
        }
        // Right opens a highlighted submenu first.
        if (key == Qt::Key_Right && menu->activeAction() && menu->activeAction()->menu()) {
            return false;
        }
        QList<int> order{kAppleMenu, kWindowMenu};
        for (int i = 0; i < m_titles.size(); ++i) {
            order << i;
        }
        const int at = order.indexOf(m_currentIndex);
        const int next = at + (key == Qt::Key_Left ? -1 : 1);
        if (at >= 0 && next >= 0 && next < order.size()) {
            Q_EMIT requestActivateIndex(order.at(next));
        }
        return true;
    }

    // A press on the bar never reaches the menu or the bar while it is
    // open, only its release: a click on the open menu's title closes it.
    if (event->type() == QEvent::MouseButtonRelease) {
        if (std::exchange(m_skipRelease, false)) {
            return false;
        }
        if (buttonIndexAt(static_cast<QMouseEvent *>(event)->globalPosition()) == m_currentIndex) {
            close();
        }
        return false;
    }

    if (event->type() == QEvent::MouseMove) {
        const auto *mouse = static_cast<QMouseEvent *>(event);
        // Only a real move: the menu moving under a still pointer (Left /
        // Right) sends one too, which would bring back the menu under it.
        const QPointF last = std::exchange(m_lastPointer, mouse->globalPosition());
        if (last.isNull() || last == mouse->globalPosition()) {
            return false;
        }
        const std::optional<int> index = buttonIndexAt(mouse->globalPosition());
        if (index && *index != m_currentIndex) {
            Q_EMIT requestActivateIndex(*index);
        }
    }
    return false;
}

#include "moc_appmenu.cpp"

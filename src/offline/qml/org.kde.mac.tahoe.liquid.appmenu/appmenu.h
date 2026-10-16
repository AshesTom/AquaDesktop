/*
    AquaDesktop — AppMenu: the active application's menus for the AquaDesktop
    shell's menu bar (the Global Menu plasmoid's model, outside Plasma).

    SPDX-License-Identifier: GPL-3.0-or-later
*/
#pragma once

#include <QObject>
#include <QPointer>
#include <QQuickItem>
#include <QStringList>

#include <memory>
#include <optional>
#include <qqmlregistration.h>

class QAction;
class QDBusServiceWatcher;
class QMenu;
class DBusMenuImporter;

namespace TaskManager
{
class TasksModel;
}

/*
    Follows the active window (KDE's TasksModel) and imports the menus it
    publishes over the AppMenu D-Bus protocol (GTK and Qt apps both do).

    `titles` are the top-level menus (File, Edit, View…); open(i, button)
    drops menu i under its button as a native QMenu, so it gets the Kvantum
    menu style. Menus opened from the bar share one "current" slot:
    `currentIndex` is the open one (-1 for none). By the bar's convention -3
    is the Apple menu (openAppleMenu()) and -2 the app-name menu
    (openWindowMenu()).

    While a menu is open, moving the pointer over another button of
    `buttonRow` (children with a `buttonIndex` property) or pressing
    Left / Right emits requestActivateIndex(index): the bar then opens that
    one, as macOS does.
*/
class AppMenu : public QObject
{
    Q_OBJECT
    QML_ELEMENT

    // The active application's name (macOS shows it in bold).
    Q_PROPERTY(QString appName READ appName NOTIFY activeChanged)
    // Its top-level menus, the visible ones.
    Q_PROPERTY(QStringList titles READ titles NOTIFY titlesChanged)
    Q_PROPERTY(int currentIndex READ currentIndex NOTIFY currentIndexChanged)
    Q_PROPERTY(QQuickItem *buttonRow READ buttonRow WRITE setButtonRow NOTIFY buttonRowChanged)

public:
    explicit AppMenu(QObject *parent = nullptr);
    ~AppMenu() override;

    QString appName() const;
    QStringList titles() const;
    int currentIndex() const;
    QQuickItem *buttonRow() const;
    void setButtonRow(QQuickItem *row);

    // Menu `index` of `titles`, under `anchor`.
    Q_INVOKABLE void open(int index, QQuickItem *anchor);
    // The active window's menu (Close, Minimize, Zoom, Full Screen).
    Q_INVOKABLE void openWindowMenu(QQuickItem *anchor);
    // The Apple menu (About This Computer… Log Out), the Global Menu
    // plasmoid's. About emits aboutRequested(); the rest runs from here.
    Q_INVOKABLE void openAppleMenu(QQuickItem *anchor);
    Q_INVOKABLE void close();

Q_SIGNALS:
    void activeChanged();
    void titlesChanged();
    void currentIndexChanged();
    void buttonRowChanged();
    void requestActivateIndex(int index);
    void aboutRequested();

protected:
    bool eventFilter(QObject *watched, QEvent *event) override;

private:
    void onActiveWindowChanged();
    void setMenuSource(const QString &service, const QString &path);
    void rebuildTitles();
    void scheduleRebuild();
    void popup(QMenu *source, int index, QQuickItem *anchor);
    void lend(QMenu *source);
    void giveBack();
    bool isOpen() const;
    // The `buttonIndex` of the bar button under a global position.
    std::optional<int> buttonIndexAt(const QPointF &globalPos) const;
    void setCurrentIndex(int index);
    QList<QAction *> visibleActions() const;

    TaskManager::TasksModel *m_tasks;
    QDBusServiceWatcher *m_serviceWatcher;
    std::unique_ptr<DBusMenuImporter> m_importer;
    QPointer<QMenu> m_menu;
    QString m_service;
    QString m_path;
    QStringList m_titles;
    bool m_rebuildPending = false;

    int m_currentIndex = -1;
    // The menu on screen, showing the actions of m_source (see popup()).
    std::unique_ptr<QMenu> m_proxy;
    QPointer<QMenu> m_source;
    // Sources for the app-name and Apple menus.
    std::unique_ptr<QMenu> m_windowMenu;
    std::unique_ptr<QMenu> m_appleMenu;
    QPointer<QQuickItem> m_buttonRow;
    QPointF m_lastPointer;
    bool m_skipRelease = false;

    static int s_instances;
};

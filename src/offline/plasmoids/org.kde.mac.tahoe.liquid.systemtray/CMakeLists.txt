# MacTahoe Liquid KDE — Plasma's system tray (plasma-workspace 6.7.5,
# applets/systemtray) built standalone under its own ID, so the tray and its
# popup can look like macOS. The C++ side is upstream's, unchanged; see
# UPSTREAM.md.
cmake_minimum_required(VERSION 3.20)
project(mac-tahoe-systemtray VERSION 1.0)

set(QT_MIN_VERSION "6.6.0")
set(KF_MIN_VERSION "6.0.0")

find_package(ECM ${KF_MIN_VERSION} REQUIRED NO_MODULE)
set(CMAKE_MODULE_PATH ${ECM_MODULE_PATH})

include(KDEInstallDirs6)
include(KDECMakeSettings)
include(KDECompilerSettings NO_POLICY_SCOPE)
include(ECMQtDeclareLoggingCategory)
include(ECMQmlModule)
include(FeatureSummary)

find_package(Qt6 ${QT_MIN_VERSION} CONFIG REQUIRED COMPONENTS
    Core
    DBus
    Gui
    GuiPrivate
    Qml
    Quick
    Widgets
)
find_package(KF6 ${KF_MIN_VERSION} REQUIRED COMPONENTS
    Config
    CoreAddons
    I18n
    IconThemes
    ItemModels
    JobWidgets
    KIO
    Notifications
    Service
    StatusNotifierItem
    WindowSystem
    XmlGui
)
find_package(Plasma REQUIRED)
find_package(PlasmaQuick REQUIRED)

set(CMAKE_CXX_STANDARD 20)
set(CMAKE_CXX_STANDARD_REQUIRED ON)
# Reuse Plasma's complete, distribution-provided translation catalog.
add_definitions(-DTRANSLATION_DOMAIN="plasma_applet_org.kde.plasma.systemtray")

# upstream's config-X11.h: the X11-only code path stays off (Wayland only).
file(WRITE ${CMAKE_CURRENT_BINARY_DIR}/config-X11.h "#define HAVE_X11 0\n")
include_directories(${CMAKE_CURRENT_BINARY_DIR} ${CMAKE_CURRENT_SOURCE_DIR})

# The same libdbusmenuqt as the Global Menu (upstream's, unchanged).
add_subdirectory(
    ${CMAKE_CURRENT_SOURCE_DIR}/../org.kde.mac.tahoe.liquid.globalmenu/libdbusmenuqt
    ${CMAKE_CURRENT_BINARY_DIR}/libdbusmenuqt
)

set(systemtray_SRCS
    dbusserviceobserver.cpp dbusserviceobserver.h
    plasmoidregistry.cpp plasmoidregistry.h
    statusnotifieritemhost.cpp statusnotifieritemhost.h
    statusnotifieritemsource.cpp statusnotifieritemsource.h
    systemtraysettings.cpp systemtraysettings.h
    systemtraytypes.cpp
    systemtraymodel.cpp
    sortedsystemtraymodel.cpp sortedsystemtraymodel.h
)

qt_add_dbus_interface(systemtray_SRCS ${KSTATUSNOTIFIERITEM_DBUS_INTERFACES_DIR}/kf6_org.kde.StatusNotifierWatcher.xml statusnotifierwatcher_interface)
qt_add_dbus_interface(systemtray_SRCS dbus/org.freedesktop.DBus.Properties.xml dbusproperties)

set(statusnotifieritem_xml ${KSTATUSNOTIFIERITEM_DBUS_INTERFACES_DIR}/kf6_org.kde.StatusNotifierItem.xml)
set_source_files_properties(${statusnotifieritem_xml} PROPERTIES
   NO_NAMESPACE false
   INCLUDE "systemtraytypes.h"
   CLASSNAME OrgKdeStatusNotifierItem
)
qt_add_dbus_interface(systemtray_SRCS ${statusnotifieritem_xml} statusnotifieritem_interface)

ecm_qt_declare_logging_category(systemtray_SRCS HEADER debug.h
                                            IDENTIFIER SYSTEM_TRAY
                                            CATEGORY_NAME kde.systemtray
                                            DEFAULT_SEVERITY Info
                                            DESCRIPTION "plasma applet systemtray")
add_library(systemtray_static STATIC ${systemtray_SRCS})
target_link_libraries(systemtray_static
    PUBLIC
        Qt::DBus
        Qt::Gui
        Qt::GuiPrivate
        Qt::Quick
        KF6::ConfigCore
        KF6::IconThemes
        KF6::I18n
        KF6::KIOGui
        KF6::JobWidgets
        KF6::Service
        KF6::ItemModels
        KF6::WindowSystem
        KF6::XmlGui
        Plasma::Plasma
        Plasma::PlasmaQuick
        dbusmenuqt
)
set_property(TARGET systemtray_static PROPERTY POSITION_INDEPENDENT_CODE ON)

set(QT_QML_NO_CACHEGEN TRUE)

plasma_add_applet(org.kde.mac.tahoe.liquid.systemtray
    CPP_SOURCES
        systemtray.cpp
    QML_SOURCES
        qml/AbstractItem.qml
        qml/BackgroundAppItem.qml
        qml/ConfigGeneral.qml
        qml/CurrentItemHighLight.qml
        qml/ExpanderArrow.qml
        qml/ItemLoader.qml
        qml/PlasmoidItem.qml
        qml/PulseAnimation.qml
        qml/SystemTrayState.qml
        qml/CompactApplet.qml
        qml/config.qml
        qml/ExpandedRepresentation.qml
        qml/HiddenItemsView.qml
        qml/main.qml
        qml/PlasmoidPopupsContainer.qml
        qml/StatusNotifierItem.qml
    RESOURCES
        main.xml
)
target_link_libraries(org.kde.mac.tahoe.liquid.systemtray PRIVATE systemtray_static)

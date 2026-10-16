# AquaDesktop — Plasma's notifications applet (plasma-workspace 6.7.5,
# applets/notifications) built standalone under its own ID, so its popups
# can look like macOS Tahoe banners. The C++ side is upstream's, unchanged
# but for the QML module URI; see UPSTREAM.md.
cmake_minimum_required(VERSION 3.20)
project(mac-tahoe-notifications VERSION 1.0)

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
    Gui
    Qml
    Quick
    WaylandClient
)
find_package(KF6 ${KF_MIN_VERSION} REQUIRED COMPONENTS
    Config
    CoreAddons
    GlobalAccel
    I18n
    KIO
    Notifications
    WindowSystem
)
find_package(Plasma REQUIRED)
find_package(PlasmaQuick REQUIRED)
find_package(LibNotificationManager REQUIRED)
find_package(Wayland REQUIRED COMPONENTS Client)

set(CMAKE_CXX_STANDARD 20)
set(CMAKE_CXX_STANDARD_REQUIRED ON)
# Reuse Plasma's complete, distribution-provided translation catalog.
add_definitions(-DTRANSLATION_DOMAIN="plasma_applet_org.kde.plasma.notifications")

set(QT_QML_NO_CACHEGEN TRUE)

plasma_add_applet(org.kde.mac.tahoe.liquid.notifications
    QML_ARGS DEPENDENCIES QtCore QtQuick org.kde.plasma.core
)

target_sources(org.kde.mac.tahoe.liquid.notifications PRIVATE
    notificationapplet.cpp
    notificationwindow.cpp
    draghelper.cpp
    fileinfo.cpp
    filemenu.cpp
    globalshortcuts.cpp
    jobaggregator.cpp
    thumbnailer.cpp
    notificationapplet.h
    notificationwindow.h
    draghelper.h
    fileinfo.h
    filemenu.h
    globalshortcuts.h
    jobaggregator.h
    thumbnailer.h
)

ecm_target_qml_sources(org.kde.mac.tahoe.liquid.notifications SOURCES
    components/ActionContainer.qml
    components/Body.qml
    components/DraggableFileArea.qml
    components/EditContextMenu.qml
    components/FooterLoader.qml
    components/HeadingButtons.qml
    components/Icon.qml
    components/JobDetails.qml
    components/JobIconItem.qml
    components/JobItem.qml
    components/ModelInterface.qml
    components/NotificationHeader.qml
    components/NotificationReplyField.qml
    components/SpeedChart.qml
    components/Summary.qml
    components/ThumbnailStrip.qml
    PATH components
)

ecm_target_qml_sources(org.kde.mac.tahoe.liquid.notifications SOURCES
    delegates/BaseDelegate.qml
    delegates/DelegateHistoryGrouped.qml
    delegates/DelegateHistory.qml
    delegates/DelegatePopup.qml
    PATH delegates
)

set_source_files_properties(global/Globals.qml PROPERTIES QT_QML_SINGLETON_TYPE ON)

ecm_target_qml_sources(org.kde.mac.tahoe.liquid.notifications SOURCES
    global/Globals.qml
    global/PulseAudio.qml
    PATH global
)

ecm_target_qml_sources(org.kde.mac.tahoe.liquid.notifications SOURCES
    CompactRepresentation.qml
    DraggableDelegate.qml
    FullRepresentation.qml
    main.qml
    NotificationPopup.qml
)

# The plasma-shell protocol ships with the fork (protocols/), so the build
# does not need plasma-wayland-protocols installed.
qt_generate_wayland_protocol_client_sources(org.kde.mac.tahoe.liquid.notifications
    FILES
        "${CMAKE_CURRENT_SOURCE_DIR}/protocols/plasma-shell.xml"
        "${Wayland_DATADIR}/wayland.xml"
    PRIVATE_CODE
)

target_link_libraries(org.kde.mac.tahoe.liquid.notifications PRIVATE
    Qt::Gui
    Qt::Quick
    KF6::ConfigGui
    KF6::I18n
    Plasma::Plasma
    Plasma::PlasmaQuick
    KF6::CoreAddons
    KF6::GlobalAccel
    KF6::KIOGui
    KF6::KIOWidgets
    KF6::Notifications
    KF6::WindowSystem
    PW::LibNotificationManager
    Wayland::Client
)

ecm_qt_declare_logging_category(org.kde.mac.tahoe.liquid.notifications
    HEADER notifications_debug.h
    IDENTIFIER PLASMA_APPLET_NOTIFICATIONS_DEBUG
    CATEGORY_NAME org.kde.mac.tahoe.liquid.notifications
    DESCRIPTION "AquaDesktop notifications applet"
)

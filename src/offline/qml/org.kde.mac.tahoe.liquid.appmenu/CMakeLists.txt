# AquaDesktop — org.kde.mac.tahoe.liquid.appmenu: the active application's
# menus (the AppMenu D-Bus protocol) for the AquaDesktop shell's menu bar,
# outside Plasma. It shares libdbusmenuqt with the Global Menu plasmoid.
cmake_minimum_required(VERSION 3.20)
project(mac-tahoe-appmenu VERSION 1.0)

set(QT_MIN_VERSION "6.6.0")
set(KF_MIN_VERSION "6.0.0")

find_package(ECM ${KF_MIN_VERSION} REQUIRED NO_MODULE)
set(CMAKE_MODULE_PATH ${ECM_MODULE_PATH})

include(KDEInstallDirs6)
include(KDECMakeSettings)
include(KDECompilerSettings NO_POLICY_SCOPE)
include(ECMQmlModule)
include(ECMQtDeclareLoggingCategory)

find_package(Qt6 ${QT_MIN_VERSION} CONFIG REQUIRED COMPONENTS Core Gui Widgets DBus Qml Quick)
find_package(KF6 ${KF_MIN_VERSION} REQUIRED COMPONENTS I18n ColorScheme CoreAddons)
find_package(LibTaskManager REQUIRED)

set(CMAKE_CXX_STANDARD 20)
set(CMAKE_CXX_STANDARD_REQUIRED ON)
add_definitions(-DTRANSLATION_DOMAIN="plasma_applet_org.kde.mac.tahoe.liquid.globalmenu")

add_subdirectory(
    ${CMAKE_CURRENT_SOURCE_DIR}/../../plasmoids/org.kde.mac.tahoe.liquid.globalmenu/libdbusmenuqt
    ${CMAKE_CURRENT_BINARY_DIR}/libdbusmenuqt
)

ecm_add_qml_module(macTahoeAppMenu URI org.kde.mac.tahoe.liquid.appmenu GENERATE_PLUGIN_SOURCE)
target_sources(macTahoeAppMenu PRIVATE appmenu.cpp appmenu.h)
target_link_libraries(macTahoeAppMenu PRIVATE
    Qt6::Gui Qt6::Widgets Qt6::DBus Qt6::Quick
    KF6::I18n KF6::ColorScheme KF6::CoreAddons
    PW::LibTaskManager
    dbusmenuqt
)
ecm_finalize_qml_module(macTahoeAppMenu DESTINATION ${KDE_INSTALL_QMLDIR})

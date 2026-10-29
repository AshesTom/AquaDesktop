# MacTahoe Liquid KDE — org.kde.mac.tahoe.liquid.glass: lets a Plasma popup ask
# KWin to blur only behind its glass shapes (the Control Center's modules),
# the way macOS blurs each module on its own instead of one panel.
cmake_minimum_required(VERSION 3.20)
project(mac-tahoe-glass VERSION 1.0)

set(QT_MIN_VERSION "6.6.0")
set(KF_MIN_VERSION "6.0.0")

find_package(ECM ${KF_MIN_VERSION} REQUIRED NO_MODULE)
set(CMAKE_MODULE_PATH ${ECM_MODULE_PATH})

include(KDEInstallDirs6)
include(KDECMakeSettings)
include(KDECompilerSettings NO_POLICY_SCOPE)
include(ECMQmlModule)

find_package(Qt6 ${QT_MIN_VERSION} CONFIG REQUIRED COMPONENTS Core Gui Qml Quick)
find_package(KF6 ${KF_MIN_VERSION} REQUIRED COMPONENTS WindowSystem)

set(CMAKE_CXX_STANDARD 20)
set(CMAKE_CXX_STANDARD_REQUIRED ON)

ecm_add_qml_module(macTahoeGlass URI org.kde.mac.tahoe.liquid.glass GENERATE_PLUGIN_SOURCE)
target_sources(macTahoeGlass PRIVATE glassblur.cpp glassblur.h)
target_link_libraries(macTahoeGlass PRIVATE Qt6::Gui Qt6::Quick KF6::WindowSystem)
ecm_finalize_qml_module(macTahoeGlass DESTINATION ${KDE_INSTALL_QMLDIR})

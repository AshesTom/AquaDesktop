cmake_minimum_required(VERSION 3.16.0)

project(kwin_acrylic_glass)
# Vendored from AndyKaslana/kwin-effects-glass 47d165c (upstream 1.6.3).
set(PROJECT_VERSION "1.6.3")
set(PROJECT_VERSION_MAJOR 0)

set(KF_MIN_VERSION "5.240.0")
set(QT_MIN_VERSION "6.6.0")
set(QT_MAJOR_VERSION 6)

set(CMAKE_CXX_STANDARD 20)
set(CMAKE_CXX_STANDARD_REQUIRED ON)
set(CMAKE_CXX_EXTENSIONS OFF)


if(NOT CMAKE_BUILD_TYPE)
    set(CMAKE_BUILD_TYPE "Release" CACHE STRING "Choose Release or Debug" FORCE)
endif()
set(CMAKE_CXX_FLAGS_RELEASE "${CMAKE_CXX_FLAGS_RELEASE} -DQT_NO_DEBUG_OUTPUT")

find_package(ECM REQUIRED NO_MODULE)
set(CMAKE_MODULE_PATH ${CMAKE_MODULE_PATH} ${ECM_MODULE_PATH} ${ECM_KDE_MODULE_DIR})

option(GLASS_WAYLAND "Whether to build Acrylic Glass for Wayland if present." ON)
option(GLASS_X11 "Whether to build Acrylic Glass for X11 if present." ON)

include(FeatureSummary)
include(KDEInstallDirs)
include(KDECMakeSettings)
include(KDECompilerSettings NO_POLICY_SCOPE)

find_package(Qt6 ${QT_MIN_VERSION} CONFIG REQUIRED COMPONENTS
    Gui
    Core
    DBus
    Widgets
    OpenGL
    Network
    Xml
)

include_directories(${Qt6Widgets_INCLUDE_DIRS} ${Qt6Network_INCLUDE_DIRS} ${Qt6OpenGL_INCLUDE_DIRS} ${Qt6Xml_INCLUDE_DIRS})
add_definitions(${Qt6Widgets_DEFINITIONS})

find_package(KF6 ${KF_MIN_VERSION} REQUIRED COMPONENTS
    I18n
    GuiAddons
    KCMUtils
)

if(GLASS_WAYLAND)
    find_package(KWin COMPONENTS
        kwineffects
    )
    if (${KWin_FOUND})
        find_package(KWinDBusInterface CONFIG REQUIRED)
        # Xwayland clients still publish their blur region as an X11 property.
        find_package(XCB REQUIRED COMPONENTS XCB)
    else()
        set(GLASS_WAYLAND OFF)
    endif()
endif()
if(GLASS_X11)
    find_package(KWinX11 COMPONENTS
        kwineffects
    )
    if (${KWinX11_FOUND})
        find_package(X11 REQUIRED)
        find_package(XCB REQUIRED COMPONENTS XCB)
        find_package(KWinX11DBusInterface CONFIG REQUIRED)
        if(NOT GLASS_WAYLAND)
            set(KWin_VERSION ${KWinX11_VERSION})
        endif()
    else()
        set(GLASS_X11 OFF)
        message(STATUS "Acrylic Glass: KWin X11 development files unavailable; skipping X11 backend")
    endif()
endif()

if(NOT GLASS_WAYLAND AND NOT GLASS_X11)
    message(FATAL_ERROR "Acrylic Glass requires KWin development files for Wayland or X11.")
endif()

if(${KWin_VERSION} VERSION_LESS 6.6)
    message(FATAL_ERROR "Acrylic Glass requires KDE Plasma 6.6+ (found ${KWin_VERSION}).")
endif()

# The Wayland SDK changed its effect ABI at 6.7 while the 6.7 X11 SDK kept
# the legacy one, so each backend gets its own gates. 6.7.90 (the 6.8 beta)
# made Effect::drawWindow() return bool. Only dereference a backend's
# version when that backend is enabled.
set(GLASS_KWIN_67_WAYLAND OFF)
set(GLASS_KWIN_68_WAYLAND OFF)
set(GLASS_KWIN_68_X11 OFF)
if(GLASS_WAYLAND)
    if(${KWin_VERSION} VERSION_GREATER_EQUAL 6.7)
        set(GLASS_KWIN_67_WAYLAND ON)
    endif()
    if(${KWin_VERSION} VERSION_GREATER_EQUAL 6.7.90)
        set(GLASS_KWIN_68_WAYLAND ON)
    endif()
endif()
if(GLASS_X11)
    if(${KWinX11_VERSION} VERSION_GREATER_EQUAL 6.7.90)
        set(GLASS_KWIN_68_X11 ON)
    endif()
endif()
message(STATUS "Acrylic Glass: KWin ${KWin_VERSION} (6.7 Wayland ABI=${GLASS_KWIN_67_WAYLAND}; 6.8 drawWindow: Wayland=${GLASS_KWIN_68_WAYLAND} X11=${GLASS_KWIN_68_X11})")

find_package(KDecoration3 REQUIRED)

add_subdirectory(src)

install(DIRECTORY "${CMAKE_CURRENT_SOURCE_DIR}/locale/" DESTINATION "${KDE_INSTALL_LOCALEDIR}")

feature_summary(WHAT ALL FATAL_ON_MISSING_REQUIRED_PACKAGES)

# Add the localization domain
add_definitions(-DTRANSLATION_DOMAIN="kwin_effect_liquidglass")

if(GLASS_WAYLAND OR GLASS_X11)
    add_subdirectory(kcm)
endif()

# Read compat preambles
file(READ shaders/compat_core.glsl COMPAT_CORE)
#file(READ shaders/compat_legacy.glsl COMPAT_LEGACY)
file(READ shaders/oklab.glsl OKLAB_SHADER)
file(READ shaders/snells-glass.glsl SNELLS_GLASS_SHADER)
file(READ shaders/rim.glsl RIM_SHADER)
file(READ shaders/glass.glsl GLASS_SHADER)

# Pre-expand snells-glass.glsl and rim.glsl into glass.glsl
string(REPLACE "#include \"snells-glass.glsl\"" "${SNELLS_GLASS_SHADER}" GLASS_SHADER "${GLASS_SHADER}")
string(REPLACE "#include \"rim.glsl\"" "${RIM_SHADER}" GLASS_SHADER "${GLASS_SHADER}")

# Generate a core shader variant from a single .glsl source. Output goes into
# the build tree; the source checkout must stay clean.
function(generate_shader_variants input_glsl output_base)
    file(READ "${input_glsl}" SHADER_SRC)

    # Expand helper-shader includes
    string(REPLACE "#include \"oklab.glsl\"" "${OKLAB_SHADER}" SHADER_SRC_EXPANDED "${SHADER_SRC}")
    string(REPLACE "#include \"glass.glsl\"" "${GLASS_SHADER}" SHADER_SRC_EXPANDED "${SHADER_SRC_EXPANDED}")

    # Core variant
    file(WRITE "${CMAKE_CURRENT_BINARY_DIR}/generated/${output_base}${ARGN}" "${COMPAT_CORE}\n${SHADER_SRC_EXPANDED}")
endfunction()

# Generate vertex shaders
generate_shader_variants(shaders/vertex.glsl vertex .vert)
generate_shader_variants(shaders/onscreen_rounded_vertex.glsl onscreen_rounded .vert)

# Generate fragment shaders
generate_shader_variants(shaders/downsample.glsl downsample .frag)
generate_shader_variants(shaders/upsample.glsl upsample .frag)
generate_shader_variants(shaders/noise.glsl noise .frag)
generate_shader_variants(shaders/onscreen_rounded.glsl onscreen_rounded .frag)

# Resident older plugins keep their Qt resources registered too. Give each
# source build its own resource namespace, not just a new library filename.
file(GLOB_RECURSE identity_inputs CONFIGURE_DEPENDS
    "${CMAKE_CURRENT_SOURCE_DIR}/*.cpp" "${CMAKE_CURRENT_SOURCE_DIR}/*.h"
    "${CMAKE_CURRENT_SOURCE_DIR}/shaders/*" "${CMAKE_CURRENT_SOURCE_DIR}/metadata.json"
    "${CMAKE_CURRENT_SOURCE_DIR}/*.kcfg" "${CMAKE_CURRENT_SOURCE_DIR}/*.kcfgc")
list(SORT identity_inputs)
set_property(DIRECTORY APPEND PROPERTY CMAKE_CONFIGURE_DEPENDS ${identity_inputs})
set(identity_contents "")
foreach(input IN LISTS identity_inputs)
    file(SHA256 "${input}" input_hash)
    string(APPEND identity_contents "${input_hash}")
endforeach()
string(SHA256 build_identity "${identity_contents}")
set(resource_prefix "/effects/liquidglass/${build_identity}/")
file(WRITE "${CMAKE_CURRENT_BINARY_DIR}/build_identity.h"
    "#pragma once\n#define MTTKDE_GLASS_BUILD_ID \"${build_identity}\"\n#define MTTKDE_GLASS_RESOURCE_PREFIX \":${resource_prefix}\"\n")
file(READ liquidglass.qrc resource_source)
string(REPLACE "/effects/liquidglass/" "${resource_prefix}" resource_source "${resource_source}")
file(WRITE "${CMAKE_CURRENT_BINARY_DIR}/liquidglass.qrc" "${resource_source}")

set(liquidglass_SOURCES
    blur.cpp
    settings.cpp
    ${CMAKE_CURRENT_BINARY_DIR}/liquidglass.qrc
    main.cpp
)

kconfig_add_kcfg_files(liquidglass_SOURCES
    blurconfig.kcfgc
)

if(GLASS_WAYLAND)
    add_library(liquidglass MODULE ${liquidglass_SOURCES})
    target_include_directories(liquidglass PRIVATE "${CMAKE_CURRENT_BINARY_DIR}")
    target_link_libraries(liquidglass PRIVATE
        KDecoration3::KDecoration
        KF6::ConfigGui
        KWin::kwin
        XCB::XCB
    )
    if(GLASS_KWIN_67_WAYLAND)
        target_compile_definitions(liquidglass PRIVATE GLASS_KWIN_67)
    endif()
    if(GLASS_KWIN_68_WAYLAND)
        target_compile_definitions(liquidglass PRIVATE GLASS_KWIN_68)
    endif()
    install(TARGETS liquidglass DESTINATION ${KDE_INSTALL_PLUGINDIR}/kwin/effects/plugins)
endif()
if(GLASS_X11)
    add_library(liquidglass_x11 MODULE ${liquidglass_SOURCES})
    target_include_directories(liquidglass_x11 PRIVATE "${CMAKE_CURRENT_BINARY_DIR}")
    target_link_libraries(liquidglass_x11 PRIVATE
        KDecoration3::KDecoration
        KF6::ConfigGui
        KWinX11::kwin
        XCB::XCB
    )
    target_compile_definitions(liquidglass_x11 PRIVATE GLASS_X11 KWIN_BUILD_X11)
    if(GLASS_KWIN_68_X11)
        target_compile_definitions(liquidglass_x11 PRIVATE GLASS_KWIN_68)
    endif()
    install(TARGETS liquidglass_x11 DESTINATION ${KDE_INSTALL_PLUGINDIR}/kwin-x11/effects/plugins)
endif()

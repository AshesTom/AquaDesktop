`plasma-shell.xml` is the unmodified protocol from Plasma Wayland Protocols
v1.20.0, shared by the supported Plasma 6.6–6.8 APIs:
https://github.com/KDE/plasma-wayland-protocols/blob/v1.20.0/src/protocols/plasma-shell.xml

The build generates only the headers needed by the exported
`PlasmaShellWaylandIntegration` API. The installed libplasma library creates
and owns the surface; this module does not create a second protocol object.

{ nixpkgs, home-manager, pkgs, modules }:
let
  lib = pkgs.lib;
  home = extra: home-manager.lib.homeManagerConfiguration {
    inherit pkgs;
    modules = [ modules.home {
      home.username = "test";
      home.homeDirectory = "/home/test";
      home.stateVersion = "26.05";
      programs.mac-tahoe.enable = true;
    } extra ];
  };
  fixed = home { programs.mac-tahoe = { mode = "dark"; reducedTransparency = true; }; };
  conflict = home { xdg.configFile."kwinrc".text = "[Plugins]"; };
  system = nixpkgs.lib.nixosSystem {
    inherit pkgs;
    modules = [ modules.system {
      system.stateVersion = "26.05";
      services.desktopManager.plasma6.enable = true;
      services.mac-tahoe = { enable = true; plymouth.enable = true; };
      boot.loader.grub.enable = false;
      fileSystems."/" = { device = "none"; fsType = "tmpfs"; };
    } ];
  };
in
assert fixed.config.systemd.user.timers == { };
assert lib.hasInfix "reduced" fixed.config.xdg.configFile."mac-tahoe-liquid-kde/appearance.json".text;
assert !(builtins.tryEval conflict.activationPackage.drvPath).success;
assert system.config.boot.plymouth.theme == "MacTahoeLiquidKde";
assert lib.length (lib.splitString ":" system.config.environment.sessionVariables.QT_PLUGIN_PATH) == 4;
pkgs.writeText "mac-tahoe-module-checks" (builtins.unsafeDiscardStringContext (
  # Force evaluation of the complete system, including module assertions.
  system.config.system.build.toplevel.drvPath
))

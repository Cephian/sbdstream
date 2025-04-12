{
  description = "SBDStream - PySide6 application for streaming and scheduling";

  inputs = {
    nixpkgs.url = "github:NixOS/nixpkgs/nixos-unstable";
    flake-utils.url = "github:numtide/flake-utils";
  };

  outputs = { self, nixpkgs, flake-utils, ... }:
    flake-utils.lib.eachDefaultSystem (system:
      let
        pkgs = import nixpkgs {
          inherit system;
        };
        
        python = pkgs.python3;
        pythonPackages = python.pkgs;
        
        sbdstream = pythonPackages.buildPythonApplication {
          pname = "sbdstream";
          version = "0.1.0";
          src = ./.;
          
          propagatedBuildInputs = with pythonPackages; [
            pyside6
            python-dateutil
          ];
          
          doCheck = false;
        };
      in
      {
        packages.default = sbdstream;
        
        devShells.default = pkgs.mkShell {
          buildInputs = with pkgs; [
            python
            pythonPackages.pyside6
            pythonPackages.python-dateutil
            pythonPackages.pip
            pythonPackages.black
            pythonPackages.pylint
            pythonPackages.pytest
            kdePackages.qtwayland
            qt6.full
            qtcreator
          ];
          
          shellHook = ''
            echo "Entering SBDStream development environment"
            export PYTHONPATH="$PWD:$PYTHONPATH"
            export NIXOS_OZONE_WL="1"
            export QT_QPA_PLATFORM="wayland"
          '';
        };
        
        apps.default = flake-utils.lib.mkApp {
          drv = sbdstream;
          name = "sbdstream";
          exePath = "/bin/sbdstream";
        };
      });
} 
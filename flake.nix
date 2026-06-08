{
  description = "Interactive SSH profile selection menu.";

  inputs = {
    nixpkgs.url = "github:NixOS/nixpkgs/nixos-unstable";
    flake-parts.url = "github:hercules-ci/flake-parts";

    # Formatting tools.
    treefmt.url = "github:numtide/treefmt-nix";

    # Pre-commit hooks.
    git-hooks.url = "github:cachix/git-hooks.nix";
    git-hooks.inputs.nixpkgs.follows = "nixpkgs";

    # Pure-Nix Python packaging from pyproject.toml + uv.lock.
    pyproject-nix = {
      url = "github:pyproject-nix/pyproject.nix";
      inputs.nixpkgs.follows = "nixpkgs";
    };
    uv2nix = {
      url = "github:pyproject-nix/uv2nix";
      inputs.pyproject-nix.follows = "pyproject-nix";
      inputs.nixpkgs.follows = "nixpkgs";
    };
    pyproject-build-systems = {
      url = "github:pyproject-nix/build-system-pkgs";
      inputs.pyproject-nix.follows = "pyproject-nix";
      inputs.uv2nix.follows = "uv2nix";
      inputs.nixpkgs.follows = "nixpkgs";
    };
  };

  outputs = inputs @ {flake-parts, ...}:
    flake-parts.lib.mkFlake {inherit inputs;} {
      imports = [
        inputs.git-hooks.flakeModule
        inputs.treefmt.flakeModule
      ];
      systems = ["x86_64-linux"];

      perSystem = {
        config,
        system,
        ...
      }: let
        pkgs = import inputs.nixpkgs {inherit system;};
        lib = pkgs.lib;

        python = pkgs.python313;

        workspace = inputs.uv2nix.lib.workspace.loadWorkspace {
          workspaceRoot = ./.;
        };

        uvOverlay = workspace.mkPyprojectOverlay {
          sourcePreference = "wheel";
        };

        # sshme is a pure-Python package built with uv_build. Override it so
        # that the build sandbox has access to the uv-build wheel and the
        # package's own source tree can be found under sources/.
        pyprojectOverrides = _final: prev: {
          sshme = prev.sshme.overrideAttrs (old: {
            nativeBuildInputs =
              (old.nativeBuildInputs or [])
              ++ [
                prev.uv-build
              ];
          });
        };

        pythonSet =
          (pkgs.callPackage inputs.pyproject-nix.build.packages {
            inherit python;
          }).overrideScope
          (
            lib.composeManyExtensions [
              inputs.pyproject-build-systems.overlays.default
              uvOverlay
              pyprojectOverrides
            ]
          );

        pythonEnv = pythonSet.mkVirtualEnv "sshme-env" workspace.deps.all;
      in {
        devShells.default = pkgs.mkShell {
          name = "sshme";

          packages = [
            pkgs.uv
            pkgs.git
            pythonEnv
          ];

          env = {
            UV_LINK_MODE = "copy";
            UV_PYTHON_DOWNLOADS = "never";
            UV_PYTHON = "${pythonEnv}/bin/python";
          };
        };

        pre-commit.settings.hooks.treefmt = {
          enable = true;
          package = config.treefmt.build.wrapper;
        };

        treefmt = {
          programs = {
            alejandra.enable = true;
            deadnix.enable = true;
            shellcheck.enable = true;
            shfmt.enable = true;
            ruff.check = true;
            ruff.format = true;
          };
          settings.formatter = {
            shellcheck.options = ["-s" "bash"];
            ruff-check.priority = 1;
            ruff-check.options = ["--fix-only"];
            ruff-format.priority = 2;
          };
        };
      };

      flake = {};
    };
}

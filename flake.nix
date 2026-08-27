{
  description = "Read-only Reddit community knowledge collector with an MCP server";

  inputs = {
    nixpkgs.url = "github:NixOS/nixpkgs/nixos-unstable";

    pyproject-nix = {
      url = "github:pyproject-nix/pyproject.nix";
      inputs.nixpkgs.follows = "nixpkgs";
    };

    uv2nix = {
      url = "github:pyproject-nix/uv2nix";
      inputs.nixpkgs.follows = "nixpkgs";
      inputs.pyproject-nix.follows = "pyproject-nix";
    };

    pyproject-build-systems = {
      url = "github:pyproject-nix/build-system-pkgs";
      inputs.nixpkgs.follows = "nixpkgs";
      inputs.pyproject-nix.follows = "pyproject-nix";
      inputs.uv2nix.follows = "uv2nix";
    };
  };

  outputs =
    {
      self,
      nixpkgs,
      pyproject-nix,
      uv2nix,
      pyproject-build-systems,
      ...
    }:
    let
      systems = [
        "x86_64-linux"
        "aarch64-linux"
        "x86_64-darwin"
        "aarch64-darwin"
      ];
      forAllSystems = nixpkgs.lib.genAttrs systems;

      mkPackage =
        system:
        let
          pkgs = nixpkgs.legacyPackages.${system};
          workspace = uv2nix.lib.workspace.loadWorkspace { workspaceRoot = ./.; };
          overlay = workspace.mkPyprojectOverlay { sourcePreference = "wheel"; };
          pythonSet =
            (pkgs.callPackage pyproject-nix.build.packages {
              python = pkgs.python312;
            }).overrideScope
              (nixpkgs.lib.composeManyExtensions [
                pyproject-build-systems.overlays.default
                overlay
              ]);
          venv = pythonSet.mkVirtualEnv "reddit-miner-env" workspace.deps.default;
          inherit (pkgs.callPackages pyproject-nix.build.util { }) mkApplication;
        in
        mkApplication {
          inherit venv;
          package = pythonSet."reddit-miner";
        };
    in
    {
      packages = forAllSystems (
        system:
        let
          package = mkPackage system;
        in
        {
          default = package;
          reddit-miner = package;
        }
      );

      apps = forAllSystems (system: {
        default = {
          type = "app";
          program = "${self.packages.${system}.default}/bin/reddit-miner";
        };
        reddit-miner = self.apps.${system}.default;
      });
    };
}

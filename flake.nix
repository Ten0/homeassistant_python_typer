{
  description = "home-assistant-config dev shell flake";
  inputs = {
    nixpkgs.url = "github:nixos/nixpkgs/nixos-unstable";
    flake-utils.url = "github:numtide/flake-utils";
  };

  outputs =
    {
      nixpkgs,
      flake-utils,
      ...
    }@flake-inputs:
    flake-utils.lib.eachDefaultSystem (
      localSystem:
      let
        pkgs = import nixpkgs { system = localSystem; };
      in
      {
        devShells.default = pkgs.callPackage ./shell.nix { inherit flake-inputs; };
      }
    );
}

{ pkgs, ... }:

let
  python = (
    pkgs.python3.withPackages (
      python-pkgs: with python-pkgs; [
        requests
      ]
    )
  );
in
pkgs.mkShell {
  packages = [
    python
  ];
  shellHook = ''
    echo "Python env to select in VSCode: ${python}/bin/python"
  '';
}

{ pkgs, ... }:

let
  python = (
    # We use python311 here because that's what's provided by the VSCode Addon, so for ease of use we should support that
    # https://github.com/hassio-addons/addon-vscode/blob/3faac467382dcad40bdbbb3ef6b2a196b221d0c0/vscode/Dockerfile#L44
    pkgs.python311.withPackages (
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

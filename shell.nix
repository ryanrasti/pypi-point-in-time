{ pkgs ? import ./default.nix {}}:
 
let
  python = pkgs.python3.withPackages (p: with p; [
    requests
    beautifulsoup4
    tenacity
  ]);
in
python.env

root: family:

let
  file = root + "/${family}/font.toml";
in
{
  inherit family file;
  data = builtins.fromTOML (builtins.readFile file);
}

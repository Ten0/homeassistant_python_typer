<!--
Thanks for opening an issue!

If your issue is about code generation, that is about anything in the generated `hapt.py`
(wrong/missing types, empty or incorrect `Literal`s, syntax errors, missing entities,
missing or wrongly-typed services...), please also provide the raw data we generate from,
otherwise we most likely won't be able to reproduce or understand what happened:

1. Re-run the generation with the `-d` flag:

       python3 -m homeassistant_python_typer /path/to/write/hapt.py -d

   (or, if you run it through `uvx`:

       uvx --from git+https://github.com/Ten0/homeassistant_python_typer.git homeassistant_python_typer /path/to/write/hapt.py -d

   )

   This writes `entities.json` and `services.json` in the directory you ran the command from.

2. Paste here the parts that are relevant to your issue: typically the `entities.json` entry
   of the affected entity (its `state` and `attributes` are what we generate from), and if a
   service/action is involved, the matching entry from `services.json`.

⚠️ These files describe your entire Home Assistant instance, so please only paste the
relevant parts, and anonymize whatever is personal (entity names, friendly names, areas,
persons, locations, IPs, tokens...) before doing so.
-->

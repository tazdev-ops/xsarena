#!/usr/bin/env python3
import pathlib

import typer
import yaml

app = typer.Typer(help="Templates registry")


@app.command("list")
def tpl_list():
    reg_path = pathlib.Path("playbooks") / "registry.yml"
    if not reg_path.exists():
        typer.echo("No registry.yml found")
        return
    reg = yaml.safe_load(reg_path.read_text(encoding="utf-8"))
    for k in reg.get("templates", {}).keys():
        print(k)


@app.command("apply")
def tpl_apply(name: str, playbook_path: str = "playbooks/z2h.yml"):
    reg_path = pathlib.Path("playbooks") / "registry.yml"
    if not reg_path.exists():
        typer.echo("registry.yml not found")
        raise typer.Exit(1)

    reg = yaml.safe_load(reg_path.read_text(encoding="utf-8"))
    tpl = reg.get("templates", {}).get(name)
    if not tpl:
        typer.echo("Template not found")
        raise typer.Exit(1)

    pb_path = pathlib.Path(playbook_path)
    if not pb_path.exists():
        typer.echo(f"Playbook {playbook_path} not found")
        raise typer.Exit(1)

    pb = yaml.safe_load(pb_path.read_text(encoding="utf-8"))
    if tpl.get("overlay"):
        pb["style_file"] = tpl["overlay"]
    if tpl.get("system_text"):
        pb["system_text"] = (pb.get("system_text", "") + "\n\n" + tpl["system_text"]).strip()
    pb_path.write_text(yaml.safe_dump(pb, sort_keys=False), encoding="utf-8")
    typer.echo(f"[templates] Applied '{name}' to {playbook_path}")

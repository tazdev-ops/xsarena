def test_snapshot_txt_author_core_cli(tmp_path, monkeypatch):
    from typer.testing import CliRunner
    from xsarena.cli.main import run as cli_run

    runner = CliRunner()
    res = runner.invoke(
        cli_run,
        [
            "ops",
            "snapshot",
            "txt",
            "--preset",
            "author-core",
            "--out",
            str(tmp_path / "flat.txt"),
            "--total-max",
            "1000000",
            "--max-per-file",
            "120000",
        ],
    )
    assert res.exit_code == 0
    assert (tmp_path / "flat.txt").exists()

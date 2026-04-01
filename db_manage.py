# # /// script
# # requires-python = ">=3.12"
# # dependencies = []
# # ///
# from pprint import pprint
from typing import Annotated

import typer
import yfinance as yf
from rich.console import Console
from rich.table import Table

from database import models  # noqa
from database.manager import DatabaseManager

db = DatabaseManager()

app = typer.Typer(help="OpenQuant Database CLI")
console = Console()


@app.command()
def init():
    """初始化数据库表结构"""
    db.init_db()
    console.print("[bold green]✔ 数据库已就绪！[/bold green]")


@app.command()
def add(symbol: Annotated[str, typer.Option("--symbol", "-s")]):
    """
    添加需要监控的 Symbol， 并通过 yfinance 获取原信息
    """
    ticker = yf.Ticker(symbol.upper())
    info = ticker.info

    if "displayName" in info:
        name = info["displayName"]
    else:
        name = info["shortName"]

    symbol = models.SymbolMeta(
        symbol=info["symbol"],
        name=name,
        asset_type=info["typeDisp"],
        sector=info.get("sector"),
        industry=info.get("industry"),
        exchange=info["exchange"],
        currency=info["currency"],
    )
    db.create_symbolmeta(symbol)


@app.command()
def list():
    """显示所有监控的 Symbol"""
    symbols = db.get_active_symbolmetas()
    table = Table(title="Symbol list")
    table.add_column("symbol", justify="left", style="dim")
    table.add_column("name", style="magenta")
    table.add_column("资产类型", justify="center")
    table.add_column("板块", justify="center")
    table.add_column("行业", justify="center")
    table.add_column("交易所", justify="center")

    for symbol in symbols:
        table.add_row(
            symbol.symbol,
            symbol.name,
            symbol.asset_type,
            symbol.sector,
            symbol.industry,
            symbol.exchange,
        )

    console.print(table)


if __name__ == "__main__":
    app()

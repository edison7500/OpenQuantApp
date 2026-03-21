# # /// script
# # requires-python = ">=3.12"
# # dependencies = []
# # ///
from pprint import pprint
# import yfinance as yf
# import click

# from database import models  # noqa
# from database.manager import DatabaseManager


# db = DatabaseManager()


# @click.group()
# def cli():
#     """简单的用户管理 CLI 工具"""
#     pass


# @cli.command()
# def init_db():
#     """初始化数据库表结构"""
#     # db = DatabaseManager()
#     db.init_db()
#     click.echo("✅ 数据库表初始化成功！")


# @cli.command()
# @click.option("--symbol", "-s", prompt="please symbol")
# def fetch_symbolmeta(symbol: str):

#     ticker = yf.Ticker(symbol.upper())
#     info = ticker.info
#     # pprint(info, indent=2)
#     symbol = models.SymbolMeta(
#         symbol=info["symbol"],
#         name=info["displayName"],
#         asset_type=info["typeDisp"],
#         sector=info["sector"],
#         industry=info["industry"],
#         exchange=info["exchange"],
#     )
#     db.create_symbolmeta(symbol)
#     click.echo(f"Ticker {symbol} 已成功保存。")


# @cli.command()
# def list_symbol():
#     symbols = db.get_active_symbols()
#     print(symbols)
#     # for row in symbols:
#     # print(row.symbol)


# if __name__ == "__main__":
#     cli()

import typer
from typing import Annotated
from rich.console import Console
from rich.table import Table

import yfinance as yf

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
def add_monitor_symbol(symbol: Annotated[str, typer.Option("--symbol", "-s")]):
    """
    添加需要监控的 Symbol， 并通过 yfinance 获取原信息
    """
    ticker = yf.Ticker(symbol.upper())
    info = ticker.info
    # pprint(info, indent=2)

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
    )
    db.create_symbolmeta(symbol)


@app.command()
def list():
    """显示所有监控的 Symbol"""
    symbols = db.get_active_symbols()
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

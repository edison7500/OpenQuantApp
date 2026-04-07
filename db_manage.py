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


def _get_symbol_info(symbol: str) -> models.SymbolMeta:
    """从 yfinance 获取标的信息并转换为 SymbolMeta 模型"""
    ticker = yf.Ticker(symbol.upper())
    info = ticker.info

    if not info or "symbol" not in info:
        raise ValueError(f"无法获取 {symbol} 的信息")

    name = (
        info.get("displayName")
        or info.get("longName")
        or info.get("shortName")
        or symbol
    )

    return models.SymbolMeta(
        symbol=info["symbol"],
        name=name,
        asset_type=info.get("typeDisp", "Equity"),
        sector=info.get("sector"),
        industry=info.get("industry"),
        exchange=info.get("exchange"),
        currency=info.get("currency"),
    )


@app.command()
def add(symbol: Annotated[str, typer.Option("--symbol", "-s")]):
    """
    添加需要监控的 Symbol， 并通过 yfinance 获取元信息
    """
    try:
        with console.status(f"[bold green]正在获取 {symbol} 的信息..."):
            symbol_meta = _get_symbol_info(symbol)

        db.create_symbol_meta(symbol_meta)
        console.print(
            f"[bold green]✔ 已成功添加 {symbol_meta.symbol} ({symbol_meta.name})[/bold green]"
        )
    except Exception as e:
        console.print(f"[bold red]✘ 添加失败: {str(e)}[/bold red]")


@app.command()
def update(symbol: Annotated[str, typer.Option("--symbol", "-s")]):
    """
    更新已存在的 Symbol 元信息
    """
    try:
        with console.status(f"[bold blue]正在更新 {symbol} 的信息..."):
            symbol_meta = _get_symbol_info(symbol)
            db.update_symbol_meta(symbol_meta)
        console.print(
            f"[bold green]✔ 已成功更新 {symbol_meta.symbol} 的元信息[/bold green]"
        )
    except Exception as e:
        console.print(f"[bold red]✘ 更新失败: {str(e)}[/bold red]")


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

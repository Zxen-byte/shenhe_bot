import functools
import importlib
import sys
from pathlib import Path
from typing import Optional
from diskcache import FanoutCache
import git
from discord.app_commands import locale_str as _
from discord.ext import commands
from discord.errors import Forbidden
import pickle
from apps.genshin.custom_model import ShenheBot
from utility.utils import DefaultEmbed, ErrorEmbed


class AdminCog(commands.Cog, name="admin"):
    def __init__(self, bot):
        self.bot: ShenheBot = bot

    @commands.is_owner()
    @commands.command(name="maintenance")
    async def maintenance(self, ctx: commands.Context, time: Optional[str] = ""):
        self.bot.maintenance = not self.bot.maintenance
        if time != "":
            self.bot.maintenance_time = time
        await ctx.send("success")

    @commands.is_owner()
    @commands.command(name="reload")
    async def reload(self, ctx: commands.Context):
        message = await ctx.send("pulling from Git...")
        if not self.bot.debug:
            g = git.cmd.Git(Path(__file__).parent.parent)
            pull = functools.partial(g.pull)
            await self.bot.loop.run_in_executor(None, pull)
        modules = list(sys.modules.values())
        for _ in range(2):
            await message.edit(content="reloading modules...")
            for module in modules:
                if module is None:
                    continue
                if module.__name__.startswith(
                    (
                        "asset",
                        "config",
                        "UI_base_models",
                        "exceptions",
                        "ambr.",
                        "apps.",
                        "cogs.",
                        "data.",
                        "text_maps.",
                        "UI_elements.",
                        "utility.",
                        "yelan.",
                    )
                ):
                    try:
                        importlib.reload(module)
                    except Exception as e:
                        return await ctx.send(
                            embed=ErrorEmbed(module.__name__, f"```{e}```"),
                            ephemeral=True,
                        )

        await message.edit(content="reloading cogs...")
        for filepath in Path("./cogs").glob("**/*.py"):
            cog_name = Path(filepath).stem
            if cog_name in ["login", "grafana"]:
                continue
            try:
                await self.bot.reload_extension(f"cogs.{cog_name}")
            except Exception as e:
                return await message.edit(
                    embed=ErrorEmbed(cog_name, f"```{e}```"),
                )
        await message.edit(content="bot reloaded")

    @commands.is_owner()
    @commands.command(name="sync")
    async def sync(self, ctx: commands.Context):
        await self.bot.tree.sync()
        await ctx.send("commands synced")
        
    @commands.is_owner()
    @commands.command(name="dm")
    async def direct_message(self, ctx: commands.Context, user: commands.UserConverter, *, message: str):
        embed = DefaultEmbed(description=message)
        embed.set_author(name=ctx.author.name+"#"+ctx.author.discriminator, icon_url=ctx.author.display_avatar.url)
        try:
            await user.send(embed=embed)
        except Forbidden:
            await ctx.send("user has DMs disabled")
        else:
            await ctx.send("message sent")
    
    @commands.is_owner()
    @commands.command(name="transfer-enka-cache")
    async def transfer_enka_cache(self, ctx: commands.Context, uid: int):
        async with self.bot.pool.acquire() as db:
            await db.execute("CREATE TABLE IF NOT EXISTS enka_cache (uid INTEGER PRIMARY KEY, en_data BLOB, data BLOB)")
            await ctx.send("getting old cache...")
            en_cache = FanoutCache("data/cache/enka_eng_cache")
            cache = FanoutCache("data/cache/enka_data_cache")
            en_cache_data = en_cache.get(uid)
            cache_data = cache.get(uid)
            await db.execute("INSERT OR REPLACE INTO enka_cache (uid, en_data, data) VALUES (?, ?, ?)", (uid, pickle.dumps(en_cache_data), pickle.dumps(cache_data)))
            await db.commit()
            await ctx.send("done")


async def setup(bot: commands.AutoShardedBot) -> None:
    await bot.add_cog(AdminCog(bot))

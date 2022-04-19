from discord.ext import commands
import yaml
from cmd.asset.global_vars import defaultEmbed, setFooter

with open(f'asset/flow.yaml', encoding='utf-8') as file:
    users = yaml.full_load(file)
with open(f'asset/confirm.yaml', encoding='utf-8') as file:
    confirms = yaml.full_load(file)


class FlowConfirmCog(commands.Cog):
    def __init__(self, bot):
        self.bot = bot

    @commands.Cog.listener()
    async def on_raw_reaction_add(self, payload):
        if payload.message_id == 965143582178705459 or payload.message_id == 963972447600771092:
            return
        for confirm in confirms:
            if payload.message_id == confirm['msgID'] and payload.emoji.name == '🆗' and payload.user_id != self.bot.user.id:
                if confirm['dm'] == 4:
                    for user in users:
                        if user['discordID'] == confirm['authorID']:
                            user['flow'] += confirm['flow']
                        elif user['discordID'] == confirm['receiverID']:
                            user['flow'] -= confirm['flow']
                else:
                    for user in users:
                        if user['discordID'] == confirm['authorID']:
                            user['flow'] -= confirm['flow']
                        elif user['discordID'] == confirm['receiverID']:
                            user['flow'] += confirm['flow']
                author = self.bot.get_user(confirm['authorID'])
                receiver = self.bot.get_user(confirm['receiverID'])
                if confirm['dm'] == 4:
                    embed = defaultEmbed("🆗 結算成功",
                                         f"幫忙名稱: {confirm['title']}\n幫助人: {author.mention} **+{confirm['flow']} flow幣**\n被幫助人: {receiver.mention} **-{confirm['flow']} flow幣**")
                else:
                    embed = defaultEmbed("🆗 結算成功",
                                         f"委託名稱: {confirm['title']}\n委託人: {author.mention} **-{confirm['flow']} flow幣**\n接收人: {receiver.mention} **+{confirm['flow']} flow幣**")
                setFooter(embed)
                await author.send(embed=embed)
                await receiver.send(embed=embed)
                confirms.remove(confirm)
                with open(f'asset/confirm.yaml', 'w', encoding='utf-8') as file:
                    yaml.dump(confirms, file)
                with open(f'asset/flow.yaml', 'w', encoding='utf-8') as file:
                    yaml.dump(users, file)
                break


def setup(bot):
    bot.add_cog(FlowConfirmCog(bot))

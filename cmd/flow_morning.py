import getpass
owner = getpass.getuser()
import sys 
sys.path.append(f'C:/Users/{owner}/shenhe_bot/asset')
import discord, yaml, cmd.flow
import global_vars
global_vars.Global()
from discord.ext import commands

with open(f'C:/Users/{owner}/shenhe_bot/asset/flow.yaml', encoding = 'utf-8') as file:
    users = yaml.full_load(file)
with open(f'C:/Users/{owner}/shenhe_bot/asset/bank.yaml', encoding = 'utf-8') as file:
    bank = yaml.full_load(file)

class FlowMorningCog(commands.Cog):
    def __init__(self, bot):
        self.bot = bot

    @commands.Cog.listener()
    async def on_message(self, message):
        if message.author == self.bot.user:
            return
        if "早安" in message.content:
            today = date.today()
            found = False
            for user in users:
                if message.author.id == user['discordID']:
                    found = True
                    if user['morning']!=today:
                        user['flow'] += 1
                        bank['flow'] -= 1
                        user['morning'] = today
                        with open(f'C:/Users/{owner}/shenhe_bot/asset/flow.yaml', 'w', encoding = 'utf-8') as file:
                            yaml.dump(users, file)
                        with open(f'C:/Users/{owner}/shenhe_bot/asset/bank.yaml', 'w', encoding = 'utf-8') as file:
                            yaml.dump(bank, file)
                        await message.add_reaction(f"☀️")
            if found == False:
                if not message.author.bot:
                    discordID = message.author.id
                    user = self.bot.get_user(message.author.id)
                    flowCog = self.bot.get_cog('FlowCog')
                    await flowCog.register(user, discordID)
                else:
                    return

def setup(bot):
    bot.add_cog(FlowMorningCog(bot))
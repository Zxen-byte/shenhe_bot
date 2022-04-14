import gspread, discord, re
from discord.ext import commands
from discord.ext.forms import Form

sa = gspread.service_account()
sh = sa.open("Genshin")
wks = sh.worksheet("4/14")
teamCol = [2, 6, 10]
teamRow = [3, 9, 15, 21]
captianCol = [4, 8, 12]
captainRow = [4, 10, 16, 22]
teams = []
for row in teamRow:
	for col in teamCol:
		if val == None:
			continue
		teams.sppend(wks.cell(row, col).value)
captains = []
for row in captainRow:
	for col in captainCol:
		if val == None:
			continue
		captains.append(wks.cell(row, col).value)

class AttendCog(commands.Cog):
	def __init__(self, bot):
		self.bot = bot

	@commands.command()
	async def get(self, ctx, arg):
		await ctx.send(wks.acell(arg).value)

	@commands.command()
	async def att(self, ctx):
		teamStr = ""
		for team in teams:
			teamStr += f"• {team}\n"
		form = Form(ctx, '要對哪個隊伍做點名?', cleanup=True)
		form.add_question(titleStr, 'title')
		form.edit_and_delete(True)
		form.set_timeout(60)
		await form.set_color("0xa68bd3")
		result = await form.start()
		team = result.title
		pos = -1
		for team in teams:
			if team == result.title:
				pos = teams.index(team)
				break
		if pos == -1:
			await ctx.send("找不到該小組, 請查看名稱是否輸入錯誤")
		else:
			if captain[pos] == ctx.author.id:
				# cotinue
				await ctx.send("continue")

def setup(bot):
	bot.add_cog(AttendCog(bot))
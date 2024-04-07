import asyncio
import random
import time
from typing import Literal, Optional, Union

import discord
from discord import app_commands
from discord.ext import commands

from libs.bot_classes import Axobot
from libs.checks.checks import is_ttt_enabled
from libs.serverconfig.options_list import options

GridType = list[Union[int, Literal['X', 'O']]]


class TicTacToe(commands.Cog):
    "Allow users to play PvP tic-tac-toe"

    def __init__(self, bot: Axobot):
        self.bot = bot
        self.file = 'tictactoe'
        self.in_game = {}
        self.types: tuple[str] = options['ttt_display']['values']

    async def get_ttt_mode(self, interaction: discord.Interaction) -> str:
        """Get the used mode for a specific context"""
        if interaction.guild is None:
            return options["ttt_display"]["default"]
        return await self.bot.get_config(interaction.guild_id, "ttt_display")

    @app_commands.command(name="tic-tac-toe")
    @app_commands.check(is_ttt_enabled)
    async def main(self, interaction: discord.Interaction):
        """A simple mini-game that consists of aligning three chips on a 9-square grid.
    The bot plays in red, the user in blue.

    ..Doc miscellaneous.html#tic-tac-toe
    """
        if interaction.user.id in self.in_game:
            await interaction.response.send_message(await self.bot._(interaction, "tictactoe.already-playing"))
            return
        await interaction.response.defer()
        self.in_game[interaction.user.id] = time.time()
        game = self.Game(interaction, self, await self.get_ttt_mode(interaction))
        await game.init_emojis()
        await game.start()
        self.in_game.pop(interaction.user.id, None)

    class Game():
        "An actual tictactoe game running"

        def __init__(self, interaction: discord.Interaction, cog: "TicTacToe", mode: Literal["disabled", "short", "normal"]):
            self.cog = cog
            self.interaction = interaction
            self.bot = cog.bot
            self.use_short = mode == "short"
            self.grid: GridType = list(range(1, 10))
            self.is_user_turn = random.random() < 0.5
            self.emojis: tuple[str, str] = tuple()
            self.valid_inputs = [str(x) for x in range(1, 10)]
            self.winning_combinations = [
                [0, 1, 2],
                [3, 4, 5],
                [6, 7, 8],
                [0, 3, 6],
                [1, 4, 7],
                [2, 5, 8],
                [0, 4, 8],
                [2, 4, 6]
            ]

        async def init_emojis(self):
            "Init the emojis used to play"
            if self.bot.current_event == 'halloween':
                self.emojis = ("🎃", ":bat:")
            elif self.bot.current_event == "christmas":
                self.emojis = ("☃️", "🎄")
            elif self.bot.current_event == 'fish':
                self.emojis = ("🐟", "🐠")
            elif self.interaction.guild:
                self.emojis = await self.bot.get_config(self.interaction.guild_id, "ttt_emojis")
            if len(self.emojis) < 2:
                self.emojis = (':red_circle:', ':blue_circle:')

        async def display_grid(self) -> str:
            """Generate the grid to display in the chat"""
            display_grid = ''
            if self.interaction.channel.permissions_for(self.interaction.guild.me).use_external_emojis:
                emojis = [f"<:{x}>" for x in self.bot.emojis_manager.numbers_names]
            else:
                emojis = [chr(48+i)+chr(8419) for i in range(10)]
            for k in range(9):
                if k % 3 == 0:
                    display_grid += '\n'
                if self.grid[k] in range(10):
                    display_grid += emojis[self.grid[k]]
                elif self.grid[k] == 'O':
                    display_grid += self.emojis[0]
                else:
                    display_grid += self.emojis[1]
            return display_grid

        async def test_valid_cell(self, user_input: str):
            """Check if the cell is empty"""
            return str(self.grid[int(user_input)-1]) not in {'X', 'O'}

        async def replace_cell(self, is_user_turn: bool, user_input: str):
            """Replace the cell value in the grid with the player's symbol"""
            if is_user_turn:
                return ['X' if x == int(user_input) else x for x in self.grid]
            return ['O' if x == int(user_input) else x for x in self.grid]

        async def test_win(self, grid: GridType):
            """Test s'il y a une position de victoire"""
            for winning_combination in self.winning_combinations:
                if grid[winning_combination[0]] == grid[winning_combination[1]] == grid[winning_combination[2]]:
                    return True
            return False

        async def test_any_empty_cell(self):
            "Return True if there is any empty cell"
            return any(isinstance(x, int) for x in self.grid)

        async def is_empty(self):
            "Test if the whole grid is empty"
            return all(isinstance(x, int) for x in self.grid)

        async def _send_initial_message(self):
            u_begin = await self.bot._(self.interaction, "tictactoe.user-begin" if self.is_user_turn else "tictactoe.bot-begin")
            tip = await self.bot._(self.interaction, "tictactoe.tip", symb1=self.emojis[0], symb2=self.emojis[1])
            await self.interaction.followup.send(u_begin.format(self.interaction.user.mention) + tip)

        async def start(self):
            "Actually starts the game"
            await self._send_initial_message()
            send_msg = self.interaction.followup.send
            is_draw = True

            def check(msg: discord.Message):
                return msg.channel == self.interaction.channel and msg.author == self.interaction.user

            display_grid = True
            last_grid: Optional[discord.WebhookMessage] = None
            while await self.test_any_empty_cell():
                if self.interaction.user.id not in self.cog.in_game.keys():
                    return

            ###
                if self.is_user_turn:
                    if display_grid:
                        # if needed, clean the messages
                        if self.use_short and last_grid:
                            await last_grid.delete()
                        last_grid = await send_msg(await self.display_grid(), wait=True)
                    display_grid = True
                    try:
                        msg: discord.Message = await self.bot.wait_for("message", check=check, timeout=50)
                    except asyncio.TimeoutError:
                        await send_msg(await self.bot._(self.interaction, "tictactoe.too-late"))
                        return
                    user_input = msg.content
                    if msg.content in self.valid_inputs:
                        if await self.test_valid_cell(user_input):
                            self.grid = await self.replace_cell(self.is_user_turn, user_input)
                            self.is_user_turn = False
                            if self.use_short:
                                await msg.delete(delay=0.1)
                        else: # cell is not empty
                            await send_msg(await self.bot._(self.interaction, "tictactoe.pion-1"))
                            display_grid = False
                            continue
                    elif msg.content.endswith("leave"): # user leaves the game
                        return
                    else: # invalid cell number
                        await send_msg(await self.bot._(self.interaction, "tictactoe.pion-2"))
                        display_grid = False
                        continue
            ###
                else:  # Bot's turn
                    # Prepare the fallback answer as a random cell
                    user_input = random.randint(1, 10)
                    # Check if the user is about to win, or if the bot can win
                    for k in range(1, 10):
                        for i in [True, False]:
                            grid_copy = await self.replace_cell(i, k)
                            if await self.test_win(grid_copy):
                                user_input = k
                                break
                    # Check if value is valid
                    if str(user_input) in self.valid_inputs:
                        if await self.test_valid_cell(user_input):
                            self.grid = await self.replace_cell(self.is_user_turn, user_input)
                            self.is_user_turn = True
                        else:
                            continue
                    else:
                        continue
                    display_grid = True
            ###
                if await self.test_win(self.grid):
                    is_draw = False
                    break
            ###
            # if needed, clean the messages
            if self.use_short and last_grid:
                await last_grid.delete()
            if is_draw:
                game_result = await self.bot._(self.interaction, "tictactoe.nul")
            else:
                if self.is_user_turn:  # The bot won
                    game_result = await self.bot._(self.interaction, "tictactoe.win-bot")
                else:  # The user won
                    game_result = await self.bot._(self.interaction, "tictactoe.win-user", user=self.interaction.user.mention)
            await send_msg(await self.display_grid() + '\n' + game_result)
            if not is_draw and not self.is_user_turn:
                # give event points if user won
                await self.cog.give_event_points(self.interaction.channel, self.interaction.user, 8)

    async def give_event_points(self, channel: "discord.interactions.InteractionChannel", user: discord.User, points: int):
        "Give points to a user and check if they had unlocked a card"
        if cog := self.bot.get_cog("BotEvents"):
            if not cog.current_event:
                return
            # send win reward embed
            emb = discord.Embed(
                title=await self.bot._(channel, 'bot_events.tictactoe.reward-title'),
                description=await self.bot._(channel, 'bot_events.tictactoe.reward-desc', points=points),
                color=cog.current_event_data['color'],
            )
            emb.set_author(name=user.global_name, icon_url=user.display_avatar)
            await channel.send(embed=emb)
            # send card unlocked notif
            await cog.check_and_send_card_unlocked_notif(channel, user)
            # give points
            await cog.db_add_user_points(user.id, points)


async def setup(bot):
    await bot.add_cog(TicTacToe(bot))

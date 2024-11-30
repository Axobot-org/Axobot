import random
import time
from typing import Literal

import discord
from discord import app_commands
from discord.ext import commands

from core.bot_classes import Axobot

GridType = list[int | Literal['X', 'O']]


class TicTacToe(commands.Cog):
    "Allow users to play PvP tic-tac-toe"

    def __init__(self, bot: Axobot):
        self.bot = bot
        self.file = "tictactoe"
        self.in_game = {}

    @app_commands.command(name="tic-tac-toe")
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
        game = self.Game(interaction, self)
        u_begin = await self.bot._(interaction, "tictactoe.user-begin" if game.is_user_turn else "tictactoe.bot-begin")
        await game.init_game()
        tip = await self.bot._(interaction, "tictactoe.tip", symb1=game.emojis[0], symb2=game.emojis[1])
        await interaction.edit_original_response(content=u_begin.format(interaction.user.mention) + tip, view=game)
        await game.wait()
        self.in_game.pop(interaction.user.id, None)

    class Game(discord.ui.View):
        "An actual tictactoe game running"

        def __init__(self, interaction: discord.Interaction, cog: "TicTacToe"):
            super().__init__(timeout=120)
            self.cog = cog
            self.interaction = interaction
            self.bot = cog.bot
            self.grid: GridType = list(range(0, 9))
            self.is_user_turn = random.random() < 0.5
            self.emojis: tuple[str, str] = tuple()
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

        async def init_game(self):
            "Init the emojis used to play"
            if self.bot.current_event == "halloween":
                self.emojis = ("🎃", "🦇")
            elif self.bot.current_event == "christmas":
                self.emojis = ("☃️", "🎄")
            elif self.bot.current_event == "fish":
                self.emojis = ("🐟", "🐠")
            elif self.interaction.guild:
                self.emojis = await self.bot.get_config(self.interaction.guild_id, "ttt_emojis")
            if len(self.emojis) < 2:
                self.emojis = ("🔴", "🔵")
            # if the bot should start, play its turn
            if not self.is_user_turn:
                await self.bot_turn()
            else:
                await self.update_grid()

        async def update_grid(self, content: str | None = discord.utils.MISSING):
            """Update the view buttons with the current grid state"""
            self.clear_items()
            for i in range(9):
                row = i // 3
                if self.grid[i] in range(10):
                    button = discord.ui.Button(
                        style=discord.ButtonStyle.blurple, label=str(i+1), custom_id=f"ttt_{i}", row=row,
                        disabled=self.is_finished()
                    )
                    button.callback = self.on_click
                elif self.grid[i] == 'O':
                    button = discord.ui.Button(style=discord.ButtonStyle.gray, emoji=self.emojis[0], disabled=True, row=row)
                else:
                    button = discord.ui.Button(style=discord.ButtonStyle.gray, emoji=self.emojis[1], disabled=True, row=row)
                self.add_item(button)
            try:
                await self.interaction.edit_original_response(content=content, view=self)
            except discord.HTTPException as err:
                self.bot.dispatch("error", err, "During a tictactoe game")

        async def test_valid_cell(self, case_id: int):
            """Check if the cell is empty"""
            return self.grid[case_id] not in {'X', 'O'}

        async def replace_cell(self, is_user_turn: bool, case_id: int):
            "Replace the cell value in the grid with the player's symbol, and return a copy of the grid"
            if is_user_turn:
                return ['X' if x == case_id else x for x in self.grid]
            return ['O' if x == case_id else x for x in self.grid]

        async def test_victory(self, grid: GridType):
            "Test if one player has won the game"
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

        async def on_click(self, interaction: discord.Interaction):
            "Handle the user's click on the grid"
            if interaction.user.id != self.interaction.user.id or not self.is_user_turn:
                return
            await interaction.response.defer()
            case_id = int(interaction.data["custom_id"].split("_")[1])
            if not await self.test_valid_cell(case_id):
                self.bot.dispatch("error", ValueError(f"Invalid cell: {case_id}"), "During a tictactoe game")
                return
            self.grid = await self.replace_cell(self.is_user_turn, case_id)
            self.interaction = interaction
            if await self.check_game_end():
                return
            self.is_user_turn = False
            await self.bot_turn()

        async def bot_turn(self):
            "Make the bot play its turn"
            chosen_cell = await self._find_optimal_cell()
            if chosen_cell is None:
            # Fallback to a random empty cell
                chosen_cell = random.choice([i for i, x in enumerate(self.grid) if isinstance(x, int)])
            # Update the game state
            self.grid = await self.replace_cell(self.is_user_turn, chosen_cell)
            if await self.check_game_end():
                return
            self.is_user_turn = True
            # Edit the message
            await self.update_grid()

        async def _find_optimal_cell(self):
            possible_cells: list[int] = []
            # Check if the user is about to win, or if the bot can win
            for cell in range(0, 9):
                if await self.test_valid_cell(cell):
                    for is_user in [True, False]:
                        grid_copy = await self.replace_cell(is_user, cell)
                        if await self.test_victory(grid_copy):
                            possible_cells.append(cell)
            if possible_cells:
                return random.choice(possible_cells)
            return None

        async def check_game_end(self):
            "Check if anyone won the game, or if no cell is empty"
            if await self.test_victory(self.grid): # someone won
                is_draw = False
                if self.is_user_turn: # The user won
                    result = await self.bot._(self.interaction, "tictactoe.win-user", user=self.interaction.user.mention)
                else: # The bot won
                    result = await self.bot._(self.interaction, "tictactoe.win-bot")
            elif not await self.test_any_empty_cell(): # No empty cell
                is_draw = True
                result = await self.bot._(self.interaction, "tictactoe.nul")
            else:
                return False
            self.stop()
            await self.update_grid(result)
            if not is_draw and self.is_user_turn:
                # give event points if user won
                await self.cog.give_event_points(self.interaction, self.interaction.user, 8)
            return True

    async def give_event_points(self, interaction: discord.Interaction, user: discord.User, points: int):
        "Give points to a user and check if they had unlocked a card"
        if cog := self.bot.get_cog("BotEvents"):
            if not cog.current_event:
                return
            # send win reward embed
            emb = discord.Embed(
                title=await self.bot._(interaction, "bot_events.tictactoe.reward-title"),
                description=await self.bot._(interaction, "bot_events.tictactoe.reward-desc", points=points),
                color=cog.current_event_data["color"],
            )
            emb.set_author(name=user.global_name, icon_url=user.display_avatar)
            await interaction.followup.send(embed=emb)
            # send card unlocked notif
            await cog.check_and_send_card_unlocked_notif(interaction, user)
            # give points
            await cog.db_add_user_points(user.id, points)


async def setup(bot):
    await bot.add_cog(TicTacToe(bot))

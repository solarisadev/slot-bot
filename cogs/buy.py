import discord
from discord.ext import commands
from discord.ui import Button, View, Modal, TextInput
import json
import logging
import requests
import asyncio
from discord import Interaction, Embed, ButtonStyle
import discord
from discord.ext import commands
from discord.ui import Button, View, Modal, TextInput
import json
import logging

class BuySlot(commands.Cog):
    def __init__(self, bot):
        self.bot = bot
        self.config = self.load_config()
        self.payment_info = self.load_payment_info()

    def load_config(self):
        try:
            with open('config.json', 'r') as f:
                return json.load(f)
        except FileNotFoundError:
            logging.error("config.json file not found.")
            return {}

    def load_payment_info(self):
        try:
            with open('payment.json', 'r') as f:
                return json.load(f)
        except FileNotFoundError:
            logging.error("payment.json file not found.")
            return {}

    def get_prices_string(self, prices):
        return (
            f"Weekly: {prices['weekly_price']} USD\n"
            f"Monthly: {prices['monthly_price']} USD\n"
            f"Lifetime: {prices['lifetime_price']} USD"
        )

    async def send_slot_info(self, channel, user):
        print("Sending slot information...")
        embed = discord.Embed(title="Slot Plans and Prices")
        for category_key in ['category1', 'category2']:
            category_id = self.config.get(category_key)
            if category_id:
                category = self.bot.get_channel(category_id)
                if category and isinstance(category, discord.CategoryChannel):
                    available = len(category.channels) < (getattr(category, 'channel_limit', float('inf')))
                    availability_status = "Available" if available else "Unavailable"
                    if 'prices' in self.payment_info.get(category_key, {}):
                        prices = self.payment_info[category_key]['prices']
                        embed.add_field(
                            name=f"Category {category_key.replace('category', '')}",
                            value=self.get_prices_string(prices) + f"\nStatus: {availability_status}",
                            inline=False
                        )
                else:
                    embed.add_field(
                        name=f"Category {category_key.replace('category', '')} Unavailable",
                        value="Currently full or does not exist",
                        inline=False
                    )
            else:
                embed.add_field(
                    name=f"Category {category_key.replace('category', '')} Not Found",
                    value="Configuration issue",
                    inline=False
                )

        ltc_address = self.payment_info.get("ltc_address", "No LTC Address Found")
        embed.add_field(name="LTC Address", value=ltc_address, inline=False)

        view = View(timeout=72000)  # 20 hours timeout
        buy_button = Button(label="Buy", style=discord.ButtonStyle.primary)
        preorder_button = Button(label="Preorder", style=discord.ButtonStyle.secondary)

        view.add_item(buy_button)
        view.add_item(preorder_button)

        async def buy_callback(interaction: discord.Interaction):
            await interaction.response.send_modal(BuyModal(self.bot, channel))

        async def preorder_callback(interaction: discord.Interaction):
            await interaction.response.send_modal(PreorderModal(self.bot, channel))

        buy_button.callback = buy_callback
        preorder_button.callback = preorder_callback

        await channel.send(f"{user.mention}, here's the slot information:", embed=embed, view=view)



    @commands.Cog.listener()
    async def on_guild_channel_create(self, channel):
        print("Channel created:", channel.name)
        try:
            await asyncio.sleep(3)
            if channel.category_id == 1249390644590416093:
                async for message in channel.history(limit=1):
                    if message.content.startswith('<@') and message.mentions:
                        user = message.mentions[0]
                        await self.send_slot_info(channel, user)
        except Exception as e:
            print(f"Error in on_guild_channel_create: {e}")


class BuyModal(Modal):
    def __init__(self, bot, channel):
        self.bot = bot
        self.channel = channel
        super().__init__(title="Buy Slot Information")
        self.add_item(TextInput(label="Your Slot Name", custom_id="slot_name"))
        self.add_item(TextInput(label="Plan (weekly, monthly, lifetime)", custom_id="plan"))
        self.add_item(TextInput(label="Your Autobuy Link (optional)", custom_id="autobuy_link", required=False))
        self.add_item(TextInput(label="How many Vouches you have in Shiba", custom_id="vouches"))

    async def on_submit(self, interaction):
        slot_name = self.children[0].value
        plan = self.children[1].value
        autobuy_link = self.children[2].value
        vouches = self.children[3].value

        embed = discord.Embed(
            title="Buy Slot Information",
            description=f"New Buy Slot Submission",
            color=discord.Color.blue()
        )
        embed.add_field(name="Slot Name", value=slot_name, inline=False)
        embed.add_field(name="Plan", value=plan, inline=False)
        embed.add_field(name="Autobuy Link", value=autobuy_link or "N/A", inline=False)
        embed.add_field(name="Vouches in Shiba", value=vouches, inline=False)

        await self.channel.send(embed=embed)
        await interaction.response.send_message("Your slot information has been submitted!", ephemeral=True)

class PreorderModal(Modal):
    def __init__(self, bot, channel):
        self.bot = bot
        self.channel = channel
        super().__init__(title="Preorder Slot Information")
        self.add_item(TextInput(label="Your Slot Name", custom_id="slot_name"))
        self.add_item(TextInput(label="Plan (weekly, monthly, lifetime)", custom_id="plan"))
        self.add_item(TextInput(label="Your Autobuy Link (optional)", custom_id="autobuy_link", required=False))
        self.add_item(TextInput(label="How many Vouches you have in Shiba", custom_id="vouches"))

    async def on_submit(self, interaction):
        slot_name = self.children[0].value
        plan = self.children[1].value
        autobuy_link = self.children[2].value
        vouches = self.children[3].value

        embed = discord.Embed(
            title="Preorder Slot Information",
            description=f"New Preorder Slot Submission",
            color=discord.Color.green()
        )
        embed.add_field(name="Slot Name", value=slot_name, inline=False)
        embed.add_field(name="Plan", value=plan, inline=False)
        embed.add_field(name="Autobuy Link", value=autobuy_link or "N/A", inline=False)
        embed.add_field(name="Vouches in Shiba", value=vouches, inline=False)

        await self.channel.send(embed=embed)
        await interaction.response.send_message("Your preorder slot information has been submitted!", ephemeral=True)



async def setup(bot):
    await bot.add_cog(BuySlot(bot))
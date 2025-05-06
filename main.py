import discord
from discord.ext import commands, tasks
import asyncio
import logging
import os
import sys
import traceback
import random
import datetime
from datetime import timezone
import json
import aiohttp
import async_timeout
import functools
import itertools
import math
import re
import time
import typing
import sqlite3
from discord import app_commands
from typing import Optional, List, Dict, Any, Union

intents = discord.Intents.all()
bot = commands.Bot(command_prefix='!', intents=intents)


if not hasattr(bot, 'tree'):
    bot.tree = app_commands.CommandTree(bot)
with open('config.json', 'r') as f:
    config = json.load(f)

token = "MTM0MTc3NjQyMzU2MzgyNTE4NQ.GZO-dq.qS8fJWjHpAfqTEdTXowB3hQgGspHGCJSm4s7XI"
logs_channel_id = 726447263636364


import colorama
from colorama import Fore, Style

colorama.init(autoreset=True)

@bot.event
async def on_ready():
    slot_bot_ascii = f"""
{Fore.CYAN}
  ██████╗ ██████╗  █████╗ ██╗  ██╗ ██████╗ ███╗   ██╗███████╗████████╗
██╔══██╗██╔══██╗██╔══██╗██║ ██╔╝██╔═══██╗████╗  ██║██╔════╝╚══██╔══╝
██████╔╝██████╔╝███████║█████╔╝ ██║   ██║██╔██╗ ██║███████╗   ██║   
██╔═══╝ ██╔═══╝ ██╔══██║██╔═██╗ ██║   ██║██║╚██╗██║╚════██║   ██║   
██║     ██║     ██║  ██║██║  ██╗╚██████╔╝██║ ╚████║███████║   ██║   
╚═╝     ╚═╝     ╚═╝  ╚═╝╚═╝  ╚═╝ ╚═════╝ ╚═╝  ╚═══╝╚══════╝   ╚═╝   
{Style.RESET_ALL}
    """

    print(slot_bot_ascii)
    print(f'{Fore.GREEN}Logged in as {bot.user.name} - {bot.user.id}{Style.RESET_ALL}')
    print(f'{Fore.YELLOW}------{Style.RESET_ALL}')
    await bot.tree.sync()
    check_slot_expiry.start()
    check_slot_warnings.start()
    auto_ping_reset.start()
    await bot.change_presence(activity=discord.Game(name='Managing Slots'))

    
    with open('config.json', 'r') as f:
        config = json.load(f)
    logs_channel_id = config['log_channel']
    logs_channel = bot.get_channel(logs_channel_id)


async def load_extensions():
    # Here you should load 'cogs.utility' and not 'utility' if your cog is inside the cogs subdirectory.
    cogs = ['cogs.buy']  # make sure the path to the cog is correct based on your project structure
    for cog in cogs:
        await bot.load_extension(cog)


def owner_only():
    def predicate(interaction: discord.Interaction) -> bool:
        with open('owners.json', 'r') as f:
            owners = json.load(f)
        if interaction.user.id in owners.get('owner_ids', []):
            return True
        else:
            raise app_commands.CheckFailure('You do not have the required permissions to use this command.')
    return app_commands.check(predicate)

@bot.tree.error
async def on_app_command_error(interaction: discord.Interaction, error: app_commands.AppCommandError):
    if isinstance(error, app_commands.CheckFailure):
        await interaction.response.send_message(str(error), ephemeral=True)
    else:
        await interaction.response.send_message('An unexpected error occurred. Please try again later.', ephemeral=True)
        # Log the error for further investigation
        logging.error(f'Error in command {interaction.command.name}: {error}')
@bot.tree.command(name='config', description='Configure server roles and categories')
@owner_only()
@app_commands.describe(
    slotowner_role='Role for slot owners',
    staff_role='Role for staff members',
    owner_role='Role for server owners',
    category1='First category',
    category2='Second category',
    slot_recovery_category='Category for slot recovery',
    log_channel='Channel for logs',
    ping_logs_channel='Channel for ping logs',
    ping_reset_logs_channel='Channel for ping reset logs',
    buyslot_category='Category for Buy Slots',
    buyslot_logs_channel='Channel for Buy Slots logs'
)
async def config(interaction: discord.Interaction, slotowner_role: discord.Role, staff_role: discord.Role, owner_role: discord.Role, category1: discord.CategoryChannel, category2: discord.CategoryChannel, slot_recovery_category: discord.CategoryChannel, log_channel: discord.TextChannel, ping_logs_channel: discord.TextChannel, ping_reset_logs_channel: discord.TextChannel, buyslot_category: discord.CategoryChannel, buyslot_logs_channel: discord.TextChannel):
    config_data = {
        'slotowner_role': slotowner_role.id,
        'staff_role': staff_role.id,
        'owner_role': owner_role.id,
        'category1': category1.id,
        'category2': category2.id,
        'slot_recovery_category': slot_recovery_category.id,
        'log_channel': log_channel.id,
        'ping_logs_channel': ping_logs_channel.id,
        'ping_reset_logs_channel': ping_reset_logs_channel.id,
        'buyslot_category': buyslot_category.id,
        'buyslot_logs_channel': buyslot_logs_channel.id
    }
    with open('config.json', 'w') as f:
        json.dump(config_data, f, indent=4)
    await interaction.response.send_message('Configuration saved successfully!')

@bot.tree.command(name='set_payment', description='Set payment details for categories')
@app_commands.describe(
    category1_weekly='Weekly price for category 1',
    category1_monthly='Monthly price for category 1',
    category1_lifetime='Optional lifetime price for category 1',
    category2_weekly='Weekly price for category 2',
    category2_monthly='Monthly price for category 2',
    category2_lifetime='Optional lifetime price for category 2',
    ltc_address='Litecoin address'
)
async def set_payment(
    interaction: discord.Interaction,
    category1_weekly: float,
    category1_monthly: float,
    category1_lifetime: Optional[float],
    category2_weekly: float,
    category2_monthly: float,
    category2_lifetime: Optional[float],
    ltc_address: str
):
    payment_data = {
        'category1': {
            'weekly_price': category1_weekly,
            'monthly_price': category1_monthly,
            'lifetime_price': category1_lifetime
        },
        'category2': {
            'weekly_price': category2_weekly,
            'monthly_price': category2_monthly,
            'lifetime_price': category2_lifetime
        },
        'ltc_address': ltc_address
    }

    with open('payment.json', 'w') as f:
        json.dump(payment_data, f, indent=4)

    await interaction.response.send_message('Payment details saved successfully!', ephemeral=True)

import random

async def Slot_Embed(interaction: discord.Interaction, category: discord.CategoryChannel, user: discord.User, slot_name: str, expiry_days: int, here_limit: int, everyone_limit: int):
    embed = discord.Embed(title="__SELLER SLOT__", color=discord.Color(0xaabbf6))

    rules = (
        f"• {here_limit} here pings per day.",
        f"• {everyone_limit} everyone pings per day.",
    )

    embed.description = "\n".join(rules)
    embed.add_field(name="SLOT OWNER INFORMATION", value=f"\nUser: {user.name}\nUserID: {user.id}\nUserTag: {user.mention}\n")

    expiry_time = datetime.datetime.now() + datetime.timedelta(days=expiry_days)
    embed.add_field(name="DURATION", value=f"Expires: <t:{int(expiry_time.timestamp())}:R> ({expiry_time.strftime('%Y-%m-%d %H:%M:%S')})")
    
    embed.add_field(name="", value=f"\n- Always Follow Slot Rules\n- Always Accept Middleman")
    
    return embed

@bot.tree.command(name='slot', description='Create a slot')
@app_commands.describe(
    category='Category choice (1 or 2)',
    user='User for the slot',
    slot_name='Name of the slot',
    expiry_days='Number of days until expiry',
    here_limit='Max @here pings per day',
    everyone_limit='Max @everyone pings per day'
)
async def slot(interaction: discord.Interaction, category: int, user: discord.User, slot_name: str, expiry_days: int, here_limit: int, everyone_limit: int):
    with open('config.json', 'r') as f:
        config = json.load(f)

    category_id = config[f'category{category}']
    category_channel = bot.get_channel(category_id)

    if not category_channel or not isinstance(category_channel, discord.CategoryChannel):
        await interaction.response.send_message('Invalid category selected.', ephemeral=True)
        return

    # ✅ Create slot channel
    channel = await category_channel.create_text_channel(name=f'〞ʚ・{slot_name}', topic=f'Slot owner: {user.id}')

    # ✅ Embed Message
    embed = await Slot_Embed(interaction, category_channel, user, slot_name, expiry_days, here_limit, everyone_limit)
    embed.color = discord.Color(0xaabbf6)
    await channel.send(embed=embed)

    # ✅ Store slot data including new ping limits
    expiry_time = datetime.datetime.now() + datetime.timedelta(days=expiry_days)
    slot_data = {
        'channel_name': channel.name,
        'expiry_info': expiry_time.strftime('%Y-%m-%d %H:%M:%S'),
        'slot_owner_id': user.id,
        'category_choice': category,
        'key': ''.join(random.choices('ABCDEFGHIJKLMNOPQRSTUVWXYZ0123456789', k=20)),
        'status': 'Active',
        'here_limit': here_limit,
        'everyone_limit': everyone_limit
    }

    if not os.path.exists('data'):
        os.makedirs('data')

    with open('data/slots.json', 'r+') as f:
        try:
            slots = json.load(f)
        except json.JSONDecodeError:
            slots = []
        slots.append(slot_data)
        f.seek(0)
        json.dump(slots, f, indent=4)

    await user.send(f'Your slot key is: {slot_data["key"]}')
    await interaction.response.send_message('Slot created successfully!')

    # ✅ Set channel permissions
    everyone_role = interaction.guild.default_role
    await channel.set_permissions(user, send_messages=True, mention_everyone=True, embed_links=True, use_external_emojis=True, use_external_stickers=True, attach_files=True)
    await channel.set_permissions(everyone_role, view_channel=True, send_messages=False, read_message_history=True)

    # ✅ Assign premium role to slot owner
    premium_role_id = config.get('slotowner_role')
    premium_role = interaction.guild.get_role(premium_role_id)
    if premium_role:
        await user.add_roles(premium_role)

    # ✅ Log message
    log_embed = discord.Embed(
        title="Slot Created",
        description=f"A slot has been created by {user.mention} in category {category}.",
        color=discord.Color(0xaabbf6)
    )
    log_embed.add_field(name="Slot Name", value=slot_name, inline=False)
    log_embed.add_field(name="Expiry Days", value=str(expiry_days), inline=False)
    log_embed.add_field(name="Channel Name", value=channel.name, inline=False)
    log_embed.add_field(name="Slot Owner", value=user.mention, inline=False)
    log_embed.add_field(name="Ping Limits", value=f"🔹 `@here`: `{here_limit}` per day\n🔹 `@everyone`: `{everyone_limit}` per day", inline=False)

    log_channel_id = config.get('log_channel')
    log_channel = bot.get_channel(log_channel_id)
    if log_channel:
        await log_channel.send(embed=log_embed)

@bot.tree.command(name='revoke', description='Revoke a user\'s slot')
@app_commands.describe(
    user='User whose slot is to be revoked',
    reason='Reason for revoking the slot (optional)'
)
async def revoke(interaction: discord.Interaction, user: discord.User, reason: Optional[str] = None):
    with open('config.json', 'r') as f:
        config = json.load(f)

    staff_role_id = config['staff_role']
    staff_role = interaction.guild.get_role(staff_role_id)

    if staff_role not in interaction.user.roles:
        await interaction.response.send_message('You do not have the required permissions to use this command.', ephemeral=True)
        return

    with open('data/slots.json', 'r+') as f:
        slots = json.load(f)
        slot = next((s for s in slots if s['slot_owner_id'] == user.id), None)

        if not slot:
            await interaction.response.send_message('No slot found for the specified user.', ephemeral=True)
            return

        channel = discord.utils.get(interaction.guild.channels, name=slot['channel_name'])
        if channel:
            await channel.set_permissions(user, send_messages=False)
            revoke_embed = discord.Embed(
                title="Slot Revoked",
                description=f"Your slot has been revoked.{' Reason: ' + reason if reason else ''}",
                color=discord.Color.red()
            )
            await user.send(embed=revoke_embed)

        slot['status'] = 'Revoked'
        f.seek(0)
        json.dump(slots, f, indent=4)
        f.truncate()

    await interaction.response.send_message(f'Slot for {user.mention} has been revoked. Reason: {reason if reason else "No reason provided."}', ephemeral=True)

@bot.tree.command(name='unrevoke', description='Unrevoke a user\'s slot')
@app_commands.describe(
    user='User whose slot is to be unrevoked'
)
async def unrevoke(interaction: discord.Interaction, user: discord.User):
    with open('config.json', 'r') as f:
        config = json.load(f)

    staff_role_id = config['staff_role']
    staff_role = interaction.guild.get_role(staff_role_id)

    if staff_role not in interaction.user.roles:
        await interaction.response.send_message('You do not have the required permissions to use this command.', ephemeral=True)
        return

    with open('data/slots.json', 'r+') as f:
        slots = json.load(f)
        slot = next((s for s in slots if s['slot_owner_id'] == user.id), None)

        if not slot:
            await interaction.response.send_message('No slot found for the specified user.', ephemeral=True)
            return

        channel = discord.utils.get(interaction.guild.channels, name=slot['channel_name'])
        if channel:
            await channel.set_permissions(user, send_messages=True)
            unrevoke_embed = discord.Embed(
                title="Slot Unrevoked",
                description="Your slot has been unrevoked.",
                color=discord.Color.green()
            )
            await user.send(embed=unrevoke_embed)

        slot['status'] = 'Active'
        f.seek(0)
        json.dump(slots, f, indent=4)
        f.truncate()

    await interaction.response.send_message(f'Slot for {user.mention} has been unrevoked.', ephemeral=True)


@tasks.loop(hours=1)
async def check_slot_expiry():
    now = datetime.datetime.now()
    with open('data/slots.json', 'r+') as f:
        slots = json.load(f)
        for slot in slots:
            expiry_time = datetime.datetime.strptime(slot['expiry_info'], '%Y-%m-%d %H:%M:%S')
            if expiry_time <= now and slot['status'] == 'Active':
                slot['status'] = 'Expired'
                user = await bot.fetch_user(slot['slot_owner_id'])
                channel = discord.utils.get(bot.get_all_channels(), name=slot['channel_name'])
                expiry_embed = discord.Embed(title="Slot Expired", description="Your slot has expired.")
                await user.send(embed=expiry_embed)
                if channel:
                    await channel.send(embed=expiry_embed)
                    await channel.set_permissions(user, send_messages=False)
        f.seek(0)
        json.dump(slots, f, indent=4)
        f.truncate()


def format_day_expiry_date(expiry_time):
            return expiry_time.strftime('%-d %B')

@tasks.loop(hours=24)
async def check_slot_warnings():
            now = datetime.datetime.now()
            warning_days = [1, 2, 3]
            with open('data/slots.json', 'r+') as f:
                slots = json.load(f)
                for slot in slots:
                    expiry_time = datetime.datetime.strptime(slot['expiry_info'], '%Y-%m-%d %H:%M:%S')
                    days_remaining = (expiry_time - now).days
                    if days_remaining in warning_days and slot['status'] == 'Active':
                        user = await bot.fetch_user(slot['slot_owner_id'])
                        channel = discord.utils.get(bot.get_all_channels(), name=slot['channel_name'])
                        warning_embed = discord.Embed(title="Slot Expiry Warning", description="Your slot expires soon, Please Renew Slot.")
                        warning_embed.add_field(name="Time Remaining", value=f"<t:{int(expiry_time.timestamp())}:R> ({format_day_expiry_date(expiry_time)})")
                        await user.send(embed=warning_embed)
                        if channel:
                            await channel.send(embed=warning_embed)


import discord
import json

@bot.event
async def on_message(message: discord.Message):
    if message.author.bot:
        return

    with open('config.json', 'r') as f:
        config = json.load(f)

    category1_id = config['category1']
    category2_id = config['category2']

    if message.channel.category_id not in [category1_id, category2_id]:
        return

    # ✅ Load slot data (Get user's limits)
    with open('data/slots.json', 'r') as f:
        slots = json.load(f)

    user_slot = next((s for s in slots if s['slot_owner_id'] == message.author.id), None)
    if not user_slot:
        return  # User doesn't own a slot, ignore.

    # ✅ Get stored ping limits
    here_limit = user_slot.get('here_limit', 2)  # Default: 2 if not set
    everyone_limit = user_slot.get('everyone_limit', 1)  # Default: 1 if not set

    user_id = str(message.author.id)

    # ✅ Load and track ping usage
    with open('data/pings.json', 'r+') as f:
        try:
            pings_data = json.load(f)
        except json.JSONDecodeError:
            pings_data = {}

        if user_id not in pings_data:
            pings_data[user_id] = {'here_pings': 0, 'everyone_pings': 0}

        # ✅ Handle @here pings
        if '@here' in message.content:
            pings_data[user_id]['here_pings'] += 1
            used_pings = pings_data[user_id]['here_pings']

            if used_pings <= here_limit:
                warning_embed = discord.Embed(
                    description=f"You have used **{used_pings}/{here_limit}** @here pings.",
                    color=discord.Color.orange()
                )
                await message.channel.send(embed=warning_embed)
                await message.channel.send("# USE MM") 

            if used_pings > here_limit:
                await revoke_slot(message.author, 'Exceeded @here ping limit')
                await message.channel.set_permissions(message.author, send_messages=False)

                # 🔹 Log slot revocation
                log_channel_id = config.get('ping_logs_channel')
                log_channel = bot.get_channel(log_channel_id)
                if log_channel:
                    log_embed = discord.Embed(
                        title="🚫 Slot Revoked: @here Ping Limit Exceeded",
                        description=f"{message.author.mention}'s slot was revoked for exceeding their @here ping limit.",
                        color=discord.Color.red()
                    )
                    await log_channel.send(embed=log_embed)

        # ✅ Handle @everyone pings
        if '@everyone' in message.content:
            pings_data[user_id]['everyone_pings'] += 1
            used_pings = pings_data[user_id]['everyone_pings']

            if used_pings <= everyone_limit:
                warning_embed = discord.Embed(
                    description=f"You have used **{used_pings}/{everyone_limit}** @everyone pings.",
                    color=discord.Color.orange()
                )
                await message.channel.send(embed=warning_embed)
                await message.channel.send("# USE MM") 

            if used_pings > everyone_limit:
                await revoke_slot(message.author, 'Exceeded @everyone ping limit')
                await message.channel.set_permissions(message.author, send_messages=False)

                # 🔹 Log slot revocation
                log_channel_id = config.get('ping_logs_channel')
                log_channel = bot.get_channel(log_channel_id)
                if log_channel:
                    log_embed = discord.Embed(
                        title="🚫 Slot Revoked: @everyone Ping Limit Exceeded",
                        description=f"{message.author.mention}'s slot was revoked for exceeding their @everyone ping limit.",
                        color=discord.Color.red()
                    )
                    await log_channel.send(embed=log_embed)

        f.seek(0)
        json.dump(pings_data, f, indent=4)
        f.truncate()


async def revoke_slot(user: discord.User, reason: str):
    with open('data/slots.json', 'r+') as f:
        slots = json.load(f)
        slot = next((s for s in slots if s['slot_owner_id'] == user.id), None)

        if slot:
            slot['status'] = 'Revoked'
            channel = discord.utils.get(bot.get_all_channels(), name=slot['channel_name'])
            if channel:
                revoke_embed = discord.Embed(
                    title="❌ Slot Revoked",
                    description=f"Your slot has been revoked!\n**Reason:** {reason}",
                    color=0xEC1111
                )
                await channel.send(embed=revoke_embed)
                await channel.set_permissions(user, send_messages=False)  # ✅ Only disable sending

            f.seek(0)
            json.dump(slots, f, indent=4)
            f.truncate()


@bot.tree.command(name='recover', description='Recover slot ownership using a key')
@app_commands.describe(
    key='The recovery key for the slot'
)
async def recover(interaction: discord.Interaction, key: str):
    with open('data/slots.json', 'r+') as f:
        slots = json.load(f)
        slot = next((s for s in slots if s['key'] == key), None)

        if not slot:
            await interaction.response.send_message('Invalid recovery key.', ephemeral=True)
            return

        old_owner_id = slot['slot_owner_id']
        new_owner_id = interaction.user.id

        if old_owner_id == new_owner_id:
            await interaction.response.send_message('You already have your slot. Please use the /getslot command.', ephemeral=True)
            return

        slot['slot_owner_id'] = new_owner_id

        channel = discord.utils.get(interaction.guild.channels, name=slot['channel_name'])
        if channel:
            # Update permissions for the new owner
            await channel.set_permissions(interaction.user, send_messages=True, mention_everyone=True, embed_links=True, use_external_emojis=True, use_external_stickers=True, attach_files=True)
            revoke_embed = discord.Embed(title="Slot Ownership Changed", description=f"Slot ownership has been transferred to {interaction.user.mention}.", color=discord.Color.green())
            await channel.send(embed=revoke_embed)

            # Remove send message permissions from the old owner
            old_owner = interaction.guild.get_member(old_owner_id)
            if old_owner:
                await channel.set_permissions(old_owner, send_messages=False)

        # Generate a new key and update the slot data
        new_key = ''.join(random.choices('ABCDEFGHIJKLMNOPQRSTUVWXYZ0123456789', k=20))
        slot['key'] = new_key

        # Save the updated slots data
        f.seek(0)
        json.dump(slots, f, indent=4)
        f.truncate()

    # Send the new key to the user's DMs
    await interaction.user.send(f'Your new slot key is: {new_key}')

    # Add slot owner role to the user
    with open('config.json', 'r') as f:
        config = json.load(f)
    slotowner_role_id = config.get('slotowner_role')
    slotowner_role = interaction.guild.get_role(slotowner_role_id)
    if slotowner_role:
        await interaction.user.add_roles(slotowner_role)

    confirmation_embed = discord.Embed(title="Slot Recovery Successful", description=f"You have successfully recovered the slot with key: {key}", color=discord.Color.blue())
    await interaction.response.send_message(embed=confirmation_embed, ephemeral=True)

    # Log the recovery details
    log_channel_id = config['log_channel']
    log_channel = bot.get_channel(log_channel_id)
    if log_channel:
        log_embed = discord.Embed(title="Slot Recovery Log", description=f"Slot with key {key} has been recovered by {interaction.user.mention}.", color=discord.Color.orange())
        log_embed.add_field(name="Old Owner ID", value=str(old_owner_id))
        log_embed.add_field(name="New Owner ID", value=str(new_owner_id))
        await log_channel.send(embed=log_embed)
@bot.event
async def on_guild_channel_create(channel: discord.abc.GuildChannel):
    await asyncio.sleep(3)  # Sleep for 3 seconds
    with open('config.json', 'r') as f:
        config = json.load(f)

    if channel.category_id == config['slot_recovery_category']:
        async for message in channel.history(limit=1):
            if message.content.startswith('<@') and message.mentions:
                user = message.mentions[0]
                with open('data/slots.json', 'r') as f:
                    slots = json.load(f)

                user_slot = next((s for s in slots if s['slot_owner_id'] == user.id), None)

                if user_slot:
                    slot_channel = discord.utils.get(channel.guild.channels, name=user_slot['channel_name'])
                    if slot_channel:
                        await slot_channel.set_permissions(user, send_messages=True, mention_everyone=True, embed_links=True, use_external_emojis=True, use_external_stickers=True, attach_files=True)
                        await channel.send(f'{user.mention}, you have been given access to: {slot_channel.mention}')
                        premium_role = discord.utils.get(channel.guild.roles, name='Premium User')
                        if premium_role:
                            await user.add_roles(premium_role)
                    else:
                        await channel.send(f'{user.mention}, failed to fetch your slot. Please recover your slot by using /recover')
                else:
                    await channel.send(f'{user.mention}, failed to fetch your slot. Please recover your slot by using /recover')

                # Advanced and detailed log
                log_channel_id = config['log_channel']
                log_channel = bot.get_channel(log_channel_id)
                if log_channel:
                    log_embed = discord.Embed(title="Slot Access Log", description=f"Slot access granted to {user.mention}.", color=discord.Color.orange())
                    log_embed.add_field(name="User ID", value=str(user.id))
                    log_embed.add_field(name="Channel", value=slot_channel.mention if slot_channel else "N/A")
                    log_embed.add_field(name="Status", value="Success" if slot_channel else "Failed")
                    await log_channel.send(embed=log_embed)


@bot.tree.command(name='renew', description='Renew a user\'s slot')
@owner_only()
@app_commands.describe(
    user='User whose slot is to be renewed',
    days='Number of days to extend the slot'
)
async def renew(interaction: discord.Interaction, user: discord.User, days: int):
    with open('data/slots.json', 'r+') as f:
        slots = json.load(f)
        slot = next((s for s in slots if s['slot_owner_id'] == user.id), None)

        if not slot:
            await interaction.response.send_message('No slot found for the specified user.', ephemeral=True)
            return

        expiry_time = datetime.datetime.strptime(slot['expiry_info'], '%Y-%m-%d %H:%M:%S')
        new_expiry_time = expiry_time + datetime.timedelta(days=days)
        slot['expiry_info'] = new_expiry_time.strftime('%Y-%m-%d %H:%M:%S')
        slot['status'] = 'Active'

        f.seek(0)
        json.dump(slots, f, indent=4)
        f.truncate()

    await interaction.response.send_message(f'Slot for {user.mention} has been renewed for {days} days.', ephemeral=True)

    # Notify the user about the renewal
    renewal_embed = discord.Embed(title="Slot Renewed", description=f"Your slot has been renewed for {days} days.", color=discord.Color.green())
    renewal_embed.add_field(name="New Expiry Date", value=new_expiry_time.strftime('%Y-%m-%d %H:%M:%S'))
    await user.send(embed=renewal_embed)


@bot.tree.command(name='set_auto_reset', description='Set the auto reset time')
@owner_only()
@app_commands.describe(time='Time in HH:MMam or HH:MMpm format')
async def set_reset_time(interaction: discord.Interaction, time: str):
    with open('config.json', 'r+') as f:
        config = json.load(f)

    # Validate time format
    try:
        reset_time = datetime.datetime.strptime(time, '%I:%M%p').time()
    except ValueError:
        await interaction.response.send_message('Invalid time format. Please use HH:MMam or HH:MMpm format.', ephemeral=True)
        return

    # Store the reset time in the config file
    config['auto_reset_time'] = reset_time.strftime('%H:%M')
    with open('config.json', 'w') as f:
        json.dump(config, f, indent=4)

    await interaction.response.send_message(f'⌛Auto reset time set to {time}.', ephemeral=True)

@tasks.loop(minutes=1)
async def auto_ping_reset():
    now = datetime.datetime.now(datetime.timezone(datetime.timedelta(hours=5, minutes=30)))  # Kolkata timezone
    with open('config.json', 'r') as f:
        config_data = json.load(f)

    reset_time_str = config_data.get('auto_reset_time')
    if reset_time_str:
        reset_time = datetime.datetime.strptime(reset_time_str, '%H:%M').time()
        if now.hour == reset_time.hour and now.minute == reset_time.minute:
            with open('data/pings.json', 'r+') as f:
                pings_data = json.load(f)
                for user_id, ping_info in pings_data.items():
                    ping_info['here_pings'] = 0
                    ping_info['everyone_pings'] = 0
                f.seek(0)
                json.dump(pings_data, f, indent=4)
                f.truncate()

            logs_channel_id = config_data.get('ping_reset_logs_channel')
            logs_channel = bot.get_channel(logs_channel_id)
            if logs_channel:
                embed = discord.Embed(title="Ping Reset", description="All pings have been reset.", color=0x00ff00)
                await logs_channel.send(embed=embed)

    await asyncio.sleep(60)

@bot.tree.command(name='profile', description='Show user profile and slot details')
@app_commands.describe(user='User to fetch the profile for (optional)')
async def profile(interaction: discord.Interaction, user: Optional[discord.User] = None):
    user = user or interaction.user

    with open('data/slots.json', 'r') as f:
        slots = json.load(f)
        slot = next((s for s in slots if s['slot_owner_id'] == user.id), None)

    if not slot:
        await interaction.response.send_message(f'{user.mention} does not have a slot.', ephemeral=True)
        return

    with open('data/pings.json', 'r') as f:
        pings_data = json.load(f)
        user_pings = pings_data.get(str(user.id), {'here_pings': 0})
        here_pings_remaining = max(0, 3 - user_pings['here_pings'])

    embed = discord.Embed(title="User Profile", color=0x87cee6, description=f"**__USER INFORMATION__**\n\n**Name:** {user.name}\n**User ID:** {user.id}\n**Tag:** {user.mention}\n\n**__SLOT INFORMATION__**\n\n**Channel Name:** {slot['channel_name']}\n**Status:** {slot['status']}\n**Expiry:** {slot['expiry_info']}\n**Pings Remaining:** {here_pings_remaining}")

    if user.avatar:
        embed.set_thumbnail(url=user.avatar.url)
    else:
        embed.set_thumbnail(url=user.default_avatar.url)

    await interaction.response.send_message(embed=embed, ephemeral=True)


@bot.tree.command(name='sync_slots', description='Sync slot information and send embed messages in all slot channels')
@owner_only()
async def sync_slots(interaction: discord.Interaction):
    with open('data/slots.json', 'r') as f:
        slots = json.load(f)

    for slot in slots:
        channel = discord.utils.get(interaction.guild.channels, name=slot['channel_name'])
        if channel:
            user = await bot.fetch_user(slot['slot_owner_id'])
            embed = await Slot_Embed(interaction, channel.category, user, slot['channel_name'], (datetime.datetime.strptime(slot['expiry_info'], '%Y-%m-%d %H:%M:%S') - datetime.datetime.now()).days)
            embed.color = discord.Color.blue()
            await channel.send(embed=embed)

    await interaction.response.send_message('Slot information synced and embed messages sent in all slot channels.', ephemeral=True)


@bot.tree.command(name='delete', description='Delete a user\'s slot and all related data')
@app_commands.describe(
    user='User whose slot and database entry are to be deleted'
)
async def delete(interaction: discord.Interaction, user: discord.User):
    with open('config.json', 'r') as f:
        config = json.load(f)

    # ✅ Permission Check (Only Owner Role Can Use)
    owner_role_id = config.get('owner_role')
    owner_role = interaction.guild.get_role(owner_role_id)

    if owner_role and owner_role not in interaction.user.roles:
        await interaction.response.send_message('❌ You do not have permission to use this command.', ephemeral=True)
        return

    # ✅ Load Slot Data
    with open('data/slots.json', 'r+') as f:
        try:
            slots = json.load(f)
        except json.JSONDecodeError:
            slots = []

        user_slots = [slot for slot in slots if slot['slot_owner_id'] == user.id]

        if not user_slots:
            await interaction.response.send_message('❌ No slot found for the specified user.', ephemeral=True)
            return

        # ✅ Delete Slot Channel
        for slot in user_slots:
            channel = discord.utils.get(interaction.guild.channels, name=slot['channel_name'])
            if channel:
                await channel.delete()

            slots.remove(slot)  # Remove from slots.json

        f.seek(0)
        json.dump(slots, f, indent=4)
        f.truncate()

    # ✅ Remove Ping Data
    with open('data/pings.json', 'r+') as f:
        try:
            pings_data = json.load(f)
        except json.JSONDecodeError:
            pings_data = {}

        if str(user.id) in pings_data:
            del pings_data[str(user.id)]  # Remove User's Ping Data

        f.seek(0)
        json.dump(pings_data, f, indent=4)
        f.truncate()

    # ✅ Remove Slot Owner Role (If Exists)
    slotowner_role_id = config.get('slotowner_role')
    slotowner_role = interaction.guild.get_role(slotowner_role_id)

    if slotowner_role and slotowner_role in user.roles:
        await user.remove_roles(slotowner_role)

    # ✅ Log Deletion (If Log Channel Exists)
    log_channel_id = config.get('log_channel')
    log_channel = bot.get_channel(log_channel_id)
    if log_channel:
        log_embed = discord.Embed(
            title="🚫 Slot Deleted",
            description=f"A slot has been **deleted** for {user.mention}.",
            color=discord.Color.red()
        )
        log_embed.add_field(name="Deleted By", value=interaction.user.mention, inline=False)
        log_embed.add_field(name="Affected User", value=user.mention, inline=False)
        await log_channel.send(embed=log_embed)

    # ✅ Confirmation Message
    await interaction.response.send_message(f'✅ Slot for {user.mention} has been deleted, including all related data.', ephemeral=True)

import requests
import asyncio
from typing import Optional

# Load config
with open('config.json', 'r') as f:
    config = json.load(f)

# Load payment details
with open('payment.json', 'r') as f:
    payment_data = json.load(f)

def usd_to_ltc(amount):
    url = 'https://min-api.cryptocompare.com/data/price?fsym=LTC&tsyms=USD'
    r = requests.get(url)
    d = r.json()
    price = d['USD']
    ltcval = amount / price
    ltcvalf = round(ltcval, 7)
    return ltcvalf

def ltc_to_usd(amount):
    url = 'https://min-api.cryptocompare.com/data/price?fsym=LTC&tsyms=USD'
    r = requests.get(url)
    d = r.json()
    price = d['USD']
    usd = amount * price
    usdf = round(usd, 3)
    return usdf

def get_hash(address):
    endpoint = f"https://api.blockcypher.com/v1/ltc/main/addrs/{address}/full"
    response = requests.get(endpoint)
    data = response.json()
    latest_transaction = data['txs'][0]
    latest_hash = latest_transaction['hash']
    conf = latest_transaction['confirmations']
    return latest_hash, conf

def get_address_balance(address):
    endpoint = f"https://api.blockcypher.com/v1/ltc/main/addrs/{address}/balance"
    response = requests.get(endpoint)
    data = response.json()
    balance = data['balance'] / 10**8
    unconfirmed_balance = data['unconfirmed_balance'] / 10**8
    return balance, unconfirmed_balance

@bot.tree.command(name='config_autobuy', description='Configure autobuy payment details for categories')
@owner_only()
@app_commands.describe(
    category1_weekly='Weekly price for category 1',
    category1_monthly='Monthly price for category 1',
    category1_lifetime='Lifetime price for category 1',
    category2_weekly='Weekly price for category 2',
    category2_monthly='Monthly price for category 2',
    category2_lifetime='Lifetime price for category 2'
)
async def config_autobuy(
    interaction: discord.Interaction,
    category1_weekly: float,
    category1_monthly: float,
    category1_lifetime: float,
    category2_weekly: float,
    category2_monthly: float,
    category2_lifetime: float
):
    payment_data = {
        'autobuy': {
            'category1': {
                'weekly_price': category1_weekly,
                'monthly_price': category1_monthly,
                'lifetime_price': category1_lifetime
            },
            'category2': {
                'weekly_price': category2_weekly,
                'monthly_price': category2_monthly,
                'lifetime_price': category2_lifetime
            }
        }
    }

    with open('payment.json', 'r+') as f:
        try:
            existing_payment_data = json.load(f)
        except json.JSONDecodeError:
            existing_payment_data = {}
        existing_payment_data.update(payment_data)
        f.seek(0)
        json.dump(existing_payment_data, f, indent=4)
        f.truncate()

    await interaction.response.send_message('Auto-buy payment details saved successfully!', ephemeral=True)


import discord
from discord.ext import commands, tasks
import json
import requests
import asyncio


# Utility functions
def usd_to_ltc(usd_amount):
    url = 'https://min-api.cryptocompare.com/data/price?fsym=LTC&tsyms=USD'
    response = requests.get(url)
    response_json = response.json()
    ltc_price_in_usd = response_json['USD']
    return round(usd_amount / ltc_price_in_usd, 8)

def verify_payment(address, amount_ltc):
    url = f'https://api.blockcypher.com/v1/ltc/main/addrs/{address}/balance'
    response = requests.get(url)
    data = response.json()
    balance = data['balance'] / 10**8  # satoshis to LTC
    unconfirmed_balance = data['unconfirmed_balance'] / 10**8  # satoshis to LTC
    return balance + unconfirmed_balance >= amount_ltc

async def fetch_category_channels(category_id):
    category = bot.get_channel(category_id)
    if category and isinstance(category, discord.CategoryChannel):
        return len(category.channels)
    else:
        return 0

# Create the buy_slot command
@bot.tree.command(name="buy_slot", description="Purchase a slot")
async def buy_slot(interaction: discord.Interaction):
    category1_count = await fetch_category_channels(config['category1'])
    category2_count = await fetch_category_channels(config['category2'])

    embed = discord.Embed(title="Buy Slot", description="Choose the category and plan.")
    embed.add_field(name="Category 1", value=f"Total Channels: {category1_count}", inline=False)
    embed.add_field(name="Category 2", value=f"Total Channels: {category2_count}", inline=False)
    embed.set_footer(text="Make your choice below")

    view = discord.ui.View(timeout=None)
    buy_button = discord.ui.Button(label="Buy", style=discord.ButtonStyle.primary, emoji="💳")
    view.add_item(buy_button)

    async def buy_callback(interaction_button: discord.Interaction):
        await interaction_button.response.send_modal(BuySlotModal())
    
    buy_button.callback = buy_callback
    await interaction.response.send_message(embed=embed, view=view)

class BuySlotModal(discord.ui.Modal):
    def __init__(self):
        super().__init__(title="Buy Slot Information")
        self.add_item(discord.ui.TextInput(label="Category (1 or 2)", custom_id="category"))
        self.add_item(discord.ui.TextInput(label="Plan (weekly, monthly, lifetime)", custom_id="plan"))

    async def on_submit(self, interaction):
        category = self.children[0].value
        plan = self.children[1].value

        if category not in ['1', '2'] or plan not in ['weekly', 'monthly', 'lifetime']:
            await interaction.response.send_message("Invalid category or plan. Please try again.", ephemeral=True)
            return

        category_key = f'category{category}'
        prices = payment_info.get(category_key, {})
        if not prices:
            await interaction.response.send_message("Prices not configured for this category.", ephemeral=True)
            return

        price_usd = prices[f'{plan}_price']
        price_ltc = usd_to_ltc(price_usd)

        embed = discord.Embed(title="Payment Details", description="Please make the payment to the following address.")
        embed.add_field(name="Category", value=category, inline=False)
        embed.add_field(name="Plan", value=plan, inline=False)
        embed.add_field(name="Addy", value=payment_info['ltc_address'], inline=False)
        embed.add_field(name="Amnt", value=f"{price_usd} USD / {price_ltc} LTC", inline=False)

        view = discord.ui.View(timeout=None)
        paste_button = discord.ui.Button(label="Paste", style=discord.ButtonStyle.secondary, emoji="📋", disabled=False)
        view.add_item(paste_button)

        async def paste_callback(interaction_button: discord.Interaction):
            await interaction_button.response.send_message(f"Address: {payment_info['ltc_address']}", ephemeral=True)
            await interaction_button.response.send_message(f"Amount: {price_ltc} LTC", ephemeral=True)
            await asyncio.sleep(1)  # Adding a sleep to debounce multiple fast clicks

            if verify_payment(payment_info['ltc_address'], price_ltc):
                await interaction_button.followup.send("Payment successful!", ephemeral=True)
            else:
                await interaction_button.followup.send("Waiting for payment to be received...", ephemeral=True)
                while not verify_payment(payment_info['ltc_address'], price_ltc):
                    await asyncio.sleep(30)  # Check every 30 seconds

                await interaction_button.followup.send("Payment successful!", ephemeral=True)

            paste_button.disabled = True
            await interaction_button.edit_original_response(view=view)

        paste_button.callback = paste_callback
        await interaction.response.send_message(embed=embed, view=view)


@bot.tree.command(name='getslot', description='Fetch and access your slot')
async def getslot(interaction: discord.Interaction):
    user = interaction.user

    # Load slot data
    with open('data/slots.json', 'r') as f:
        slots = json.load(f)
        slot = next((s for s in slots if s['slot_owner_id'] == user.id and (s['status'] == 'Active' or not s['status'])), None)

    if not slot:
        await interaction.response.send_message('You do not have an active slot.', ephemeral=True)
        return

    channel = discord.utils.get(interaction.guild.channels, name=slot['channel_name'])
    
    if not channel:
        await interaction.response.send_message('Failed to fetch the slot channel. Please contact the administrator.', ephemeral=True)
        return

    # Check existing permissions
    existing_permissions = channel.permissions_for(user)
    if existing_permissions.send_messages and existing_permissions.view_channel:
        await interaction.response.send_message('You already have access to your slot.', ephemeral=True)
        return

    # Set permissions for the user
    await channel.set_permissions(user, send_messages=True, mention_everyone=True, embed_links=True, use_external_emojis=True, use_external_stickers=True, attach_files=True)

    # Send confirmation message in the slot channel
    confirmation_embed = discord.Embed(
        title="Slot Access Granted",
        description=f"{user.mention}, you have been granted access to your slot: {channel.mention}",
        color=discord.Color.green()
    )
    await channel.send(embed=confirmation_embed)

    # Notify the user
    await interaction.response.send_message('Access to your slot has been granted.', ephemeral=True)

    # Log the action
    with open('config.json', 'r') as f:
        config = json.load(f)
    log_channel_id = config.get('log_channel')
    log_channel = bot.get_channel(log_channel_id)
    if log_channel:
        log_embed = discord.Embed(
            title="Slot Access Log",
            description=f"{user.mention} has been granted access to their slot: {channel.mention}.",
            color=discord.Color.orange()
        )
        await log_channel.send(embed=log_embed)

@bot.command(name='getmyslot', help='Fetch and access your slot')
async def getmyslot(ctx):
    user = ctx.author  # Replace interaction.user with ctx.author

    # Load slot data
    with open('data/slots.json', 'r') as f:
        slots = json.load(f)
        slot = next((s for s in slots if s['slot_owner_id'] == user.id and (s['status'] == 'Active' or not s['status'])), None)

    if not slot:
        await ctx.send('You do not have an active slot.')
        return

    channel = discord.utils.get(ctx.guild.channels, name=slot['channel_name'])
    
    if not channel:
        await ctx.send('Failed to fetch the slot channel. Please contact the administrator.')
        return

    # Check existing permissions
    existing_permissions = channel.permissions_for(user)
    if existing_permissions.send_messages and existing_permissions.view_channel:
        await ctx.send('You already have access to your slot.')
        return

    # Set permissions for the user
    await channel.set_permissions(user, send_messages=True, mention_everyone=True, embed_links=True, use_external_emojis=True, use_external_stickers=True, attach_files=True)

    # Send confirmation message in the slot channel
    confirmation_embed = discord.Embed(
        title="Slot Access Granted",
        description=f"{user.mention}, you have been granted access to your slot: {channel.mention}",
        color=discord.Color.green()
    )
    await channel.send(embed=confirmation_embed)

    # Notify the user
    await ctx.send('Access to your slot has been granted.')

    # Log the action
    with open('config.json', 'r') as f:
        config = json.load(f)
    log_channel_id = config.get('log_channel')
    log_channel = bot.get_channel(log_channel_id)
    if log_channel:
        log_embed = discord.Embed(
            title="Slot Access Log",
            description=f"{user.mention} has been granted access to their slot: {channel.mention}.",
            color=discord.Color.orange()
        )
        await log_channel.send(embed=log_embed)

import discord
from discord.ext import commands
import json
import random

class RecoverSlotModal(discord.ui.Modal):
    def __init__(self):
        super().__init__(title="Recover Slot")
        self.add_item(discord.ui.TextInput(label="Recovery Key", style=discord.TextStyle.short, custom_id="recovery_key"))

    async def on_submit(self, interaction: discord.Interaction):
        recovery_key = self.children[0].value
        with open('data/slots.json', 'r+') as f:
            slots = json.load(f)
            slot = next((s for s in slots if s['key'] == recovery_key), None)

            if not slot:
                await interaction.response.send_message('Invalid recovery key.', ephemeral=True)
                return

            if slot['slot_owner_id'] == interaction.user.id:
                await interaction.response.send_message('You already own this slot. Please use the Get Slot button.', ephemeral=True)
                return

            old_owner_id = slot['slot_owner_id']
            new_owner_id = interaction.user.id
            channel = discord.utils.get(interaction.guild.channels, name=slot['channel_name'])

            if channel:
                await channel.set_permissions(interaction.user, read_messages=True, send_messages=True, mention_everyone=True, embed_links=True, use_external_emojis=True, use_external_stickers=True, attach_files=True)
                await channel.send(f'Slot ownership has been transferred to {interaction.user.mention}.')
                old_owner = interaction.guild.get_member(old_owner_id)
                if old_owner:
                    await channel.set_permissions(old_owner, overwrite=None)

            slot['slot_owner_id'] = new_owner_id
            new_key = ''.join(random.choices('ABCDEFGHIJKLMNOPQRSTUVWXYZ0123456789', k=20))
            slot['key'] = new_key

            f.seek(0)
            json.dump(slots, f, indent=4)
            f.truncate()

        await interaction.user.send(f'Your new slot key is: {new_key}')
        await interaction.response.send_message('Slot ownership has been transferred.', ephemeral=True)

        # Log the action
        with open('config.json', 'r') as f:
            config = json.load(f)
        log_channel_id = config.get('log_channel')
        log_channel = interaction.guild.get_channel(log_channel_id)
        if log_channel:
            log_embed = discord.Embed(
                title="Slot Recovery Log",
                description=f"Slot with key {recovery_key} has been recovered by {interaction.user.mention}.",
                color=discord.Color.orange()
            )
            log_embed.add_field(name="Old Owner ID", value=str(old_owner_id))
            log_embed.add_field(name="New Owner ID", value=str(new_owner_id))
            await log_channel.send(embed=log_embed)

class RecoveryButtons(discord.ui.View):
    def __init__(self):
        super().__init__(timeout=None)

    @discord.ui.button(label="Get Slot", style=discord.ButtonStyle.green, emoji="🎟", custom_id="get_slot")
    async def get_slot(self, interaction: discord.Interaction, button: discord.ui.Button):
        user = interaction.user
        with open('data/slots.json', 'r') as f:
            slots = json.load(f)
            slot = next((s for s in slots if s['slot_owner_id'] == user.id and (s['status'] == 'Active' or not s['status'])), None)

        if not slot:
            await interaction.response.send_message('You do not have an active slot.', ephemeral=True)
            return

        channel = discord.utils.get(interaction.guild.channels, name=slot['channel_name'])
        
        if not channel:
            await interaction.response.send_message('Failed to fetch the slot channel. Please contact the administrator.', ephemeral=True)
            return

        existing_permissions = channel.permissions_for(user)
        if existing_permissions.send_messages and existing_permissions.view_channel:
            await interaction.response.send_message('You already have access to your slot.', ephemeral=True)
            return

        await channel.set_permissions(user, read_messages=True, send_messages=True, mention_everyone=True, embed_links=True, use_external_emojis=True, use_external_stickers=True, attach_files=True)

        confirmation_embed = discord.Embed(
            title="Slot Access Granted",
            description=f"{user.mention}, you have been granted access to your slot: {channel.mention}",
            color=discord.Color.green()
        )
        await channel.send(embed=confirmation_embed)
        await interaction.response.send_message('Access to your slot has been granted.', ephemeral=True)

    @discord.ui.button(label="Recover", style=discord.ButtonStyle.blurple, emoji="🔑", custom_id="recover_slot")
    async def recover_slot(self, interaction: discord.Interaction, button: discord.ui.Button):
        await interaction.response.send_modal(RecoverSlotModal())

@bot.tree.command(name='start_autorec', description='Start the auto recovery process')
@commands.has_permissions(administrator=True)
@app_commands.describe(channel='Channel to send the tutorial message in')
async def start_autorec(interaction: discord.Interaction, channel: discord.TextChannel):
    embed = discord.Embed(
        title="Slot Recovery and Profile Recovery",
        description="**__Get Slot__**\n> If you are using same if which had slot then use ``GetSlot`` button\n**__Recover__**\n> Recover If your id got term which had slot, then recover database from old to new via ``Recover`` button",
        color=discord.Color.green()
    )
    embed.add_field(name='Get Slot', value='Retrieve your slot if you already have one.', inline=False)
    embed.add_field(name='Recover', value='Recover your database of Slot using a recovery key.', inline=False)
    embed.set_thumbnail(url='https://example.com/tutorial_thumbnail.png')  # Replace with your thumbnail URL

    await channel.send(embed=embed, view=RecoveryButtons())
    await interaction.response.send_message('Tutorial message sent.', ephemeral=True)


@bot.command(name='ping', help='Check the bot\'s responsiveness')
async def ping(ctx):
    latency = bot.latency
    await ctx.send(f'Pong! Bot latency is {latency * 1000:.2f}ms.')


@bot.tree.command(name='getslots', description='Get a user\'s slot and grant permissions')
@owner_only()
@app_commands.describe(
    user='User to fetch the slot for'
)
async def getslots(interaction: discord.Interaction, user: discord.User):
    with open('data/slots.json', 'r') as f:
        slots = json.load(f)
        slot = next((s for s in slots if s['slot_owner_id'] == user.id and s['status'] == 'Active'), None)

        if not slot:
            await interaction.response.send_message('The specified user does not have an active slot.', ephemeral=True)
            return

        channel = discord.utils.get(interaction.guild.channels, name=slot['channel_name'])
        if not channel:
            await interaction.response.send_message('Could not find the slot channel for the specified user.', ephemeral=True)
            return

        await channel.set_permissions(user, send_messages=True, mention_everyone=True, embed_links=True, use_external_emojis=True, use_external_stickers=True, attach_files=True)

        embed = await Slot_Embed(interaction, channel.category, user, slot['channel_name'][5:], (datetime.datetime.strptime(slot['expiry_info'], '%Y-%m-%d %H:%M:%S') - datetime.datetime.now()).days)
        embed.color = discord.Color(0xaabbf6)
        await channel.send(embed=embed)

    await interaction.response.send_message(f'Permissions granted and slot details sent in the channel {channel.mention} for user {user.mention}.', ephemeral=True)


@bot.tree.command(name='help', description='Show help for the bot commands')
async def help_command(interaction: discord.Interaction):
    help_embed = discord.Embed(title='Bot Commands', description='Here is a list of all available commands:', color=0xf0fff0)
    tree = bot.tree
    for command in tree.walk_commands():
        help_embed.add_field(name=f'/{command.name}', value=command.description, inline=False)
    help_embed.set_footer(text='Made by Amaze')
    await interaction.response.send_message(embed=help_embed, ephemeral=True)
bot.run(token)
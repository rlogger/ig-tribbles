import discord
from discord import app_commands
from discord.ext import commands
import os
from dotenv import load_dotenv
import asyncio
from io import BytesIO

from database import (
    init_db,
    save_snapshot,
    get_snapshots,
    get_snapshot_records,
    get_latest_snapshot,
    get_all_snapshots_for_plotting,
    compare_snapshots,
    add_requested,
    remove_requested,
    get_requested,
    get_requested_count,
    clear_requested,
    check_requested_accepted
)
from csv_parser import parse_instagram_csv, parse_filename, analyze_follow_status
from plotting import (
    create_follower_trend_plot,
    create_comparison_pie_chart,
    create_change_bar_chart,
    create_growth_rate_plot,
    create_summary_dashboard
)

load_dotenv()

TOKEN = os.getenv('DISCORD_TOKEN')

intents = discord.Intents.default()
intents.message_content = True
intents.dm_messages = True  # Enable DM support

bot = commands.Bot(command_prefix='!', intents=intents)


def get_guild_id(interaction_or_message) -> int:
    """Get guild_id, using 0 for DMs."""
    if hasattr(interaction_or_message, 'guild_id'):
        return interaction_or_message.guild_id or 0
    elif hasattr(interaction_or_message, 'guild'):
        return interaction_or_message.guild.id if interaction_or_message.guild else 0
    return 0


@bot.event
async def on_ready():
    """Initialize bot and sync commands."""
    await init_db()
    try:
        synced = await bot.tree.sync()
        print(f'Synced {len(synced)} command(s)')
    except Exception as e:
        print(f'Failed to sync commands: {e}')
    print(f'{bot.user} is now running!')
    print(f'Bot can be used in DMs! Just message me directly.')


@bot.event
async def on_message(message: discord.Message):
    """Handle direct CSV uploads without slash commands."""
    # Ignore bot's own messages
    if message.author == bot.user:
        return

    # Check if message has CSV attachment
    csv_attachments = [a for a in message.attachments if a.filename.endswith('.csv')]

    if csv_attachments:
        # Auto-process CSV uploads
        attachment = csv_attachments[0]
        await process_csv_upload(message, attachment)
        return

    # Handle simple text commands in DMs
    if not message.guild:  # This is a DM
        content = message.content.lower().strip()

        if content in ['hi', 'hello', 'hey', 'help', 'start']:
            await send_welcome_message(message)
        elif content in ['stats', 'status', 'dashboard']:
            await send_stats_from_message(message)
        elif content in ['history', 'uploads']:
            await send_history_from_message(message)
        elif content in ['changes', 'diff', 'compare']:
            await send_changes_from_message(message)
        elif 'who' in content and ('unfollow' in content or "doesn't follow" in content or 'not follow' in content):
            await send_nonfollowers_from_message(message)

    await bot.process_commands(message)


async def send_welcome_message(message: discord.Message):
    """Send welcome/help message."""
    embed = discord.Embed(
        title="👋 Hey! I'm your Instagram Follower Tracker",
        description="I help you track who follows you, who unfollowed, and more!",
        color=discord.Color.blurple()
    )

    embed.add_field(
        name="📤 Getting Started",
        value="Just **drop your Instagram CSV file** here and I'll analyze it!",
        inline=False
    )

    embed.add_field(
        name="💬 Quick Commands",
        value=(
            "• `stats` - View your dashboard\n"
            "• `changes` - See who followed/unfollowed\n"
            "• `history` - View past uploads\n"
            "• Or use slash commands like `/upload`, `/stats`, etc."
        ),
        inline=False
    )

    embed.add_field(
        name="📱 How to Get Your CSV",
        value=(
            "1. Instagram → Settings → Accounts Center\n"
            "2. Your information and permissions → Download your information\n"
            "3. Select your account → Download or transfer information\n"
            "4. Some of your information → Followers and following\n"
            "5. Download to device (CSV format)\n"
            "6. Upload the CSV file here!"
        ),
        inline=False
    )

    await message.reply(embed=embed)


async def process_csv_upload(message: discord.Message, attachment: discord.Attachment):
    """Process a CSV file uploaded via message."""
    async with message.channel.typing():
        try:
            content = await attachment.read()
            records, metadata = parse_instagram_csv(content, attachment.filename)

            if not records:
                await message.reply("❌ Couldn't parse that CSV. Make sure it's an Instagram export!")
                return

            # Use detected type from filename, or fallback to simple detection
            file_info = parse_filename(attachment.filename)
            file_type = file_info['file_type']
            ig_username = file_info.get('ig_username') or metadata.get('ig_username')

            user_id = message.author.id
            guild_id = get_guild_id(message)

            # Get previous snapshot
            prev_snapshot = await get_latest_snapshot(user_id, guild_id, file_type)

            # Save new snapshot
            snapshot_id = await save_snapshot(
                user_id, guild_id, attachment.filename, records, file_type
            )

            # Analyze
            analysis = analyze_follow_status(records)

            # Build response
            title = f"✅ Got it! Processed your {file_type}"
            if ig_username:
                title = f"✅ @{ig_username}'s {file_type}"

            embed = discord.Embed(title=title, color=discord.Color.green())

            embed.add_field(name="📊 Total", value=f"**{metadata['total']}**", inline=True)
            embed.add_field(name="🤝 Mutual", value=f"**{metadata['following_back']}**", inline=True)
            embed.add_field(name="👀 Fans", value=f"**{metadata['not_following_back']}**", inline=True)

            # Comparison with previous
            if prev_snapshot:
                comparison = await compare_snapshots(prev_snapshot['id'], snapshot_id)
                net = comparison['net_change']

                if net > 0:
                    change_msg = f"📈 **+{net}** since last upload!"
                elif net < 0:
                    change_msg = f"📉 **{net}** since last upload"
                else:
                    change_msg = "No change since last upload"

                embed.add_field(name="📊 Change", value=change_msg, inline=False)

                if comparison['gained']:
                    names = ', '.join(f"@{r['username']}" for r in comparison['gained'][:3])
                    if len(comparison['gained']) > 3:
                        names += f" +{len(comparison['gained']) - 3} more"
                    embed.add_field(name="🆕 New", value=names, inline=True)

                if comparison['lost']:
                    names = ', '.join(f"@{r['username']}" for r in comparison['lost'][:3])
                    if len(comparison['lost']) > 3:
                        names += f" +{len(comparison['lost']) - 3} more"
                    embed.add_field(name="👋 Lost", value=names, inline=True)

            embed.set_footer(text="Type 'stats' for full dashboard or 'changes' for details")

            await message.reply(embed=embed)

        except Exception as e:
            await message.reply(f"❌ Error processing file: {str(e)}")


async def send_stats_from_message(message: discord.Message):
    """Send stats dashboard from a text message."""
    user_id = message.author.id
    guild_id = get_guild_id(message)

    async with message.channel.typing():
        snapshots = await get_all_snapshots_for_plotting(user_id, guild_id)

        if not snapshots:
            await message.reply("❌ No data yet! Drop a CSV file to get started.")
            return

        latest = await get_latest_snapshot(user_id, guild_id, "followers")
        if latest:
            records = await get_snapshot_records(latest['id'])
            analysis = analyze_follow_status(records)
        else:
            analysis = {'followers': [], 'mutual': [], 'fans': []}

        comparison = None
        follower_snapshots = [s for s in snapshots if s.get('snapshot_type') == 'followers']
        if len(follower_snapshots) >= 2:
            comparison = await compare_snapshots(
                follower_snapshots[-2]['id'],
                follower_snapshots[-1]['id']
            )

        dashboard_buf = create_summary_dashboard(follower_snapshots, analysis, comparison)
        file = discord.File(dashboard_buf, filename="dashboard.png")

        embed = discord.Embed(title="📊 Your Dashboard", color=discord.Color.blurple())
        embed.set_image(url="attachment://dashboard.png")

        await message.reply(embed=embed, file=file)


async def send_history_from_message(message: discord.Message):
    """Send upload history from a text message."""
    user_id = message.author.id
    guild_id = get_guild_id(message)

    snapshots = await get_snapshots(user_id, guild_id, limit=5)

    if not snapshots:
        await message.reply("❌ No uploads yet! Drop a CSV file to get started.")
        return

    embed = discord.Embed(title="📜 Your Upload History", color=discord.Color.blurple())

    for s in snapshots:
        from datetime import datetime
        uploaded_at = s['uploaded_at']
        if isinstance(uploaded_at, str):
            dt = datetime.fromisoformat(uploaded_at.replace('Z', '+00:00'))
            date_str = dt.strftime("%b %d, %Y")
        else:
            date_str = str(uploaded_at)

        embed.add_field(
            name=f"#{s['id']} - {date_str}",
            value=f"👥 {s['total_followers']} {s['snapshot_type']}",
            inline=True
        )

    await message.reply(embed=embed)


async def send_changes_from_message(message: discord.Message):
    """Send changes comparison from a text message."""
    user_id = message.author.id
    guild_id = get_guild_id(message)

    snapshots = await get_snapshots(user_id, guild_id, limit=2)

    if len(snapshots) < 2:
        await message.reply("❌ Need at least 2 uploads to compare. Upload another CSV!")
        return

    async with message.channel.typing():
        comparison = await compare_snapshots(snapshots[1]['id'], snapshots[0]['id'])
        chart_buf = create_change_bar_chart(comparison)
        file = discord.File(chart_buf, filename="changes.png")

        embed = discord.Embed(title="📊 Recent Changes", color=discord.Color.blurple())
        embed.add_field(
            name="Summary",
            value=f"**{comparison['old_total']}** → **{comparison['new_total']}** ({comparison['net_change']:+d})",
            inline=False
        )

        if comparison['gained']:
            names = '\n'.join(f"@{r['username']}" for r in comparison['gained'][:5])
            embed.add_field(name=f"🆕 New (+{comparison['gained_count']})", value=names, inline=True)

        if comparison['lost']:
            names = '\n'.join(f"@{r['username']}" for r in comparison['lost'][:5])
            embed.add_field(name=f"👋 Lost (-{comparison['lost_count']})", value=names, inline=True)

        embed.set_image(url="attachment://changes.png")
        await message.reply(embed=embed, file=file)


async def send_nonfollowers_from_message(message: discord.Message):
    """Send non-followers list from a text message."""
    user_id = message.author.id
    guild_id = get_guild_id(message)

    latest = await get_latest_snapshot(user_id, guild_id, "followers")

    if not latest:
        await message.reply("❌ No data yet! Drop a CSV file to get started.")
        return

    records = await get_snapshot_records(latest['id'])
    analysis = analyze_follow_status(records)
    fans = analysis['fans'][:10]

    if not fans:
        await message.reply("✨ Everyone who follows you is followed back!")
        return

    embed = discord.Embed(
        title="👀 Fans (You don't follow back)",
        description=f"Showing {len(fans)} of {len(analysis['fans'])} total",
        color=discord.Color.orange()
    )

    user_list = '\n'.join(f"• @{r['username']}" for r in fans)
    embed.add_field(name="Users", value=user_list, inline=False)

    await message.reply(embed=embed)


@bot.tree.command(name="upload", description="Upload your Instagram followers/following CSV file")
@app_commands.describe(
    file="Your Instagram CSV export file",
    file_type="Type of data: 'followers' or 'following'"
)
@app_commands.choices(file_type=[
    app_commands.Choice(name="Followers (people who follow you)", value="followers"),
    app_commands.Choice(name="Following (people you follow)", value="following")
])
async def upload_csv(
    interaction: discord.Interaction,
    file: discord.Attachment,
    file_type: str = "followers"
):
    """Upload and process Instagram CSV file."""
    await interaction.response.defer(thinking=True)

    if not file.filename.endswith('.csv'):
        await interaction.followup.send("❌ Please upload a CSV file.")
        return

    try:
        content = await file.read()
        records, metadata = parse_instagram_csv(content)

        if not records:
            await interaction.followup.send("❌ No valid records found in the CSV file.")
            return

        guild_id = get_guild_id(interaction)

        # Get previous snapshot for comparison
        prev_snapshot = await get_latest_snapshot(
            interaction.user.id,
            guild_id,
            file_type
        )

        # Save new snapshot
        snapshot_id = await save_snapshot(
            interaction.user.id,
            guild_id,
            file.filename,
            records,
            file_type
        )

        # Analyze relationships
        analysis = analyze_follow_status(records)

        # Build response embed
        embed = discord.Embed(
            title=f"📊 {file_type.title()} Upload Successful",
            color=discord.Color.green()
        )

        embed.add_field(
            name="📈 Total Records",
            value=f"**{metadata['total']}** accounts",
            inline=True
        )

        if file_type == "followers":
            embed.add_field(
                name="🤝 You Follow Back",
                value=f"**{metadata['following_back']}** accounts",
                inline=True
            )
            embed.add_field(
                name="👀 You Don't Follow Back",
                value=f"**{metadata['not_following_back']}** accounts",
                inline=True
            )

        embed.add_field(
            name="✅ Verified Accounts",
            value=f"**{metadata['verified']}** accounts",
            inline=True
        )

        # Add comparison if previous data exists
        if prev_snapshot:
            comparison = await compare_snapshots(prev_snapshot['id'], snapshot_id)

            change_text = []
            if comparison['gained_count'] > 0:
                change_text.append(f"📈 +{comparison['gained_count']} new")
            if comparison['lost_count'] > 0:
                change_text.append(f"📉 -{comparison['lost_count']} lost")

            net = comparison['net_change']
            net_emoji = "🟢" if net > 0 else "🔴" if net < 0 else "⚪"
            change_text.append(f"{net_emoji} Net: {net:+d}")

            embed.add_field(
                name="📊 Changes Since Last Upload",
                value="\n".join(change_text) if change_text else "No changes",
                inline=False
            )

            # Show some gained/lost usernames
            if comparison['gained']:
                gained_names = [r['username'] for r in comparison['gained'][:5]]
                more = len(comparison['gained']) - 5
                gained_text = ", ".join(f"@{n}" for n in gained_names)
                if more > 0:
                    gained_text += f" (+{more} more)"
                embed.add_field(
                    name="🆕 New Followers",
                    value=gained_text,
                    inline=False
                )

            if comparison['lost']:
                lost_names = [r['username'] for r in comparison['lost'][:5]]
                more = len(comparison['lost']) - 5
                lost_text = ", ".join(f"@{n}" for n in lost_names)
                if more > 0:
                    lost_text += f" (+{more} more)"
                embed.add_field(
                    name="👋 Lost Followers",
                    value=lost_text,
                    inline=False
                )

        embed.set_footer(text=f"Snapshot ID: {snapshot_id} | Use /stats for detailed analysis")

        await interaction.followup.send(embed=embed)

    except Exception as e:
        await interaction.followup.send(f"❌ Error processing file: {str(e)}")


@bot.tree.command(name="stats", description="View your follower statistics and trends")
@app_commands.dm_permission(True)
async def stats(interaction: discord.Interaction):
    """Show statistics and visualizations."""
    await interaction.response.defer(thinking=True)

    guild_id = get_guild_id(interaction)
    snapshots = await get_all_snapshots_for_plotting(
        interaction.user.id,
        guild_id
    )

    if not snapshots:
        await interaction.followup.send(
            "❌ No data found! Upload a CSV file first using `/upload`"
        )
        return

    # Get latest snapshot and its records
    latest = await get_latest_snapshot(
        interaction.user.id,
        guild_id,
        "followers"
    )

    if latest:
        records = await get_snapshot_records(latest['id'])
        analysis = analyze_follow_status(records)
    else:
        analysis = {'followers': [], 'mutual': [], 'fans': []}

    # Get comparison if we have multiple snapshots
    comparison = None
    follower_snapshots = [s for s in snapshots if s.get('snapshot_type') == 'followers']
    if len(follower_snapshots) >= 2:
        prev_id = follower_snapshots[-2]['id']
        curr_id = follower_snapshots[-1]['id']
        comparison = await compare_snapshots(prev_id, curr_id)

    # Create dashboard
    dashboard_buf = create_summary_dashboard(follower_snapshots, analysis, comparison)

    file = discord.File(dashboard_buf, filename="dashboard.png")

    embed = discord.Embed(
        title="📊 Your Instagram Follower Dashboard",
        color=discord.Color.blurple()
    )
    embed.set_image(url="attachment://dashboard.png")
    embed.set_footer(text=f"Based on {len(snapshots)} upload(s)")

    await interaction.followup.send(embed=embed, file=file)


@bot.tree.command(name="trend", description="View your follower count trend over time")
@app_commands.dm_permission(True)
async def trend(interaction: discord.Interaction):
    """Show follower trend plot."""
    await interaction.response.defer(thinking=True)

    guild_id = get_guild_id(interaction)
    snapshots = await get_all_snapshots_for_plotting(
        interaction.user.id,
        guild_id
    )

    follower_snapshots = [s for s in snapshots if s.get('snapshot_type', 'followers') == 'followers']

    if not follower_snapshots:
        await interaction.followup.send(
            "❌ No follower data found! Upload a CSV file first using `/upload`"
        )
        return

    plot_buf = create_follower_trend_plot(follower_snapshots)
    file = discord.File(plot_buf, filename="trend.png")

    embed = discord.Embed(
        title="📈 Follower Count Trend",
        description=f"Showing data from {len(follower_snapshots)} upload(s)",
        color=discord.Color.blurple()
    )
    embed.set_image(url="attachment://trend.png")

    await interaction.followup.send(embed=embed, file=file)


@bot.tree.command(name="growth", description="View your follower growth rate")
@app_commands.dm_permission(True)
async def growth(interaction: discord.Interaction):
    """Show growth rate between uploads."""
    await interaction.response.defer(thinking=True)

    guild_id = get_guild_id(interaction)
    snapshots = await get_all_snapshots_for_plotting(
        interaction.user.id,
        guild_id
    )

    follower_snapshots = [s for s in snapshots if s.get('snapshot_type', 'followers') == 'followers']

    if len(follower_snapshots) < 2:
        await interaction.followup.send(
            "❌ Need at least 2 uploads to show growth rate. Upload more data!"
        )
        return

    plot_buf = create_growth_rate_plot(follower_snapshots)
    file = discord.File(plot_buf, filename="growth.png")

    embed = discord.Embed(
        title="📈 Follower Growth Rate",
        description="Percentage change between each upload",
        color=discord.Color.green()
    )
    embed.set_image(url="attachment://growth.png")

    await interaction.followup.send(embed=embed, file=file)


@bot.tree.command(name="nonfollowers", description="See who doesn't follow you back")
@app_commands.describe(limit="Maximum number of results to show (default: 20)")
@app_commands.dm_permission(True)
async def non_followers(interaction: discord.Interaction, limit: int = 20):
    """Show people you follow who don't follow you back."""
    await interaction.response.defer(thinking=True)

    guild_id = get_guild_id(interaction)

    # Get followers data
    followers_snapshot = await get_latest_snapshot(
        interaction.user.id,
        guild_id,
        "followers"
    )

    if not followers_snapshot:
        await interaction.followup.send(
            "❌ No follower data found! Upload your followers CSV first using `/upload`"
        )
        return

    records = await get_snapshot_records(followers_snapshot['id'])

    # Filter those with "Followed by you" = YES in followers list
    # These are mutual follows - we want to find who you follow that doesn't follow back
    analysis = analyze_follow_status(records)

    # In followers list, people with "NO" are fans (they follow you, you don't follow them)
    # This command should show the opposite - you need following.csv for complete picture
    # For now, show fans (people you might want to follow back)

    fans = analysis['fans']  # People following you that you don't follow back

    if not fans:
        embed = discord.Embed(
            title="✨ Perfect!",
            description="Everyone who follows you is followed back by you!",
            color=discord.Color.green()
        )
        await interaction.followup.send(embed=embed)
        return

    # Paginate results
    fans = fans[:limit]

    embed = discord.Embed(
        title="👀 People Following You (Not Followed Back)",
        description=f"These {len(fans)} people follow you but you don't follow them back",
        color=discord.Color.orange()
    )

    # Create list of usernames
    user_list = []
    for i, record in enumerate(fans, 1):
        username = record['username']
        fullname = record['fullname']
        verified = "✅" if record['is_verified'] == 'YES' else ""
        user_list.append(f"{i}. @{username} {verified}")
        if fullname:
            user_list[-1] += f" ({fullname})"

    # Split into chunks if too long
    chunk_size = 10
    for i in range(0, len(user_list), chunk_size):
        chunk = user_list[i:i + chunk_size]
        field_name = f"Users {i + 1}-{min(i + chunk_size, len(user_list))}"
        embed.add_field(name=field_name, value="\n".join(chunk), inline=False)

    total_fans = len(analysis['fans'])
    if total_fans > limit:
        embed.set_footer(text=f"Showing {limit} of {total_fans} total. Use /nonfollowers limit:50 to see more")

    await interaction.followup.send(embed=embed)


@bot.tree.command(name="changes", description="View detailed changes from your last upload")
@app_commands.dm_permission(True)
async def changes(interaction: discord.Interaction):
    """Show detailed comparison with previous upload."""
    await interaction.response.defer(thinking=True)

    guild_id = get_guild_id(interaction)
    snapshots = await get_snapshots(interaction.user.id, guild_id, limit=2)

    if len(snapshots) < 2:
        await interaction.followup.send(
            "❌ Need at least 2 uploads to compare changes. Upload more data!"
        )
        return

    # snapshots are ordered DESC, so [0] is newest, [1] is previous
    comparison = await compare_snapshots(snapshots[1]['id'], snapshots[0]['id'])

    # Create change chart
    chart_buf = create_change_bar_chart(comparison)
    file = discord.File(chart_buf, filename="changes.png")

    embed = discord.Embed(
        title="📊 Follower Changes",
        color=discord.Color.blurple()
    )

    embed.add_field(
        name="📈 Summary",
        value=(
            f"Previous: **{comparison['old_total']}** followers\n"
            f"Current: **{comparison['new_total']}** followers\n"
            f"Net Change: **{comparison['net_change']:+d}**"
        ),
        inline=False
    )

    if comparison['gained']:
        gained_list = [f"@{r['username']}" for r in comparison['gained'][:10]]
        gained_text = "\n".join(gained_list)
        if len(comparison['gained']) > 10:
            gained_text += f"\n... and {len(comparison['gained']) - 10} more"
        embed.add_field(
            name=f"🆕 New Followers (+{comparison['gained_count']})",
            value=gained_text or "None",
            inline=True
        )

    if comparison['lost']:
        lost_list = [f"@{r['username']}" for r in comparison['lost'][:10]]
        lost_text = "\n".join(lost_list)
        if len(comparison['lost']) > 10:
            lost_text += f"\n... and {len(comparison['lost']) - 10} more"
        embed.add_field(
            name=f"👋 Unfollowed (-{comparison['lost_count']})",
            value=lost_text or "None",
            inline=True
        )

    embed.set_image(url="attachment://changes.png")

    await interaction.followup.send(embed=embed, file=file)


@bot.tree.command(name="history", description="View your upload history")
@app_commands.dm_permission(True)
async def history(interaction: discord.Interaction):
    """Show upload history."""
    await interaction.response.defer(thinking=True)

    guild_id = get_guild_id(interaction)
    snapshots = await get_snapshots(interaction.user.id, guild_id, limit=10)

    if not snapshots:
        await interaction.followup.send(
            "❌ No uploads found! Start by uploading a CSV file using `/upload`"
        )
        return

    embed = discord.Embed(
        title="📜 Your Upload History",
        color=discord.Color.blurple()
    )

    for snapshot in snapshots:
        uploaded_at = snapshot['uploaded_at']
        if isinstance(uploaded_at, str):
            # Format the date nicely
            from datetime import datetime
            dt = datetime.fromisoformat(uploaded_at.replace('Z', '+00:00'))
            date_str = dt.strftime("%b %d, %Y at %H:%M")
        else:
            date_str = str(uploaded_at)

        embed.add_field(
            name=f"#{snapshot['id']} - {snapshot['snapshot_type'].title()}",
            value=(
                f"📅 {date_str}\n"
                f"📁 {snapshot['filename']}\n"
                f"👥 {snapshot['total_followers']} records"
            ),
            inline=True
        )

    embed.set_footer(text="Use /changes to see differences between uploads")

    await interaction.followup.send(embed=embed)


@bot.tree.command(name="breakdown", description="See your follower relationship breakdown")
@app_commands.dm_permission(True)
async def breakdown(interaction: discord.Interaction):
    """Show pie chart of follow relationships."""
    await interaction.response.defer(thinking=True)

    guild_id = get_guild_id(interaction)
    latest = await get_latest_snapshot(
        interaction.user.id,
        guild_id,
        "followers"
    )

    if not latest:
        await interaction.followup.send(
            "❌ No data found! Upload a CSV file first using `/upload`"
        )
        return

    records = await get_snapshot_records(latest['id'])
    analysis = analyze_follow_status(records)

    mutual = len(analysis['mutual'])
    fans = len(analysis['fans'])

    chart_buf = create_comparison_pie_chart(mutual, fans, 0)
    file = discord.File(chart_buf, filename="breakdown.png")

    embed = discord.Embed(
        title="🥧 Follow Relationship Breakdown",
        color=discord.Color.blurple()
    )

    embed.add_field(name="🤝 Mutual", value=f"{mutual} accounts", inline=True)
    embed.add_field(name="👀 Fans", value=f"{fans} accounts", inline=True)
    embed.add_field(name="📊 Total", value=f"{mutual + fans} followers", inline=True)

    embed.set_image(url="attachment://breakdown.png")

    await interaction.followup.send(embed=embed, file=file)


@bot.tree.command(name="search", description="Search for a specific user in your data")
@app_commands.describe(username="Instagram username to search for")
@app_commands.dm_permission(True)
async def search_user(interaction: discord.Interaction, username: str):
    """Search for a user in follower data."""
    await interaction.response.defer(thinking=True)

    guild_id = get_guild_id(interaction)
    latest = await get_latest_snapshot(
        interaction.user.id,
        guild_id,
        "followers"
    )

    if not latest:
        await interaction.followup.send(
            "❌ No data found! Upload a CSV file first using `/upload`"
        )
        return

    records = await get_snapshot_records(latest['id'])

    # Search for username (case-insensitive partial match)
    search_lower = username.lower()
    matches = [
        r for r in records
        if search_lower in r['username'].lower() or search_lower in r['fullname'].lower()
    ]

    if not matches:
        await interaction.followup.send(f"❌ No user found matching `{username}`")
        return

    embed = discord.Embed(
        title=f"🔍 Search Results for '{username}'",
        description=f"Found {len(matches)} match(es)",
        color=discord.Color.blurple()
    )

    for match in matches[:10]:
        verified = "✅" if match['is_verified'] == 'YES' else ""
        follows_back = "✅ You follow back" if match['followed_by_you'] == 'YES' else "❌ You don't follow back"

        embed.add_field(
            name=f"@{match['username']} {verified}",
            value=(
                f"**Name:** {match['fullname'] or 'N/A'}\n"
                f"**Status:** {follows_back}\n"
                f"[View Profile]({match['profile_url']})"
            ),
            inline=True
        )

    if len(matches) > 10:
        embed.set_footer(text=f"Showing 10 of {len(matches)} results")

    await interaction.followup.send(embed=embed)


@bot.tree.command(name="demo", description="Load sample data to try out the bot")
@app_commands.dm_permission(True)
async def demo(interaction: discord.Interaction):
    """Load the sample CSV file to demonstrate bot features."""
    await interaction.response.defer(thinking=True)

    # Path to sample CSV
    sample_path = os.path.join(os.path.dirname(__file__), "IGFollow_rajj__singhh_287_followers.csv")

    if not os.path.exists(sample_path):
        await interaction.followup.send("❌ Sample file not found. Upload your own CSV!")
        return

    try:
        with open(sample_path, 'rb') as f:
            content = f.read()

        filename = "IGFollow_rajj__singhh_287_followers.csv"
        records, metadata = parse_instagram_csv(content, filename)

        if not records:
            await interaction.followup.send("❌ Couldn't parse sample file.")
            return

        file_info = parse_filename(filename)
        file_type = file_info['file_type']
        ig_username = file_info.get('ig_username')

        guild_id = get_guild_id(interaction)

        # Save snapshot
        snapshot_id = await save_snapshot(
            interaction.user.id,
            guild_id,
            filename,
            records,
            file_type
        )

        # Analyze
        analysis = analyze_follow_status(records)

        embed = discord.Embed(
            title=f"🎉 Demo loaded: @{ig_username}'s {file_type}",
            description="Sample data loaded! Try these commands:",
            color=discord.Color.green()
        )

        embed.add_field(name="📊 Total Followers", value=f"**{metadata['total']}**", inline=True)
        embed.add_field(name="🤝 Mutual", value=f"**{metadata['following_back']}**", inline=True)
        embed.add_field(name="👀 Fans", value=f"**{metadata['not_following_back']}**", inline=True)

        embed.add_field(
            name="🚀 Try These Commands",
            value=(
                "• `/stats` - See the full dashboard\n"
                "• `/breakdown` - Pie chart of relationships\n"
                "• `/nonfollowers` - List of fans\n"
                "• `/search <username>` - Find someone"
            ),
            inline=False
        )

        await interaction.followup.send(embed=embed)

    except Exception as e:
        await interaction.followup.send(f"❌ Error loading demo: {str(e)}")


# ============================================================================
# REQUESTED FOLLOWS TRACKING
# ============================================================================

@bot.tree.command(name="requested", description="View your pending follow requests list")
@app_commands.dm_permission(True)
async def requested_list(interaction: discord.Interaction):
    """Show the list of people you've requested to follow."""
    await interaction.response.defer(thinking=True)

    guild_id = get_guild_id(interaction)
    requested = await get_requested(interaction.user.id, guild_id, limit=50)
    total = await get_requested_count(interaction.user.id, guild_id)

    if not requested:
        embed = discord.Embed(
            title="📋 Pending Follow Requests",
            description="No pending requests tracked.\n\nUse `/requested_add` to add usernames.",
            color=discord.Color.light_gray()
        )
        await interaction.followup.send(embed=embed)
        return

    embed = discord.Embed(
        title="📋 Pending Follow Requests",
        description=f"You have **{total}** pending request(s)",
        color=discord.Color.orange()
    )

    # Format the list
    user_list = []
    for i, r in enumerate(requested[:50], 1):
        user_list.append(f"{i}. @{r['username']}")

    # Split into chunks
    chunk_size = 15
    for i in range(0, len(user_list), chunk_size):
        chunk = user_list[i:i + chunk_size]
        field_name = f"Users {i + 1}-{min(i + chunk_size, len(user_list))}" if len(user_list) > chunk_size else "Users"
        embed.add_field(name=field_name, value="\n".join(chunk), inline=True)

    embed.set_footer(text="Use /requested_add or /requested_remove to manage")

    await interaction.followup.send(embed=embed)


@bot.tree.command(name="requested_add", description="Add usernames to your pending requests list")
@app_commands.describe(usernames="Usernames separated by newlines, commas, or spaces")
@app_commands.dm_permission(True)
async def requested_add_cmd(interaction: discord.Interaction, usernames: str):
    """Add usernames to the requested list."""
    await interaction.response.defer(thinking=True)

    # Parse usernames - split by newlines, commas, or spaces
    import re
    username_list = re.split(r'[\n,\s]+', usernames)
    username_list = [u.strip().lstrip('@') for u in username_list if u.strip()]

    if not username_list:
        await interaction.followup.send("❌ No valid usernames provided.")
        return

    guild_id = get_guild_id(interaction)
    added, skipped = await add_requested(interaction.user.id, guild_id, username_list)

    embed = discord.Embed(
        title="📝 Added to Requested List",
        color=discord.Color.green()
    )

    embed.add_field(name="✅ Added", value=str(added), inline=True)
    if skipped > 0:
        embed.add_field(name="⏭️ Already existed", value=str(skipped), inline=True)

    total = await get_requested_count(interaction.user.id, guild_id)
    embed.add_field(name="📊 Total", value=str(total), inline=True)

    if added > 0:
        added_names = username_list[:10]
        embed.add_field(
            name="Added Users",
            value="\n".join(f"• @{u}" for u in added_names) + (f"\n... +{len(username_list) - 10} more" if len(username_list) > 10 else ""),
            inline=False
        )

    await interaction.followup.send(embed=embed)


@bot.tree.command(name="requested_remove", description="Remove usernames from your pending requests list")
@app_commands.describe(usernames="Usernames to remove (separated by newlines, commas, or spaces)")
@app_commands.dm_permission(True)
async def requested_remove_cmd(interaction: discord.Interaction, usernames: str):
    """Remove usernames from the requested list."""
    await interaction.response.defer(thinking=True)

    import re
    username_list = re.split(r'[\n,\s]+', usernames)
    username_list = [u.strip().lstrip('@') for u in username_list if u.strip()]

    if not username_list:
        await interaction.followup.send("❌ No valid usernames provided.")
        return

    guild_id = get_guild_id(interaction)
    removed = await remove_requested(interaction.user.id, guild_id, username_list)

    total = await get_requested_count(interaction.user.id, guild_id)

    embed = discord.Embed(
        title="🗑️ Removed from Requested List",
        color=discord.Color.red() if removed > 0 else discord.Color.light_gray()
    )

    embed.add_field(name="❌ Removed", value=str(removed), inline=True)
    embed.add_field(name="📊 Remaining", value=str(total), inline=True)

    await interaction.followup.send(embed=embed)


@bot.tree.command(name="requested_clear", description="Clear your entire pending requests list")
@app_commands.dm_permission(True)
async def requested_clear_cmd(interaction: discord.Interaction):
    """Clear all requested usernames."""
    guild_id = get_guild_id(interaction)
    count = await get_requested_count(interaction.user.id, guild_id)

    if count == 0:
        await interaction.response.send_message("📋 Your requested list is already empty.")
        return

    # Create confirmation button
    class ConfirmView(discord.ui.View):
        def __init__(self):
            super().__init__(timeout=30)
            self.confirmed = False

        @discord.ui.button(label=f"Yes, clear {count} entries", style=discord.ButtonStyle.danger)
        async def confirm(self, button_interaction: discord.Interaction, button: discord.ui.Button):
            if button_interaction.user.id != interaction.user.id:
                return

            self.confirmed = True
            cleared = await clear_requested(interaction.user.id, guild_id)

            embed = discord.Embed(
                title="🗑️ Requested List Cleared",
                description=f"Removed **{cleared}** entries.",
                color=discord.Color.red()
            )
            await button_interaction.response.edit_message(embed=embed, view=None)
            self.stop()

        @discord.ui.button(label="Cancel", style=discord.ButtonStyle.secondary)
        async def cancel(self, button_interaction: discord.Interaction, button: discord.ui.Button):
            if button_interaction.user.id != interaction.user.id:
                return

            embed = discord.Embed(
                title="❌ Cancelled",
                description="Your requested list was not cleared.",
                color=discord.Color.light_gray()
            )
            await button_interaction.response.edit_message(embed=embed, view=None)
            self.stop()

    view = ConfirmView()

    embed = discord.Embed(
        title="⚠️ Confirm Clear",
        description=f"Are you sure you want to clear **{count}** entries from your requested list?",
        color=discord.Color.orange()
    )

    await interaction.response.send_message(embed=embed, view=view)


@bot.tree.command(name="requested_check", description="Check which requested users have accepted your follow")
@app_commands.dm_permission(True)
async def requested_check_cmd(interaction: discord.Interaction):
    """Check if any requested users have accepted and now follow you back."""
    await interaction.response.defer(thinking=True)

    guild_id = get_guild_id(interaction)

    # Get latest followers snapshot
    latest = await get_latest_snapshot(interaction.user.id, guild_id, "followers")

    if not latest:
        await interaction.followup.send(
            "❌ No follower data found! Upload your followers CSV first using `/upload`"
        )
        return

    records = await get_snapshot_records(latest['id'])
    accepted = await check_requested_accepted(interaction.user.id, guild_id, records)

    if not accepted:
        embed = discord.Embed(
            title="📋 Requested Check",
            description="None of your requested users appear in your followers list yet.",
            color=discord.Color.light_gray()
        )
        embed.set_footer(text="Upload a new followers CSV to check again")
        await interaction.followup.send(embed=embed)
        return

    embed = discord.Embed(
        title="🎉 Accepted Follow Requests!",
        description=f"**{len(accepted)}** user(s) from your requested list now follow you!",
        color=discord.Color.green()
    )

    accepted_list = "\n".join(f"• @{u}" for u in accepted[:20])
    if len(accepted) > 20:
        accepted_list += f"\n... +{len(accepted) - 20} more"

    embed.add_field(name="Now Following You", value=accepted_list, inline=False)
    embed.set_footer(text="Use /requested_remove to remove them from your list")

    await interaction.followup.send(embed=embed)


@bot.tree.command(name="help", description="Show all available commands")
@app_commands.dm_permission(True)
async def help_command(interaction: discord.Interaction):
    """Show help information."""
    embed = discord.Embed(
        title="📚 Instagram Follower Tracker - Help",
        description="Track your Instagram followers and following with CSV uploads!",
        color=discord.Color.blurple()
    )

    commands_list = [
        ("📤 /upload", "Upload your Instagram CSV file"),
        ("📊 /stats", "View your dashboard"),
        ("📈 /trend", "Follower count trend"),
        ("📉 /growth", "Growth rate between uploads"),
        ("🔄 /changes", "See who followed/unfollowed"),
        ("👀 /nonfollowers", "Fans you don't follow back"),
        ("🥧 /breakdown", "Pie chart of relationships"),
        ("📜 /history", "Upload history"),
        ("🔍 /search", "Search for a username"),
        ("🎉 /demo", "Load sample data"),
    ]

    for cmd, desc in commands_list:
        embed.add_field(name=cmd, value=desc, inline=True)

    embed.add_field(
        name="📋 Requested Tracking",
        value=(
            "`/requested` - View pending requests\n"
            "`/requested_add` - Add usernames\n"
            "`/requested_remove` - Remove usernames\n"
            "`/requested_check` - Check who accepted\n"
            "`/requested_clear` - Clear all"
        ),
        inline=False
    )

    embed.add_field(
        name="💬 DM Commands",
        value=(
            "DM me directly!\n"
            "• Drop a CSV file\n"
            "• Type `stats`, `changes`, `history`"
        ),
        inline=False
    )

    embed.add_field(
        name="📝 How to Get Your Data",
        value=(
            "1. Go to Instagram → Settings → Your Activity\n"
            "2. Download your data as CSV\n"
            "3. Upload the followers/following CSV here!"
        ),
        inline=False
    )

    await interaction.response.send_message(embed=embed)


def main():
    """Run the bot."""
    if not TOKEN:
        print("Error: DISCORD_TOKEN not found in environment variables!")
        print("Create a .env file with: DISCORD_TOKEN=your_token_here")
        return

    bot.run(TOKEN)


if __name__ == '__main__':
    main()

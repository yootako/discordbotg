# This example requires the 'message_content' intent.

import discord
import discord.types
import config
from io import BytesIO
from typing import Dict, TypedDict

from ytdl_wrapper import YTDLSource
# from ytdl_wrapper import ffmpeg_options
from voicebox import VoiceBox

intents = discord.Intents.default()
intents.message_content = True

client = discord.Client(intents=intents)
tree = discord.app_commands.CommandTree(client)
voicevox = VoiceBox()


# 簡易DBとしてのDict
class server_setting(TypedDict):
    read_channel: str

class user_setting(TypedDict):
    speaker_id: int
    speaker_name: str
    speed: float


class DictDB(TypedDict):
    server_settings: Dict[int, server_setting]
    user_settings: Dict[int, user_setting]

dict_db: DictDB = {
    "server_settings": {},  # 空の辞書で初期化
    "user_settings": {}     # 空の辞書で初期化
}
# DictDB.server_settings[ctx.server.id]

# slash command
# /set_read_channel
@tree.command(
    name="set_read_channel",
    description="現在のテキストチャンネルを読み上げ対象に設定します。"
)
async def set_read_channel(ctx: discord.Interaction):
    if ctx.channel is None:
        await ctx.response.send_message("チャンネルが見つかりませんでした。")
        return
    elif ctx.channel.type != discord.ChannelType.text:
        await ctx.response.send_message("テキストチャンネルではありません。")
        return
    elif ctx.channel.guild is None:
        await ctx.response.send_message("サーバーが見つかりませんでした。")
        return
    elif ctx.channel.guild.id not in dict_db["server_settings"]:
        dict_db["server_settings"][ctx.channel.guild.id] = {"read_channel": ctx.channel.id}
    else:
        dict_db["server_settings"][ctx.channel.guild.id]["read_channel"] = ctx.channel.id
    await ctx.response.send_message(f"テキストチャンネル {ctx.channel.name} を読み上げ対象に設定しました。")
    


# /unset_read_channel
@tree.command(
    name="unset_read_channel",
    description="現在のテキストチャンネルを読み上げ対象から外します。"
)
async def unset_read_channel(ctx: discord.Interaction):
    if ctx.channel is None:
        await ctx.response.send_message("チャンネルが見つかりませんでした。")
        return
    elif ctx.channel.type != discord.ChannelType.text:
        await ctx.response.send_message("テキストチャンネルではありません。")
        return
    elif ctx.channel.guild is None:
        await ctx.response.send_message("サーバーが見つかりませんでした。")
        return
    elif ctx.channel.guild.id not in dict_db["server_settings"]:
        await ctx.response.send_message("読み上げ対象に設定されていません。")
        return
    elif dict_db["server_settings"][ctx.channel.guild.id]["read_channel"] != ctx.channel.id:
        await ctx.response.send_message("読み上げ対象に設定されていません。")
        return
    dict_db["server_settings"][ctx.channel.guild.id]["read_channel"] = None
    await ctx.response.send_message(f"テキストチャンネル {ctx.channel.name} を読み上げ対象から外しました。")


# /join
@tree.command(
    name="join",
    description="現在のボイスチャンネルに接続します。"
)
async def join(ctx: discord.Interaction):
    if ctx.user.voice is None:
        await ctx.response.send_message("あなたはボイスチャンネルに接続していません。")
        return
    
    elif ctx.guild.voice_client is not None:
        if ctx.guild.voice_client.channel == ctx.user.voice.channel:  
            await ctx.response.send_message("すでに接続しています。")
            return

    # ボイスチャンネルに接続する
    await ctx.user.voice.channel.connect()

    # 設定
    if ctx.channel.guild.id not in dict_db["server_settings"]:
        dict_db["server_settings"][ctx.channel.guild.id] = {"read_channel": ctx.channel.id}
    else:
        dict_db["server_settings"][ctx.channel.guild.id]["read_channel"] = ctx.channel.id

    # 成功メッセージを送信
    await ctx.response.send_message(f"接続しました。テキストチャンネル <#{ctx.channel.id}> を読み上げ対象に設定しました。")

# /leave
@tree.command(
    name="leave",
    description="ボイスチャンネルから切断します。"
)
async def leave(ctx: discord.Interaction):
    if ctx.guild.voice_client is None:
        await ctx.response.send_message("接続していません。")
        return

    # 切断する
    await ctx.guild.voice_client.disconnect()
    await ctx.response.send_message("切断しました。")


async def autocomplete_style(
    ctx: discord.Interaction,
    current: str,
) -> list[discord.app_commands.Choice[str]]:
    speaker_name = dict_db["user_settings"].get(ctx.user.id, {}).get("speaker_name", "ずんだもん") # デフォルト値がずんだもん
    style_list = voicevox.get_style_list(speaker_name)
    return [
        discord.app_commands.Choice(name=style["name"], value=style["name"])
            for style in style_list
    ]
    

# /set_voice <音声名>
@tree.command(
    name="set_voice",
    description="音声を設定します。"
)
@discord.app_commands.choices(
    speaker=voicevox.build_speaker_choices()[0:25]
)
async def set_voice(ctx: discord.Interaction, speaker: str):
    speaker_name = speaker
    speaker_id = voicevox.get_speaker_id(speaker_name)
    # ユーザー設定を更新
    if ctx.user.id in dict_db["user_settings"]:
        dict_db["user_settings"][ctx.user.id]["speaker_name"] = speaker_name
        dict_db["user_settings"][ctx.user.id]["speaker_id"] = speaker_id
    else:
        dict_db["user_settings"][ctx.user.id] = {"speaker_name": speaker_name, "speaker_id": speaker_id}

    # メッセージを送信
    await ctx.response.send_message(f"音声を {speaker_name}({voicevox.get_speaker_style_name(speaker_id)}) に設定しました。")

# /set_voice_style <声色>
@tree.command(
    name="set_voice_style",
    description="声色を設定します。"
)
@discord.app_commands.autocomplete(
    style=autocomplete_style
)
async def set_voice_style(ctx: discord.Interaction, style: str):
    speaker_name = dict_db["user_settings"].get(ctx.user.id, {}).get("speaker_name", "ずんだもん") # デフォルト値がずんだもん
    speaker_id = voicevox.get_speaker_id(speaker_name, style) or 3

    # ユーザー設定を更新
    if ctx.user.id in dict_db["user_settings"]:
        dict_db["user_settings"][ctx.user.id]["speaker_id"] = speaker_id
    else:
        dict_db["user_settings"][ctx.user.id] = {"speaker_id": speaker_id}

    # speaker_nameがなかった場合はずんだもんをデフォルト値とする
    if "speaker_name" not in dict_db["user_settings"][ctx.user.id]:
        dict_db["user_settings"][ctx.user.id]["speaker_name"] = "ずんだもん"
        
    # メッセージを送信
    await ctx.response.send_message(f"声色を {dict_db["user_settings"][ctx.user.id]["speaker_name"]}({voicevox.get_speaker_style_name(speaker_id)}) に設定しました。")

# /set_speed <速度>
@tree.command(
    name="set_speed",
    description="読み上げ速度を設定します。"
)
@discord.app_commands.describe(speed="読み上げ速度を設定します。デフォルト値は1.0です。")
async def set_speed(ctx: discord.Interaction, speed: discord.app_commands.Range[float, 0.1, 3.0]):

    # ユーザー設定を更新
    if ctx.user.id in dict_db["user_settings"]:
        dict_db["user_settings"][ctx.user.id]["speed"] = speed
    else:
        dict_db["user_settings"][ctx.user.id] = {"speed": speed}

    # メッセージを送信
    await ctx.response.send_message(f"読み上げ速度を {speed} に設定しました。")


@client.event
async def on_message(message):
    server = message.channel.guild
    author = message.author
    channel = message.channel

    # 自分のメッセージは無視
    if author == client.user:
        return

    # ボイスチャンネルに接続していない場合は無視
    if message.guild.voice_client is None:
        # await channel.send("ボイスチャンネルに接続していません。")
        return
    

    # テキストチャンネルが読み上げ対象でない場合は無視
    if server.id not in dict_db["server_settings"]:
        # await channel.send("設定ファイルがありません。")
        return
    
    if channel.id != dict_db["server_settings"][int(server.id)]["read_channel"]:
        # await channel.send("読上げ対象のチャンネルではありません。")
        return
    
    # ボイスチャンネルに接続している場合は、読み上げを行う
    voice_client = message.guild.voice_client

    # テキストを読み上げる
    wav_data = voicevox.get_voice(
        message.content, 
        speaker_id = dict_db["user_settings"].get(author.id, {}).get("speaker_id", 3),
        speak_speed = dict_db["user_settings"].get(author.id, {}).get("speed", 1.0)
    )
    await voice_client.play(discord.FFmpegPCMAudio(wav_data, **VoiceBox.ffmpeg_options))



# voicechannelから全員が切断した時にvoicebotを切断する
@client.event
async def on_voice_state_update(member, before, after):
    if member.guild.voice_client is not None:
        if before.channel == member.guild.voice_client.channel and after.channel is not before.channel:
            if member.guild.voice_client is not None and len(member.guild.voice_client.channel.members) == 1:
                await member.guild.voice_client.disconnect()
                await member.guild.text_channels[0].send("全員が退出したため、切断しました。")

@client.event
async def on_ready():
    print(f'We have logged in as {client.user}')
    await tree.sync()

client.run(config.DISCORD_TOKEN)

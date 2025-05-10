# This example requires the 'message_content' intent.

import discord
import discord.types
import config
from io import BytesIO
from typing import Dict, TypedDict, List, Optional, Tuple, Deque
import re 
import asyncio
from collections import deque
from ytdl_wrapper import YTDLSource
# from ytdl_wrapper import ffmpeg_options
from voicebox import VoiceBox

intents = discord.Intents.default()
intents.message_content = True

client = discord.Client(intents=intents)
tree = discord.app_commands.CommandTree(client)
voicevox = VoiceBox()

# 各サーバーごとのメッセージキューを管理するためのDict
voice_queues: Dict[int, Deque[Tuple[str, str, float]]] = {}
# キュー処理中かどうかを示すフラグ
processing_queues: Dict[int, bool] = {}


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
    await ctx.response.send_message(f"声色を {dict_db['user_settings'][ctx.user.id]['speaker_name']}({voicevox.get_speaker_style_name(speaker_id)}) に設定しました。")
    

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


# 音声の再生のキュー処理関数
async def process_voice_queue(guild_id: int):
    """
    音声キューを処理する関数
    guild_id: サーバーID
    """
    # 既に処理中の場合は何もしない
    if processing_queues.get(guild_id, False):
        return
    
    processing_queues[guild_id] = True
    
    guild = client.get_guild(guild_id)
    if not guild or not guild.voice_client:
        # ボイスクライアントがない場合はキューをクリアする
        if guild_id in voice_queues:
            voice_queues[guild_id].clear()
        processing_queues[guild_id] = False
        return
    
    voice_client = guild.voice_client
    
    try:
        while guild_id in voice_queues and voice_queues[guild_id]:
            # ボイスクライアントが接続されていないまたは再生中なら待機
            if not voice_client.is_connected():
                break
            
            if voice_client.is_playing():
                # 再生中なら0.5秒待機して再チェック
                await asyncio.sleep(0.5)
                continue
            
            # キューから次のメッセージを取得
            message_content, speaker_id, speak_speed = voice_queues[guild_id].popleft()
            
            # 音声データを取得して再生
            wav_data = voicevox.get_voice(message_content, speaker_id=speaker_id, speak_speed=speak_speed)
            
            # 再生
            voice_client.play(discord.FFmpegPCMAudio(wav_data, **VoiceBox.ffmpeg_options))
            
            # 再生が完了するまで待機する代わりに次のループへ
            # 再生状態は次のループで確認する
    except Exception as e:
        print(f"キュー処理中にエラーが発生しました: {e}")
    finally:
        processing_queues[guild_id] = False

@client.event
async def on_message(message):
    server = message.channel.guild
    author = message.author
    channel = message.channel

    try:
        # 自分のメッセージは無視
        if author == client.user:
            return

        # ボイスチャンネルに接続していない場合は無視
        if message.guild.voice_client is None:
            return

        # テキストチャンネルが読み上げ対象でない場合は無視
        if server.id not in dict_db["server_settings"]:
            return

        if channel.id != dict_db["server_settings"][int(server.id)]["read_channel"]:
            return

        # メッセージを整形
        content = message.content
        # 改行をスペースに変換
        content = content.replace("\n", " ")

        # 記号を除去
        content = re.sub(r'[^\w\s]', '', content)

        # "゛"を除去
        content = content.replace("゛", "")
        # "゜"を除去
        content = content.replace("゜", "")

        #おちんほを含む場合、メッセージを置き換える
        if "おちんほ" in content:
            content = content.replace("おちんほ", "おちんぽ")

        # URLを含む場合、URL部分を「URL省略」に変換
        content = re.sub(r'https?://[\w/:%#\$&\?\(\)~\.=\+\-]+', 'URL省略', content)

        # 100文字以上の場合、100文字までに切り詰める
        if len(content) > 100:
            content = content[:100] + "以下省略"

        # 話者IDと速度を取得
        speaker_id = dict_db["user_settings"].get(author.id, {}).get("speaker_id", 3)
        speak_speed = dict_db["user_settings"].get(author.id, {}).get("speed", 1.0)
        
        # キューに追加
        guild_id = message.guild.id
        if guild_id not in voice_queues:
            voice_queues[guild_id] = deque()
        
        voice_queues[guild_id].append((content, speaker_id, speak_speed))
        
        # キュー処理を開始
        asyncio.create_task(process_voice_queue(guild_id))

    except Exception as e:
        print(e)
        await channel.send("エラーが発生しました。")


# voicechannelから全員が切断した時にvoicebotを切断する
@client.event
async def on_voice_state_update(member, before, after):
    if member.guild.voice_client is not None:
        if before.channel == member.guild.voice_client.channel and after.channel is not before.channel:
            if member.guild.voice_client is not None and len(member.guild.voice_client.channel.members) == 1:
                await member.guild.voice_client.disconnect()
                
                # 読み上げ対象のチャンネルIDを取得
                read_channel_id = dict_db["server_settings"].get(member.guild.id, {}).get("read_channel")
                
                # 読み上げ対象のチャンネルが設定されている場合はそのチャンネルに、
                # 設定されていない場合は最初のテキストチャンネルにメッセージを送信
                if read_channel_id:
                    read_channel = member.guild.get_channel(read_channel_id)
                    if read_channel:
                        await read_channel.send("全員が退出したため、切断しました。")
                        return
                
                # 読み上げ対象が見つからない場合は最初のテキストチャンネルに送信（フォールバック）
                await member.guild.text_channels[0].send("全員が退出したため、切断しました。")

@client.event
async def on_ready():
    print(f'We have logged in as {client.user}')
    await tree.sync()

client.run(config.DISCORD_TOKEN)

# This example requires the 'message_content' intent.

import discord
import config
from io import BytesIO

intents = discord.Intents.default()
intents.message_content = True

client = discord.Client(intents=intents)

from ytdl_wrapper import YTDLSource
# from ytdl_wrapper import ffmpeg_options
from voicebox import VoiceBox

@client.event
async def on_ready():
    print(f'We have logged in as {client.user}')

@client.event
async def on_message(message):
    if message.author == client.user:
        return

    if message.content.startswith('$hello'):
        await message.channel.send('Hello!')

    if message.content == "!join":
        if message.author.voice is None:
            await message.channel.send("あなたはボイスチャンネルに接続していません。")
            return
        # ボイスチャンネルに接続する
        await message.author.voice.channel.connect()

        await message.channel.send("接続しました。")

    elif message.content == "!leave":
        if message.guild.voice_client is None:
            await message.channel.send("接続していません。")
            return

        # 切断する
        await message.guild.voice_client.disconnect()

        await message.channel.send("切断しました。")
    elif message.content.startswith("!speak "):
        if message.guild.voice_client is None:
            await message.channel.send("接続していません。")
            return
        # 再生中の場合は再生しない
        if message.guild.voice_client.is_playing():
            await message.channel.send("再生中です。")
            return

        text = message.content[7:]
        # youtubeから音楽をダウンロードする
        voice_box = VoiceBox()
        wav_data = voice_box.get_voice(text)

        # 再生する
        await message.guild.voice_client.play(discord.FFmpegPCMAudio(wav_data, **VoiceBox.ffmpeg_options))

        await message.channel.send('{} を再生します。'.format(player.title))

    elif message.content.startswith("!play "):
        if message.guild.voice_client is None:
            await message.channel.send("接続していません。")
            return
        # 再生中の場合は再生しない
        if message.guild.voice_client.is_playing():
            await message.channel.send("再生中です。")
            return

        url = message.content[6:]
        # youtubeから音楽をダウンロードする
        player = await YTDLSource.from_url(url, loop=client.loop)

        # 再生する
        await message.guild.voice_client.play(player)

        await message.channel.send('{} を再生します。'.format(player.title))

    elif message.content == "!stop":
        if message.guild.voice_client is None:
            await message.channel.send("接続していません。")
            return

        # 再生中ではない場合は実行しない
        if not message.guild.voice_client.is_playing():
            await message.channel.send("再生していません。")
            return

        message.guild.voice_client.stop()

        await message.channel.send("ストップしました。")


client.run(config.DISCORD_TOKEN)

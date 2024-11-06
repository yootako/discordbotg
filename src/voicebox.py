import requests
import discord
import config

class VoiceBox:
    ffmpeg_options = {
        'before_options': '-ar 24000 -ac 1 -f s16le',
        'pipe': True,
    }
    # 文字列を受け取り、voice boxのhttpリクエストに投げてwavを返す
    def get_voice(self, text: str):
        query_url = "http://voicebox:50021/audio_query?speaker=1"
        response = requests.post(query_url, params={"text": text})
        query_json = response.json()
        url = "http://voicebox:50021/synthesis?speaker=1"

        response = requests.post(url, json=query_json, stream=True)

        return response.raw

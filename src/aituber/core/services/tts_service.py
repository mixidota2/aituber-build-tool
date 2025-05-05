from voicevox_core.blocking import Onnxruntime, OpenJtalk, Synthesizer, VoiceModelFile
from voicevox_core.asyncio import (
    Onnxruntime as AsyncOnnxruntime,
    OpenJtalk as AsyncOpenJtalk,
    Synthesizer as AsyncSynthesizer,
    VoiceModelFile as AsyncVoiceModelFile,
)
from aituber.core.models.character import Character
import os


class TTSSyncService:
    def __init__(
        self, model_dir: str = "voicevox_core/models/vvms", use_gpu: bool = False
    ):
        # ONNX Runtimeのパス
        onnxruntime_path = (
            "voicevox_core/onnxruntime/lib/" + Onnxruntime.LIB_VERSIONED_FILENAME
        )
        self.onnx = Onnxruntime.load_once(filename=onnxruntime_path)
        self.open_jtalk = OpenJtalk("voicevox_core/dict/open_jtalk_dic_utf_8-1.11")
        self.synthesizer = Synthesizer(
            self.onnx, self.open_jtalk, acceleration_mode="GPU" if use_gpu else "CPU"
        )
        # モデルをすべてロード
        for file in os.listdir(model_dir):
            if file.endswith(".vvm"):
                with VoiceModelFile.open(os.path.join(model_dir, file)) as model:
                    self.synthesizer.load_voice_model(model)

    def synthesize(self, text: str, character: Character) -> bytes:
        if not character.voicevox or character.voicevox.style_id is None:
            raise ValueError("キャラクターにvoicevoxのstyle_idが設定されていません")
        style_id = character.voicevox.style_id
        # ttsで直接合成
        wav = self.synthesizer.tts(text, style_id)
        return wav


class TTSAsyncService:
    def __init__(
        self, model_dir: str = "voicevox_core/models/vvms", use_gpu: bool = False
    ):
        self.model_dir = model_dir
        self.use_gpu = use_gpu
        self.synthesizer = None
        self.onnx = None
        self.open_jtalk = None

    async def initialize(self):
        self.onnx = await AsyncOnnxruntime.load_once()
        self.open_jtalk = await AsyncOpenJtalk.new(
            "voicevox_core/dict/open_jtalk_dic_utf_8-1.11"
        )
        mode = "GPU" if self.use_gpu else "CPU"
        self.synthesizer = AsyncSynthesizer(
            self.onnx, self.open_jtalk, acceleration_mode=mode
        )
        # ディレクトリ内の全モデルをロード
        import asyncio

        tasks = []
        for file in os.listdir(self.model_dir):
            if file.endswith(".vvm"):
                tasks.append(
                    self.synthesizer.load_voice_model(
                        AsyncVoiceModelFile(os.path.join(self.model_dir, file))
                    )
                )
        await asyncio.gather(*tasks)

    async def synthesize(self, text: str, character: Character) -> bytes:
        if not self.synthesizer:
            raise RuntimeError(
                "Synthesizerが初期化されていません。initialize()を先に呼んでください。"
            )
        if not character.voicevox or character.voicevox.style_id is None:
            raise ValueError("キャラクターにvoicevoxのstyle_idが設定されていません")
        style_id = character.voicevox.style_id
        audio_query = await self.synthesizer.create_audio_query(text, style_id)
        wav = await self.synthesizer.synthesis(audio_query, style_id)
        return wav

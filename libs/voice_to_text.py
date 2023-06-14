
from typing import Union

import ffmpeg
import numpy as np
import whisper
from whisper.audio import SAMPLE_RATE


def load_audio(file: Union[str, bytes], sample_rate: int = SAMPLE_RATE):
    """
    Open an audio file and read as mono waveform, resampling as necessary

    Parameters
    ----------
    file: (str, bytes)
        The audio file to open or bytes of audio file

    sr: int
        The sample rate to resample the audio if necessary

    Returns
    -------
    A NumPy array containing the audio waveform, in float32 dtype.
    """
    if isinstance(file, bytes):
        inp = file
        file = 'pipe:'
    else:
        inp = None
    try:
        # This launches a subprocess to decode audio while down-mixing and resampling as necessary.
        # Requires the ffmpeg CLI and `ffmpeg-python` package to be installed.
        out, _ = (
            ffmpeg.input(file, threads=0)
            .output("-", format="s16le", acodec="pcm_s16le", ac=1, ar=sample_rate)
            .run(cmd="ffmpeg", capture_stdout=True, capture_stderr=True, input=inp)
        )
    except ffmpeg.Error as err:
        raise RuntimeError(f"Failed to load audio: {err.stderr.decode()}") from err

    return np.frombuffer(out, np.int16).flatten().astype(np.float32) / 32768.0

def cpu_get_transcript(model: whisper.Whisper, file: Union[str, bytes]) -> str:
    """
    Get the transcript of a voice message

    Parameters
    ----------
    model: whisper.Whisper
        The model to use to transcribe the audio

    file: (str, bytes)
        The audio file to open or bytes of audio file

    Returns
    -------
    The transcript of the audio file
    """
    audio = load_audio(file)
    result = model.transcribe(audio, fp16=False)
    text = ""
    for segment in result["segments"]:
        if segment["no_speech_prob"] < 0.9:
            text += segment["text"]
        else:
            text += "\n"
    return text.strip()

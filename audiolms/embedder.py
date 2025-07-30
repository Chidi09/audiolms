# audiolms/embedder.py
import logging

logger = logging.getLogger(__name__)

def generate_embed_code(audio_url: str, title: str = "Audio Playback") -> str:
    """
    Generates an HTML <audio> tag for embedding an audio file.
    """
    if not audio_url:
        logger.warning("Attempted to generate embed code with empty audio_url.")
        return "<p>Error: Audio URL not provided.</p>"

    # Simple HTML5 audio tag
    embed_html = f"""
    <audio controls>
        <source src="{audio_url}" type="audio/mpeg">
        Your browser does not support the audio element.
    </audio>
    """
    logger.info(f"Generated embed code for {audio_url}")
    return embed_html

def generate_download_link(audio_url: str, filename: str = "audio.wav") -> str:
    """
    Generates an HTML link for downloading an audio file.
    """
    if not audio_url:
        logger.warning("Attempted to generate download link with empty audio_url.")
        return "<p>Error: Audio URL not provided.</p>"

    download_link_html = f"""
    <a href="{audio_url}" download="{filename}">Download {filename}</a>
    """
    logger.info(f"Generated download link for {audio_url}")
    return download_link_html

"""
EdgeTTS integration for generating speech with Microsoft Edge TTS voices.
Uses the edge-tts library to synthesize text to speech.
"""
import asyncio
import io
import os
import tempfile
from typing import Optional

try:
    import edge_tts
except ImportError:
    edge_tts = None

# S3 imports for uploading audio files
try:
    import boto3
    from botocore.exceptions import ClientError
except ImportError:
    boto3 = None


class EdgeTTSClient:
    """EdgeTTS Text to Speech Client using Microsoft Edge TTS service.
    
    Args:
        voice (str): The voice name to use (e.g., 'en-CA-LiamNeural')
        s3_bucket (str, optional): S3 bucket name for storing audio files
        s3_region (str, optional): AWS region for S3 bucket (default: 'us-east-1')
    """

    def __init__(
        self,
        voice: str = "en-CA-LiamNeural",
        s3_bucket: Optional[str] = None,
        s3_region: str = "us-east-1",
    ) -> None:
        if edge_tts is None:
            raise ImportError(
                "edge-tts is not installed. Please add it to requirements.txt"
            )
        
        self.voice = voice
        self.s3_bucket = s3_bucket
        self.s3_region = s3_region
        self.s3_client = None
        
        if s3_bucket and boto3:
            self.s3_client = boto3.client("s3", region_name=s3_region)

    def synthesize(self, text: str) -> str:
        """
        Synthesizes text to speech using EdgeTTS and returns a URL.
        
        Args:
            text (str): The text to synthesize
            
        Returns:
            str: URL to the audio file (S3 URL if S3 is configured, otherwise temporary)
        """
        if not text or not text.strip():
            raise ValueError("Text cannot be empty")
        
        # Run the async synthesis
        # Handle event loop for Lambda environment
        try:
            loop = asyncio.get_event_loop()
            if loop.is_closed():
                loop = asyncio.new_event_loop()
                asyncio.set_event_loop(loop)
        except RuntimeError:
            loop = asyncio.new_event_loop()
            asyncio.set_event_loop(loop)
        
        try:
            audio_data = loop.run_until_complete(self._synthesize_async(text))
        finally:
            # Don't close the loop in Lambda - it might be reused
            pass
        
        # Upload to S3 if configured, otherwise use a temporary solution
        if self.s3_client and self.s3_bucket:
            return self._upload_to_s3(audio_data, text)
        else:
            # Fallback: return a data URI (may have size limitations)
            # For production, S3 is recommended
            return self._create_data_uri(audio_data)

    async def _synthesize_async(self, text: str) -> bytes:
        """Async method to synthesize text using EdgeTTS."""
        communicate = edge_tts.Communicate(text, self.voice)
        audio_data = b""
        async for chunk in communicate.stream():
            if chunk["type"] == "audio":
                audio_data += chunk["data"]
        return audio_data

    def _upload_to_s3(self, audio_data: bytes, text: str) -> str:
        """
        Uploads audio data to S3 and returns the public URL.
        
        Args:
            audio_data (bytes): The audio file data
            text (str): The original text (used for filename)
            
        Returns:
            str: Public HTTPS URL to the audio file
        """
        import hashlib
        import time
        
        # Create a unique filename
        text_hash = hashlib.md5(text.encode()).hexdigest()[:8]
        timestamp = int(time.time())
        filename = f"tts/{timestamp}_{text_hash}.mp3"
        
        try:
            # Upload to S3
            self.s3_client.put_object(
                Bucket=self.s3_bucket,
                Key=filename,
                Body=audio_data,
                ContentType="audio/mpeg",
                ACL="public-read",  # Make the file publicly accessible
            )
            
            # Return the public URL
            url = f"https://{self.s3_bucket}.s3.{self.s3_region}.amazonaws.com/{filename}"
            return url
        except ClientError as e:
            raise Exception(f"Failed to upload audio to S3: {str(e)}")

    def _create_data_uri(self, audio_data: bytes) -> str:
        """
        Creates a data URI from audio data.
        Note: This has size limitations and may not work for long texts.
        For production use, configure S3.
        
        Args:
            audio_data (bytes): The audio file data
            
        Returns:
            str: Data URI (base64 encoded)
        """
        import base64
        
        # Check size limit (Alexa has limitations on data URIs)
        if len(audio_data) > 100000:  # ~100KB limit
            raise Exception(
                "Audio file too large for data URI. Please configure S3 bucket."
            )
        
        audio_base64 = base64.b64encode(audio_data).decode("utf-8")
        return f"data:audio/mpeg;base64,{audio_base64}"


class EdgeTTSError(Exception):
    """EdgeTTS error wrapper"""
    pass


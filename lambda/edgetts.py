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
        
        # Verify edge_tts is importable
        try:
            import edge_tts as et
            self._edge_tts_module = et
        except ImportError as e:
            raise ImportError(f"Failed to import edge_tts: {str(e)}")

    def synthesize(self, text: str) -> str:
        """
        Synthesizes text to speech using EdgeTTS and returns a URL.
        
        Args:
            text (str): The text to synthesize
            
        Returns:
            str: URL to the audio file (S3 URL if S3 is configured, otherwise temporary)
        """
        import time
        
        if not text or not text.strip():
            raise ValueError("Text cannot be empty")
        
        # Run the async synthesis with timeout
        # Handle event loop for Lambda environment
        try:
            # Try to get the existing event loop
            loop = asyncio.get_event_loop()
            if loop.is_closed():
                raise RuntimeError("Loop is closed")
        except RuntimeError:
            # No event loop exists, create a new one
            loop = asyncio.new_event_loop()
            asyncio.set_event_loop(loop)
        
        try:
            # Run the async function with a timeout (15 seconds for Lambda - EdgeTTS can be slow)
            start_time = time.time()
            import logging
            logging.info(f"Starting async synthesis with timeout of 15 seconds...")
            
            audio_data = loop.run_until_complete(
                asyncio.wait_for(self._synthesize_async(text), timeout=15.0)
            )
            elapsed = time.time() - start_time
            
            # Check if we got audio data
            if not audio_data or len(audio_data) == 0:
                raise Exception("No audio was received. Please verify that your parameters are correct.")
            
            # Log success
            logging.info(f"EdgeTTS synthesis completed in {elapsed:.2f}s, audio size: {len(audio_data)} bytes")
            
        except asyncio.TimeoutError:
            import logging
            logging.error("EdgeTTS synthesis timed out after 15 seconds")
            raise Exception("EdgeTTS synthesis timed out after 15 seconds. This might indicate a network issue or the service is slow.")
        except Exception as e:
            # Re-raise with more context
            import logging
            logging.error(f"EdgeTTS synthesis failed in synthesize() method: {str(e)}", exc_info=True)
            raise Exception(f"EdgeTTS synthesis failed: {str(e)}")
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
        """Async method to synthesize text using EdgeTTS.
        Based on working implementation that uses communicate.save() method.
        """
        import logging
        import tempfile
        import os
        
        temp_file_path = None
        try:
            logging.info(f"Starting EdgeTTS synthesis with voice: {self.voice}, text length: {len(text)}")
            
            # Use the exact same pattern as the working code:
            # communicate = edge_tts.Communicate(text, voice)
            # await communicate.save(file_path)
            communicate = self._edge_tts_module.Communicate(text, self.voice)
            
            # Use a temporary file (Lambda /tmp directory) to save the audio
            # This matches the working pattern of saving to a file path
            try:
                # Create a temporary file in /tmp (Lambda's writable directory)
                temp_file = tempfile.NamedTemporaryFile(delete=False, suffix='.mp3', dir='/tmp')
                temp_file_path = temp_file.name
                temp_file.close()  # Close so edge_tts can write to it
                
                logging.info(f"Created temp file: {temp_file_path}, exists: {os.path.exists(temp_file_path)}")
                
                # Use save() method exactly like the working code
                logging.info("Calling communicate.save()...")
                try:
                    await communicate.save(temp_file_path)
                    logging.info("communicate.save() completed")
                except Exception as save_error:
                    logging.error(f"Error during communicate.save(): {str(save_error)}", exc_info=True)
                    raise Exception(f"Failed to save audio file: {str(save_error)}")
                
                # Check if file was created and has content
                if not os.path.exists(temp_file_path):
                    raise Exception(f"Temp file was not created at {temp_file_path}")
                
                file_size = os.path.getsize(temp_file_path)
                logging.info(f"File exists, size: {file_size} bytes")
                
                if file_size == 0:
                    raise Exception("File was created but is empty (0 bytes)")
                
                # Read the file back into bytes
                with open(temp_file_path, 'rb') as f:
                    audio_data = f.read()
                
                logging.info(f"Successfully read {len(audio_data)} bytes from file")
                
                if not audio_data or len(audio_data) == 0:
                    raise Exception(f"File exists but read returned empty data. File size: {file_size} bytes")
                
                return audio_data
                
            except Exception as file_error:
                logging.error(f"File operation error: {str(file_error)}", exc_info=True)
                raise
            finally:
                # Clean up temporary file
                if temp_file_path and os.path.exists(temp_file_path):
                    try:
                        os.unlink(temp_file_path)
                        logging.info("Cleaned up temporary file")
                    except Exception as cleanup_error:
                        logging.warning(f"Could not delete temp file: {str(cleanup_error)}")
            
        except Exception as e:
            # Provide more helpful error message with full traceback
            import traceback
            error_trace = traceback.format_exc()
            logging.error(f"EdgeTTS synthesis error: {str(e)}\nTraceback: {error_trace}")
            raise Exception(f"EdgeTTS synthesis error: {str(e)}. Voice: {self.voice}, Text length: {len(text)}")

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


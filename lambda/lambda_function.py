import logging
import os

from ask_sdk_core.skill_builder import SkillBuilder
from ask_sdk_core.utils import is_request_type, is_intent_name
from ask_sdk_core.handler_input import HandlerInput

from ask_sdk_model.ui import SimpleCard
from ask_sdk_model import Response

from edgetts import EdgeTTSClient

###############################################################################
# Customize your skill here!
###############################################################################
# EdgeTTS voice to use - Liam Neural (Canadian English)
# You can change this to any EdgeTTS voice name
# List of voices: https://github.com/rany2/edge-tts/blob/master/src/edge_tts/voices.json
VOICE = "en-CA-LiamNeural"

# GitHub Configuration for audio file
# Upload speech.mp3 to your GitHub repo and use the raw URL
# Format: https://raw.githubusercontent.com/USERNAME/REPO/BRANCH/PATH/speech.mp3
GITHUB_AUDIO_URL = os.environ.get(
    "GITHUB_AUDIO_URL", 
    "https://raw.githubusercontent.com/Jarvis4everyone/alexa/main/speech.mp3"
)  # GitHub raw URL to your speech.mp3 file

# S3 Configuration (optional - only needed if not using GitHub)
S3_BUCKET = os.environ.get("S3_BUCKET", None)
S3_REGION = os.environ.get("S3_REGION", "us-east-1")

# text to read as a response
RESPONSE = "You're good enough, you're smart enough, and dog gone it, people like you!"

# the name of your skill (shown on cards)
SKILL_NAME = "Custom TTS Voice"

###############################################################################
# This is basically the only feature we've added.
# All it does is insert EdgeTTS audio URLs in an SSML tag.
###############################################################################
# Initialize TTS client lazily to handle import errors gracefully
tts = None

def get_tts_client():
    """Get or create the EdgeTTS client."""
    global tts
    if tts is None:
        try:
            tts = EdgeTTSClient(voice=VOICE, s3_bucket=S3_BUCKET, s3_region=S3_REGION)
        except Exception as e:
            logging.error(f"Failed to initialize EdgeTTS client: {str(e)}", exc_info=True)
            raise
    return tts


def synthesize(text, show_error=False):
    """
    Creates an SSML `<audio>` element containing a URL to
    a synthesized version of the text using EdgeTTS or pre-generated audio.
    
    Args:
        text: Text to synthesize
        show_error: If True, include error details in response (for debugging)
    """
    import base64
    
    # First, try to use GitHub raw URL (simplest solution!)
    if GITHUB_AUDIO_URL:
        try:
            logging.info(f"Using GitHub audio URL: {GITHUB_AUDIO_URL}")
            return {
                "audio": f'<audio src="{GITHUB_AUDIO_URL}"/>',
                "text": text
            }
        except Exception as github_error:
            logging.warning(f"Could not use GitHub URL: {str(github_error)}")
    
    # Fallback: Try to read from Lambda package and upload to S3
    try:
        logging.info("Trying to use pre-generated speech.mp3 file from Lambda package...")
        
        # Try to read the file from Lambda package directory
        audio_file_paths = [
            '/var/task/speech.mp3',  # Lambda package root
            '/var/task/lambda/speech.mp3',  # If in lambda subdirectory
            os.path.join(os.path.dirname(__file__), 'speech.mp3'),  # Same directory as this file
            'speech.mp3',  # Current directory
        ]
        
        audio_data = None
        for path in audio_file_paths:
            try:
                if os.path.exists(path):
                    with open(path, 'rb') as f:
                        audio_data = f.read()
                    logging.info(f"Found pre-generated audio file at {path}, size: {len(audio_data)} bytes")
                    break
            except Exception as e:
                logging.debug(f"Could not read {path}: {str(e)}")
                continue
        
        if audio_data and len(audio_data) > 0:
            # We have the audio file! Upload it to S3 with public-read ACL
            if S3_BUCKET:
                try:
                    import boto3
                    s3_client = boto3.client("s3", region_name=S3_REGION)
                    
                    # Upload to S3 with public-read ACL
                    import hashlib
                    import time
                    text_hash = hashlib.md5(text.encode()).hexdigest()[:8]
                    timestamp = int(time.time())
                    s3_key = f"tts/speech_{timestamp}_{text_hash}.mp3"
                    
                    logging.info(f"Uploading audio to S3: s3://{S3_BUCKET}/{s3_key}")
                    s3_client.put_object(
                        Bucket=S3_BUCKET,
                        Key=s3_key,
                        Body=audio_data,
                        ContentType="audio/mpeg",
                        ACL="public-read",
                    )
                    
                    url = f"https://{S3_BUCKET}.s3.{S3_REGION}.amazonaws.com/{s3_key}"
                    logging.info(f"Successfully uploaded audio to S3: {url}")
                    return {
                        "audio": f'<audio src="{url}"/>',
                        "text": text
                    }
                except Exception as s3_error:
                    logging.error(f"Failed to upload to S3: {str(s3_error)}")
                    raise Exception(f"S3 upload failed: {str(s3_error)}")
            else:
                raise Exception("S3_BUCKET must be configured if not using GitHub URL. The audio file is too large for data URIs.")
        
    except Exception as pregen_error:
        logging.warning(f"Could not use pre-generated file: {str(pregen_error)}")
    
    # Fallback to EdgeTTS if pre-generated file not found
    try:
        logging.info(f"Pre-generated file not found, using EdgeTTS for text: {text[:50]}...")
        tts_client = get_tts_client()
        url = tts_client.synthesize(text)
        logging.info(f"TTS synthesis successful, URL: {url[:100]}...")
        
        # Handle both HTTPS URLs and data URIs
        if url.startswith("data:"):
            return {
                "audio": f'<audio src="{url}"/>',
                "text": text
            }
        else:
            return {
                "audio": f'<audio src="{url}"/>',
                "text": text
            }
    except Exception as e:
        error_msg = str(e)
        logging.error(f"TTS synthesis error: {error_msg}", exc_info=True)
        
        # Check if it's an import error
        if "edge-tts" in error_msg.lower() or "import" in error_msg.lower():
            logging.error("EdgeTTS library may not be installed. Check requirements.txt and redeploy.")
        
        # If show_error is True, include error in response for debugging
        if show_error:
            error_text = f"EdgeTTS Error: {error_msg[:100]}"
            return {
                "audio": f"<speak>{text}. Error: {error_text}</speak>",
                "text": f"{text} - ERROR: {error_msg}"
            }
        
        # Return fallback - use Alexa's default TTS as backup
        return {
            "audio": f"<speak>{text}</speak>",  # Fallback to default Alexa TTS
            "text": text
        }


###############################################################################
# The code below comes from an Amazon sample with slight modification to
# intercept the response and run it through TTS before returning it.
# See https://github.com/alexa/skill-sample-python-helloworld-decorators
###############################################################################
sb = SkillBuilder()

logger = logging.getLogger(__name__)
logger.setLevel(logging.INFO)

def _create_response(response_builder, synthesized, end_session=True):
    return response_builder.speak(synthesized["audio"]).set_card(
        SimpleCard(SKILL_NAME, synthesized["text"])).set_should_end_session(
            end_session).response

@sb.request_handler(can_handle_func=is_request_type("LaunchRequest"))
def launch_request_handler(handler_input):
    """Handler for skill launch."""
    # Try to synthesize with error details for debugging
    try:
        synth = synthesize(RESPONSE, show_error=True)
    except Exception as e:
        # If even synthesize fails, return diagnostic info
        error_text = f"Critical error: {str(e)[:200]}"
        synth = {
            "audio": f"<speak>{error_text}</speak>",
            "text": error_text
        }
    
    return _create_response(handler_input.response_builder, synth)

# handle other intents, even though we won't need to since we're
# exiting after launch

@sb.request_handler(can_handle_func=is_intent_name("MotivateIntent"))
def motivate_intent_handler(handler_input):
    """Handler for MotivateIntent."""
    synth = synthesize(RESPONSE)

    return _create_response(handler_input.response_builder, synth)


@sb.request_handler(can_handle_func=is_intent_name("AMAZON.HelpIntent"))
def help_intent_handler(handler_input):
    """Handler for HelpIntent."""
    # Add diagnostic info to help response
    try:
        # Try to check if edge_tts is available
        import edge_tts
        status = "EdgeTTS is available"
    except ImportError as e:
        status = f"EdgeTTS NOT installed: {str(e)}"
    except Exception as e:
        status = f"EdgeTTS check failed: {str(e)}"
    
    help_text = f"Ask me to motivate you! Diagnostic: {status}"
    synth = synthesize(help_text, show_error=True)
    
    return _create_response(handler_input.response_builder, synth, False)


@sb.request_handler(
    can_handle_func=lambda handler_input:
        is_intent_name("AMAZON.CancelIntent")(handler_input) or
        is_intent_name("AMAZON.StopIntent")(handler_input))
def cancel_and_stop_intent_handler(handler_input):
    """Single handler for CancelIntent and StopIntent."""
    synth = synthesize("Goodbye for now!")

    return _create_response(handler_input.response_builder, synth, False)


@sb.request_handler(can_handle_func=is_intent_name("AMAZON.FallbackIntent"))
def fallback_handler(handler_input):
    """AMAZON.FallbackIntent is only available in en-US locale.
    This handler will not be triggered except in that locale,
    so it is safe to deploy on any locale.
    """
    speech = ("Sorry; I can't help with that. Only you can help you. "
              "You can ask me to motivate you.")
    reprompt = "Ask me to say something."
    synth = synthesize(speech)
    reprompt_synth = synthesize(reprompt)
    handler_input.response_builder.speak(synth["audio"]).ask(reprompt_synth["audio"])
    return handler_input.response_builder.response


@sb.request_handler(can_handle_func=is_request_type("SessionEndedRequest"))
def session_ended_request_handler(handler_input):
    """Handler for session end."""
    return handler_input.response_builder.response


@sb.exception_handler(can_handle_func=lambda i, e: True)
def all_exception_handler(handler_input, exception):
    """Catch-all exception handler.
    Log exception and respond with custom message.
    """
    logger.error(exception, exc_info=True)

    speech = "Sorry, there was a problem. Please try again!"
    synth = synthesize(speech)

    handler_input.response_builder.speak(synth["audio"]).ask(synth["audio"])

    return handler_input.response_builder.response


# special assignment for AWS Lambda
lambda_handler = sb.lambda_handler()

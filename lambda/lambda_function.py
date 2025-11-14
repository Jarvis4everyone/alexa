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

# S3 Configuration (optional but recommended for production)
# If you don't set up S3, the code will use data URIs (limited to ~100KB)
# To set up S3:
# 1. Create an S3 bucket in your AWS account
# 2. Enable public read access for the bucket or objects
# 3. Set the bucket name and region below
# 4. Make sure your Lambda execution role has S3 write permissions
S3_BUCKET = os.environ.get("S3_BUCKET", None)  # Set via environment variable or here
S3_REGION = os.environ.get("S3_REGION", "us-east-1")  # Change to your bucket's region

# text to read as a response
RESPONSE = "You're good enough, you're smart enough, and dog gone it, people like you!"

# the name of your skill (shown on cards)
SKILL_NAME = "Custom TTS Voice"

###############################################################################
# This is basically the only feature we've added.
# All it does is insert EdgeTTS audio URLs in an SSML tag.
###############################################################################
tts = EdgeTTSClient(voice=VOICE, s3_bucket=S3_BUCKET, s3_region=S3_REGION)


def synthesize(text):
    """
    Creates an SSML `<audio>` element containing a URL to
    a synthesized version of the text using EdgeTTS.
    """
    try:
        url = tts.synthesize(text)
        # Handle both HTTPS URLs and data URIs
        if url.startswith("data:"):
            # For data URIs, we need to use a different SSML format
            return {
                "audio": f'<audio src="{url}"/>',
                "text": text
            }
        else:
            # For HTTPS URLs (S3)
            return {
                "audio": f'<audio src="{url}"/>',
                "text": text
            }
    except Exception as e:
        logging.error(f"TTS synthesis error: {str(e)}", exc_info=True)
        return {
            "audio": "Sorry; there was a problem generating the audio",
            "text": f"There was a problem: {e}"
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
    synth = synthesize(RESPONSE)

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
    synth = synthesize("Ask me to motivate you!")

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

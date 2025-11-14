import logging
import os
import random

from ask_sdk_core.skill_builder import SkillBuilder
from ask_sdk_core.utils import is_request_type, is_intent_name
from ask_sdk_core.handler_input import HandlerInput

from ask_sdk_model.ui import SimpleCard
from ask_sdk_model import Response

###############################################################################
# Customize your skill here!
###############################################################################
# GitHub Configuration for audio files
# Upload audio files to your GitHub repo in the 'audio' folder
# Format: https://raw.githubusercontent.com/USERNAME/REPO/BRANCH/audio/FILENAME.mp3
GITHUB_REPO = "Jarvis4everyone/alexa"
GITHUB_BRANCH = "main"
GITHUB_AUDIO_FOLDER = "audio"

# List of audio files to randomly choose from
# Add more audio files to the 'audio' folder and add their names here
AUDIO_FILES = [
    "speech.mp3",
    # Add more audio files here, e.g.:
    # "greeting.mp3",
    # "motivation.mp3",
    # "goodbye.mp3",
]

# text to read as a response (shown on card)
RESPONSE = "You're good enough, you're smart enough, and dog gone it, people like you!"

# the name of your skill (shown on cards)
SKILL_NAME = "Custom TTS Voice"


def get_random_audio_url():
    """
    Returns a random GitHub raw URL for an audio file.
    """
    if not AUDIO_FILES:
        raise Exception("No audio files configured in AUDIO_FILES list")
    
    # Randomly select an audio file
    selected_file = random.choice(AUDIO_FILES)
    
    # Construct GitHub raw URL
    url = f"https://raw.githubusercontent.com/{GITHUB_REPO}/{GITHUB_BRANCH}/{GITHUB_AUDIO_FOLDER}/{selected_file}"
    
    logging.info(f"Selected random audio file: {selected_file}, URL: {url}")
    return url


def synthesize(text, show_error=False):
    """
    Creates an SSML `<audio>` element containing a GitHub URL to a random audio file.
    
    Args:
        text: Text to display (shown on card)
        show_error: If True, include error details in response (for debugging)
    """
    try:
        audio_url = get_random_audio_url()
        logging.info(f"Using GitHub audio URL: {audio_url}")
        return {
            "audio": f'<audio src="{audio_url}"/>',
            "text": text
        }
    except Exception as e:
        error_msg = str(e)
        logging.error(f"Error getting audio URL: {error_msg}", exc_info=True)
        
        if show_error:
            error_text = f"Error: {error_msg[:100]}"
            return {
                "audio": f"<speak>{text}. {error_text}</speak>",
                "text": f"{text} - ERROR: {error_msg}"
            }
        
        # Fallback to default Alexa TTS
        return {
            "audio": f"<speak>{text}</speak>",
            "text": text
        }


###############################################################################
# Alexa Skill Handlers
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

@sb.request_handler(can_handle_func=is_intent_name("MotivateIntent"))
def motivate_intent_handler(handler_input):
    """Handler for MotivateIntent."""
    synth = synthesize(RESPONSE)
    return _create_response(handler_input.response_builder, synth)

@sb.request_handler(can_handle_func=is_intent_name("AMAZON.HelpIntent"))
def help_intent_handler(handler_input):
    """Handler for HelpIntent."""
    help_text = "Ask me to motivate you!"
    synth = synthesize(help_text)
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
    """AMAZON.FallbackIntent is only available in en-US locale."""
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
    """Catch-all exception handler."""
    logger.error(exception, exc_info=True)
    speech = "Sorry, there was a problem. Please try again!"
    synth = synthesize(speech)
    handler_input.response_builder.speak(synth["audio"]).ask(synth["audio"])
    return handler_input.response_builder.response

# special assignment for AWS Lambda
lambda_handler = sb.lambda_handler()

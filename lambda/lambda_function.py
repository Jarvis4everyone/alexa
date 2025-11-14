import logging
import random

from ask_sdk_core.skill_builder import SkillBuilder
from ask_sdk_core.utils import is_request_type, is_intent_name
from ask_sdk_model.ui import SimpleCard

###############################################################################
# Configuration
###############################################################################
GITHUB_REPO = "Jarvis4everyone/alexa"
GITHUB_BRANCH = "main"
GITHUB_AUDIO_FOLDER = "audio"

# Hardcoded audio file URLs (1.mp3 through 10.mp3)
# Using raw.githubusercontent.com for direct file access (required for Alexa)
AUDIO_URLS = [
    "https://raw.githubusercontent.com/Jarvis4everyone/alexa/main/audio/1.mp3",
    "https://raw.githubusercontent.com/Jarvis4everyone/alexa/main/audio/2.mp3",
    "https://raw.githubusercontent.com/Jarvis4everyone/alexa/main/audio/3.mp3",
    "https://raw.githubusercontent.com/Jarvis4everyone/alexa/main/audio/4.mp3",
    "https://raw.githubusercontent.com/Jarvis4everyone/alexa/main/audio/5.mp3",
    "https://raw.githubusercontent.com/Jarvis4everyone/alexa/main/audio/6.mp3",
    "https://raw.githubusercontent.com/Jarvis4everyone/alexa/main/audio/7.mp3",
    "https://raw.githubusercontent.com/Jarvis4everyone/alexa/main/audio/8.mp3",
    "https://raw.githubusercontent.com/Jarvis4everyone/alexa/main/audio/9.mp3",
    "https://raw.githubusercontent.com/Jarvis4everyone/alexa/main/audio/10.mp3",
]

RESPONSE = "You're good enough, you're smart enough, and dog gone it, people like you!"
SKILL_NAME = "Custom TTS Voice"


def get_random_audio_url():
    """Returns a random audio file URL from hardcoded list."""
    selected_url = random.choice(AUDIO_URLS)
    logging.info(f"Randomly selected audio file: {selected_url}")
    return selected_url


def get_audio_response():
    """Returns SSML audio tag with random GitHub audio file."""
    try:
        audio_url = get_random_audio_url()
        # Return just the audio tag - Alexa will wrap it in <speak>
        return f'<audio src="{audio_url}"/>'
    except Exception as e:
        logging.error(f"Error: {str(e)}")
        return "<speak>Sorry, there was a problem.</speak>"


###############################################################################
# Alexa Skill Handlers
###############################################################################
sb = SkillBuilder()
logger = logging.getLogger(__name__)
logger.setLevel(logging.INFO)


@sb.request_handler(can_handle_func=is_request_type("LaunchRequest"))
def launch_request_handler(handler_input):
    """Plays random audio and ends session."""
    audio_ssml = get_audio_response()
    return handler_input.response_builder.speak(audio_ssml).set_should_end_session(True).response


@sb.request_handler(can_handle_func=is_intent_name("MotivateIntent"))
def motivate_intent_handler(handler_input):
    """Plays random audio and ends session."""
    audio_ssml = get_audio_response()
    return handler_input.response_builder.speak(audio_ssml).set_should_end_session(True).response


@sb.request_handler(can_handle_func=is_intent_name("AMAZON.HelpIntent"))
def help_intent_handler(handler_input):
    """Help handler."""
    audio_ssml = get_audio_response()
    return handler_input.response_builder.speak(audio_ssml).set_should_end_session(True).response


@sb.request_handler(
    can_handle_func=lambda handler_input:
        is_intent_name("AMAZON.CancelIntent")(handler_input) or
        is_intent_name("AMAZON.StopIntent")(handler_input))
def cancel_and_stop_intent_handler(handler_input):
    """Cancel/Stop handler."""
    return handler_input.response_builder.speak("<speak>Goodbye!</speak>").set_should_end_session(True).response


@sb.request_handler(can_handle_func=is_intent_name("AMAZON.FallbackIntent"))
def fallback_handler(handler_input):
    """Fallback handler."""
    audio_ssml = get_audio_response()
    return handler_input.response_builder.speak(audio_ssml).set_should_end_session(True).response


@sb.request_handler(can_handle_func=is_request_type("SessionEndedRequest"))
def session_ended_request_handler(handler_input):
    """Session ended handler."""
    return handler_input.response_builder.response


@sb.exception_handler(can_handle_func=lambda i, e: True)
def all_exception_handler(handler_input, exception):
    """Exception handler."""
    logger.error(exception, exc_info=True)
    return handler_input.response_builder.speak(
        "<speak>Sorry, there was a problem.</speak>"
    ).set_should_end_session(True).response


lambda_handler = sb.lambda_handler()

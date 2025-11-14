import logging
import random
import json
import urllib.request
import urllib.parse

from ask_sdk_core.skill_builder import SkillBuilder
from ask_sdk_core.utils import is_request_type, is_intent_name
from ask_sdk_model.ui import SimpleCard

###############################################################################
# Configuration
###############################################################################
GITHUB_REPO = "Jarvis4everyone/alexa"
GITHUB_BRANCH = "main"
GITHUB_AUDIO_FOLDER = "audio"

RESPONSE = "You're good enough, you're smart enough, and dog gone it, people like you!"
SKILL_NAME = "Custom TTS Voice"

# Cache for audio files list
_audio_files_cache = None


def get_audio_files_from_github():
    """Fetches list of .mp3 files from GitHub repository."""
    global _audio_files_cache
    
    if _audio_files_cache is not None:
        logging.info(f"Using cached audio files: {len(_audio_files_cache)} files")
        return _audio_files_cache
    
    try:
        api_url = f"https://api.github.com/repos/{GITHUB_REPO}/contents/{GITHUB_AUDIO_FOLDER}"
        req = urllib.request.Request(api_url)
        req.add_header('Accept', 'application/vnd.github.v3+json')
        
        with urllib.request.urlopen(req, timeout=5) as response:
            data = json.loads(response.read().decode())
            audio_files = [
                item['name'] 
                for item in data 
                if isinstance(item, dict) and item.get('name', '').endswith('.mp3')
            ]
            
            # Sort files to ensure consistent ordering
            audio_files.sort()
            
            if audio_files:
                _audio_files_cache = audio_files
                logging.info(f"Found {len(audio_files)} audio files: {audio_files}")
            else:
                logging.warning("No .mp3 files found in GitHub repository")
            
            return audio_files
    except Exception as e:
        logging.error(f"Error fetching audio files: {str(e)}", exc_info=True)
        return []


def get_random_audio_url():
    """Returns a random GitHub raw URL for an audio file."""
    audio_files = get_audio_files_from_github()
    
    if not audio_files:
        raise Exception("No audio files found in GitHub repository")
    
    if len(audio_files) != 10:
        logging.warning(f"Expected 10 files, but found {len(audio_files)} files")
    
    selected_file = random.choice(audio_files)
    encoded_file = urllib.parse.quote(selected_file, safe='')
    url = f"https://raw.githubusercontent.com/{GITHUB_REPO}/{GITHUB_BRANCH}/{GITHUB_AUDIO_FOLDER}/{encoded_file}"
    
    logging.info(f"Randomly selected file {selected_file} from {len(audio_files)} available files")
    return url


def get_audio_response():
    """Returns SSML audio tag with random GitHub audio file."""
    try:
        audio_url = get_random_audio_url()
        return f'<audio src="{audio_url}"/>'
    except Exception as e:
        logging.error(f"Error: {str(e)}")
        return f"<speak>Sorry, there was a problem.</speak>"


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
    return handler_input.response_builder.speak(audio_ssml).set_card(
        SimpleCard(SKILL_NAME, RESPONSE)
    ).set_should_end_session(True).response


@sb.request_handler(can_handle_func=is_intent_name("MotivateIntent"))
def motivate_intent_handler(handler_input):
    """Plays random audio and ends session."""
    audio_ssml = get_audio_response()
    return handler_input.response_builder.speak(audio_ssml).set_card(
        SimpleCard(SKILL_NAME, RESPONSE)
    ).set_should_end_session(True).response


@sb.request_handler(can_handle_func=is_intent_name("AMAZON.HelpIntent"))
def help_intent_handler(handler_input):
    """Help handler."""
    audio_ssml = get_audio_response()
    return handler_input.response_builder.speak(audio_ssml).set_card(
        SimpleCard(SKILL_NAME, "Ask me to motivate you!")
    ).set_should_end_session(True).response


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

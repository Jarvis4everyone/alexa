## EdgeTTS Custom Text to Speech on Alexa

This is sample code for an [Alexa-hosted skill](https://developer.amazon.com/en-US/docs/alexa/hosted-skills/build-a-skill-end-to-end-using-an-alexa-hosted-skill.html) that uses [Microsoft EdgeTTS](https://github.com/rany2/edge-tts) to replace Alexa's voice with custom TTS voices, including the **Liam Neural** voice.

The skill itself isn't impressive; it simply repeats an encouraging message (see https://www.youtube.com/watch?v=xNx_gU57gQ4 for our inspiration) and exits. Its main purpose is to be a template demonstrating the use of SSML and a custom TTS service to replace the default voice on a smart speaker. The same SSML will work for Google Assistant, but the rest of the code in this repository is structured to run in Amazon's hosting infrastructure.

## Installation

_You'll need an [Amazon developer account](https://developer.amazon.com/) to set up this skill. No API keys or paid services required - EdgeTTS is free!_

1. Log in to the [Alexa developer console](https://developer.amazon.com/alexa/console/ask#).
1. On the "*Skills*" tab (which is selected by default at the time of writing), click `Create Skill`.
1. On the "*Create a new skill*" screen:
    - Enter a name for your skill. Any name will do.
    - Under "*Choose a model...*" select "*Custom*" (selected by default).
    - Under "*Choose a method...*" select "*Alexa-hosted (Python)*".
    - Click the "*Create skill*" button (you may have to scroll up to see it).
1. On the next screen ("*Choose a template...*"), click the "*Import skill*" button.
1. Enter this repository's URL in the "*Import skill*" box.
1. Click "*Import*".

Once you've clicked "*Import*", Amazon will take care of copying over the code and creating a new sandbox for your skill to run in. When the import completes:
1. Click on the "*Code*" tab to finish setup. This will open the `lambda_function.py` file in a code editor.
1. Look for the "*Customize your skill here!*" section.
    - The voice is already set to **Liam Neural** (`en-CA-LiamNeural`), but you can change it to any EdgeTTS voice.
    - **Optional but recommended**: Set up an S3 bucket for audio storage (see S3 Setup below).
1. When you're finished making changes, click "*Save*" at the top of the page.
1. Click "*Deploy*" (next to "*Save*").
1. Click over to the "*Test*" tab while you're waiting for the deployment to finish.
1. In the dropdown next to "*Test is disabled for this skill*" (at the top of the page), you'll want to select "*Development*". This will let you test your skill directly on the page or on any Alexa-enabled devices connected to the account you used to create this skill.

That's it! Enjoy your new smart speaker voice with Liam Neural!

## S3 Setup (Recommended for Production)

For production use, you should set up an S3 bucket to store the generated audio files. Without S3, the code uses data URIs which have size limitations (~100KB).

### Setting up S3:

1. **Create an S3 bucket:**
   - Go to AWS S3 Console
   - Create a new bucket (e.g., `alexa-tts-audio`)
   - Note the bucket name and region

2. **Configure bucket permissions:**
   - Go to your bucket → Permissions tab
   - Edit "Block public access" settings and allow public read access
   - Add a bucket policy to allow public read:
   ```json
   {
     "Version": "2012-10-17",
     "Statement": [
       {
         "Sid": "PublicReadGetObject",
         "Effect": "Allow",
         "Principal": "*",
         "Action": "s3:GetObject",
         "Resource": "arn:aws:s3:::YOUR-BUCKET-NAME/*"
       }
     ]
   }
   ```

3. **Configure Lambda permissions:**
   - In Alexa Developer Console → Code tab → Environment variables
   - Add `S3_BUCKET` = your bucket name
   - Add `S3_REGION` = your bucket region (e.g., `us-east-1`)
   - The Lambda execution role should already have S3 write permissions for Alexa-hosted skills

Alternatively, you can set `S3_BUCKET` and `S3_REGION` directly in `lambda_function.py`.

## How Does It Work?

The bulk of the sample code here is based on Amazon's [Python SDK example](https://github.com/alexa/skill-sample-python-helloworld-decorators). The only thing we're customizing is running the text of our responses through EdgeTTS to generate speech audio. The audio is then uploaded to S3 (or encoded as a data URI) and we're using the [SSML `audio` element](https://www.w3.org/TR/speech-synthesis11/#S3.3.1) to play the audio instead of having Amazon's TTS service synthesize the text for us in Alexa's voice.

The code for the actual synthesis is in the `edgetts.py` file. It uses the `edge-tts` Python library to generate speech with Microsoft Edge TTS voices.

## Can I Use Other Voices?

Yes! EdgeTTS supports many voices. The default is set to **Liam Neural** (`en-CA-LiamNeural`), but you can change the `VOICE` variable in `lambda_function.py` to any EdgeTTS voice. 

To see all available voices, check the [EdgeTTS voices list](https://github.com/rany2/edge-tts/blob/master/src/edge_tts/voices.json) or run:
```python
import edge_tts
import asyncio

async def list_voices():
    voices = await edge_tts.list_voices()
    for voice in voices:
        print(f"{voice['ShortName']} - {voice['Gender']} - {voice['Locale']}")

asyncio.run(list_voices())
```

## Troubleshooting

### Alexa says, "Sorry, I don't know that one" during testing
This happens if you ask Alexa to open a skill, but the skill's name isn't recognized. Development skills can run into this problem if the invocation name has been changed without rebuilding the skill's model. To ensure your skill name is up to date:
1. Click on the "*Build*" tab in the development console.
1. Click on "*Invocation Name*" in the Skill builder checklist.
1. Double-check that your invocation name is what you want, then click "*Save Model*" at the top of the page.
1. Click "*Deploy Model*".
When the model is updated, Amazon will notify you with a popup at the bottom of the screen. At this point, "open `skill name`" should work in the test console.

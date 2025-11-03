from moviepy import ImageClip, AudioFileClip
from moviepy.audio.AudioClip import CompositeAudioClip, AudioArrayClip
from moviepy.audio.fx.MultiplyVolume import MultiplyVolume
from PIL import Image, ImageDraw, ImageFont
from transformers import VitsModel, AutoTokenizer
import torch
import scipy.io.wavfile as wavfile
import os

import numpy as np
from google.oauth2.credentials import Credentials
from google_auth_oauthlib.flow import InstalledAppFlow
from googleapiclient.discovery import build
from googleapiclient.http import MediaFileUpload
from google.auth.transport.requests import Request
import pickle
from datetime import datetime, timedelta, date
import config

# Configuration - Import from config.py
image_path = config.IMAGE_PATH
font_path = config.FONT_PATH
font_size = config.FONT_SIZE
output_dir = config.OUTPUT_DIR
audio_dir = config.AUDIO_DIR
bgm_path = config.BGM_PATH
bgm_volume = config.BGM_VOLUME

# YouTube Upload Configuration - Import from config.py
YOUTUBE_UPLOAD_ENABLED = config.YOUTUBE_UPLOAD_ENABLED
YOUTUBE_CHANNEL_NAME = config.YOUTUBE_CHANNEL_NAME
YOUTUBE_CLIENT_SECRETS_FILE = config.YOUTUBE_CLIENT_SECRETS_FILE
YOUTUBE_TOKEN_FILE = config.YOUTUBE_TOKEN_FILE
YOUTUBE_SCOPES = config.YOUTUBE_SCOPES
YOUTUBE_PRIVACY_STATUS = config.YOUTUBE_PRIVACY_STATUS

# Scheduling Configuration - Import from config.py
YOUTUBE_SCHEDULE_ENABLED = config.YOUTUBE_SCHEDULE_ENABLED
YOUTUBE_SCHEDULE_TIME = config.YOUTUBE_SCHEDULE_TIME
YOUTUBE_SCHEDULE_START_DATE = config.YOUTUBE_SCHEDULE_START_DATE
YOUTUBE_TIMEZONE = config.YOUTUBE_TIMEZONE


# Adhigaram (Chapter) names for each group of 10 kurals
adhigaram_names = [
    "கடவுள் வாழ்த்து",      # 1-10: Invocation to God
    "வான்சிறப்பு",            # 11-20: Excellence of Rain
    "நீத்தார் பெருமை",        # 21-30: Greatness of Renunciation
]

# Function to get adhigaram name for a kural number
def get_adhigaram_name(kural_number):
    """Get the adhigaram name for a given kural number (1-based)"""
    # Calculate which group of 10 (0-indexed)
    group_index = (kural_number - 1) // 10
    if 0 <= group_index < len(adhigaram_names):
        return adhigaram_names[group_index]
    return ""  # Return empty string if out of range

# Array of Tamil sentences - First 30 Thirukural
sentences = [

    # 1-10 (existing)
    "அகர முதல எழுத்தெல்லாம் ஆதி பகவன் முதற்றே உலகு.",
    "கற்றதனால் ஆய பயனென்கொல் வாலறிவன் நற்றாள் தொழாஅர் எனின்.",
    "மலர்மிசை ஏகினான் மாணடி சேர்ந்தார் நிலமிசை நீடுவாழ் வார்.",
    "வேண்டுதல்வேண் டாமை இலானடி சேர்ந்தார்க்கு யாண்டும் இடும்பை இல.",
    "இருள்சேர் இருவினையும் சேரா இறைவன் பொருள்சேர் புகழ்புரிந்தார் மாட்டு.",
    "பொறிவாயில் ஐந்தவித்தான் பொய்தீர் ஒழுக்க நெறிநின்றார் நீடுவாழ் வார்.",
    "தனக்குவமை இல்லாதான் தாள்சேர்ந்தார்க் கல்லால் மனக்கவலை மாற்றல் அரிது.",
    "அறவாழி அந்தணன் தாள்சேர்ந்தார்க் கல்லால் பிறவாழி நீந்தல் அரிது.",
    "கோளில் பொறியின் குணமிலவே எண்குணத்தான் தாளை வணங்காத் தலை.",
    "பிறவிப் பெருங்கடல் நீந்துவர் நீந்தார் இறைவன் அடிசேரா தார்.",
    # 11-20 (Rain and Nature)
    "வான்நின்று உலகம் வழங்கி வருதலால் தான்அமிழ்தம் என்றுணரற் பாற்று.",
    "துப்பார்க்குத் துப்பாய துப்பாக்கித் துப்பார்க்குத் துப்பாய தூஉம் மழை.",
    "விண்இன்று பொய்ப்பின் விரிநீர் வியனுலகத்து உள்நின்று உடற்றும் பசி.",
    "ஏரின் உழாஅர் உழவர் புயல்என்னும் வாரி வளங்குன்றிக் கால்.",
    "கெடுப்பதூஉம் கெட்டார்க்குச் சார்வாய்மற் றாங்கே எடுப்பதூஉம் எல்லாம் மழை.",
    "விசும்பின் துளிவீழின் அல்லால்மற் றாங்கே பசும்புல் தலைகாண்பு அரிது.",
    "நெடுங்கடலும் தன்நீர்மை குன்றும் தடிந்தெழிலி தான்நல்கா தாகி விடின்.",
    "சிறப்பொடு பூசனை செல்லாது வானம் வறக்குமேல் வானோர்க்கும் ஈண்டு.",
    "தானம் தவம்இரண்டும் தங்கா வியன்உலகம் வானம் வழங்கா தெனின்.",
    "நீர்இன்று அமையாது உலகெனின் யார்யார்க்கும் வான்இன்று அமையாது ஒழுக்கு.",
    # 21-30 (Virtue and Righteousness)
    "ஒழுக்கத்து நீத்தார் பெருமை விழுப்பத்து வேண்டும் பனுவல் துணிவு.",
    "துறந்தார் பெருமை துணைக்கூறின் வையத்து இறந்தாரை எண்ணிக்கொண் டற்று.",
    "இருமை வகைதெரிந்து ஈண்டுஅறம் பூண்டார் பெருமை பிறங்கிற்று உலகு.",
    "உரனென்னும் தோட்டியான் ஓரைந்தும் காப்பான் வரனென்னும் வைப்பிற்கோர் வித்தது.",
    "ஐந்தவித்தான் ஆற்றல் அகல்விசும்பு ளார்கோமான் இந்திரனே சாலுங் கரி.",
    "செயற்கரிய செய்வார் பெரியர் சிறியர் செயற்கரிய செய்கலா தார்.",
    "சுவைஒளி ஊறுஓசை நாற்றமென ஐந்தின் வகைதெரிவான் கட்டே உலகு.",
    "நிறைமொழி மாந்தர் பெருமை நிலத்து மறைமொழி காட்டி விடும்.",
    "குணமென்னும் குன்றேறி நின்றார் வெகுளி கணமேயும் காத்தல் அரிது.",
    "அந்தணர் என்போர் அறவோர்மற் றெவ்வுயிர்க்கும் செந்தண்மை பூண்டொழுக லான்.",
]

# Detailed meanings for each Tirukural - Elaborated to ensure 30-second videos
meanings = [
    "அகரம் எழுத்துக்களுக்கு எல்லாம் முதன்மை; ஆதிபகவன், உலகில் வாழும் உயிர்களுக்கு எல்லாம் முதன்மை. அகரம் என்பது எழுத்துக்களுக்கெல்லாம் முதலாவது எழுத்தாகும். அதைப்போல இறைவனும் உலகில் உள்ள உயிர்களுக்கெல்லாம் முதலாவதும், ஆதாரமுமாக விளங்குகிறார். எல்லா எழுத்துக்களும் அகரத்திலிருந்து தொடங்குவது போல, எல்லா உயிர்களும் இறைவனிடமிருந்தே உருவாக்கப்பட்டன. இந்த குறள் வாழ்க்கையின் அடிப்படையை எடுத்துரைக்கிறது. எல்லாமே ஒரு முதன்மையிலிருந்து தொடங்குகிறது. அகரத்தின் முக்கியத்துவம் போல, இறைவனின் முக்கியத்துவமும் வாழ்க்கையின் ஒவ்வொரு அம்சத்திலும் காணப்படுகிறது. இது ஒரு ஆழமான தத்துவமாகும்.",
    "தன்னைவிட அறிவில் மூத்த பெருந்தகையாளரின் முன்னே வணங்கி நிற்கும் பண்பு இல்லாவிடில் என்னதான் ஒருவர் கற்றிருந்தாலும் அதனால் என்ன பயன்? ஒன்றுமில்லை. ஒருவர் பல கலைகளையும் கற்று அறிவாளியாக இருந்தாலும், தன்னைவிட மேம்பட்ட அறிவாளர்களிடம் பணிவு காட்டாதவராயின், அவரது கல்வி பயனற்றதாகிறது. உண்மையான கல்வி என்பது அறிவோடு பணிவையும் சேர்த்து கொள்வதே ஆகும். இந்த குறள் கல்வியின் உண்மையான மதிப்பை எடுத்துரைக்கிறது. ஒருவர் பல நூல்களைப் படித்து, பல மொழிகளைக் கற்று, பல பட்டங்களைப் பெற்றாலும், அன்பும் பணிவும் இல்லாவிடில் அது பயனற்றது. உண்மையான கல்வி என்பது அடக்கமும் நற்குணமும் கொண்ட கல்வியே ஆகும்.",
    "மலர் போன்ற மனத்தில் நிறைந்தவனைப் பின்பற்றுவோரின் புகழ்வாழ்வு, உலகில் நெடுங்காலம் நிலைத்து நிற்கும். மலர்போல மனம் நிறைந்தவனின் அடியைப் பின்பற்றி நடப்போர், இவ்வுலகில் நீண்ட காலம் புகழுடன் வாழ்வர். மலரின் மணம் போல பரவும் அவரது புகழ், பல நூற்றாண்டுகளுக்கும் நிலைத்து நிற்கும். இந்த குறள் புகழின் நிலைத்தன்மையைப் பற்றி கூறுகிறது. ஒருவர் மலர்போல மனம் நிறைந்தவரைத் தொடர்ந்து செல்வாராயின், அவரது புகழ் எப்போதும் நிலைத்திருக்கும். மலரின் மணம் பரவுவது போல, அவரது நற்பெயரும் எல்லா இடங்களிலும் பரவும். இது வாழ்க்கையின் நீடித்த புகழைப் பற்றிய புரட்சிகரமான எண்ணமாகும்.",
    "விருப்பு வெறுப்பற்றுத் தன்னலமின்றித் திகழ்கின்றவரைப் பின்பற்றி நடப்பவர்களுக்கு எப்போதுமே துன்பம் ஏற்படுவதில்லை. விருப்பும் வெறுப்பும் இல்லாமல், தன்னலம் இல்லாமல் வாழ்க்கை நடத்தும் பெரியோரின் பாதத்தைத் தொடர்பவர்களுக்கு, எப்போதும் எந்த துன்பமும் வராது. இத்தகையோரின் வாழ்க்கை சீராகவும் நிம்மதியாகவும் இருக்கும். இந்த குறள் துன்பமற்ற வாழ்க்கைக்கான வழியைக் காட்டுகிறது. ஒருவர் எல்லா சந்தர்ப்பங்களிலும் சமநிலையைக் கடைப்பிடித்து, தன்னலம் இல்லாமல் வாழ்ந்தால், அவருக்கு எந்த துன்பமும் ஏற்படாது. இது வாழ்க்கையின் மிக முக்கியமான பாடமாகும். உண்மையான அமைதி என்பது இத்தகைய வாழ்க்கையில்தான் கிடைக்கிறது.",
    "இறைவன் என்பதற்குரிய பொருளைப் புரிந்து கொண்டு புகழ் பெற விரும்புகிறவர்கள், நன்மை தீமைகளை ஒரே அளவில் எதிர் கொள்வார்கள். இறைவனின் தன்மையை உணர்ந்தவர்கள், நன்மையையும் தீமையையும் சமமாக ஏற்றுக்கொள்வார்கள். அவர்கள் சந்தோஷத்தில் மட்டுமல்ல, துன்பத்திலும் மன அமைதியை இழக்காது, சமநிலையோடு வாழ்வார்கள். இந்த குறள் மன ஆற்றலின் மேன்மையைப் பற்றி கூறுகிறது. ஒருவர் இறைவனின் உண்மையான தன்மையை அறிந்த பின்னர், வாழ்க்கையின் எல்லா சூழ்நிலைகளையும் சமமாக ஏற்றுக்கொள்வர். இது மிக உயர்ந்த ஒரு பண்பாகும். சந்தோஷம், துன்பம், வெற்றி, தோல்வி ஆகியவற்றை எல்லாம் ஒரே அளவில் ஏற்றுக்கொள்ளும் ஆற்றல், உண்மையான ஞானத்தின் அடையாளமாகும்.",
    "மெய், வாய், கண், மூக்கு, செவி எனும் ஐம்பொறிகளையும் கட்டுப்படுத்திய தூயவனின் உண்மையான ஒழுக்கமுடைய நெறியைப் பின்பற்றி நிற்பவர்களின் புகழ்வாழ்வு நிலையானதாக அமையும். ஐந்து பொறிகளையும் அடக்கி ஆண்ட பரிசுத்தமானவரின் சத்திய ஒழுக்க வழியில் நின்றவர்கள், நீண்ட காலம் புகழுடன் வாழ்வார்கள். இத்தகைய ஒழுக்கமான வாழ்க்கையே மக்களால் நினைவில் கொள்ளப்படும். இந்த குறள் ஒழுக்கத்தின் முக்கியத்துவத்தை எடுத்துரைக்கிறது. ஐம்பொறிகளின் ஆசைகளைக் கட்டுப்படுத்தி, உண்மையான ஒழுக்கத்தில் நிற்பவர்களே நீடித்த புகழைப் பெற முடியும். இது வாழ்க்கையின் அடிப்படைக் கோட்பாடுகளில் ஒன்றாகும். தன்னைக் கட்டுப்படுத்துதல் என்பது மனித வாழ்க்கையின் மிகச் சிறந்த குணங்களில் ஒன்றாகும்.",
    "ஒப்பாரும் மிக்காருமில்லாதவனுடைய அடியொற்றி நடப்பவர்களைத் தவிர, மற்றவர்களின் மனக்கவலை தீர வழியேதுமில்லை. இணையற்றவனான இறைவனின் பாதத்தைப் பின்பற்றாதவர்களின் மனக்கவலையை நீக்க வழியே இல்லை. மன அமைதி பெற, இறைவனின் திருவடிகளைத் தொடர்வதே ஒரே வழியாகும். இந்த குறள் மன அமைதிக்கான வழியைக் காட்டுகிறது. வாழ்க்கையில் பல கவலைகள் வருகின்றன. அவற்றைத் தீர்க்க முடிந்த ஒரே வழி, இறைவனின் பாதத்தைத் தொடர்வதே ஆகும். இது மனித மனத்தின் ஆழமான தேவையை எடுத்துரைக்கிறது. உண்மையான மன அமைதி என்பது, இறைவனுடன் இணைந்து வாழ்வதில்தான் கிடைக்கிறது.",
    "அந்தணர் என்பதற்குப் பொருள் சான்றோர் என்பதால், அறக்கடலாகவே விளங்கும் அந்தச் சான்றோரின் அடியொற்றி நடப்பவர்க்கேயன்றி, மற்றவர்களுக்குப் பிற துன்பக் கடல்களைக் கடப்பது என்பது எளிதான காரியமல்ல. அறிவு நிறைந்த பெரியோரின் பாதத்தைத் தொடராதவர்களால், துன்பங்களின் கடலைக் கடப்பது மிகவும் கடினம். அறிவு நிறைந்தவர்களின் வழிகாட்டுதலே, வாழ்க்கையின் கடினங்களை எளிதாக்கும். இந்த குறள் வழிகாட்டியின் முக்கியத்துவத்தை எடுத்துரைக்கிறது. வாழ்க்கையில் பல கடினங்கள் வருகின்றன. அவற்றைத் தாண்டிச் செல்ல, அறிவு நிறைந்த பெரியோரின் வழிகாட்டுதல் தேவை. இது மனித வாழ்க்கையின் ஒரு முக்கிய உண்மையாகும். சான்றோர்களைத் தொடர்வதே, வாழ்க்கையின் சிக்கல்களை எளிதாக்கும் உண்மையான வழியாகும்.",
    "உடல், கண், காது, மூக்கு, வாய் எனும் ஐம்பொறிகள் இருந்தும், அவைகள் இயங்காவிட்டால் என்ன நிலையோ அதே நிலைதான் ஈடற்ற ஆற்றலும் பண்பும் கொண்டவனை வணங்கி நடக்காதவனின் நிலையும் ஆகும். ஒருவருக்கு ஐம்பொறிகள் இருந்தும் செயலற்றதாக இருந்தால், அது பயனற்றது. அதேபோல, எட்டு குணங்களையும் கொண்ட இறைவனை வணங்காதவரின் வாழ்க்கையும் பயனற்றதாகும். வணக்கம் என்பது மனித வாழ்க்கையின் முக்கியமான செயலாகும். இந்த குறள் வணக்கத்தின் முக்கியத்துவத்தை எடுத்துரைக்கிறது. ஒருவருக்கு ஐம்பொறிகள் இருந்தும் அவை செயலற்றதாக இருந்தால் பயனில்லை. அதேபோல, இறைவனை வணங்காத வாழ்க்கையும் பயனற்றதாகும். இது வாழ்க்கையின் ஒரு மிக முக்கியமான பாடமாகும். வணக்கம் என்பது மனிதனின் உண்மையான கடமையாகும்.",
    "வாழ்க்கை எனும் பெருங்கடலை நீந்திக் கடக்க முனைவோர், தலையானவனாக இருப்பவனின் அடி தொடர்ந்து செல்லாவிடில் நீந்த முடியாமல் தவிக்க நேரிடும். இவ்வுலக வாழ்க்கையின் பெரும் கடலை நீந்த முயற்சிக்கும் ஒருவர், இறைவனின் பாதத்தைப் பின்பற்றாதவிடத்து, நீந்த முடியாமல் துன்பத்தில் மூழ்க நேரிடும். இறைவனின் அருளே வாழ்க்கைக் கடலைக் கடக்க உதவும் ஒரே தூணாகும். இந்த குறள் வாழ்க்கையின் பயணத்தைப் பற்றி கூறுகிறது. வாழ்க்கை என்பது ஒரு பெரிய கடலாகும். அதைக் கடக்க, இறைவனின் அருள் தேவை. இறைவனின் பாதத்தைத் தொடராதவர்கள், வாழ்க்கையின் கடினங்களைத் தாங்க முடியாமல் துன்பப்படுவார்கள். இது மனித வாழ்க்கையின் ஒரு உண்மையான உண்மையாகும்.",
    # 11-20 meanings - Elaborated
    "மழை பெய்வதனாலேதான் உலக உயிர்கள் வாழ்கின்றன. ஆதலால், மழையே உயிர்களுக்கு அமிழ்தம் என்று உணரத்தகும். உரிய காலத்தில் இடைவிடாது மழை பெய்வதால்தான் உலகம் நிலைபெற்று வருகிறது. அதனால் மழையே அமிழ்தம் எனலாம். இந்த குறள் மழையின் முக்கியத்துவத்தை எடுத்துரைக்கிறது. மழை இல்லாவிடில் உலகில் உயிர்கள் வாழ முடியாது. மழை என்பது உயிர்களுக்கு அமிழ்தம் போன்றது. இது இயற்கையின் மிக முக்கியமான அம்சங்களில் ஒன்றாகும். மழையின் பயனை நாம் எப்போதும் நினைவில் கொள்ள வேண்டும்.",
    "உண்பவர்க்குத் தகுந்த பொருள்களை விளைவித்துத் தந்து அவற்றைப் பருகுவார்க்குத் தானும் ஓர் உணவாக விளங்குவதும் மழையே ஆகும். நல்ல உணவுகளைச் சமைக்கவும், சமைக்கப்பட்ட உணவுகளை உண்பவர்க்கு இன்னுமோர் உணவாகவும் பயன்படுவது மழையே. இந்த குறள் மழையின் பல்வேறு பயன்களைக் கூறுகிறது. மழை நீர் விளைச்சலுக்கு உதவுகிறது, அத்துடன் அது நேரடியாக உணவாகவும் பயன்படுகிறது. மழை என்பது மனித வாழ்க்கைக்கு மிக முக்கியமான ஒரு பொருளாகும். இதை நாம் முழுமையாக பயன்படுத்த வேண்டும்.",
    "மழை காலத்தால் பெய்யாது பொய்க்குமானால், கடலால் சூழப்பட்டுள்ள இப்பரந்த உலகினுள் பசி நிலைபெற்று உயிர்களை வாட்டும். உரிய காலத்தே மழை பெய்யாது பொய்க்குமானால், கடல் சூழ்ந்த இப்பேருலகத்தில் வாழும் உயிர்களைப் பசி வருத்தும். இந்த குறள் மழையின் இன்றியமையாமையை எடுத்துரைக்கிறது. மழை பெய்யாது போனால், உலகம் முழுவதும் பசி பிடிக்கும். இது ஒரு மிகவும் கடுமையான சூழ்நிலையாகும். மழையின் முக்கியத்துவத்தை நாம் புரிந்து கொள்ள வேண்டும். மழை இல்லாவிடில் உலகில் வாழ்க்கை சாத்தியமற்றது.",
    "மழை என்னும் வருவாயின் வளம் குறைந்ததனால், பயிர் செய்யும் உழவரும் ஏரால் உழுதலைச் செய்யமாட்டார்கள். மழை என்னும் வருவாய் தன் வளத்தில் குறைந்தால், உழவர் ஏரால் உழவு செய்யமாட்டார். இந்த குறள் விவசாயத்திற்கும் மழைக்கும் உள்ள தொடர்பை எடுத்துரைக்கிறது. மழை இல்லாவிடில் விவசாயம் சாத்தியமற்றது. உழவர் மழையை எதிர்பார்த்தே தங்கள் வேலையைச் செய்கிறார்கள். மழையின் முக்கியத்துவத்தை இது காட்டுகிறது. விவசாயம் என்பது மழையின் அருளைப் பொறுத்தது.",
    "காலத்தால் பெய்யாது உலகில் வாழும் உயிர்களைக் கெடுப்பதும் மழை. அப்படி கெட்டவற்றைப் பெய்து வாழச் செய்வதும் மழையே ஆகும். பெய்யாமல் மக்களைக் கெடுப்பதும், பெய்து கெட்டவரைத் திருத்துவதும் எல்லாமே மழைதான். இந்த குறள் மழையின் இரட்டைப் பண்பைக் கூறுகிறது. மழை பெய்யாது போனால் உயிர்கள் கெடும். மழை பெய்தால் கெட்டவை மீண்டும் செழிக்கும். இது இயற்கையின் சமநிலையைக் காட்டுகிறது. மழை என்பது வாழ்க்கைக்கு ஒரு காவலனாகவும், நண்பனாகவும் இருக்கிறது.",
    "வானிலிருந்து மழைத்துளி வீழ்ந்தால் அல்லாமல், உலகில் பசும்புல்லின் தலையைக் காண்பதுங்கூட அருமையாகிவிடும். மேகத்திலிருந்து மழைத்துளி விழாது போனால், பசும்புல்லின் நுனியைக்கூட இங்கே காண்பது அரிதாகிவிடும். இந்த குறள் மழையின் தேவையை மிகத் தெளிவாகக் காட்டுகிறது. மழை இல்லாவிடில் பசுமையே இருக்காது. புல் மற்றும் மரங்கள் எல்லாம் வறண்டு போகும். இது மழையின் முக்கியத்துவத்தை எடுத்துரைக்கிறது. மழை என்பது இயற்கையின் உயிர் நாடி போன்றது.",
    "மேகமானது கடல் நீரை முகந்து சென்று மீண்டும் மழையாகப் பெய்யாவிட்டால், அப்பெரிய கடலும் தன் வளமையில் குறைந்து போகும். பெய்யும் இயல்பிலிருந்து மாறி மேகம் பெய்யாது போனால், நீண்ட கடல் கூட வற்றிப் போகும். இந்த குறள் இயற்கையின் சுழற்சியைப் பற்றி கூறுகிறது. கடல் நீர் மேகமாக மாறி, மழையாகப் பெய்து மீண்டும் கடலுக்கு வருகிறது. இந்த சுழற்சி இல்லாவிடில், கடல் கூட வற்றிப் போகும். இது இயற்கையின் நுணுக்கமான அமைப்பைக் காட்டுகிறது. மழை என்பது இயற்கையின் வாழ்க்கை சுழற்சியின் ஒரு முக்கிய பகுதியாகும்.",
    "மழையானது முறையாகப் பெய்யாவிட்டால், உலகத்திலே வானோர்க்காக நடத்தப்படும் திருவிழாக்களும் பூசனைகளும் நடைபெறமாட்டா. மழை பொய்த்துப் போனால் தெய்வத்திற்குத் தினமும் நடக்கும் பூசனையும் நடக்காது, ஆண்டுதோறும் கொண்டாடப்படும் திருவிழாவும் நடைபெறாது. இந்த குறள் மழையின் சமூக முக்கியத்துவத்தை எடுத்துரைக்கிறது. மழை பெய்யாது போனால், மக்களுக்கு உணவு இல்லாமல் போகும். அப்போது திருவிழாக்கள் மற்றும் வழிபாடுகள் நடக்க முடியாது. இது மழையின் பல்முகப்பான பயனைக் காட்டுகிறது. மழை என்பது சமூக வாழ்க்கையின் அடித்தளமாகும்.",
    "மழை பெய்து உதவாவிட்டால், இந்தப் பரந்த உலகத்திலே பிறருக்காகச் செய்யப்படும் தானமும், தனக்காக மேற்கொள்ளும் தவமும் இரண்டுமே நிலையாமற் போய்விடும். மழை பொய்த்துப் போனால், விரிந்த இவ்வுலகத்தில் பிறர்க்குத் தரும் தானம் இராது, தன்னை உயர்த்தும் தவமும் இராது. இந்த குறள் மழையின் தர்ம முக்கியத்துவத்தை எடுத்துரைக்கிறது. மழை இல்லாவிடில், மக்களுக்கு உணவு இல்லாமல் போகும். அப்போது தானம் செய்யவும் முடியாது, தவம் செய்யவும் முடியாது. இது மழையின் ஆன்மீக முக்கியத்துவத்தைக் காட்டுகிறது. மழை என்பது தர்மத்தின் அடித்தளமாகும்.",
    "நீர் இல்லாமல் எத்தகையோருக்கும் உலக வாழ்க்கை அமையாது என்றால், மழை இல்லாமல் ஒழுக்கமும் நிலைபெறாது. எப்படிப்பட்டவர்க்கும் நீர் இல்லாமல் உலக வாழ்க்கை நடைபெறாது என்றால், மழை இல்லையானால் ஒழுக்கமும் நிலைபெறாமல் போகும். இந்த குறள் மழையின் முழுமையான முக்கியத்துவத்தை எடுத்துரைக்கிறது. மழை இல்லாவிடில் வாழ்க்கை மட்டுமல்ல, ஒழுக்கமும் நிலைபெறாது. இது மழையின் முழுமையான பயனைக் காட்டுகிறது. மழை என்பது வாழ்க்கையின் ஒவ்வொரு அம்சத்திற்கும் தேவையான ஒன்றாகும். மழையின் முக்கியத்துவத்தை நாம் எப்போதும் பாராட்ட வேண்டும்.",
    # 21-30 meanings - Elaborated
    "ஒழுக்கத்தில் நிலையாக நின்று, பற்றுகளை விட்டவர்களின் பெருமையைப் போற்றிச் சிறப்பித்துச் சொல்வதே நூல்களின் துணிபு. ஒழுக்கத்தில் நிலைத்து நின்று பற்று விட்டவர்களின் பெருமையைச் சிறந்ததாக போற்றி கூறுவதே நூல்களின் துணிவாகும். இந்த குறள் ஒழுக்கமுடையவர்களின் மதிப்பை எடுத்துரைக்கிறது. நூல்கள் எப்போதும் ஒழுக்கமுடையவர்களின் பெருமையைப் பாராட்டுகின்றன. ஒழுக்கம் என்பது வாழ்க்கையின் மிக முக்கியமான குணமாகும். இத்தகையோரின் பெருமையை நாம் புரிந்து கொள்ள வேண்டும். ஒழுக்கத்தில் நிலைத்து நிற்பவர்கள் எப்போதும் மதிக்கப்படுகிறார்கள். அவர்களின் வாழ்க்கை ஒரு முன்மாதிரியாக இருக்கிறது. உண்மையான ஒழுக்கம் என்பது வெறும் வார்த்தைகளல்ல, செயல்களில் வெளிப்படுகிறது. இத்தகையோரின் பெருமையை உலகம் முழுவதும் போற்றுகிறது. நூல்களில் இத்தகையோரின் பெயர்கள் எப்போதும் நினைவில் வைக்கப்படுகின்றன.",
    "பற்றுகளை விட்டவரின் பெருமையை அளந்து சொல்வதானால் உலகில் இதுவரை இறந்தவர்களைக் கணக்கெடுத்தாற் போன்றதாகும். பற்றுக்களைத் துறந்தவர்களின் பெருமையை அளந்து கூறுதல், உலகத்தில் இதுவரை பிறந்து இறந்தவர்களை கணக்கிடுவதைப்போன்றது. இந்த குறள் துறவிகளின் பெருமையின் அளவை எடுத்துரைக்கிறது. பற்றுகளை விட்டவர்களின் பெருமை எண்ணியற்கரியது. இது ஒரு மிக உயர்ந்த நிலையாகும். உண்மையான துறவிகளின் பெருமையை நாம் முழுமையாக புரிந்து கொள்ள முடியாது. பற்றுகளிலிருந்து விடுபட்டவர்கள் எப்போதும் சுதந்திரமாக வாழ்கிறார்கள். அவர்களின் மனம் எப்போதும் அமைதியாக இருக்கிறது. பற்றுகள் இல்லாத நிலையில், அவர்கள் உலகின் எந்தவொரு துன்பத்திலிருந்தும் விடுபடுகிறார்கள். இத்தகையோரின் பெருமையை அளவிடுவது என்பது முடியாத ஒன்றாகும். உலகில் இறந்த மக்களின் எண்ணிக்கையைக் கணக்கிட முடியாதது போல, துறந்தவர்களின் பெருமையையும் கணக்கிட முடியாது.",
    "இம்மை மறுமை என்னும் இரண்டின் கூறுகளைத் தெரிந்து இவ்வுலகில் அறநெறியை மேற்கொண்டவரின் பெருமையே உயர்ந்ததாகும். பிறப்பு வீடு என்பன போல் இரண்டிரண்டாக உள்ளவைகளின் கூறுபாடுகளை ஆராய்ந்தறிந்து அறத்தை மேற்கொண்டவரின் பெருமையே உலகத்தில் உயர்ந்தது. இந்த குறள் அறத்தின் முக்கியத்துவத்தை எடுத்துரைக்கிறது. இம்மை மற்றும் மறுமையின் தன்மையை அறிந்து, அறத்தில் நிற்பவரின் பெருமையே உலகில் மிக உயர்ந்தது. இது வாழ்க்கையின் ஒரு முக்கிய உண்மையாகும். அறத்தில் நிற்பவரே உண்மையான பெருமைக்குரியவர். இம்மையில் நன்மையும், மறுமையில் பேறும் பெற, அறத்தில் நிற்பது தேவை. அறத்தை மேற்கொள்பவர் எப்போதும் மதிக்கப்படுகிறார். அவரின் வாழ்க்கை ஒரு முன்மாதிரியாக இருக்கிறது. உலகில் உள்ள எல்லா பெருமையும் அறத்தில் நிற்பவருக்கே உரியது. இது மனித வாழ்க்கையின் மிக உயர்ந்த நிலையாகும்.",
    "அறிவு என்னும் அங்குசத்தால் ஐம்பொறிகளாகிய யானைகளை அடக்கிக் காப்பவன் எவனோ, அவனே மேலான வீட்டுலகிற்கு ஒரு வித்து ஆவான். அறிவு என்னும் கருவியினால் ஐம்பொறிகளாகிய யானைகளை அடக்கி காக்க வல்லவன், மேலான வீட்டிற்கு விதை போன்றவன். இந்த குறள் அறிவின் பயனை எடுத்துரைக்கிறது. அறிவு என்னும் கருவியால் ஐம்பொறிகளை அடக்கி ஆள்பவனே மேலான வாழ்க்கைக்கு வித்தாகிறான். இது வாழ்க்கையின் ஒரு முக்கிய பாடமாகும். அறிவோடு ஒழுக்கத்தை இணைத்தவனே உண்மையான வெற்றியாளனாகிறான். ஐம்பொறிகள் என்பது மனிதனின் இயற்கையான விருப்பங்கள். அவற்றை அறிவினால் கட்டுப்படுத்துவது மிகவும் கடினமான ஒன்று. அதைச் சாதித்தவனே உண்மையான மேன்மக்களில் ஒருவன். அத்தகையவன் மேலான வாழ்க்கைக்கு வித்தாகிறான். அவனின் வாழ்க்கை ஒரு முன்மாதிரியாக இருக்கிறது. அறிவே மனிதனின் உண்மையான சக்தி என்பதை இது காட்டுகிறது.",
    "ஐம்பொறி வழியாக எழுகின்ற ஆசைகளை அவித்தவனுடைய வலிமைக்கு அகன்ற வானுலகோர் கோமானாகிய இந்திரனே போதிய சான்று. ஐந்து புலன்களாலாகும் ஆசைகளை ஒழித்தவனுடைய வல்லமைக்கு, வானுலகத்தாரின் தலைவனாகிய இந்திரனே போதுமான சான்று ஆவான். இந்த குறள் ஆசைகளை அடக்குவதன் முக்கியத்துவத்தை எடுத்துரைக்கிறது. ஐம்பொறிகளின் ஆசைகளை அடக்கியவனின் ஆற்றல், இந்திரனின் மேன்மையைப் போன்றது. இது ஒரு மிக உயர்ந்த சாதனையாகும். ஆசைகளை அடக்குவதே உண்மையான வலிமையின் அடையாளமாகும். இந்திரன் என்பவன் தேவர்களின் தலைவன். அவன் ஐம்பொறிகளின் ஆசைகளை அடக்கியதால் தான் அத்தகைய உயர்ந்த நிலையைப் பெற்றான். அதைப் போலவே, ஐம்பொறிகளின் ஆசைகளை அடக்கிய மனிதனும் மிக உயர்ந்த நிலையை அடைகிறான். இது மனித வாழ்க்கையின் மிக முக்கியமான பாடமாகும். ஆசைகளை அடக்குவதே உண்மையான வலிமையின் அடையாளமாகும்.",
    "செய்வதற்கு அருமையானவற்றைச் செய்பவர் பெரியோர். சிறியோர், செய்வதற்கு அரியவற்றைச் செய்யமாட்டாதவர் ஆவர். பிறர் செய்வதற்கு முடியாத செயல்களைச் செய்பவரே மேன்மக்கள். செய்ய முடியாதவரோ சிறியவரே. இந்த குறள் பெரியோர் மற்றும் சிறியோரின் வேறுபாட்டை எடுத்துரைக்கிறது. அருமையான செயல்களைச் செய்பவரே உண்மையான பெரியோர். இது வாழ்க்கையின் ஒரு முக்கிய உண்மையாகும். செயற்கரிய செயல்களைச் செய்வதே ஒருவரின் மேன்மையைக் காட்டுகிறது. எளிதான செயல்களைச் செய்வது எவரும் செய்யக்கூடியது. ஆனால் அருமையான செயல்களைச் செய்வது மேன்மக்களின் இயல்பு. இத்தகையோர் எப்போதும் மதிக்கப்படுகிறார்கள். அவர்களின் செயல்கள் வரலாற்றில் பதிவாகின்றன. உண்மையான பெருமை என்பது செயற்கரிய செயல்களைச் செய்வதில்தான் உள்ளது. இது மனித வாழ்க்கையின் ஒரு முக்கிய உண்மையாகும்.",
    "சுவை, ஒளி, ஊறு, ஓசை, நாற்றம் என்று கூறப்படுகின்ற ஐந்தின் வகைகளையும் தெரிந்து நடப்பவனிடமே உலகம் உள்ளது. சுவை, ஒளி, ஊறு, ஓசை, நாற்றம் என்று சொல்லப்படும் ஐந்தின் வகைகளையும் ஆராய்ந்து அறிய வல்லவனுடைய அறிவில் உள்ளது உலகம். இந்த குறள் ஐம்புலன்களின் முக்கியத்துவத்தை எடுத்துரைக்கிறது. ஐம்புலன்களின் இயல்பை அறிந்து அவற்றை அடக்கியாள்பவனிடமே உலகம் உள்ளது. இது ஒரு மிக உயர்ந்த அறிவாகும். ஐம்புலன்களைக் கட்டுப்படுத்துபவனே உண்மையான மேன்மக்களில் ஒருவனாகிறான். ஐம்புலன்கள் என்பது சுவை, ஒளி, ஊறு, ஓசை, நாற்றம் ஆகியன. இவற்றின் இயல்பை அறிந்து அவற்றைக் கட்டுப்படுத்துவது மிகவும் முக்கியமான ஒன்று. இத்தகையவனின் அறிவில் முழு உலகமும் அடங்கியிருக்கிறது. அவனே உண்மையான ஞானியாகிறான். இது மனித வாழ்க்கையின் மிக உயர்ந்த அறிவாகும். ஐம்புலன்களை அறிந்து கட்டுப்படுத்துவதே உண்மையான வெற்றியின் அடையாளமாகும்.",
    "நிறைவான மொழிகளையே சொல்லும் சான்றோரின் பெருமையை, உலகத்தில் நிலையாக விளங்கும் அவர்களுடைய மறைமொழிகளே காட்டிவிடும். பயன் நிறைந்த மொழிகளில் வல்ல சான்றோரின் பெருமையை, உலகத்தில் அழியாமல் விளங்கும் அவர்களுடைய மறைமொழிகளே காட்டிவிடும். இந்த குறள் சான்றோரின் நிலைத்தன்மையை எடுத்துரைக்கிறது. சான்றோர் சொன்ன மொழிகள் எப்போதும் உலகில் நிலைத்து நிற்கும். அவர்களின் நூல்களே அவர்களின் பெருமையைக் காட்டுகின்றன. இது வாழ்க்கையின் ஒரு முக்கிய உண்மையாகும். நிறைவான மொழி என்பது பயனுள்ள மொழி. அத்தகைய மொழிகளைச் சொல்லும் சான்றோரின் பெருமையை அவர்களின் நூல்களே எடுத்துரைக்கின்றன. அவர்களின் மறைமொழிகள் எப்போதும் உலகில் நிலைத்து நிற்கும். இத்தகையோரின் பெருமையை அளவிடுவது முடியாத ஒன்றாகும். சான்றோரின் மொழிகள் எப்போதும் மக்களுக்கு வழிகாட்டுகின்றன. அவர்களின் நூல்கள் மனித வாழ்க்கையின் மிக முக்கியமான கருவிகளாக இருக்கின்றன.",
    "நல்ல குணம் என்கின்ற குன்றின்மேல் ஏறி நின்ற சான்றோரால், சினத்தை ஒரு கணமேனும் பேணிக் காத்தல் அருமையாகும். நல்ல பண்புகளாகிய மலையின்மேல் ஏறி நின்ற பெரியோர், ஒரு கணப்பொழுதே சினம் கொள்வார் ஆயினும் அதிலிருந்து ஒருவரைக் காத்தல் அரிதாகும். இந்த குறள் குணமுடையவர்களின் சினத்தின் மேன்மையை எடுத்துரைக்கிறது. குணமுடையவர்கள் சினம் கொண்டாலும், அது கணமே நிற்கும். இது அவர்களின் உயர்ந்த பண்பாகும். நற்குணமுடையவர்களின் சினம் எப்போதும் நீண்டநேரம் நிற்காது. குணமுடையவர்கள் எப்போதும் அமைதியாகவே இருக்கிறார்கள். அவர்கள் சினம் கொண்டாலும், அது மிகவும் குறுகிய காலத்திற்கு மட்டுமே நிலைத்திருக்கும். இது அவர்களின் உயர்ந்த பண்பின் அடையாளமாகும். நற்குணம் என்பது ஒரு மலையைப் போன்றது. அதன் மேல் ஏறி நின்றவர்கள் எப்போதும் உயர்ந்த நிலையில் இருக்கிறார்கள். அவர்களின் சினம் கூட மிகவும் சிறியது. இத்தகையோரின் பண்பை மற்றவர்கள் பின்பற்ற வேண்டும்.",
    "எவ்வகைப்பட்ட உயிருக்கும் செவ்வையான அருளை மேற்கொண்டு நடப்பதனால், அந்தணர் எனப்படுவோரே அறவோர் ஆவர். எல்லா உயிர்களிடத்திலும் செம்மையான அருளை மேற்கொண்டு ஒழுகுவதால், அறவோரே அந்தணர் எனப்படுவோர் ஆவர். இந்த குறள் அருளின் முக்கியத்துவத்தை எடுத்துரைக்கிறது. எல்லா உயிர்களிடத்திலும் அருள் கொண்டு நடப்பவரே உண்மையான அந்தணர். இது வாழ்க்கையின் ஒரு மிக முக்கியமான பாடமாகும். அருளுடன் வாழ்பவரே உண்மையான சான்றோர் ஆவர். அருள் என்பது எல்லா உயிர்களுக்கும் காட்டப்பட வேண்டிய ஒரு குணம். இத்தகைய அருளைக் கொண்டவர்களே உண்மையான அந்தணர். அவர்கள் எப்போதும் மக்களுக்கு பயனுள்ளவர்களாக இருக்கிறார்கள். அவர்களின் வாழ்க்கை ஒரு முன்மாதிரியாக இருக்கிறது. அருள் கொண்டு வாழ்பவரே உண்மையான சான்றோர் ஆவர். இது மனித வாழ்க்கையின் மிக உயர்ந்த நிலையாகும். அருளே மனிதனின் மிக முக்கியமான குணங்களில் ஒன்றாகும்.",
]

# Initialize TTS model
print("Loading TTS model...")
model_name = config.TTS_MODEL_NAME
tokenizer = AutoTokenizer.from_pretrained(model_name)
model = VitsModel.from_pretrained(model_name).to(config.TTS_DEVICE)
print("✓ TTS model loaded")


# Function to get athirakaram (first word) from Thirukural
def get_athirakaram(text):
    """Extract the first word (athirakaram) from Thirukural verse"""
    # Remove period if present
    text = text.rstrip('.')
    words = text.split()
    if words:
        return words[0]  # Return first word
    return ""

# Function to split Tirukural into 4 words + 3 words
def split_tirukural(text):
    """Split Tirukural verse into two lines: first 4 words, then remaining words
    Properly handles Tamil text by preserving word boundaries and character order"""
    # Remove period if present
    text = text.rstrip('.').strip()
    
    # Split by spaces - Tamil uses spaces between words
    words = text.split()
    
    # Filter out empty strings
    words = [w for w in words if w.strip()]
    
    if len(words) >= 7:
        # First 4 words for line 1, remaining for line 2
        line1 = ' '.join(words[:4])
        line2 = ' '.join(words[4:])
    elif len(words) > 0:
        # If less than 7 words, split roughly in half
        mid = (len(words) + 1) // 2  # Add 1 to ensure second line gets any extra word
        line1 = ' '.join(words[:mid])
        line2 = ' '.join(words[mid:])
    else:
        # Fallback if no words
        line1 = text[:len(text)//2] if text else ""
        line2 = text[len(text)//2:] if text else ""
    
    # Ensure no leading/trailing spaces
    line1 = line1.strip()
    line2 = line2.strip()
    
    return line1, line2

# Function to generate audio from text with emotion
def generate_audio(text, output_path, meaning=""):
    """Generate audio file from Tamil text using TTS with emotional expression"""
    # Combine verse and meaning if provided
    if meaning:
        full_text = f"{text} இதன் பொருள் என்ன என்றால், {meaning}"
    else:
        full_text = text
    
    print(f"\nGenerating audio for: {text}")

    if meaning:
        print(f"Including meaning: {meaning[:50]}...")
    
    inputs = tokenizer(full_text, return_tensors="pt")
    
    with torch.no_grad():
        output = model(**inputs).waveform  # tensor shape [1, samples]
    

    # Apply emotion adjustments (etram - uplifting, irkam - intensity)
    # Convert to numpy for processing
    audio_data = output.cpu().numpy()[0].astype(np.float32)
    
    # Add slight pitch variation and emphasis for emotional expression
    # Normalize audio
    max_val = np.max(np.abs(audio_data))
    if max_val > 0:
        audio_data = audio_data / max_val
    
    # Apply slight pitch shift and dynamics for emotion
    # Create a smooth envelope for emphasis
    length = len(audio_data)
    envelope = np.ones(length)
    
    # Add emphasis at key points (60% and 80% through)
    emphasis_points = [int(length * 0.6), int(length * 0.8)]
    for point in emphasis_points:
        window = int(length * 0.1)
        start = max(0, point - window)
        end = min(length, point + window)
        envelope[start:end] = np.linspace(1.0, 1.15, end - start)
    
    # Apply envelope
    audio_data = audio_data * envelope
    
    # Normalize again
    max_val = np.max(np.abs(audio_data))
    if max_val > 0:
        audio_data = audio_data / max_val
    
    # Convert back to int16 for wavfile
    audio_int16 = (audio_data * 32767).astype(np.int16)
    
    wavfile.write(output_path, model.config.sampling_rate, audio_int16)
    print(f"✓ Audio saved: {output_path}")
    return output_path

# Global font cache
_font_cache = None

# Function to load Tamil font
def load_tamil_font(size, verbose=False):
    """Load Tamil font with fallbacks (cached)"""
    global _font_cache
    if _font_cache is not None:
        return _font_cache
    
    font = None
    

    # Try modern Tamil fonts first
    modern_tamil_fonts = [
        "C:/Windows/Fonts/muktamalar.ttf",  # Mukta Malar - modern
        "C:/Windows/Fonts/NotoSansTamil-Regular.ttf",  # Noto Sans Tamil
        "C:/Windows/Fonts/NotoSansTamil-Bold.ttf",
        "C:/Windows/Fonts/catamaran.ttf",  # Catamaran - modern
        "C:/Windows/Fonts/Pothana2000.ttf",  # Modern Tamil font
        "C:/Windows/Fonts/Vani.ttf",  # Modern alternative
    ]
    
    # Try Windows Tamil fonts (fallback)
    windows_tamil_fonts = [
        "C:/Windows/Fonts/nirmala.ttf",
        "C:/Windows/Fonts/nirmalab.ttf",
        "C:/Windows/Fonts/latha.ttf",
        "C:/Windows/Fonts/gautami.ttf",
    ]
    

    # Try modern fonts first
    for win_font in modern_tamil_fonts:
        try:
            if os.path.exists(win_font):
                font = ImageFont.truetype(win_font, size)
                if verbose:
                    print(f"✓ Loaded modern font: {os.path.basename(win_font)}")
                _font_cache = font
                return font
        except:
            continue
    
    # Fallback to standard Windows Tamil fonts
    for win_font in windows_tamil_fonts:
        try:
            if os.path.exists(win_font):
                font = ImageFont.truetype(win_font, size)
                if verbose:
                    print(f"✓ Loaded font: {os.path.basename(win_font)}")
                _font_cache = font
                return font
        except:
            continue
    
    # Try custom font
    try:
        if os.path.exists(font_path):
            font = ImageFont.truetype(font_path, size)
            if verbose:
                print(f"✓ Loaded custom font")
            _font_cache = font
            return font
    except:
        pass
    
    # Fallback to default
    if verbose:
        print("⚠ Using default font")
    font = ImageFont.load_default()
    _font_cache = font
    return font

# Function to create video from text and audio

def create_video(text, audio_path, output_video_path, kural_number=1):
    """Create video with text overlay and audio"""
    print(f"\nCreating video: {output_video_path}")
    
    # Load audio
    audio_clip = AudioFileClip(audio_path)
    
    # Open background image
    img = Image.open(image_path).convert("RGBA")
    draw = ImageDraw.Draw(img)
    
    # Load font (from cache)
    font = load_tamil_font(font_size)
    

    # Get adhigaram name for this kural
    adhigaram = get_adhigaram_name(kural_number)
    
    # Split text into two lines (4 words + 3 words)
    line1, line2 = split_tirukural(text)
    
    # Calculate positions for adhigaram at top
    top_margin = 50  # Margin from top (moved up)
    if adhigaram:
        adhigaram_font_size = font_size + 4  # Slightly larger font for adhigaram
        adhigaram_font = load_tamil_font(adhigaram_font_size)
        # Use textbbox with explicit direction and language for accurate Tamil measurement
        try:
            # Try with language and direction parameters (Pillow 8.0+)
            bbox_adhigaram = draw.textbbox((0, 0), adhigaram, font=adhigaram_font, direction="ltr", language="ta")
            use_language_params_adhigaram = True
        except (TypeError, KeyError):
            # Fallback for older Pillow versions or when libraqm is not available
            bbox_adhigaram = draw.textbbox((0, 0), adhigaram, font=adhigaram_font)
            use_language_params_adhigaram = False
        
        adhigaram_width = bbox_adhigaram[2] - bbox_adhigaram[0]
        adhigaram_height = bbox_adhigaram[3] - bbox_adhigaram[1]
        adhigaram_x = (img.width - adhigaram_width) // 2  # Center horizontally
        adhigaram_y = top_margin
        
        # Add padding for white background box
        padding_x = 20  # Horizontal padding
        padding_y = 10  # Vertical padding
        
        # Draw white background rectangle
        bg_x1 = adhigaram_x - padding_x
        bg_y1 = adhigaram_y - padding_y
        bg_x2 = adhigaram_x + adhigaram_width + padding_x
        bg_y2 = adhigaram_y + adhigaram_height + padding_y
        draw.rectangle([bg_x1, bg_y1, bg_x2, bg_y2], fill="white")
        
        # Draw adhigaram text on white background - black text
        # Explicitly set direction and language for proper Tamil rendering (if supported)
        if use_language_params_adhigaram:
            draw.text((adhigaram_x, adhigaram_y), adhigaram, font=adhigaram_font, fill="black", direction="ltr", language="ta")
        else:
            # Fallback for older Pillow versions
            draw.text((adhigaram_x, adhigaram_y), adhigaram, font=adhigaram_font, fill="black")
    
    # Calculate positions for both lines (verse text)
    # Use textbbox for accurate measurement of Tamil text with proper language support
    try:
        # Try with language and direction parameters (Pillow 8.0+)
        bbox1 = draw.textbbox((0, 0), line1, font=font, direction="ltr", language="ta")
        bbox2 = draw.textbbox((0, 0), line2, font=font, direction="ltr", language="ta")
        use_language_params = True
    except (TypeError, KeyError):
        # Fallback for older Pillow versions or when libraqm is not available
        bbox1 = draw.textbbox((0, 0), line1, font=font)
        bbox2 = draw.textbbox((0, 0), line2, font=font)
        use_language_params = False
    
    text_width1 = bbox1[2] - bbox1[0]
    text_width2 = bbox2[2] - bbox2[0]
    text_height1 = bbox1[3] - bbox1[1]
    text_height2 = bbox2[3] - bbox2[1]
    
    # Calculate vertical spacing
    line_spacing = text_height1 * 0.3  # 30% spacing between lines
    
    # Left-align both lines with margin from left edge
    left_margin = 50  # 50px margin from left
    x1 = left_margin
    x2 = left_margin
    
    # Position higher up from bottom (moved up)
    y2 = img.height - text_height2 - 150  # Second line (moved higher)
    y1 = y2 - text_height1 - line_spacing  # First line (above)
    
    # Draw both lines - black text with white stroke
    # Explicitly set direction and language for proper Tamil rendering (if supported)
    if use_language_params:
        draw.text((x1, y1), line1, font=font, fill="black", stroke_width=2, stroke_fill="white", direction="ltr", language="ta")
        draw.text((x2, y2), line2, font=font, fill="black", stroke_width=2, stroke_fill="white", direction="ltr", language="ta")
    else:
        # Fallback for older Pillow versions
        draw.text((x1, y1), line1, font=font, fill="black", stroke_width=2, stroke_fill="white")
        draw.text((x2, y2), line2, font=font, fill="black", stroke_width=2, stroke_fill="white")
    
    # Save temporary image
    temp_image_path = os.path.join(config.TEMP_DIR, "text_image.png")
    img.save(temp_image_path)
    

    # Create video - let audio complete fully, extend with silence if needed to reach minimum 30 seconds
    min_duration = config.MIN_VIDEO_DURATION
    audio_duration = audio_clip.duration
    
    # Process main audio - complete sentence fully, extend if shorter than 30 seconds
    silence_clip = None
    extended_audio = None
    if audio_duration < min_duration:
        # Extend audio with silence to reach minimum 30 seconds
        silence_duration = min_duration - audio_duration
        # Create silent audio clip matching the audio format
        sampling_rate = int(audio_clip.fps)
        channels = 2 if audio_clip.nchannels == 2 else 1
        silent_samples = int(silence_duration * sampling_rate)
        if channels == 2:
            silent_array = np.zeros((silent_samples, 2), dtype=np.float32)
        else:
            silent_array = np.zeros(silent_samples, dtype=np.float32)
        silence_clip = AudioArrayClip(silent_array, fps=sampling_rate)
        # Use with_start instead of set_start
        silence_with_start = silence_clip.with_start(audio_duration)
        extended_audio = CompositeAudioClip([audio_clip, silence_with_start])
        main_audio = extended_audio
        target_duration = min_duration  # Use minimum duration (30 seconds)
    else:
        # Audio is 30 seconds or longer - use full audio duration (complete sentence)
        main_audio = audio_clip
        target_duration = audio_duration  # Use actual audio duration (may be longer than 30 seconds)
    
    # Add BGM if configured
    bgm_clip = None
    bgm_looped = None
    if bgm_path and os.path.exists(bgm_path):
        try:
            print(f"  Adding BGM: {bgm_path}")
            bgm_clip = AudioFileClip(bgm_path)
            # Loop BGM to match target duration (full audio duration)
            bgm_duration = bgm_clip.duration
            if bgm_duration < target_duration:
                # Loop BGM to fill the full duration using AudioLoop effect
                from moviepy.audio.fx.AudioLoop import AudioLoop
                bgm_looped = bgm_clip.with_effects([AudioLoop(duration=target_duration)])
            else:
                # Use full BGM if it's longer, or trim to match target duration
                bgm_looped = bgm_clip[:target_duration]
            
            # Lower BGM volume
            bgm_looped = bgm_looped.with_effects([MultiplyVolume(bgm_volume)])
            
            # Mix TTS audio with BGM
            final_audio = CompositeAudioClip([bgm_looped, main_audio])
            
        except Exception as e:
            print(f"  ⚠ Warning: Could not add BGM: {e}")
            final_audio = main_audio
            if bgm_clip:
                bgm_clip.close()
            bgm_clip = None
            bgm_looped = None
    else:
        final_audio = main_audio
    
    # Create image clip to match full audio duration (complete sentence)
    image_clip = ImageClip(temp_image_path).with_duration(target_duration)
    video = image_clip.with_audio(final_audio)
    
    video.write_videofile(output_video_path, fps=24)
    
    # Cleanup - close clips to free resources

    # Note: Close in order and avoid comparing clips (can cause errors if already closed)
    try:
        video.close()
    except:
        pass
    
    try:
        image_clip.close()
    except:
        pass
    
    # Close final_audio if it's a CompositeAudioClip (it contains other clips)
    try:
        if isinstance(final_audio, CompositeAudioClipType):
            final_audio.close()
    except:
        pass
    
    # Close extended audio if it exists (it's also a composite)
    if extended_audio is not None:
        try:
            extended_audio.close()
        except:
            pass
    
    # Close silence clip if it exists
    if silence_clip is not None:
        try:
            silence_clip.close()
        except:
            pass
    
    # Close BGM clips
    if bgm_looped is not None:
        try:
            bgm_looped.close()
        except:
            pass
    if bgm_clip is not None:
        try:
            bgm_clip.close()
        except:
            pass
    
    # Close main audio clip last (it may have been used in composites)
    try:
        audio_clip.close()
    except:
        pass
    
    if os.path.exists(temp_image_path):
        os.remove(temp_image_path)
    
    print(f"✓ Video created: {output_video_path}")
    return output_video_path


# YouTube Upload Functions
def get_authenticated_service():
    """Authenticate and return YouTube service"""
    creds = None
    
    # Load existing token if available
    if os.path.exists(YOUTUBE_TOKEN_FILE):
        with open(YOUTUBE_TOKEN_FILE, 'rb') as token:
            creds = pickle.load(token)
    
    # If there are no valid credentials, request authorization
    if not creds or not creds.valid:
        if creds and creds.expired and creds.refresh_token:
            creds.refresh(Request())
        else:
            if not os.path.exists(YOUTUBE_CLIENT_SECRETS_FILE):
                raise FileNotFoundError(
                    f"OAuth2 client secrets file not found: {YOUTUBE_CLIENT_SECRETS_FILE}\n"
                    "Please download it from Google Cloud Console and save it as 'client_secrets.json'"
                )
            flow = InstalledAppFlow.from_client_secrets_file(
                YOUTUBE_CLIENT_SECRETS_FILE, YOUTUBE_SCOPES)
            creds = flow.run_local_server(port=0)
        
        # Save credentials for next run
        with open(YOUTUBE_TOKEN_FILE, 'wb') as token:
            pickle.dump(creds, token)
    
    return build('youtube', 'v3', credentials=creds)

def calculate_publish_date(video_index, start_date=None, schedule_time="08:00"):
    """
    Calculate the publish date for a video based on its index
    
    Args:
        video_index: Index of the video (1-based)
        start_date: Start date as string (YYYY-MM-DD) or None for tomorrow
        schedule_time: Time in 24-hour format (HH:MM)
    
    Returns:
        RFC 3339 formatted datetime string for YouTube API
    """
    from datetime import datetime, timedelta
    import pytz
    
    # Parse time
    hour, minute = map(int, schedule_time.split(':'))
    
    # Get timezone
    try:
        tz = pytz.timezone(YOUTUBE_TIMEZONE)
    except:
        # Fallback to UTC if timezone not available
        tz = pytz.UTC
    
    # Determine start date
    if start_date:
        try:
            # Parse start date and make it timezone-aware
            start = datetime.strptime(start_date, "%Y-%m-%d")
            start = tz.localize(start.replace(hour=hour, minute=minute, second=0, microsecond=0))
        except:
            # If invalid, use tomorrow
            now = datetime.now(tz)
            start = now + timedelta(days=1)
            start = start.replace(hour=hour, minute=minute, second=0, microsecond=0)
    else:
        # Start from tomorrow at the scheduled time
        now = datetime.now(tz)
        tomorrow = now + timedelta(days=1)
        start = tomorrow.replace(hour=hour, minute=minute, second=0, microsecond=0)
    
    # Calculate publish date (video_index days from start, with video_index 1 being the first day)
    publish_date = start + timedelta(days=video_index - 1)
    
    # Convert to RFC 3339 format (ISO 8601)
    return publish_date.isoformat()

def validate_and_clean_tags(tags):
    """Validate and clean tags for YouTube API"""
    import re
    valid_tags = []
    for tag in tags:
        # Remove spaces and convert to string
        tag = str(tag).strip().replace(' ', '')
        # Remove special characters except alphanumeric, hyphens, underscores
        tag = re.sub(r'[^a-zA-Z0-9_-]', '', tag)
        # Limit to 30 characters (YouTube limit)
        if len(tag) > 30:
            tag = tag[:30]
        # Must be at least 1 character
        if tag and len(tag) > 0:
            valid_tags.append(tag)
    # Limit total tags to 100 (YouTube recommendation, though max is 500)
    return valid_tags[:100]

def upload_to_youtube(video_path, title, description="", tags=None, category_id=None, publish_at=None, default_language=None, default_audio_language=None):
    """
    Upload video to YouTube as Shorts with comprehensive metadata for maximum reach
    
    Args:
        video_path: Path to video file
        title: Video title
        description: Video description
        tags: List of tags
        category_id: Video category (27 = Education - optimal for wisdom/philosophy content)
        publish_at: RFC 3339 formatted datetime string for scheduling (None = publish immediately)
        default_language: Default language code (ta = Tamil)
        default_audio_language: Default audio language code (ta = Tamil)
    
    Returns:
        Video ID if successful, None otherwise
    """
    if not YOUTUBE_UPLOAD_ENABLED:
        print("  YouTube upload is disabled")
        return None
    
    # Use config defaults if not provided
    if category_id is None:
        category_id = config.YOUTUBE_CATEGORY_ID
    if default_language is None:
        default_language = config.YOUTUBE_DEFAULT_LANGUAGE
    if default_audio_language is None:
        default_audio_language = config.YOUTUBE_DEFAULT_AUDIO_LANGUAGE
    
    try:
        youtube = get_authenticated_service()
        
        # Prepare metadata
        # Validate and clean tags
        valid_tags = validate_and_clean_tags(tags) if tags else []
        
        # Debug: print cleaned tags
        print(f"  Using {len(valid_tags)} tags: {valid_tags[:10]}...")
        
        # Prepare status object with all options for better reach
        status = {
            'privacyStatus': YOUTUBE_PRIVACY_STATUS,
            'selfDeclaredMadeForKids': False,
            'madeForKids': False,
            # Enable features for better engagement
            'publicStatsViewable': True
        }
        
        # Add publishAt if scheduling is enabled
        if publish_at:
            status['publishAt'] = publish_at
            print(f"  📅 Scheduled for: {publish_at}")
        
        # Comprehensive snippet with all metadata options
        snippet = {
            'title': title,
            'description': description,
            'tags': valid_tags if valid_tags else None,
            'categoryId': category_id,
            'defaultLanguage': default_language,
            'defaultAudioLanguage': default_audio_language
        }
        
        body = {
            'snippet': snippet,
            'status': status
        }
        
        # Insert video
        media = MediaFileUpload(video_path, chunksize=-1, resumable=True)
        insert_request = youtube.videos().insert(
            part=','.join(body.keys()),
            body=body,
            media_body=media
        )
        
        # Upload video
        print(f"  Uploading to YouTube: {title}")
        response = None
        error = None
        retry = 0
        while response is None:
            try:
                status, response = insert_request.next_chunk()
                if response is not None:
                    if 'id' in response:
                        video_id = response['id']
                        video_url = f"https://www.youtube.com/watch?v={video_id}"
                        print(f"  ✓ Uploaded successfully!")
                        print(f"  📺 Video URL: {video_url}")
                        return video_id
                    else:
                        error = f"Upload failed: {response}"
                        print(f"  ❌ {error}")
                        return None
            except Exception as e:
                if retry < 3:
                    retry += 1
                    print(f"  ⚠ Retry {retry}/3...")
                else:
                    error = str(e)
                    print(f"  ❌ Upload error: {error}")
                    return None
        
    except FileNotFoundError as e:
        print(f"  ⚠ {e}")
        return None
    except Exception as e:
        print(f"  ❌ YouTube upload error: {e}")
        return None
    
    return None

# Main processing loop
def process_sentences():
    """Process all sentences: generate audio and create videos"""
    total = len(sentences)
    
    # Load font once at start
    print("\nLoading font...")
    load_tamil_font(font_size, verbose=True)
    
    print(f"\n{'='*60}")
    print(f"Processing {total} sentence(s)")
    print(f"{'='*60}\n")
    
    for i, sentence in enumerate(sentences, 1):
        print(f"\n[{i}/{total}] Processing: {sentence}")
        print("-" * 60)
        
        # Generate audio filename
        audio_filename = f"audio_{i:03d}.wav"
        audio_path = os.path.join(audio_dir, audio_filename)
        
        # Generate video filename
        video_filename = f"video_{i:03d}.mp4"
        video_path = os.path.join(output_dir, video_filename)
        

        # Get meaning for this verse
        meaning = meanings[i-1] if i <= len(meanings) else ""
        
        # Step 1: Generate audio (with meaning included)
        generate_audio(sentence, audio_path, meaning)
        
        # Step 2: Create video (only verse text, not meaning) - pass kural number for adhigaram
        create_video(sentence, audio_path, video_path, kural_number=i)
        
        # Step 3: Upload to YouTube (if enabled)
        if YOUTUBE_UPLOAD_ENABLED:
            # Create title and description with channel branding - optimized for global reach
            channel_name_english = YOUTUBE_CHANNEL_NAME  # Use the configured channel name
            
            # English translation of the verse for global audience
            english_translations = [
                # 1-10
                "A, as its first of letters, every speech maintains; The 'Primal Deity' is first through all the world's domains.",
                "No fruit have men of all their studied lore, Save they the 'Purely Wise One's' feet adore.",
                "His feet, 'Who o'er the full-blown flower hath past,' who gain In bliss long time shall dwell above this earthly plain.",
                "His foot, 'Whom want affects not, irks not grief,' who gain Shall not, through every time, of any woes complain.",
                "The men, who on the 'King's' true praised delight to dwell, Affects not them the fruit of deeds done ill or well.",
                "Long live they blest, who 've stood in path from falsehood freed; His, 'Who quenched lusts that from the sense-gates five proceed'.",
                "Unless His foot, 'to Whom none can compare,' men gain, 'This hard for mind to find relief from anxious pain.",
                "Unless His feet 'the Sea of Good, the Fair and Bountiful,' men gain, 'This hard the further bank of being's changeful sea to attain.",
                "Before His foot, 'the Eight-fold Excellence,' with unbent head, Who stands, like palsied sense, is to all living functions dead.",
                "They swim the sea of births, the 'Monarch's' foot who gain; None others reach the shore of being's mighty main.",
                # 11-20
                "The world subsists by rain; with rain men gain The nectar-draught that gives their souls delight.",
                "Rain makes the food; rain makes the world to feed; From rain all beings draw their life's supply.",
                "If clouds bring not the rain, then famine wide Spreads o'er the sea-girt world, and kills its life.",
                "When clouds withhold the rain, the farmer's plough Stays from the fields; the world no food enjoys.",
                "Rain ruins those who ruin; on the good It falls, and saves them from misfortune's power.",
                "Unless the heavens drop rain, no grass will grow; Earth's fertile face would barren lie below.",
                "Though ocean vast may circle round the world, Without the rain its waters all would fail.",
                "If heavens deny the rain, no festive day, No worship can be held on earth below.",
                "Should rain from heaven fail, alms and penance both Would vanish from the world, and cease to be.",
                "If water fail, no creature here can live; Without the rain, virtue itself would die.",
                # 21-30
                "Books declare that they who virtue's way have trod, Are peerless: this is virtue's own reward.",
                "As counting all the dead this world has known, So hard to measure those from lust who've flown.",
                "Those who have truly learned the twofold way, In virtue walk, their greatness shines most bright.",
                "He who with wisdom's hook his senses five Controls, becomes a seed for heaven's light.",
                "Indra, heaven's king, bears witness to the power Of him who quenched desires' five-fold fire.",
                "Great souls are they who hard things accomplish; Small souls who leave such tasks undone remain.",
                "The world belongs to him who understands The nature of the senses' five-fold train.",
                "The greatness of the wise, whose words are full, Their sacred texts reveal to all the world.",
                "On virtue's mountain peak the great ones stand; Their anger, even for a moment, hard to bear.",
                "Those who show kindness to all living things, Are truly called the righteous and the wise.",
            ]
            
            # SEO-optimized title for better reach (under 60 chars for Shorts)
            title = f"Thirukural {i} | Ancient Tamil Wisdom | {YOUTUBE_CHANNEL_NAME}"
            
            # Comprehensive description with SEO, CTAs, and engagement elements
            description = f"""🌍 Ancient Wisdom for the Modern World | திருக்குறள் {i}

📖 Tamil Verse (தமிழ்):
{sentence}

💡 Detailed Meaning (விளக்கம்):
{meanings[i-1] if i <= len(meanings) else ''}

🌐 English Translation:
{english_translations[i-1] if i <= len(english_translations) else ''}

━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
📚 {YOUTUBE_CHANNEL_NAME}
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

🔔 Subscribe for Daily Wisdom: https://www.youtube.com/@{YOUTUBE_CHANNEL_NAME.replace(' ', '')}

We connect timeless Tamil wisdom to the world through:
✨ Thirukural teachings & explanations
📖 Ancient Tamil literature & philosophy
🎓 Education & continuous learning
💡 General knowledge & cultural insights
🌟 Life motivation & personal growth
📱 Daily wisdom in short, digestible formats

━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
💬 ENGAGE WITH US:
👍 Like this video if it inspired you!
💬 Comment your thoughts below
📤 Share with friends who need wisdom
🔔 Turn on notifications for daily content

━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
🏷️ KEYWORDS & HASHTAGS:
Thirukural, Thirukkural, Tamil Wisdom, Ancient Philosophy, Life Lessons, Spiritual Wisdom, Motivational Quotes, Self Improvement, Personal Growth, Education, Indian Culture, Eastern Philosophy, Wisdom Literature, Daily Wisdom, Inspirational Content, Mindfulness, Tamil Culture, Tamil Literature, Classical Tamil, Ethical Living, Moral Values, Life Philosophy, Wisdom Quotes, Spiritual Growth, Mental Health, Positive Thinking, Success Mindset, Life Motivation, Philosophy, Ethics

━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
🌍 GLOBAL HASHTAGS FOR REACH:
#Thirukural #Thirukkural #{YOUTUBE_CHANNEL_NAME.replace(' ', '')} #AncientWisdom #TamilWisdom #WorldWisdom #Philosophy #LifeLessons #WisdomQuotes #SpiritualWisdom #InspirationalQuotes #Mindfulness #SelfImprovement #PersonalGrowth #Motivation #Education #IndianPhilosophy #EasternWisdom #WisdomLiterature #Shorts #WisdomShorts #Worldwide #GlobalWisdom #UniversalWisdom #TimelessWisdom #DailyWisdom #TamilCulture #TamilLiterature #ClassicalTamil #EthicalLiving #MoralValues #LifePhilosophy #MentalHealth #PositiveThinking #SuccessMindset #LifeMotivation #Philosophy #Ethics #WisdomDaily #MotivationDaily #SelfHelp #PersonalDevelopment #SpiritualGrowth #MindfulLiving #TamilHeritage #CulturalWisdom #AncientTeachings #WisdomForLife #QuoteOfTheDay #DailyInspiration #WisdomWednesday #ShortsWisdom"""
            
            # Comprehensive tags optimized for YouTube Shorts reach
            tags = [
                # Primary keywords
                "Thirukural",
                "Thirukkural",
                "TamilWisdom",
                "AncientWisdom",
                "TamilPhilosophy",
                "TamilLiterature",
                # Topic keywords
                "Wisdom",
                "Philosophy",
                "LifeLessons",
                "MoralValues",
                "Ethics",
                "SpiritualWisdom",
                "SpiritualGrowth",
                "SelfImprovement",
                "PersonalGrowth",
                "Motivation",
                "Inspiration",
                "Mindfulness",
                "MentalHealth",
                "PositiveThinking",
                # Format keywords
                "Shorts",
                "YouTubeShorts",
                "ShortForm",
                "QuickWisdom",
                # Cultural keywords
                "TamilCulture",
                "TamilHeritage",
                "IndianPhilosophy",
                "EasternWisdom",
                "ClassicalTamil",
                # Educational keywords
                "Education",
                "Learning",
                "SelfHelp",
                "PersonalDevelopment",
                "LifeCoaching",
                # Engagement keywords
                "DailyWisdom",
                "WisdomQuotes",
                "QuoteOfTheDay",
                "DailyInspiration",
                "MotivationalQuotes",
                "InspirationalQuotes",
                # SEO keywords
                "AncientTeachings",
                "TimelessWisdom",
                "UniversalWisdom",
                "WorldWisdom",
                "WisdomForLife",
                "LifeMotivation",
                "SuccessMindset",
                "MindfulLiving",
                "EthicalLiving",
                "WisdomDaily"
            ]
            
            # Calculate publish date if scheduling is enabled
            publish_at = None
            if YOUTUBE_SCHEDULE_ENABLED:
                try:
                    publish_at = calculate_publish_date(
                        i, 
                        start_date=YOUTUBE_SCHEDULE_START_DATE,
                        schedule_time=YOUTUBE_SCHEDULE_TIME
                    )
                except Exception as e:
                    print(f"  ⚠ Scheduling error: {e}, publishing immediately")
                    publish_at = None
            
            # Upload with comprehensive metadata for maximum reach
            upload_to_youtube(
                video_path, 
                title, 
                description, 
                tags, 
                category_id=config.YOUTUBE_CATEGORY_ID,
                publish_at=publish_at,
                default_language=config.YOUTUBE_DEFAULT_LANGUAGE,
                default_audio_language=config.YOUTUBE_DEFAULT_AUDIO_LANGUAGE
            )
        
        print(f"✓ Completed: {sentence}")
    
    print(f"\n{'='*60}")
    print(f"✅ All {total} videos generated successfully!")
    print(f"📁 Videos saved in: {output_dir}/")
    print(f"📁 Audio files saved in: {audio_dir}/")
    print(f"{'='*60}")

if __name__ == "__main__":
    try:
        process_sentences()
    except KeyboardInterrupt:
        print("\n⚠ Process interrupted by user")
    except Exception as e:
        print(f"\n❌ Error: {e}")
        import traceback
        traceback.print_exc()



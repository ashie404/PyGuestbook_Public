#!/usr/bin/env python3
from ashiecaptcha.config import config
from io import BytesIO
from werkzeug.security import generate_password_hash, check_password_hash
import base64
import string
import random
import os

from captcha.image import ImageCaptcha
import pyttsx3

class CAPTCHA:
    def __init__(self, default_config=config, config=config):
        self.config = default_config
        f_path = os.path.dirname(os.path.realpath(__file__))
        f_path = os.path.join(f_path, 'captcha.ttf')
        self.captcha_img = ImageCaptcha(fonts=[f_path])
        for key in config.keys():
            self.config[key] = config[key]

    def random_string(self, min=40, max=50):
        chars = string.ascii_uppercase
        chars = chars + string.ascii_lowercase
        chars = chars + string.digits
    
        ran_int = random.randint(min, max)
        return [random.choice(chars) for i in range(ran_int)]
    
    
    def create(self, length=None, digits=None):
        length = self.config['CAPTCHA_LENGTH'] if length is None else length
        digits = self.config['CAPTCHA_DIGITS'] if digits is None else digits
        size = 30
        width, height = length * size, size

        characters = string.digits if digits else string.ascii_uppercase
        self.text = ''.join([random.choice(characters) for i in range(length)])

        c_key = self.text + self.config['SECRET_CAPTCHA_KEY']

        c_hash = generate_password_hash(c_key,
                                        method=self.config['METHOD'],
                                        salt_length=8)
        c_hash = c_hash.replace(self.config['METHOD'] + '$', '')

        # generate captcha audio
        audio_txt = " ".join(self.text)
        engine = pyttsx3.init()
        engine.save_to_file(audio_txt, 'captcha_audio.mp3')
        engine.runAndWait()
        captcha_audio = ""

        with open('/home/ashie/PyGuestbook/ashiecaptcha/captcha_audio.mp3', 'rb') as audio_file:
            b64audio = base64.b64encode(audio_file.read())
            captcha_audio = str(b64audio)[2:][:-1]

        return {'img': self.gen_b64img(), 'audio': captcha_audio, 'text': self.text, 'hash': c_hash}
    
    
    def gen_b64img(self):
        byte_array = BytesIO()
        self.captcha_img.write(self.text, byte_array, 'png')
        byte_array = byte_array.getvalue()
    
        b64image = base64.b64encode(byte_array)
        b64image = str(b64image)
        b64image = b64image[2:][:-1]
    
        return b64image
    
    
    def captcha_html(self, captcha):
        audio = '<audio controls class="captcha-audio">' + \
        '<source type="audio/mp3" src="data:audio/mp3;base64, ' + captcha['audio'] + '/>' + \
        '</audio>'

        img = '<img class="simple-captcha-img" ' + \
              'src="data:image/png;base64, %s" />' % captcha['img']
    
        inpu = '<input type="text" class="simple-captcha-text"' + \
               'name="captcha-text">\n' + \
               '<input type="hidden" name="captcha-hash" ' + \
               'value="%s">' % captcha['hash'] 
    
        return '%s\n%s\n%s' % (audio, img, inpu)
    
    
    def verify(self, c_text, c_hash, c_key=None):
        c_key = self.config['SECRET_CAPTCHA_KEY'] if c_key is None else c_key
        c_text = c_text.upper()
        c_hash = self.config['METHOD'] + '$' + c_hash
        c_key = c_text + c_key
        return check_password_hash(c_hash, c_key)
    
    
    def init_app(self, app):
        app.jinja_env.globals.update(captcha_html=self.captcha_html)
    
        return app


if __name__ == '__main__':
    print(CAPTCHA().create())

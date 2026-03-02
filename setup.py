from setuptools import setup

APP = ['macamp.py']
DATA_FILES = []
OPTIONS = {
    'argv_emulation': True,
    'iconfile': 'icon.icns',  # Mets ici le nom de ton icône orange si besoin
    'packages': [
        'numpy', 'librosa', 'sounddevice', 'pyglet', 'soundfile', 'mutagen', 'pyloudnorm'
    ],
    'includes': [
        'PyQt6.QtWidgets', 'PyQt6.QtCore', 'PyQt6.QtGui'
    ],
    'plist': {
        'CFBundleName': 'MacAmp',
        'CFBundleShortVersionString': '1.0.0',
        'CFBundleIdentifier': 'com.tonnom.macamp',
    }
}

setup(
    app=APP,
    data_files=DATA_FILES,
    options={'py2app': OPTIONS},
    setup_requires=['py2app'],
) 
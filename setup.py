from setuptools import setup

setup(
    name='pycbox',
    version='0.0.0',
    description='Web interface for directory listings and picture gallery',
    long_description=None,
    author='Thomas Gläßle',
    author_email='thomas@coldfix.de',
    url='https://github.com/coldfix/pycbox',
    license='Unlicense',
    py_modules=['pycbox'],
    install_requires=[
        'docopt',
        'flask',
        'Pillow',
        'PyYAML',
    ],
)

# encoding: utf-8
from setuptools import setup
import os


def read(filename):
    with open(filename, 'rb') as f:
        return f.read().decode('utf-8')

try:
    long_description = read('README.rst') + '\n' + read('CHANGES.rst')
except IOError:
    long_description = None


setup(
    name='pycbox',
    version='0.0.3',
    description='Web interface for directory listings and picture gallery',
    long_description=long_description,
    author='Thomas Gläßle',
    author_email='thomas@coldfix.de',
    url='https://github.com/coldfix/pycbox',
    license='Unlicense',
    packages=['pycbox'],
    include_package_data=True,
    zip_safe=False,
    scripts=[os.path.join("bin", "pycbox")],
    install_requires=[
        'docopt',
        'flask',
        'Pillow',
        'PyYAML',
    ],
    classifiers=[
        'Development Status :: 4 - Beta',
        'Environment :: Web Environment',
        'Framework :: Flask',
        'Intended Audience :: End Users/Desktop',
        'License :: Public Domain',
        'Natural Language :: English',
        'Operating System :: OS Independent',
        'Programming Language :: Python :: 2.7',
        'Programming Language :: Python :: 3.3',
        'Programming Language :: Python :: 3.4',
        'Programming Language :: Python :: 3.5',
        'Programming Language :: Python :: 3.6',
        'Programming Language :: Python :: 3.7',
        'Topic :: Communications :: File Sharing',
    ],
)

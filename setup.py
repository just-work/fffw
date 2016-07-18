from setuptools import setup

from setuptools import find_packages

setup(
    name='fffw',
    version='0.1.2',
    packages=find_packages(exclude=["tests"]),
    url='http://github.com/rutube/fffw',
    license='Beer License',
    author='tumb1er',
    author_email='zimbler@gmail.com',
    description='FFMPEG filters wrapper', requires=['six'],
    test_suite="tests"
)

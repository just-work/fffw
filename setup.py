from distutils.core import setup

from setuptools import find_packages

try:
    # noinspection PyPackageRequirements
    from pypandoc import convert
    read_md = lambda f: convert(f, 'rst')
except ImportError:
    print("warning: pypandoc not found, could not convert Markdown to RST")
    read_md = lambda f: open(f, 'r').read()


setup(
    name='fffw',
    version='0.5.0',
    packages=find_packages(exclude=["tests"]),
    url='http://github.com/rutube/fffw',
    license='Beer License',
    author='tumb1er',
    author_email='zimbler@gmail.com',
    description='FFMPEG filters wrapper',
    long_description=read_md('README.md'),
    requires=['six'],
    test_suite="tests"
)

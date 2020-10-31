import os
import re
import subprocess
from typing import Optional

from setuptools import setup, find_packages  # type: ignore
from pathlib import Path

with open('README.md') as f:
    long_description = f.read()

version_re = re.compile('^Version: (.+)$', re.M)
package_name = 'fffw'


def get_version() -> Optional[str]:
    """
    Reads version from git status or PKG-INFO

    https://gist.github.com/pwithnall/7bc5f320b3bdf418265a
    """
    d: Path = Path(__file__).parent.absolute()
    git_dir = d.joinpath('.git')
    version: Optional[str]
    if git_dir.is_dir():
        # Get the version using "git describe".
        cmd = 'git describe --tags --match [0-9]*'.split()
        try:
            version = subprocess.check_output(cmd).decode().strip()
        except subprocess.CalledProcessError:
            return None

        # PEP 386 compatibility
        if '-' in version:
            version = '.post'.join(version.split('-')[:2])

        # Don't declare a version "dirty" merely because a time stamp has
        # changed. If it is dirty, append a ".dev1" suffix to indicate a
        # development revision after the release.
        with open(os.devnull, 'w') as fd_devnull:
            subprocess.call(['git', 'status'],
                            stdout=fd_devnull, stderr=fd_devnull)

        cmd = 'git diff-index --name-only HEAD'.split()
        try:
            dirty = subprocess.check_output(cmd).decode().strip()
        except subprocess.CalledProcessError:
            return None

        if dirty != '':
            version += '.dev1'
    else:
        # Extract the version from the PKG-INFO file.
        try:
            with open('PKG-INFO') as v:
                match = version_re.search(v.read())
                version = match.group(1) if match else None
        except FileNotFoundError:
            version = None

    return version


setup(
    name=package_name,
    version=get_version() or 'dev',
    packages=find_packages(exclude=["tests"]),
    url='http://github.com/just-work/fffw',
    license='MIT',
    author='tumb1er',
    author_email='zimbler@gmail.com',
    description='FFMPEG wrapper',
    long_description=long_description,
    long_description_content_type='text/markdown',
    test_suite="tests",
    install_requires=[
        'pymediainfo',
        'dataclasses; python_version < "3.7.0"',
        'typing_extensions; python_version < "3.8.0"',
    ],
    classifiers=[
        'Development Status :: 4 - Beta',
        'Environment :: Console',
        'Operating System :: POSIX',
        'Programming Language :: Python :: 3.6',
        'Programming Language :: Python :: 3.7',
        'Programming Language :: Python :: 3.8',
        'Programming Language :: Python :: 3.9',
        'Topic :: Multimedia :: Video :: Conversion',
    ]

)

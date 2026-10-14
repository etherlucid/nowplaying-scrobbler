from setuptools import setup, find_packages

setup(
    name="nowplaying-scrobbler",
    version="0.1.0-beta.1",
    description="ListenBrainz scrobbler for YouTube Music Safari PWA and macOS MediaRemote",
    author="etherlucid",
    packages=find_packages(),
    scripts=["bin/nowplaying-scrobbler"],
    python_requires=">=3.8",
)

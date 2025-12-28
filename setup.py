from setuptools import setup
import os

VERSION = "0.9.0"


def get_long_description():
    with open(
        os.path.join(os.path.dirname(os.path.abspath(__file__)), "README.md"),
        encoding="utf8",
    ) as fp:
        return fp.read()


setup(
    name="mbox2sqlite-llm",
    description="Load email from .mbox files into SQLite with Gmail support and LLM optimization",
    long_description=get_long_description(),
    long_description_content_type="text/markdown",
    author="Zack Shih",
    url="https://github.com/imZack/mbox2sqlite-llm",
    project_urls={
        "Issues": "https://github.com/imZack/mbox2sqlite-llm/issues",
        "CI": "https://github.com/imZack/mbox2sqlite-llm/actions",
        "Changelog": "https://github.com/imZack/mbox2sqlite-llm/releases",
    },
    license="Apache License, Version 2.0",
    version=VERSION,
    packages=["mbox_to_sqlite"],
    entry_points="""
        [console_scripts]
        mbox2sqlite-llm=mbox_to_sqlite.cli:cli
    """,
    install_requires=[
        "click",
        "sqlite-utils",
        "html2text>=2020.1.16",
        "beautifulsoup4>=4.9.0",
        "quotequail>=0.2.0",  # For quoted reply detection
    ],
    extras_require={"test": ["pytest"]},
    python_requires=">=3.7",
)

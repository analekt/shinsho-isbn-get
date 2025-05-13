from setuptools import setup, find_packages

setup(
    name="shinsho-isbn-get",
    version="0.1.0",
    packages=find_packages(),
    install_requires=[
        "requests==2.31.0",
        "feedgen==0.9.0",
        "PyYAML==6.0.1",
    ],
    author="Your Name",
    author_email="your.email@example.com",
    description="OpenBD APIから新書情報を取得してRSSフィードを生成するツール",
    keywords="openbd, rss, shinsho, book",
    url="https://github.com/yourusername/shinsho-isbn-get",
    python_requires=">=3.6",
    entry_points={
        "console_scripts": [
            "shinsho-rss=scripts.main:main",
        ],
    },
) 
from setuptools import setup, find_packages

setup(
    name="gen_unittest",
    version="0.1.0",
    packages=find_packages(),
    install_requires=[
        "metagpt>=0.1.0",
        "python-dotenv>=0.19.0",
        "javalang>=0.13.0",
    ],
    author="Your Name",
    author_email="your.email@example.com",
    description="自动生成单元测试的工具，支持Android（Java/Kotlin）和Python代码",
    long_description=open("README.md", "r", encoding="utf-8").read(),
    long_description_content_type="text/markdown",
    url="https://github.com/yourusername/gen_unittest",
    classifiers=[
        "Programming Language :: Python :: 3",
        "License :: OSI Approved :: MIT License",
        "Operating System :: OS Independent",
    ],
    python_requires=">=3.8",
    entry_points={
        "console_scripts": [
            "gen_unittest=gen_unittest.main:main_cli",
        ],
    },
)

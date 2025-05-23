from setuptools import setup, find_packages

with open("README.md", "r", encoding="utf-8") as fh:
    long_description = fh.read()

setup(
    name="sparqlsmith",
    version="0.1.1",
    author="Tim Schwabe",
    author_email="tim.schwabe@tum.de",
    description="A Python library for crafting, manipulating and analyzing SPARQL queries",
    long_description=long_description,
    long_description_content_type="text/markdown",
    url="https://github.com/TimEricSchwabe/sparqlsmith",
    packages=find_packages(),
    classifiers=[
        "Development Status :: 3 - Alpha",
        "Intended Audience :: Developers",
        "License :: OSI Approved :: MIT License",
        "Operating System :: OS Independent",
        "Programming Language :: Python :: 3",
        "Programming Language :: Python :: 3.7",
        "Programming Language :: Python :: 3.8",
        "Programming Language :: Python :: 3.9",
        "Programming Language :: Python :: 3.10",
        "Topic :: Database :: Database Engines/Servers",
        "Topic :: Software Development :: Libraries :: Python Modules",
    ],
    python_requires=">=3.7",
    install_requires=[
        "pyparsing>=3.0.0",
        "pytest>=7.0.0",
        "pytest-cov>=4.0.0",
        "requests>=2.0.0",
        "networkx>=3.0.0",
    ],
    extras_require={
        "dev": [
            "pytest>=6.0",
            "pytest-cov>=2.0",
            "black>=22.0",
            "isort>=5.0",
            "flake8>=3.9",
            "mypy>=0.9",
        ],
    },
) 
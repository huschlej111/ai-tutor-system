"""
Setup script for Know-It-All Tutor System
"""
from setuptools import setup, find_packages

with open("README.md", "r", encoding="utf-8") as fh:
    long_description = fh.read()

with open("requirements.txt", "r", encoding="utf-8") as fh:
    requirements = [line.strip() for line in fh if line.strip() and not line.startswith("#")]

setup(
    name="tutor-system",
    version="1.0.0",
    author="Know-It-All Tutor Team",
    description="A serverless learning platform for terminology-heavy subjects",
    long_description=long_description,
    long_description_content_type="text/markdown",
    packages=find_packages(where="src"),
    package_dir={"": "src"},
    classifiers=[
        "Development Status :: 4 - Beta",
        "Intended Audience :: Education",
        "License :: OSI Approved :: MIT License",
        "Operating System :: OS Independent",
        "Programming Language :: Python :: 3",
        "Programming Language :: Python :: 3.11",
    ],
    python_requires=">=3.11",
    install_requires=requirements,
    extras_require={
        "dev": [
            "pytest>=7.4.0",
            "pytest-asyncio>=0.21.0",
            "moto>=4.2.0",
            "black>=23.0.0",
            "flake8>=6.0.0",
            "mypy>=1.5.0",
        ],
        "ml": [
            "torch>=2.0.0",
            "transformers>=4.30.0",
            "sentence-transformers>=2.2.0",
            "numpy>=1.24.0",
            "scikit-learn>=1.3.0",
        ]
    },
    entry_points={
        "console_scripts": [
            "tutor-deploy=scripts.deploy:main",
            "tutor-migrate=scripts.migrate:main",
        ],
    },
)
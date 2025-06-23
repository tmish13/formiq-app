from setuptools import setup, find_packages
import os

# Function to read dependencies from a requirements.txt file
def load_requirements(filename='requirements.txt'):
    if os.path.exists(filename):
        with open(filename, 'r') as f:
            return [line.strip() for line in f if line.strip() and not line.startswith('#') and not line.startswith('-e')]
    return []

setup(
    name="formiq",
    version="0.1.0",
    description="AI-powered fitness tracking and analysis platform - Core Services",
    packages=find_packages(),
    include_package_data=True,
    python_requires=">=3.9",
    install_requires=load_requirements('requirements.txt'),
) 
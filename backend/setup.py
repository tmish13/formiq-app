from setuptools import setup, find_packages

setup(
    name="formiq",
    version="0.1.0",
    description="AI-powered fitness tracking and analysis platform",
    packages=find_packages(),
    include_package_data=True,
    python_requires=">=3.9",
    install_requires=[
        "fastapi>=0.104.0",
        "uvicorn>=0.24.0",
        "sqlalchemy>=2.0.23",
        "pydantic>=2.4.2",
        "python-jose>=3.3.0",
        "passlib>=1.7.4",
        "python-multipart>=0.0.6",
        "alembic>=1.12.1",
        "python-dotenv>=1.0.0",
        "httpx>=0.25.1",
    ],
) 
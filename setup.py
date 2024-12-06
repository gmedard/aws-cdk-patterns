from setuptools import setup, find_packages

setup(
    name="aws-cdk-patterns",
    version="0.1.0",
    packages=find_packages(),
    install_requires=[
        "aws-cdk-lib>=2.0.0",
        "constructs>=10.0.0",
    ],
)

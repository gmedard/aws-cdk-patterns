from setuptools import setup, find_packages

setup(
    name="aws-cdk-patterns",
    version="0.1.0",
    description="Reusable AWS CDK Patterns",
    author="Greg Medard",
    author_email="medarg@amazon.com",
    packages=find_packages(include=["aws_cdk_patterns", "aws_cdk_patterns.*"]),
    install_requires=["aws-cdk-lib>=2.0.0", "constructs>=10.0.0,<11.0.0"],
    python_requires=">=3.12",
)

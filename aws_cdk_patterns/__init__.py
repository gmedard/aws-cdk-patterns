# aws_cdk_patterns/__init__.py

from .network.vpc import CustomVpcPattern, IVpcPattern
from .compute.ec2 import EC2InstancePattern

__version__ = "0.1.0"

__all__ = [
    "CustomVpcPattern",
    "IVpcPattern",
    "EC2InstancePattern",
]

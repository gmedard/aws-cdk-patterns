from constructs import Construct
from aws_cdk import aws_ec2 as ec2


class CustomVpcPattern(Construct):
    def __init__(self, scope: Construct, id: str, **kwargs):
        super().__init__(scope, id)

        # Configuration with defaults
        self.config = {
            "cidr": kwargs.get("cidr", "10.0.0.0/16"),
            "max_azs": kwargs.get("max_azs", 3),
            "enable_internet": kwargs.get("enable_internet", True),
            "nat_gateways": (
                kwargs.get("nat_gateways", 1)
                if kwargs.get("enable_internet", True)
                else 0
            ),
        }

        # Create the VPC
        self.vpc = ec2.Vpc(
            self,
            "CustomVpc",
            ip_addresses=ec2.IpAddresses.cidr(self.config["cidr"]),
            max_azs=self.config["max_azs"],
            nat_gateways=self.config["nat_gateways"],
            subnet_configuration=(
                [
                    ec2.SubnetConfiguration(
                        name="Public", subnet_type=ec2.SubnetType.PUBLIC, cidr_mask=24
                    ),
                    ec2.SubnetConfiguration(
                        name="Private",
                        subnet_type=(
                            ec2.SubnetType.PRIVATE_WITH_EGRESS
                            if self.config["enable_internet"]
                            else ec2.SubnetType.PRIVATE_ISOLATED
                        ),
                        cidr_mask=24,
                    ),
                ]
                if self.config["enable_internet"]
                else [
                    ec2.SubnetConfiguration(
                        name="Isolated",
                        subnet_type=ec2.SubnetType.PRIVATE_ISOLATED,
                        cidr_mask=24,
                    )
                ]
            ),
        )

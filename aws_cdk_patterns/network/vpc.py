from constructs import Construct
from aws_cdk import aws_ec2 as ec2


class CustomVpcPattern(Construct):
    """
    A custom VPC pattern that creates a VPC with configurable options and required Systems Manager endpoints.

    By default, creates a VPC with public subnets, private subnets with egress, and NAT Gateway.
    When enable_internet=False, creates only isolated private subnets with no internet access.

    Usage:
        from aws_cdk_patterns.network.vpc import CustomVpcPattern

        # Create with default settings (public and private subnets with NAT Gateway)
        vpc = CustomVpcPattern(self, "MyVPC")

        # Create private-only VPC with no internet access
        vpc = CustomVpcPattern(
            self,
            "MyPrivateVPC",
            cidr="172.16.0.0/16",
            max_azs=2,
            enable_internet=False
        )

        # Create VPC with public and private subnets and multiple NAT Gateways
        vpc = CustomVpcPattern(
            self,
            "MyHighAvailabilityVPC",
            max_azs=3,
            nat_gateways=3  # One NAT Gateway per AZ
        )

        # Access the underlying VPC construct
        actual_vpc = vpc.vpc

    Attributes:
        vpc: The underlying ec2.Vpc construct

    Configuration Options:
        cidr (str): The CIDR range for the VPC (default: "10.0.0.0/16")
        max_azs (int): Maximum number of Availability Zones to use (default: 3)
        enable_internet (bool): Whether to create public subnets and NAT Gateways (default: True)
        nat_gateways (int): Number of NAT Gateways to create if enable_internet is True (default: 1)
    """

    def __init__(self, scope: Construct, id: str, **kwargs):
        super().__init__(scope, id)

        # Configuration with defaults
        enable_internet = kwargs.get("enable_internet", True)
        nat_gateways = kwargs.get("nat_gateways", 1)

        self.config = {
            "cidr": kwargs.get("cidr", "10.0.0.0/16"),
            "max_azs": kwargs.get("max_azs", 3),
            "enable_internet": enable_internet,
            # NAT Gateways are only created if enable_internet is True
            "nat_gateways": nat_gateways if enable_internet else 0,
        }

        # Define subnet configurations based on enable_internet flag
        subnet_configs = []

        if self.config["enable_internet"]:
            # Default: public subnets and private subnets with egress
            subnet_configs.extend(
                [
                    ec2.SubnetConfiguration(
                        name="Public", subnet_type=ec2.SubnetType.PUBLIC, cidr_mask=24
                    ),
                    ec2.SubnetConfiguration(
                        name="Private",
                        subnet_type=ec2.SubnetType.PRIVATE_WITH_EGRESS,
                        cidr_mask=24,
                    ),
                ]
            )
        else:
            # When enable_internet is False: only isolated private subnets
            subnet_configs.append(
                ec2.SubnetConfiguration(
                    name="Isolated",
                    subnet_type=ec2.SubnetType.PRIVATE_ISOLATED,
                    cidr_mask=24,
                )
            )

        # Create the VPC
        self.vpc = ec2.Vpc(
            self,
            "CustomVpc",
            ip_addresses=ec2.IpAddresses.cidr(self.config["cidr"]),
            max_azs=self.config["max_azs"],
            nat_gateways=self.config["nat_gateways"],
            subnet_configuration=subnet_configs,
        )

        # Add S3 Gateway Endpoint (available even without internet access)
        self.vpc.add_gateway_endpoint(
            "S3Gateway", service=ec2.GatewayVpcEndpointAwsService.S3
        )

        # Add required VPC Endpoints for Systems Manager functionality
        self.vpc.add_interface_endpoint(
            "SSMEndpoint", service=ec2.InterfaceVpcEndpointAwsService.SSM
        )

        self.vpc.add_interface_endpoint(
            "SSMMessagesEndpoint",
            service=ec2.InterfaceVpcEndpointAwsService.SSM_MESSAGES,
        )

        self.vpc.add_interface_endpoint(
            "EC2MessagesEndpoint",
            service=ec2.InterfaceVpcEndpointAwsService.EC2_MESSAGES,
        )

        self.vpc.add_interface_endpoint(
            "EC2Endpoint", service=ec2.InterfaceVpcEndpointAwsService.EC2
        )

        # SSM Incidents
        self.vpc.add_interface_endpoint(
            "SSMIncidents", service=ec2.InterfaceVpcEndpointAwsService.SSM_INCIDENTS
        )

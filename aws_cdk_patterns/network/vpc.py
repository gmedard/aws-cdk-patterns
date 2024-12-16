from constructs import Construct
from aws_cdk import aws_ec2 as ec2
from typing import Optional, List


class CustomVpcPattern(Construct):
    """A custom VPC pattern that creates a VPC with configurable options and required Systems Manager endpoints.

    By default, creates a VPC with public subnets, private subnets with egress, and NAT Gateway.
    When enable_internet=False, creates only isolated private subnets with no internet access.

    Args:
        scope (Construct): The scope in which to define this construct.
        id (str): The scoped construct ID.
        cidr (Optional[str]): The CIDR range for the VPC. Defaults to "10.0.0.0/16".
        max_azs (Optional[int]): Maximum number of Availability Zones to use. Defaults to 3.
        enable_internet (Optional[bool]): Whether to create public subnets and NAT Gateways. Defaults to True.
        nat_gateways (Optional[int]): Number of NAT Gateways to create if enable_internet is True. Defaults to 1.

    Properties:
        vpc (ec2.Vpc): The underlying VPC construct
        vpc_id (str): The ID of the VPC
        private_subnets (List[ec2.ISubnet]): List of private subnets in the VPC
        public_subnets (List[ec2.ISubnet]): List of public subnets in the VPC (empty if enable_internet is False)
        isolated_subnets (List[ec2.ISubnet]): List of isolated subnets in the VPC (only when enable_internet is False)
    """

    def __init__(
        self,
        scope: Construct,
        id: str,
        *,
        cidr: str = "10.0.0.0/16",
        max_azs: int = 3,
        enable_internet: bool = True,
        nat_gateways: int = 1,
    ) -> None:
        """Initialize a new CustomVpcPattern.

        Args:
            scope (Construct): The scope in which to define this construct
            id (str): The scoped construct ID
            cidr (str, optional): The CIDR range for the VPC. Defaults to "10.0.0.0/16"
            max_azs (int, optional): Maximum number of Availability Zones to use. Defaults to 3
            enable_internet (bool, optional): Whether to create public subnets and NAT Gateways. Defaults to True
            nat_gateways (int, optional): Number of NAT Gateways to create if enable_internet is True. Defaults to 1
        """
        super().__init__(scope, id)

        self.config = {
            "cidr": cidr,
            "max_azs": max_azs,
            "enable_internet": enable_internet,
            "nat_gateways": nat_gateways if enable_internet else 0,
        }

        subnet_configs = []

        if self.config["enable_internet"]:
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
            subnet_configs.append(
                ec2.SubnetConfiguration(
                    name="Isolated",
                    subnet_type=ec2.SubnetType.PRIVATE_ISOLATED,
                    cidr_mask=24,
                )
            )

        self.vpc = ec2.Vpc(
            self,
            "CustomVpc",
            ip_addresses=ec2.IpAddresses.cidr(self.config["cidr"]),
            max_azs=self.config["max_azs"],
            nat_gateways=self.config["nat_gateways"],
            subnet_configuration=subnet_configs,
        )

        # Add required VPC endpoints
        self._add_vpc_endpoints()

    def _add_vpc_endpoints(self) -> None:
        """Add required VPC endpoints for Systems Manager functionality."""
        # Add S3 Gateway Endpoint
        self.vpc.add_gateway_endpoint(
            "S3Gateway", service=ec2.GatewayVpcEndpointAwsService.S3
        )

        # Add Systems Manager endpoints
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

        self.vpc.add_interface_endpoint(
            "SSMIncidents", service=ec2.InterfaceVpcEndpointAwsService.SSM_INCIDENTS
        )

    @property
    def vpc_id(self) -> str:
        """Get the VPC ID.

        Returns:
            str: The ID of the VPC
        """
        return self.vpc.vpc_id

    @property
    def private_subnets(self) -> List[ec2.ISubnet]:
        """Get the private subnets.

        Returns:
            List[ec2.ISubnet]: List of private subnets in the VPC
        """
        return self.vpc.private_subnets

    @property
    def public_subnets(self) -> List[ec2.ISubnet]:
        """Get the public subnets.

        Returns:
            List[ec2.ISubnet]: List of public subnets in the VPC
        """
        return self.vpc.public_subnets

    @property
    def isolated_subnets(self) -> List[ec2.ISubnet]:
        """Get the isolated subnets.

        Returns:
            List[ec2.ISubnet]: List of isolated subnets in the VPC
        """
        return self.vpc.isolated_subnets

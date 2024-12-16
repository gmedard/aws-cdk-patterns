# aws_cdk_patterns/network/vpc.py

import ipaddress
import logging
from typing import Optional, Dict, Any, Protocol, runtime_checkable

from constructs import Construct
from aws_cdk import (
    aws_ec2 as ec2,
    aws_iam as iam,
    Stack,
    CfnOutput,
    Tags,
)

logger = logging.getLogger(__name__)


@runtime_checkable
class IVpcPattern(Protocol):
    """Interface for VPC patterns"""

    def get_vpc(self) -> ec2.IVpc:
        """Get the VPC instance"""
        pass

    def get_instance_role(self) -> iam.IRole:
        """Get the instance IAM role"""
        pass

    def get_instance_security_group(self) -> ec2.ISecurityGroup:
        """Get the instance security group"""
        pass


class CustomVpcPattern(Construct, IVpcPattern):
    """
    A pattern for creating a custom VPC with configurable options
    """

    DEFAULT_CIDR = "10.0.0.0/16"
    DEFAULT_MAX_AZS = 2
    DEFAULT_NAT_GATEWAYS = 1
    SUBNET_MASK = 24

    def __init__(self, scope: Construct, id: str, **kwargs):
        """
        Initialize a Custom VPC Pattern.

        Args:
            scope: CDK Construct scope
            id: Unique identifier for the construct
            **kwargs: Configuration options including:
                - cidr: VPC CIDR block
                - max_azs: Maximum number of availability zones
                - enable_internet: Whether to enable internet access
                - nat_gateways: Number of NAT gateways
                - enable_ssm: Whether to enable Systems Manager endpoints
                - enable_ec2_connect: Whether to enable EC2 Instance Connect
                - tags: Additional tags to apply to resources

        Raises:
            ValueError: If the CIDR format is invalid or configuration is invalid
        """
        super().__init__(scope, id)

        self.environment = self.node.try_get_context("environment") or "development"
        self.config = self._init_config(kwargs)
        self._validate_config()

        # Create resources
        self.vpc = self._create_vpc()

        if self.config["enable_ssm"]:
            self._create_ssm_endpoints()

        self.instance_security_group = self._create_instance_security_group()
        self.instance_role = self._create_instance_role()

        # Add tags and outputs
        self._add_tags(kwargs.get("tags", {}))
        self._create_outputs()

    def _init_config(self, kwargs: dict) -> dict:
        """Initialize and return the configuration dictionary"""
        cidr = kwargs.get("cidr", self.DEFAULT_CIDR)

        if not self._is_valid_cidr(cidr):
            raise ValueError(f"Invalid CIDR format: {cidr}")

        return {
            "cidr": cidr,
            "max_azs": kwargs.get("max_azs", self.DEFAULT_MAX_AZS),
            "enable_internet": kwargs.get("enable_internet", True),
            "nat_gateways": (
                kwargs.get("nat_gateways", self.DEFAULT_NAT_GATEWAYS)
                if kwargs.get("enable_internet", True)
                else 0
            ),
            "enable_ssm": kwargs.get("enable_ssm", True),
            "enable_ec2_connect": kwargs.get("enable_ec2_connect", True),
        }

    def _validate_config(self):
        """Validate the configuration"""
        if self.config["max_azs"] < 1:
            raise ValueError("max_azs must be at least 1")

        if self.config["nat_gateways"] < 0:
            raise ValueError("nat_gateways cannot be negative")

        if self.config["nat_gateways"] > 0 and not self.config["enable_internet"]:
            raise ValueError("NAT Gateways require internet access to be enabled")

    @staticmethod
    def _is_valid_cidr(cidr: str) -> bool:
        """Validate CIDR block format"""
        try:
            ipaddress.ip_network(cidr)
            return True
        except ValueError:
            return False

    def _create_vpc(self) -> ec2.Vpc:
        """Create and return the VPC"""
        try:
            logger.info(f"Creating VPC with CIDR {self.config['cidr']}")

            subnet_configs = self._get_subnet_configurations()

            vpc = ec2.Vpc(
                self,
                "CustomVpc",
                ip_addresses=ec2.IpAddresses.cidr(self.config["cidr"]),
                max_azs=self.config["max_azs"],
                nat_gateways=self.config["nat_gateways"],
                subnet_configuration=subnet_configs,
            )

            logger.info(f"Successfully created VPC: {vpc.vpc_id}")
            return vpc

        except Exception as e:
            logger.error(f"Failed to create VPC: {str(e)}")
            raise

    def _get_subnet_configurations(self) -> list:
        """Get subnet configurations based on VPC settings"""
        subnet_configs = []

        if self.config["enable_internet"]:
            subnet_configs.extend(
                [
                    ec2.SubnetConfiguration(
                        name="Public",
                        subnet_type=ec2.SubnetType.PUBLIC,
                        cidr_mask=self.SUBNET_MASK,
                    ),
                    ec2.SubnetConfiguration(
                        name="Private",
                        subnet_type=ec2.SubnetType.PRIVATE_WITH_EGRESS,
                        cidr_mask=self.SUBNET_MASK,
                    ),
                ]
            )
        else:
            subnet_configs.append(
                ec2.SubnetConfiguration(
                    name="Isolated",
                    subnet_type=ec2.SubnetType.PRIVATE_ISOLATED,
                    cidr_mask=self.SUBNET_MASK,
                )
            )

        return subnet_configs

    def _create_ssm_endpoints(self):
        """
        Create required VPC endpoints for SSM Session Manager.

        Raises:
            Exception: If endpoint creation fails
        """
        try:
            # Security group for VPC endpoints
            self.endpoint_security_group = ec2.SecurityGroup(
                self,
                "EndpointSecurityGroup",
                vpc=self.vpc,
                description="Security group for VPC Endpoints",
                allow_all_outbound=True,
            )

            # Allow HTTPS inbound from VPC CIDR
            self.endpoint_security_group.add_ingress_rule(
                ec2.Peer.ipv4(self.vpc.vpc_cidr_block),
                ec2.Port.tcp(443),
                "Allow HTTPS from VPC",
            )

            # Create VPC Endpoints
            endpoints = {
                "ssm": "com.amazonaws.{}.ssm",
                "ssmmessages": "com.amazonaws.{}.ssmmessages",
                "ec2messages": "com.amazonaws.{}.ec2messages",
            }

            for name, endpoint_service in endpoints.items():
                ec2.InterfaceVpcEndpoint(
                    self,
                    f"{name}Endpoint",
                    vpc=self.vpc,
                    service=ec2.InterfaceVpcEndpoint.from_interface_vpc_endpoint_attributes(
                        self,
                        f"{name}Service",
                        port=443,
                        vpc_endpoint_service_name=endpoint_service.format(
                            Stack.of(self).region
                        ),
                    ),
                    security_groups=[self.endpoint_security_group],
                    private_dns_enabled=True,
                )

            # S3 Gateway Endpoint for SSM
            self.vpc.add_gateway_endpoint(
                "s3Endpoint", service=ec2.GatewayVpcEndpointAwsService.S3
            )

        except Exception as e:
            logging.error(f"Failed to create SSM endpoints: {str(e)}")
            raise

    def _create_instance_security_group(self) -> ec2.SecurityGroup:
        """
        Create security group for EC2 instances.

        Returns:
            ec2.SecurityGroup: The created security group
        """
        security_group = ec2.SecurityGroup(
            self,
            "InstanceSecurityGroup",
            vpc=self.vpc,
            description="Security group for EC2 instances",
            allow_all_outbound=True,
        )

        if self.config["enable_ec2_connect"]:
            region = Stack.of(self).region

            # Allow inbound SSH from EC2 Instance Connect service
            security_group.add_ingress_rule(
                ec2.Peer.prefix_list(f"com.amazonaws.{region}.ec2-instance-connect"),
                ec2.Port.tcp(22),
                "Allow SSH from EC2 Instance Connect",
            )

        return security_group

    def _create_instance_role(self) -> iam.Role:
        """
        Create IAM role for EC2 instances.

        Returns:
            iam.Role: The created IAM role
        """
        role = iam.Role(
            self, "InstanceRole", assumed_by=iam.ServicePrincipal("ec2.amazonaws.com")
        )

        # Add required policies for SSM Session Manager
        role.add_managed_policy(
            iam.ManagedPolicy.from_aws_managed_policy_name(
                "AmazonSSMManagedInstanceCore"
            )
        )

        if self.config["enable_ec2_connect"]:
            # Add policy for EC2 Instance Connect
            role.add_to_policy(
                iam.PolicyStatement(
                    actions=["ec2-instance-connect:SendSSHPublicKey"], resources=["*"]
                )
            )

        return role

    def get_vpc(self) -> ec2.IVpc:
        """Implementation of IVpcPattern interface"""
        return self.vpc

    def get_instance_role(self) -> iam.IRole:
        """Implementation of IVpcPattern interface"""
        return self.instance_role

    def get_instance_security_group(self) -> ec2.ISecurityGroup:
        """Implementation of IVpcPattern interface"""
        return self.instance_security_group

    def _generate_resource_name(self, resource_type: str) -> str:
        """Generate a consistent resource name"""
        stack_name = Stack.of(self).stack_name
        return f"{stack_name}-{self.node.id}-{resource_type}"

    def _add_tags(self, additional_tags: dict):
        """Add tags to all resources"""
        resources = [self.vpc, self.instance_security_group, self.instance_role]

        if self.config["enable_ssm"]:
            resources.append(self.endpoint_security_group)

        default_tags = {
            "Environment": self.environment,
            "ManagedBy": "CDK",
            "Pattern": "CustomVpcPattern",
            "Project": self.node.try_get_context("project") or "default",
        }

        # Merge additional tags with default tags
        tags = {**default_tags, **additional_tags}

        for resource in resources:
            for key, value in tags.items():
                Tags.of(resource).add(key, value)

    def _create_outputs(self):
        """Create CloudFormation outputs"""
        CfnOutput(
            self,
            "VpcId",
            value=self.vpc.vpc_id,
            description="VPC ID",
            export_name=f"{self.node.id}-vpc-id",
        )

        CfnOutput(
            self,
            "InstanceSecurityGroupId",
            value=self.instance_security_group.security_group_id,
            description="Instance Security Group ID",
            export_name=f"{self.node.id}-instance-sg-id",
        )

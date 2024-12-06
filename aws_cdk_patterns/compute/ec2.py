# aws_cdk_patterns/compute/ec2.py

import logging
from typing import Optional, Dict, Any, TYPE_CHECKING

from constructs import Construct
from aws_cdk import aws_ec2 as ec2, aws_iam as iam, Stack, Tags, CfnOutput

if TYPE_CHECKING:
    from ..network.vpc import IVpcPattern

logger = logging.getLogger(__name__)


class EC2InstancePattern(Construct):
    """
    A pattern for creating EC2 instances with standardized configuration
    """

    def __init__(self, scope: Construct, id: str, vpc_pattern: IVpcPattern, **kwargs):
        """
        Initialize EC2 Instance Pattern.

        Args:
            scope: CDK Construct scope
            id: Unique identifier for the construct
            vpc_pattern: VPC pattern implementing IVpcPattern
            **kwargs: Additional configuration options including:
                - instance_type: EC2 instance type
                - machine_image: EC2 machine image
                - subnet_type: Type of subnet to launch in
                - tags: Additional tags to apply to instances
        """
        super().__init__(scope, id)

        self.vpc_pattern = vpc_pattern
        self.environment = self.node.try_get_context("environment") or "development"

        # Initialize configuration
        self.config = self._init_config(kwargs)
        self._validate_config(self.config)

        # Store additional tags
        self.additional_tags = kwargs.get("tags", {})

    def _init_config(self, kwargs: dict) -> dict:
        """Initialize and return the configuration dictionary"""
        env_config = self._get_environment_config()

        return {
            "instance_type": kwargs.get(
                "instance_type",
                env_config.get(
                    "instance_type",
                    ec2.InstanceType.of(ec2.InstanceClass.T3, ec2.InstanceSize.MICRO),
                ),
            ),
            "machine_image": kwargs.get(
                "machine_image",
                ec2.AmazonLinuxImage(
                    generation=ec2.AmazonLinuxGeneration.AMAZON_LINUX_2
                ),
            ),
            "subnet_type": kwargs.get("subnet_type"),
        }

    def _get_environment_config(self) -> dict:
        """Get environment-specific configuration"""
        base_config = {
            "development": {
                "instance_type": ec2.InstanceType.of(
                    ec2.InstanceClass.T3, ec2.InstanceSize.MICRO
                ),
            },
            "production": {
                "instance_type": ec2.InstanceType.of(
                    ec2.InstanceClass.T3, ec2.InstanceSize.SMALL
                ),
            },
        }
        return base_config.get(self.environment, base_config["development"])

    def _validate_config(self, config: dict):
        """Validate the configuration"""
        if not isinstance(config["instance_type"], ec2.InstanceType):
            raise ValueError("instance_type must be an ec2.InstanceType")

        if not isinstance(config["machine_image"], ec2.IMachineImage):
            raise ValueError("machine_image must implement ec2.IMachineImage")

    def _generate_resource_name(self, resource_type: str) -> str:
        """Generate a consistent resource name"""
        stack_name = Stack.of(self).stack_name
        return f"{stack_name}-{self.node.id}-{resource_type}"

    def create_instance(
        self,
        id: str,
        *,
        instance_type: Optional[ec2.InstanceType] = None,
        machine_image: Optional[ec2.IMachineImage] = None,
        subnet_type: Optional[ec2.SubnetType] = None,
        user_data: Optional[ec2.UserData] = None,
        tags: Optional[Dict[str, str]] = None,
    ) -> ec2.Instance:
        """
        Create an EC2 instance with the specified configuration.

        Args:
            id: Unique identifier for the instance
            instance_type: Override default instance type
            machine_image: Override default machine image
            subnet_type: Override default subnet type
            user_data: Optional user data script
            tags: Additional tags for the instance

        Returns:
            ec2.Instance: The created EC2 instance

        Raises:
            ValueError: If the configuration is invalid
        """
        try:
            logger.info(f"Creating EC2 instance with ID: {id}")

            # Use provided values or defaults from config
            instance_type = instance_type or self.config["instance_type"]
            machine_image = machine_image or self.config["machine_image"]
            subnet_type = subnet_type or self.config["subnet_type"]

            # Create the instance
            # amazonq-ignore-next-line
            instance = ec2.Instance(
                self,
                id,
                vpc=self.vpc_pattern.get_vpc(),
                vpc_subnets=ec2.SubnetSelection(subnet_type=subnet_type),
                instance_type=instance_type,
                machine_image=machine_image,
                security_group=self.vpc_pattern.get_instance_security_group(),
                role=self.vpc_pattern.get_instance_role(),
                user_data=user_data,
            )

            # Add tags
            self._add_instance_tags(instance, tags or {})

            # Create outputs
            self._create_instance_outputs(instance, id)

            logger.info(f"Successfully created EC2 instance: {instance.instance_id}")
            return instance

        except Exception as e:
            logger.error(f"Failed to create EC2 instance: {str(e)}")
            raise

    def _add_instance_tags(self, instance: ec2.Instance, instance_tags: Dict[str, str]):
        """Add tags to the EC2 instance"""
        default_tags = {
            "Name": self._generate_resource_name("instance"),
            "Environment": self.environment,
            "ManagedBy": "CDK",
            "Pattern": "EC2InstancePattern",
            "Project": self.node.try_get_context("project") or "default",
        }

        # Merge tags: instance_tags override additional_tags which override default_tags
        tags = {**default_tags, **self.additional_tags, **instance_tags}

        for key, value in tags.items():
            Tags.of(instance).add(key, value)

    def _create_instance_outputs(self, instance: ec2.Instance, instance_id: str):
        """Create CloudFormation outputs for the instance"""
        CfnOutput(
            self,
            f"{instance_id}InstanceId",
            value=instance.instance_id,
            description=f"Instance ID of {instance_id}",
            export_name=f"{self.node.id}-{instance_id}-instance-id",
        )

        CfnOutput(
            self,
            f"{instance_id}PrivateIp",
            value=instance.instance_private_ip,
            description=f"Private IP of {instance_id}",
            export_name=f"{self.node.id}-{instance_id}-private-ip",
        )

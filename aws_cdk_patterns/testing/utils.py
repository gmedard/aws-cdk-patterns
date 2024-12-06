# aws_cdk_patterns/testing/utils.py

from aws_cdk import App, Stack
from constructs import Construct
from typing import Optional, Dict, Any


class TestStack(Stack):
    """Utility stack for testing CDK constructs"""

    def __init__(
        self, scope: Construct, id: str, env: Optional[Dict[str, Any]] = None, **kwargs
    ):
        super().__init__(scope, id, env=env, **kwargs)

    @staticmethod
    def create_test_app(env: Optional[Dict[str, Any]] = None) -> tuple:
        """
        Create a test app and stack for testing constructs

        Args:
            env: Optional environment variables

        Returns:
            tuple: (App, TestStack)
        """
        app = App()
        stack = TestStack(app, "TestStack", env=env)
        return app, stack

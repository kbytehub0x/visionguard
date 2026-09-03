import aws_cdk as cdk
from visionguard_stack import VisionGuardStack

app = cdk.App()
VisionGuardStack(app, "VisionGuard-Stack")
app.synth()

import aws_cdk as cdk
from aws_cdk import (
    aws_s3 as s3,
    aws_dynamodb as dynamodb,
    aws_ecs as ecs,
    aws_lambda as _lambda,
    aws_iam as iam,
    aws_stepfunctions as sfn,
    aws_sqs as sqs,
    aws_sns as sns
)
from constructs import Construct

class VisionGuardStack(cdk.Stack):
    def __init__(self, scope: Construct, construct_id: str, **kwargs) -> None:
        super().__init__(scope, construct_id, **kwargs)

        raw_bucket = s3.Bucket(self, "RawVideoBucket", removal_policy=cdk.RemovalPolicy.DESTROY)
        evidence_bucket = s3.Bucket(self, "EvidenceBucket", removal_policy=cdk.RemovalPolicy.DESTROY)
        models_bucket = s3.Bucket(self, "ModelsBucket", removal_policy=cdk.RemovalPolicy.DESTROY)

        cdk.CfnOutput(self, "RawBucketName", value=raw_bucket.bucket_name)
        cdk.CfnOutput(self, "EvidenceBucketName", value=evidence_bucket.bucket_name)
        cdk.CfnOutput(self, "ModelsBucketName", value=models_bucket.bucket_name)

        table = dynamodb.Table(self, "IncidentsTable",
            partition_key=dynamodb.Attribute(name="PK", type=dynamodb.AttributeType.STRING),
            sort_key=dynamodb.Attribute(name="SK", type=dynamodb.AttributeType.STRING),
            billing_mode=dynamodb.BillingMode.PAY_PER_REQUEST,
            removal_policy=cdk.RemovalPolicy.DESTROY
        )

        cluster = ecs.Cluster(self, "GravitonCluster", cluster_name="VisionGuard-Graviton-Cluster")
        
        task_def = ecs.FargateTaskDefinition(self, "CoolTaskDef",
            family="VisionGuard-COOL-Task",
            cpu=4096,
            memory_limit_mib=8192,
            runtime_platform=ecs.RuntimePlatform(
                operating_system_family=ecs.OperatingSystemFamily.LINUX,
                cpu_architecture=ecs.CpuArchitecture.ARM64
            )
        )
        
        container = task_def.add_container("opencv-cool-container",
            image=ecs.ContainerImage.from_asset("../", file="Dockerfile.graviton"),
            logging=ecs.LogDrivers.aws_logs(stream_prefix="CoolTask")
        )
        
        raw_bucket.grant_read(task_def.task_role)
        evidence_bucket.grant_read_write(task_def.task_role)
        models_bucket.grant_read(task_def.task_role)

        init_lambda = _lambda.Function(self, "InitIncident",
            function_name="VisionGuard-InitIncident",
            runtime=_lambda.Runtime.PYTHON_3_12,
            code=_lambda.Code.from_asset("../src/lambda"),
            handler="init_incident.lambda_handler",
            timeout=cdk.Duration.seconds(10),
            environment={"TABLE_NAME": table.table_name}
        )
        table.grant_write_data(init_lambda)

        audit_lambda = _lambda.Function(self, "WriteAuditLog",
            function_name="VisionGuard-WriteAuditLog",
            runtime=_lambda.Runtime.PYTHON_3_12,
            code=_lambda.Code.from_asset("../src/lambda"),
            handler="write_audit.lambda_handler",
            timeout=cdk.Duration.seconds(10),
            environment={"TABLE_NAME": table.table_name}
        )
        table.grant_write_data(audit_lambda)

        router_lambda = _lambda.Function(self, "BedrockRouter",
            function_name="VisionGuard-BedrockRouter",
            runtime=_lambda.Runtime.PYTHON_3_12,
            code=_lambda.Code.from_asset("../src/lambda"),
            handler="lambda_function.lambda_handler",
            timeout=cdk.Duration.seconds(30)
        )
        router_lambda.add_to_role_policy(iam.PolicyStatement(
            actions=["bedrock:InvokeModel", "bedrock:Converse"],
            resources=["arn:aws:bedrock:*::foundation-model/anthropic.claude-3-*"]
        ))

        review_queue = sqs.Queue(self, "HumanReviewQueue", queue_name="VisionGuard-HumanReviewQueue")
        alerts_topic = sns.Topic(self, "AlertsTopic", topic_name="VisionGuard-Alerts")
        escalations_topic = sns.Topic(self, "EscalationsTopic", topic_name="VisionGuard-Escalations")

        with open("../step_functions/asl.json", "r") as f:
            asl_definition = f.read()

        state_machine = sfn.StateMachine(self, "AgenticLoop",
            state_machine_name="VisionGuard-Agentic-Loop",
            definition_body=sfn.DefinitionBody.from_string(asl_definition)
        )
        
        router_lambda.grant_invoke(state_machine.role)
        init_lambda.grant_invoke(state_machine.role)
        audit_lambda.grant_invoke(state_machine.role)
        review_queue.grant_send_messages(state_machine.role)
        alerts_topic.grant_publish(state_machine.role)
        escalations_topic.grant_publish(state_machine.role)

        state_machine.role.add_to_policy(iam.PolicyStatement(
            actions=["ecs:RunTask", "ecs:StopTask", "ecs:DescribeTasks"],
            resources=[task_def.task_definition_arn]
        ))
        state_machine.role.add_to_policy(iam.PolicyStatement(
            actions=["iam:PassRole"],
            resources=[task_def.task_role.role_arn, task_def.execution_role.role_arn]
        ))

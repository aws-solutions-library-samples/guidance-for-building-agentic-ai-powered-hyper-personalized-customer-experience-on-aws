// ai-service.ts
import { Duration } from "aws-cdk-lib";
import { Construct } from "constructs";
import * as cdk_nag from 'cdk-nag';
import * as ec2 from "aws-cdk-lib/aws-ec2";
import * as ecs from "aws-cdk-lib/aws-ecs";
import * as iam from "aws-cdk-lib/aws-iam";
import * as logs from "aws-cdk-lib/aws-logs";
import * as elbv2 from "aws-cdk-lib/aws-elasticloadbalancingv2";
import * as ecrAssets from "aws-cdk-lib/aws-ecr-assets";
import * as ssm from "aws-cdk-lib/aws-ssm";
import * as path from "path";

export interface AiServiceProps {
  vpc: ec2.IVpc;
  cluster: ecs.Cluster;                     // reusing existing cluster
  alb: elbv2.ApplicationLoadBalancer;       // reusing existing ALB
  albSecurityGroup: ec2.ISecurityGroup;     // to allow ALB -> service
  apiPathPattern?: string;                  // default "/api/*"
  containerPort?: number;                   // default 8000
  cpuArch?: ecs.CpuArchitecture;            // default ARM64
  ssmParameter?: ssm.StringParameter;       // SSM parameter with configuration
}

export class AiService extends Construct {
  public readonly service: ecs.FargateService;
  public readonly targetGroup: elbv2.ApplicationTargetGroup;

  constructor(scope: Construct, id: string, props: AiServiceProps) {
    super(scope, id);

    const apiPath = props.apiPathPattern ?? "/api/*";
    const containerPort = props.containerPort ?? 8000;
    const cpuArch = props.cpuArch ?? ecs.CpuArchitecture.ARM64;

    // Logs
    const logGroup = new logs.LogGroup(this, "AiLogs", {
      retention: logs.RetentionDays.ONE_WEEK,
    });

    // Roles
    const executionRole = new iam.Role(this, "AiExecRole", {
      assumedBy: new iam.ServicePrincipal("ecs-tasks.amazonaws.com"),
      managedPolicies: [
        iam.ManagedPolicy.fromAwsManagedPolicyName("service-role/AmazonECSTaskExecutionRolePolicy"),
      ],
    });

    // Suppress CDK-Nag for AWS managed policy usage
    cdk_nag.NagSuppressions.addResourceSuppressions(executionRole, [
      { 
        id: "AwsSolutions-IAM4", 
        reason: "ECS Task Execution Role requires AmazonECSTaskExecutionRolePolicy for container image pulling and CloudWatch logging. This is the standard AWS managed policy for ECS task execution.",
        appliesTo: ['Policy::arn:<AWS::Partition>:iam::aws:policy/service-role/AmazonECSTaskExecutionRolePolicy']
      }
    ]);

    const taskRole = new iam.Role(this, "AiTaskRole", {
      assumedBy: new iam.ServicePrincipal("ecs-tasks.amazonaws.com"),
    });
    taskRole.addToPolicy(new iam.PolicyStatement({
      actions: [
        "bedrock:InvokeModel", 
        "bedrock:InvokeModelWithResponseStream"
      ],
      resources: [
        "arn:aws:bedrock:*::foundation-model/*",
        "arn:aws:bedrock:*:*:inference-profile/*"
      ],
    }));
    taskRole.addToPolicy(new iam.PolicyStatement({
      actions: [
        "dynamodb:PutItem",
        "dynamodb:GetItem",
        "dynamodb:UpdateItem",
        "dynamodb:DeleteItem",
        "dynamodb:Scan",
        "dynamodb:Query",
        "dynamodb:BatchWriteItem",
        "dynamodb:DescribeTable"
      ],
      resources: [
        "arn:aws:dynamodb:*:*:table/customers",
        "arn:aws:dynamodb:*:*:table/products",
        "arn:aws:dynamodb:*:*:table/search_history",
        "arn:aws:dynamodb:*:*:table/products/index/*"

      ],
    }));
    taskRole.addToPolicy(new iam.PolicyStatement({
      actions: [
        "es:ESHttpGet",
        "es:ESHttpPost",
        "es:ESHttpPut",
        "es:ESHttpDelete",
        "es:DescribeDomain",
        "es:ListDomainNames"

      ],
      resources: [
        "arn:aws:es:*:*:domain/healthcare-products-domain/*"
      ],
    }));

    // Suppress CDK-Nag for wildcard permissions in task role - apply to the role itself and its default policy
    cdk_nag.NagSuppressions.addResourceSuppressions(taskRole, [
      { 
        id: "AwsSolutions-IAM5", 
        reason: "Bedrock foundation models require wildcard permissions as model ARNs contain region wildcards. This is required for cross-region model access and inference profiles. See: https://docs.aws.amazon.com/bedrock/latest/userguide/security_iam_service-with-iam.html",
        appliesTo: [
          'Resource::arn:aws:bedrock:*::foundation-model/*',
          'Resource::arn:aws:bedrock:*:*:inference-profile/*'
        ]
      },
      { 
        id: "AwsSolutions-IAM5", 
        reason: "DynamoDB table ARNs require region wildcards for multi-region deployment flexibility. The table names are fixed and scoped to specific application tables only.",
        appliesTo: [
          'Resource::arn:aws:dynamodb:*:*:table/customers',
          'Resource::arn:aws:dynamodb:*:*:table/products', 
          'Resource::arn:aws:dynamodb:*:*:table/search_history',
          'Resource::arn:aws:dynamodb:*:*:table/products/index/*'
        ]
      },
      { 
        id: "AwsSolutions-IAM5", 
        reason: "OpenSearch domain ARN requires region wildcard for multi-region deployment flexibility. The domain name is fixed and scoped to the specific healthcare-products-domain only.",
        appliesTo: ['Resource::arn:aws:es:*:*:domain/healthcare-products-domain/*']
      }
    ], true); // Apply recursively to child resources including DefaultPolicy

    // Image (build from your docker dir)
    const dockerAsset = new ecrAssets.DockerImageAsset(this, "AiServiceImage", {
      directory: path.join(__dirname, "../../strands"),
      file: "./Dockerfile",
      platform: ecrAssets.Platform.LINUX_ARM64,     // match cpuArch
    });

    // Create a task definition
    const taskDefinition = new ecs.FargateTaskDefinition(this, "AiServiceTaskDefinition", {
      memoryLimitMiB: 512,
      cpu: 256,
      executionRole,
      taskRole,
      runtimePlatform: {
        cpuArchitecture: ecs.CpuArchitecture.ARM64,
        operatingSystemFamily: ecs.OperatingSystemFamily.LINUX,
      },
    });

    // Create SSM parameter for LOG_LEVEL to avoid direct environment variables
    const logLevelParameter = new ssm.StringParameter(this, "LogLevelParameter", {
      parameterName: `/ai-service/log-level`,
      stringValue: "INFO",
      description: "Log level for AI service container",
    });

    // Prepare container configuration with secrets instead of environment variables
    const containerConfig: any = {
      image: ecs.ContainerImage.fromDockerImageAsset(dockerAsset),
      logging: ecs.LogDrivers.awsLogs({
        streamPrefix: "ai-service",
        logGroup,
      }),
      secrets: {
        LOG_LEVEL: ecs.Secret.fromSsmParameter(logLevelParameter),
      },
      portMappings: [
        {
          containerPort: 8000, // FastApi port
          protocol: ecs.Protocol.TCP,
        },
      ],
    };

    // Grant read access to the log level parameter
    logLevelParameter.grantRead(taskRole);

    // Add SSM parameter as secret if provided
    if (props.ssmParameter) {
      containerConfig.secrets["AWS_RESOURCE_NAMES_PARAMETER"] = ecs.Secret.fromSsmParameter(props.ssmParameter);
      // Grant read access to the task role
      props.ssmParameter.grantRead(taskRole);
    }

    // Add container to the task definition
    taskDefinition.addContainer("AiServiceContainer", containerConfig);

    // Fargate service for Python AI app (AWS Strands)
    this.service = new ecs.FargateService(this, "AiService", {
      cluster: props.cluster,
      taskDefinition: taskDefinition,
      desiredCount: 2, // Running 2 instances for high availability
      assignPublicIp: false, // using private subnets with NAT gateway (see below)
      vpcSubnets: { subnetType: ec2.SubnetType.PRIVATE_WITH_EGRESS },
      circuitBreaker: {
        rollback: true,
      },
      securityGroups: [
        new ec2.SecurityGroup(this, "AiServiceSG", {
          vpc: props.vpc,
          description: "Security group for AI Fargate Service",
          allowAllOutbound: true,
        }),
      ],
      minHealthyPercent: 100,
      maxHealthyPercent: 200,
      healthCheckGracePeriod: Duration.seconds(60),
    });

    // SG inbound: allow traffic from ALB -> AI service thru port 8000
    this.service.connections.allowFrom(props.albSecurityGroup, ec2.Port.tcp(containerPort), "ALB-to-AI-8000");

    // Target group for ALB
    // Only exposing target group, caller will choose rule/conditions/priority and attach to listener of choice
    this.targetGroup = new elbv2.ApplicationTargetGroup(this, "AiServiceTargetGroup", {
      vpc: props.vpc,
      targetType: elbv2.TargetType.IP,
      protocol: elbv2.ApplicationProtocol.HTTP,
      port: containerPort,
      healthCheck: {
        path: "/health",
        interval: Duration.seconds(15),
        timeout: Duration.seconds(5),
        healthyHttpCodes: "200",
      },
      deregistrationDelay: Duration.seconds(30),
    });
    this.targetGroup.addTarget(this.service);

    // Final suppression for execution role after all grants are complete
    // This is needed because SSM parameter grants add wildcard permissions after role creation
    cdk_nag.NagSuppressions.addResourceSuppressions(executionRole, [
      { 
        id: "AwsSolutions-IAM5", 
        reason: "ECS Task Execution Role requires wildcard permissions for ECR image pulling, CloudWatch logging, and SSM parameter access. These permissions are added by CDK grants and are necessary for ECS task execution. See: https://docs.aws.amazon.com/AmazonECS/latest/developerguide/task_execution_IAM_role.html",
        appliesTo: ['Resource::*']
      }
    ], true); // Apply recursively to child resources including DefaultPolicy
  }
}

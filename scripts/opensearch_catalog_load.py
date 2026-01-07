#!/usr/bin/env python3
"""
Simple VPC Catalog Load Script
This script runs the catalog load directly in an ECS task using the existing AI service infrastructure.
"""
import boto3
import sys
import os
import time
import asyncio
from typing import Optional, Dict, Any

def get_stack_outputs() -> Dict[str, str]:
    """Get stack outputs from CloudFormation or use defaults"""
    try:
        # Get region from environment or default
        region = os.getenv('AWS_REGION', 'us-east-1')
        cf_client = boto3.client('cloudformation', region_name=region)
        
        # Find the stack - look for CxApp pattern
        stacks = cf_client.list_stacks(StackStatusFilter=['CREATE_COMPLETE', 'UPDATE_COMPLETE'])
        
        target_stack = None
        for stack in stacks['StackSummaries']:
            stack_name = stack['StackName']
            if 'CxHyperPersonalizeApp' in stack_name or 'cx-app' in stack_name.lower():
                target_stack = stack_name
                break
        
        if not target_stack:
            print("⚠️  Could not find CloudFormation stack with 'CxHyperPersonalizeApp' pattern")
            print("   Using environment variables and defaults instead")
            return {
                'AwsRegion': region,
                'OpenSearchDomainEndpoint': os.getenv('OPENSEARCH_ENDPOINT', 'Not configured'),
                'ReactUrl': 'Not available without stack'
            }
        
        print(f"✅ Found stack: {target_stack}")
        
        # Get stack outputs
        stack_details = cf_client.describe_stacks(StackName=target_stack)
        outputs = {}
        
        for output in stack_details['Stacks'][0].get('Outputs', []):
            outputs[output['OutputKey']] = output['OutputValue']
        
        return outputs
        
    except Exception as e:
        print(f"⚠️  Error getting stack outputs: {str(e)}")
        print("   Using environment variables and defaults instead")
        region = os.getenv('AWS_REGION', 'us-east-1')
        return {
            'AwsRegion': region,
            'OpenSearchDomainEndpoint': os.getenv('OPENSEARCH_ENDPOINT', 'Not configured'),
            'ReactUrl': 'Not available without stack'
        }

def get_ecs_resources(region: str) -> Dict[str, str]:
    """Get ECS cluster and task definition from the stack"""
    try:
        ecs_client = boto3.client('ecs', region_name=region)
        
        # List clusters and find the one with our pattern
        clusters = ecs_client.list_clusters()
        target_cluster = None
        
        for cluster_arn in clusters['clusterArns']:
            cluster_name = cluster_arn.split('/')[-1]
            # Look for cluster names ending with '-ecs' (CDK naming pattern)
            if cluster_name.endswith('-ecs') or 'CxHyperPersonalizeApp' in cluster_name:
                target_cluster = cluster_name
                break
        
        if not target_cluster:
            print("❌ Could not find ECS cluster")
            print("Available clusters:")
            for cluster_arn in clusters['clusterArns']:
                cluster_name = cluster_arn.split('/')[-1]
                print(f"   - {cluster_name}")
            return {}
        
        print(f"✅ Found cluster: {target_cluster}")
        
        # List all task definitions and find the AI service one
        all_task_defs = ecs_client.list_task_definitions()
        
        # Look for task definitions that contain "AiService" in their name
        ai_task_defs = [td for td in all_task_defs['taskDefinitionArns'] if 'AiService' in td]
        
        if not ai_task_defs:
            print("❌ Could not find AI service task definition")
            print("Available task definitions:")
            for td in all_task_defs['taskDefinitionArns']:
                print(f"   - {td}")
            return {}
        
        # Get the latest AI task definition (highest revision number)
        latest_task_def = sorted(ai_task_defs)[-1]
        print(f"✅ Found AI task definition: {latest_task_def}")
        
        return {
            'cluster': target_cluster,
            'task_definition': latest_task_def
        }
        
    except Exception as e:
        print(f"❌ Error getting ECS resources: {str(e)}")
        return {}

def get_network_config(cluster_name: str, region: str) -> Optional[Dict[str, Any]]:
    """Get network configuration from existing AI service"""
    try:
        ecs_client = boto3.client('ecs', region_name=region)
        
        # List services in the cluster
        services = ecs_client.list_services(cluster=cluster_name)
        
        if not services['serviceArns']:
            print("❌ No services found in cluster")
            return None
        
        # Find the AI service
        ai_service = None
        for service_arn in services['serviceArns']:
            service_name = service_arn.split('/')[-1]
            if 'AiService' in service_name or 'Ai' in service_name:
                ai_service = service_arn
                break
        
        if not ai_service:
            print("❌ Could not find AI service")
            print("Available services:")
            for service_arn in services['serviceArns']:
                service_name = service_arn.split('/')[-1]
                print(f"   - {service_name}")
            return None
        
        # Get service details
        service_details = ecs_client.describe_services(
            cluster=cluster_name,
            services=[ai_service]
        )
        
        service = service_details['services'][0]
        network_config = service.get('networkConfiguration', {}).get('awsvpcConfiguration', {})
        
        return {
            'subnets': network_config.get('subnets', []),
            'securityGroups': network_config.get('securityGroups', []),
            'assignPublicIp': network_config.get('assignPublicIp', 'ENABLED')
        }
        
    except Exception as e:
        print(f"❌ Error getting network configuration: {str(e)}")
        return None

def run_catalog_load_task(cluster_name: str, task_definition: str, network_config: Dict[str, Any], region: str) -> bool:
    """Run the catalog load as an ECS task"""
    try:
        ecs_client = boto3.client('ecs', region_name=region)
        
        print(f"🚀 Starting catalog load task...")
        print(f"   Cluster: {cluster_name}")
        print(f"   Task Definition: {task_definition}")
        print(f"   Network: {len(network_config['subnets'])} subnets, {len(network_config['securityGroups'])} security groups")
        
        # Run the task with command override
        response = ecs_client.run_task(
            cluster=cluster_name,
            taskDefinition=task_definition,
            launchType='FARGATE',
            networkConfiguration={
                'awsvpcConfiguration': network_config
            },
            overrides={
                'containerOverrides': [
                    {
                        'name': 'AiServiceContainer',  # This should match the container name in the task definition
                        'command': ['python', 'run_catalog_load.py', '--auto-confirm']
                    }
                ]
            }
        )
        
        if response['failures']:
            print("❌ Task failed to start:")
            for failure in response['failures']:
                print(f"   {failure['reason']}: {failure.get('detail', 'No details')}")
            return False
        
        task_arn = response['tasks'][0]['taskArn']
        task_id = task_arn.split('/')[-1]
        
        print(f"✅ Task started successfully!")
        print(f"   Task ARN: {task_arn}")
        print(f"   Task ID: {task_id}")
        
        # Monitor the task
        return monitor_task(cluster_name, task_arn, region)
        
    except Exception as e:
        print(f"❌ Error running task: {str(e)}")
        return False

def monitor_task(cluster_name: str, task_arn: str, region: str) -> bool:
    """Monitor the ECS task until completion"""
    try:
        ecs_client = boto3.client('ecs', region_name=region)
        task_id = task_arn.split('/')[-1]
        
        print(f"\n🔍 Monitoring task progress...")
        print(f"   Task ID: {task_id}")
        print(f"   You can monitor in AWS Console: ECS > Clusters > {cluster_name} > Tasks")
        
        while True:
            response = ecs_client.describe_tasks(
                cluster=cluster_name,
                tasks=[task_arn]
            )
            
            if not response['tasks']:
                print("❌ Task not found")
                return False
            
            task = response['tasks'][0]
            last_status = task['lastStatus']
            desired_status = task['desiredStatus']
            
            print(f"   Status: {last_status} (desired: {desired_status})")
            
            if last_status == 'STOPPED':
                # Check exit code
                containers = task.get('containers', [])
                if containers:
                    container = containers[0]
                    exit_code = container.get('exitCode', -1)
                    reason = container.get('reason', 'Unknown')
                    
                    print(f"\n📊 Task Completion Details:")
                    print(f"   Exit Code: {exit_code}")
                    print(f"   Reason: {reason}")
                    
                    if 'stoppedReason' in task:
                        print(f"   Stopped Reason: {task['stoppedReason']}")
                    
                    # Try to get CloudWatch logs
                    get_task_logs(cluster_name, task_id, region)
                    
                    if exit_code == 0:
                        print("\n✅ Catalog load completed successfully!")
                        return True
                    else:
                        print(f"\n❌ Catalog load failed with exit code: {exit_code}")
                        return False
                break
            
            asyncio.sleep(10)
        
        return False
        
    except Exception as e:
        print(f"❌ Error monitoring task: {str(e)}")
        return False

def get_task_logs(cluster_name: str, task_id: str, region: str):
    """Try to retrieve CloudWatch logs for the task"""
    try:
        logs_client = boto3.client('logs', region_name=region)
        
        # Common log group patterns for ECS tasks
        log_groups = [
            f"/ecs/{cluster_name}",
            f"/aws/ecs/containerinsights/{cluster_name}/performance",
            f"/ecs/ai-service"
        ]
        
        print(f"\n📋 Attempting to retrieve logs...")
        
        for log_group in log_groups:
            try:
                # List log streams in this group
                streams = logs_client.describe_log_streams(
                    logGroupName=log_group,
                    orderBy='LastEventTime',
                    descending=True,
                    limit=10
                )
                
                # Look for streams containing our task ID
                for stream in streams['logStreams']:
                    if task_id in stream['logStreamName']:
                        print(f"   Found log stream: {stream['logStreamName']}")
                        
                        # Get recent log events
                        events = logs_client.get_log_events(
                            logGroupName=log_group,
                            logStreamName=stream['logStreamName'],
                            startFromHead=False,
                            limit=20
                        )
                        
                        if events['events']:
                            print(f"\n📋 Recent logs from {log_group}:")
                            print("=" * 80)
                            for event in events['events'][-10:]:  # Show last 10 entries
                                timestamp = time.strftime('%Y-%m-%d %H:%M:%S', time.localtime(event['timestamp'] / 1000))
                                message = event['message'].strip()
                                print(f"[{timestamp}] {message}")
                            print("=" * 80)
                            return
                        
            except logs_client.exceptions.ResourceNotFoundException:
                continue
            except Exception as e:
                print(f"   Error checking log group {log_group}: {str(e)}")
                continue
        
        print("   ⚠️  No logs found. Check CloudWatch Logs manually:")
        print(f"      - Log Groups: {', '.join(log_groups)}")
        print(f"      - Look for streams containing: {task_id}")
        
    except Exception as e:
        print(f"   ❌ Error retrieving logs: {str(e)}")

def main():
    """Main function"""
    print("🏥 Simple VPC Catalog Loader")
    print("=" * 80)
    print("This script runs the catalog load in your existing ECS infrastructure")
    print("=" * 80)
    
    # Get stack outputs
    print("\n🔍 Getting CloudFormation stack information...")
    outputs = get_stack_outputs()
    
    # Extract region from outputs or use default
    region = outputs.get('AwsRegion', os.getenv('AWS_REGION', 'us-east-1'))
    print(f"✅ Using region: {region}")
    
    # Get ECS resources
    print("\n🔍 Getting ECS resources...")
    ecs_resources = get_ecs_resources(region)
    
    if not ecs_resources:
        print("❌ Could not get ECS resources")
        return False
    
    cluster_name = ecs_resources['cluster']
    task_definition = ecs_resources['task_definition']
    
    print(f"✅ Found cluster: {cluster_name}")
    print(f"✅ Found task definition: {task_definition}")
    
    # Get network configuration
    print("\n🔍 Getting network configuration...")
    network_config = get_network_config(cluster_name, region)
    
    if not network_config:
        print("❌ Could not get network configuration")
        return False
    
    print(f"✅ Network configuration ready")
    
    # Show what we found
    print(f"\n📋 Configuration Summary:")
    print(f"   OpenSearch Endpoint: {outputs.get('OpenSearchDomainEndpoint', 'Not found')}")
    print(f"   S3 Bucket: {outputs.get('S3 Bucket (Images)', 'Not found')}")
    print(f"   DynamoDB Tables: customers, products, search_history")
    
    # Run the catalog load
    print(f"\n🚀 Starting catalog load...")
    success = run_catalog_load_task(cluster_name, task_definition, network_config, region)
    
    if success:
        print(f"\n🎉 Catalog load completed successfully!")
        print(f"   Your product data is now loaded and ready!")
        print(f"   Frontend URL: https://{outputs.get('ReactUrl', 'Not found').replace('https://', '')}")
    else:
        print(f"\n❌ Catalog load failed.")
        print(f"   Check the logs above for error details.")
    
    return success

if __name__ == "__main__":
    try:
        success = main()
        sys.exit(0 if success else 1)
    except KeyboardInterrupt:
        print("\n\nOperation cancelled by user.")
        sys.exit(1)
    except Exception as e:
        print(f"\n❌ Unexpected error: {str(e)}")
        import traceback
        traceback.print_exc()
        sys.exit(1)

#!/usr/bin/env python3
"""
Helper script to run the catalog load script in ECS Fargate within the VPC.
This script creates and runs an ECS task to execute the catalog load with proper VPC connectivity.
"""
import boto3
import time
import sys
import argparse
import os
import asyncio
from botocore.exceptions import ClientError

def load_env_config():
    """Load configuration from .env file"""
    env_config = {}
    env_file_path = os.path.join(os.path.dirname(__file__), '..', 'strands', '.env')
    
    if os.path.exists(env_file_path):
        with open(env_file_path, 'r') as f:
            for line in f:
                line = line.strip()
                if line and not line.startswith('#') and '=' in line:
                    key, value = line.split('=', 1)
                    env_config[key.strip()] = value.strip()
    
    return env_config

def get_target_region():
    """Get the target AWS region from configuration"""
    # First try environment variables
    region = os.getenv('AWS_REGION')
    if region:
        return region
    
    # Then try .env file
    env_config = load_env_config()
    region = env_config.get('AWS_REGION')
    if region:
        return region
    
    # Finally fall back to session region
    session = boto3.Session()
    return session.region_name or 'us-west-2'

def get_stack_resources():
    """Get the ECS cluster and task definition from CloudFormation stack"""
    try:
        # Get target region and create region-specific client
        target_region = get_target_region()
        print(f"🔍 Using region: {target_region}")
        
        # Try to find the stack by looking for common patterns
        cf_client = boto3.client('cloudformation', region_name=target_region)
        
        # List stacks and find the one with our resources
        stacks = cf_client.list_stacks(StackStatusFilter=['CREATE_COMPLETE', 'UPDATE_COMPLETE'])
        
        target_stack = None
        for stack in stacks['StackSummaries']:
            stack_name = stack['StackName']
            if 'cx' in stack_name.lower() or 'healthcare' in stack_name.lower():
                target_stack = stack_name
                break
        
        if not target_stack:
            print("❌ Could not find CloudFormation stack. Please specify manually.")
            return None, None, None
        
        print(f"🔍 Found stack: {target_stack}")
        
        # Get stack resources
        resources = cf_client.describe_stack_resources(StackName=target_stack)
        
        cluster_name = None
        task_definition_arn = None
        
        for resource in resources['StackResources']:
            if resource['ResourceType'] == 'AWS::ECS::Cluster':
                cluster_name = resource['PhysicalResourceId']
            elif resource['ResourceType'] == 'AWS::ECS::TaskDefinition' and 'Ai' in resource['LogicalResourceId']:
                task_definition_arn = resource['PhysicalResourceId']
        
        return target_stack, cluster_name, task_definition_arn
        
    except Exception as e:
        print(f"❌ Error getting stack resources: {str(e)}")
        return None, None, None

def get_task_definition_details(task_definition_arn):
    """Get details from the AI service task definition"""
    try:
        target_region = get_target_region()
        ecs_client = boto3.client('ecs', region_name=target_region)
        
        response = ecs_client.describe_task_definition(taskDefinition=task_definition_arn)
        task_def = response['taskDefinition']
        
        # Extract network configuration from the task definition
        network_mode = task_def.get('networkMode', 'awsvpc')
        requires_attributes = task_def.get('requiresAttributes', [])
        
        # Get the container definition
        containers = task_def.get('containerDefinitions', [])
        if not containers:
            print("❌ No containers found in task definition")
            return None
        
        container = containers[0]  # Use the first container
        
        return {
            'family': task_def['family'],
            'taskRoleArn': task_def.get('taskRoleArn'),
            'executionRoleArn': task_def.get('executionRoleArn'),
            'networkMode': network_mode,
            'cpu': task_def.get('cpu'),
            'memory': task_def.get('memory'),
            'containerName': container['name'],
            'image': container['image']
        }
        
    except Exception as e:
        print(f"❌ Error getting task definition details: {str(e)}")
        return None

def get_network_configuration(cluster_name):
    """Get network configuration from existing AI service"""
    try:
        target_region = get_target_region()
        ecs_client = boto3.client('ecs', region_name=target_region)
        
        # List services in the cluster
        services = ecs_client.list_services(cluster=cluster_name)
        
        if not services['serviceArns']:
            print("❌ No services found in cluster")
            return None
        
        # Get the first service (should be the AI service)
        service_arn = services['serviceArns'][0]
        service_details = ecs_client.describe_services(
            cluster=cluster_name,
            services=[service_arn]
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

def run_catalog_load_task(cluster_name, task_definition_arn, network_config, script_args=None):
    """Run the catalog load script as an ECS task"""
    try:
        target_region = get_target_region()
        ecs_client = boto3.client('ecs', region_name=target_region)
        
        # Get task definition details
        task_details = get_task_definition_details(task_definition_arn)
        if not task_details:
            return False
        
        # Prepare the command override - use correct path in container
        base_command = ["python", "run_catalog_load.py"]
        if script_args:
            base_command.extend(script_args)
        
        # Create the task override
        overrides = {
            'containerOverrides': [
                {
                    'name': task_details['containerName'],
                    'command': base_command
                }
            ]
        }
        
        print(f"🚀 Starting ECS task with command: {' '.join(base_command)}")
        print(f"   Cluster: {cluster_name}")
        print(f"   Task Definition: {task_definition_arn}")
        print(f"   Network: {len(network_config['subnets'])} subnets, {len(network_config['securityGroups'])} security groups")
        
        # Run the task
        response = ecs_client.run_task(
            cluster=cluster_name,
            taskDefinition=task_definition_arn,
            launchType='FARGATE',
            networkConfiguration={
                'awsvpcConfiguration': network_config
            },
            overrides=overrides
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
        print(f"\n🔍 Monitoring task progress...")
        return monitor_task(cluster_name, task_arn)
        
    except Exception as e:
        print(f"❌ Error running task: {str(e)}")
        return False

def get_cloudwatch_logs(task_arn, container_name, cluster_name):
    """Retrieve CloudWatch logs for the task"""
    try:
        target_region = get_target_region()
        logs_client = boto3.client('logs', region_name=target_region)
        
        # Extract task ID from ARN
        task_id = task_arn.split('/')[-1]
        
        # Construct log group and stream names
        log_group = f"/ecs/{cluster_name}"
        log_stream = f"ai-service/{container_name}/{task_id}"
        
        print(f"\n🔍 Retrieving CloudWatch logs...")
        print(f"   Log Group: {log_group}")
        print(f"   Log Stream: {log_stream}")
        
        try:
            # Get log events
            response = logs_client.get_log_events(
                logGroupName=log_group,
                logStreamName=log_stream,
                startFromHead=True
            )
            
            events = response.get('events', [])
            if events:
                print(f"\n📋 Task Logs ({len(events)} entries):")
                print("=" * 80)
                for event in events[-20:]:  # Show last 20 log entries
                    timestamp = time.strftime('%Y-%m-%d %H:%M:%S', time.localtime(event['timestamp'] / 1000))
                    message = event['message'].strip()
                    print(f"[{timestamp}] {message}")
                print("=" * 80)
            else:
                print("   ⚠️  No log events found")
                
        except logs_client.exceptions.ResourceNotFoundException:
            print("   ⚠️  Log group or stream not found")
            print(f"   💡 Try checking these log locations:")
            print(f"      - /aws/ecs/containerinsights/{cluster_name}/performance")
            print(f"      - /ecs/{cluster_name}")
            print(f"      - Look for streams containing: {task_id}")
            
    except Exception as e:
        print(f"   ❌ Error retrieving logs: {str(e)}")

def monitor_task(cluster_name, task_arn):
    """Monitor the ECS task and show logs"""
    try:
        target_region = get_target_region()
        ecs_client = boto3.client('ecs', region_name=target_region)
        
        task_id = task_arn.split('/')[-1]
        
        print(f"   Task ID: {task_id}")
        print(f"   You can also monitor in AWS Console: ECS > Clusters > {cluster_name} > Tasks")
        
        container_name = None
        
        # Wait for task to complete
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
            
            # Get container name for logs
            if not container_name and task.get('containers'):
                container_name = task['containers'][0]['name']
            
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
                    
                    # Get more detailed failure information
                    if 'stoppedReason' in task:
                        print(f"   Stopped Reason: {task['stoppedReason']}")
                    
                    # Retrieve CloudWatch logs
                    if container_name:
                        get_cloudwatch_logs(task_arn, container_name, cluster_name)
                    
                    if exit_code == 0:
                        print("\n✅ Task completed successfully!")
                        return True
                    else:
                        print(f"\n❌ Task failed with exit code: {exit_code}")
                        
                        # Provide troubleshooting guidance
                        print(f"\n🔧 Troubleshooting Steps:")
                        print(f"   1. Check the logs above for specific error messages")
                        print(f"   2. Verify the catalog file exists in the container")
                        print(f"   3. Check IAM permissions for OpenSearch, DynamoDB, and Bedrock")
                        print(f"   4. Ensure security groups allow OpenSearch access")
                        print(f"   5. Verify OpenSearch domain is healthy")
                        
                        return False
                break
            
            asyncio.sleep(10)
        
        return False
        
    except Exception as e:
        print(f"❌ Error monitoring task: {str(e)}")
        return False

def check_prerequisites(cluster_name, task_definition_arn):
    """Check prerequisites before running the task"""
    print("\n🔍 Checking prerequisites...")
    
    try:
        # Check ECS cluster status
        target_region = get_target_region()
        ecs_client = boto3.client('ecs', region_name=target_region)
        cluster_response = ecs_client.describe_clusters(clusters=[cluster_name])
        
        if not cluster_response['clusters']:
            print("❌ Cluster not found")
            return False
            
        cluster = cluster_response['clusters'][0]
        if cluster['status'] != 'ACTIVE':
            print(f"❌ Cluster status is {cluster['status']}, expected ACTIVE")
            return False
            
        print(f"✅ Cluster is active with {cluster['runningTasksCount']} running tasks")
        
        # Check task definition
        task_def_response = ecs_client.describe_task_definition(taskDefinition=task_definition_arn)
        task_def = task_def_response['taskDefinition']
        
        if task_def['status'] != 'ACTIVE':
            print(f"❌ Task definition status is {task_def['status']}, expected ACTIVE")
            return False
            
        print(f"✅ Task definition is active (revision {task_def['revision']})")
        
        # Check IAM roles
        task_role_arn = task_def.get('taskRoleArn')
        execution_role_arn = task_def.get('executionRoleArn')
        
        if task_role_arn:
            print(f"✅ Task role configured: {task_role_arn.split('/')[-1]}")
        else:
            print("⚠️  No task role configured")
            
        if execution_role_arn:
            print(f"✅ Execution role configured: {execution_role_arn.split('/')[-1]}")
        else:
            print("❌ No execution role configured")
            return False
        
        # Check OpenSearch domain - extract configuration from environment
        try:
            # Get configuration from environment variables or CloudFormation stack
            target_region = None
            expected_domain_name = None
            expected_endpoint = None
            
            # Try to get configuration from environment variables first
            import os
            target_region = os.getenv('AWS_REGION')
            expected_endpoint = os.getenv('OPENSEARCH_ENDPOINT')
            
            # Extract domain name from endpoint if available
            if expected_endpoint:
                # Parse domain name from endpoint like: https://vpc-healthcare-products-domain-xxx.us-west-2.es.amazonaws.com
                import re
                endpoint_match = re.search(r'vpc-([^-]+(?:-[^-]+)*)-[a-z0-9]+\.([^.]+)\.es\.amazonaws\.com', expected_endpoint)
                if endpoint_match:
                    expected_domain_name = endpoint_match.group(1)
                    endpoint_region = endpoint_match.group(2)
                    if not target_region:
                        target_region = endpoint_region
                    print(f"🔍 Extracted from endpoint: domain='{expected_domain_name}', region='{target_region}'")
            
            # If no environment config, try to get from CloudFormation stack
            if not target_region or not expected_domain_name:
                try:
                    # Use the same target region for CloudFormation client
                    cf_client = boto3.client('cloudformation', region_name=target_region if target_region else get_target_region())
                    stacks = cf_client.list_stacks(StackStatusFilter=['CREATE_COMPLETE', 'UPDATE_COMPLETE'])
                    
                    for stack in stacks['StackSummaries']:
                        stack_name = stack['StackName']
                        if 'cx' in stack_name.lower() or 'healthcare' in stack_name.lower():
                            # Get stack outputs
                            stack_details = cf_client.describe_stacks(StackName=stack_name)
                            outputs = stack_details['Stacks'][0].get('Outputs', [])
                            
                            for output in outputs:
                                if 'opensearch' in output['OutputKey'].lower() and 'endpoint' in output['OutputKey'].lower():
                                    stack_endpoint = output['OutputValue']
                                    endpoint_match = re.search(r'vpc-([^-]+(?:-[^-]+)*)-[a-z0-9]+\.([^.]+)\.es\.amazonaws\.com', stack_endpoint)
                                    if endpoint_match:
                                        expected_domain_name = endpoint_match.group(1)
                                        if not target_region:
                                            target_region = endpoint_match.group(2)
                                        print(f"🔍 Extracted from CloudFormation: domain='{expected_domain_name}', region='{target_region}'")
                                        break
                            break
                except Exception as e:
                    print(f"   ⚠️  Could not get config from CloudFormation: {str(e)}")
            
            # Fallback to current session region if still not found
            if not target_region:
                session = boto3.Session()
                target_region = session.region_name or 'us-west-2'
                print(f"🔍 Using session region: {target_region}")
            
            # Create region-specific OpenSearch client
            opensearch_client = boto3.client('opensearch', region_name=target_region)
            
            print(f"🔍 Checking OpenSearch domains in region: {target_region}")
            if expected_domain_name:
                print(f"🔍 Looking for expected domain: {expected_domain_name}")
            
            domains = opensearch_client.list_domain_names()
            healthcare_domain = None
            
            # First, try to find the expected domain name if we have it
            if expected_domain_name:
                for domain in domains['DomainNames']:
                    if domain['DomainName'] == expected_domain_name:
                        healthcare_domain = domain['DomainName']
                        print(f"✅ Found expected domain: {healthcare_domain}")
                        break
            
            # If no expected domain or not found, try pattern matching
            if not healthcare_domain:
                target_domain_patterns = ['healthcare-products-domain', 'healthcare-products', 'healthcare']
                for pattern in target_domain_patterns:
                    matching_domains = [d for d in domains['DomainNames'] if pattern in d['DomainName'].lower()]
                    if matching_domains:
                        healthcare_domain = matching_domains[0]['DomainName']
                        print(f"✅ Found pattern match for '{pattern}': {healthcare_domain}")
                        break
            
            if healthcare_domain:
                domain_info = opensearch_client.describe_domain(DomainName=healthcare_domain)
                domain_status = domain_info['DomainStatus']
                
                print(f"✅ OpenSearch domain: {healthcare_domain}")
                print(f"   Region: {target_region}")
                print(f"   Processing: {domain_status.get('Processing', 'Unknown')}")
                print(f"   Endpoint: {domain_status.get('Endpoint', 'Not available')}")
                
                # Validate endpoint matches expected if we have it
                actual_endpoint = domain_status.get('Endpoint', '')
                if expected_endpoint and actual_endpoint:
                    if expected_endpoint.replace('https://', '') == actual_endpoint:
                        print(f"✅ Endpoint matches configuration")
                    else:
                        print(f"⚠️  Endpoint mismatch:")
                        print(f"   Expected: {expected_endpoint}")
                        print(f"   Actual: https://{actual_endpoint}")
                
                if not domain_status.get('Processing', True):
                    print("✅ Domain is ready")
                else:
                    print("⚠️  Domain is still processing")
                    
                # Check if this is a VPC domain
                vpc_options = domain_status.get('VPCOptions', {})
                if vpc_options:
                    print(f"✅ VPC domain detected")
                    print(f"   VPC ID: {vpc_options.get('VPCId', 'Unknown')}")
                    print(f"   Subnets: {len(vpc_options.get('SubnetIds', []))}")
                    print(f"   Security Groups: {len(vpc_options.get('SecurityGroupIds', []))}")
                else:
                    print("⚠️  Public domain (not VPC)")
            else:
                print(f"⚠️  No healthcare OpenSearch domain found in {target_region}")
                print(f"   Available domains: {[d['DomainName'] for d in domains['DomainNames']]}")
                
        except Exception as e:
            print(f"⚠️  Could not check OpenSearch domain: {str(e)}")
        
        return True
        
    except Exception as e:
        print(f"❌ Error checking prerequisites: {str(e)}")
        return False

def main():
    """Main function"""
    parser = argparse.ArgumentParser(description='Run catalog load script in ECS Fargate within VPC')
    parser.add_argument('--cluster', help='ECS cluster name (auto-detected if not provided)')
    parser.add_argument('--task-definition', help='Task definition ARN (auto-detected if not provided)')
    parser.add_argument('--products-only', action='store_true', help='Load products only')
    parser.add_argument('--customers-only', action='store_true', help='Load customers only')
    parser.add_argument('--skip-opensearch-health', action='store_true', help='Skip OpenSearch health check')
    parser.add_argument('--auto-confirm', '-y', action='store_true', help='Auto-confirm all prompts')
    parser.add_argument('--skip-prereq-check', action='store_true', help='Skip prerequisite checks')
    
    args = parser.parse_args()
    
    print("🏥 Healthcare Data Loader - VPC Runner")
    print("=" * 80)
    print("This script runs the catalog load within ECS Fargate for VPC OpenSearch access")
    print("=" * 80)
    
    # Get cluster and task definition
    if args.cluster and args.task_definition:
        cluster_name = args.cluster
        task_definition_arn = args.task_definition
        stack_name = "manual"
    else:
        print("🔍 Auto-detecting ECS resources...")
        stack_name, cluster_name, task_definition_arn = get_stack_resources()
        
        if not cluster_name or not task_definition_arn:
            print("❌ Could not auto-detect resources. Please specify --cluster and --task-definition")
            return False
    
    print(f"✅ Using cluster: {cluster_name}")
    print(f"✅ Using task definition: {task_definition_arn}")
    
    # Get network configuration
    print("🔍 Getting network configuration...")
    network_config = get_network_configuration(cluster_name)
    if not network_config:
        print("❌ Could not get network configuration")
        return False
    
    print(f"✅ Network configuration ready")
    
    # Check prerequisites unless skipped
    if not args.skip_prereq_check:
        prereq_ok = check_prerequisites(cluster_name, task_definition_arn)
        if not prereq_ok:
            print("\n❌ Prerequisite checks failed. Use --skip-prereq-check to bypass.")
            return False
    else:
        print("⏭️  Skipping prerequisite checks")
    
    # Prepare script arguments
    script_args = ['--auto-confirm']  # Always auto-confirm in ECS
    
    if args.products_only:
        script_args.append('--products-only')
    elif args.customers_only:
        script_args.append('--customers-only')
    
    if args.skip_opensearch_health:
        script_args.append('--skip-opensearch-health')
    
    # Run the task
    print("\n🚀 Starting catalog load task...")
    success = run_catalog_load_task(cluster_name, task_definition_arn, network_config, script_args)
    
    if success:
        print("\n🎉 Catalog load completed successfully!")
        print("   Your data is now loaded and ready for use.")
    else:
        print("\n❌ Catalog load failed.")
        print("   Check the ECS task logs in CloudWatch for more details.")
    
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

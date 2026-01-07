import json
import boto3
import logging
from botocore.exceptions import ClientError

logger = logging.getLogger()
logger.setLevel(logging.INFO)

def lambda_handler(event, context):
    """
    Custom resource Lambda function to create OpenSearch service-linked role
    """
    logger.info(f"Received event: {json.dumps(event)}")
    
    request_type = event.get('RequestType')
    
    try:
        if request_type == 'Create' or request_type == 'Update':
            return create_service_linked_role(event, context)
        elif request_type == 'Delete':
            return delete_service_linked_role(event, context)
        else:
            logger.error(f"Unknown request type: {request_type}")
            return send_response(event, context, 'FAILED', f"Unknown request type: {request_type}")
    
    except Exception as e:
        logger.error(f"Error processing request: {str(e)}")
        return send_response(event, context, 'FAILED', str(e))

def create_service_linked_role(event, context):
    """
    Create the OpenSearch service-linked role if it doesn't exist
    """
    iam_client = boto3.client('iam')
    
    service_name = 'opensearch.amazonaws.com'
    role_name = 'AWSServiceRoleForAmazonOpenSearchService'
    
    try:
        # Check if the service-linked role already exists
        logger.info(f"Checking if service-linked role {role_name} exists...")
        try:
            response = iam_client.get_role(RoleName=role_name)
            logger.info(f"Service-linked role {role_name} already exists")
            return send_response(event, context, 'SUCCESS', 
                               f"Service-linked role {role_name} already exists",
                               {'ServiceLinkedRoleName': role_name})
        except ClientError as e:
            if e.response['Error']['Code'] == 'NoSuchEntity':
                logger.info(f"Service-linked role {role_name} does not exist, creating...")
            else:
                raise e
        
        # Create the service-linked role
        logger.info(f"Creating service-linked role for {service_name}")
        response = iam_client.create_service_linked_role(
            AWSServiceName=service_name,
            Description='Service-linked role for Amazon OpenSearch Service to access VPC resources'
        )
        
        role_arn = response['Role']['Arn']
        created_role_name = response['Role']['RoleName']
        
        logger.info(f"Successfully created service-linked role: {created_role_name}")
        logger.info(f"Role ARN: {role_arn}")
        
        return send_response(event, context, 'SUCCESS', 
                           f"Successfully created service-linked role {created_role_name}",
                           {'ServiceLinkedRoleName': created_role_name, 'ServiceLinkedRoleArn': role_arn})
        
    except ClientError as e:
        error_code = e.response['Error']['Code']
        if error_code == 'InvalidInput':
            # Role already exists
            logger.info(f"Service-linked role for {service_name} already exists")
            return send_response(event, context, 'SUCCESS', 
                               f"Service-linked role for {service_name} already exists",
                               {'ServiceLinkedRoleName': role_name})
        else:
            logger.error(f"Failed to create service-linked role: {e}")
            return send_response(event, context, 'FAILED', str(e))

def delete_service_linked_role(event, context):
    """
    Handle deletion of the service-linked role (typically we don't delete service-linked roles)
    """
    logger.info("Delete event received - service-linked roles are typically not deleted")
    return send_response(event, context, 'SUCCESS', 
                       "Delete request acknowledged - service-linked roles are retained for account security")

def send_response(event, context, response_status, reason, response_data=None):
    """
    Send response back to CloudFormation
    """
    if response_data is None:
        response_data = {}
    
    response_url = event['ResponseURL']
    
    logger.info(f"Sending {response_status} response to CloudFormation")
    
    response_body = {
        'Status': response_status,
        'Reason': reason,
        'PhysicalResourceId': event.get('LogicalResourceId', context.log_stream_name),
        'StackId': event['StackId'],
        'RequestId': event['RequestId'],
        'LogicalResourceId': event['LogicalResourceId'],
        'Data': response_data
    }
    
    json_response_body = json.dumps(response_body)
    
    logger.info(f"Response body: {json_response_body}")
    
    headers = {
        'content-type': '',
        'content-length': str(len(json_response_body))
    }
    
    try:
        import urllib3
        http = urllib3.PoolManager()
        response = http.request('PUT', response_url, body=json_response_body, headers=headers)
        logger.info(f"Status code: {response.status}")
        return response_body
    except Exception as e:
        logger.error(f"Failed to send response: {e}")
        raise e

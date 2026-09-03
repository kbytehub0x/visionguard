import boto3, os, json
from datetime import datetime

dynamodb = boto3.resource('dynamodb')
table = dynamodb.Table(os.environ.get('TABLE_NAME', 'VisionGuard_Incidents'))

def lambda_handler(event, context):
    table.update_item(
        Key={
            'PK': f"INCIDENT#{event.get('incident_id', 'UNKNOWN')}",
            'SK': f"TIMESTAMP#{datetime.utcnow().isoformat()}Z"
        },
        UpdateExpression='SET #s = :s, final_result = :r',
        ExpressionAttributeNames={'#s': 'status'},
        ExpressionAttributeValues={
            ':s': 'RESOLVED',
            ':r': json.dumps(event)
        }
    )
    return {'status': 'audit_written'}

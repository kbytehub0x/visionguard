import boto3, os, json
from datetime import datetime

dynamodb = boto3.resource('dynamodb')
table = dynamodb.Table(os.environ.get('TABLE_NAME', 'VisionGuard_Incidents'))

def lambda_handler(event, context):
    table.put_item(Item={
        'PK': f"INCIDENT#{event['incident_id']}",
        'SK': f"TIMESTAMP#{datetime.utcnow().isoformat()}Z",
        'status': 'QUEUED',
        'agent_loop_count': 0,
        **{k: event[k] for k in ['incident_id', 'video_s3_uri', 'zone_id', 'camera_id'] if k in event}
    })
    return event

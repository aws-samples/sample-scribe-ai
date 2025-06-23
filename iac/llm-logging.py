import os
import gzip
import json
import base64
import boto3
from datetime import datetime

s3 = boto3.client("s3")


def lambda_handler(event, context):
    cw_data = event['awslogs']['data']
    compressed_payload = base64.b64decode(cw_data)
    uncompressed_payload = gzip.decompress(compressed_payload)
    payload = json.loads(uncompressed_payload)
    log_events = payload['logEvents']
    for log_event in log_events:
        if log_event['message'].startswith('LLM: '):
            json_string = log_event['message'][5:]
            ts = log_event['timestamp']
            print("timestamp =", ts)
            dt = datetime.fromtimestamp(ts/1000)
            ts_str = dt.strftime("%Y/%m/%d")
            key = f"{ts_str}/{ts}.json"

            print("writing llm log to s3")
            s3.put_object(Body=json_string,
                          ContentType="application/json",
                          Bucket=os.getenv("S3_BUCKET"),
                          Key=key,
                          )
            print("done")

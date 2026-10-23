# Deadline Board

A serverless web app for tracking bursary and job applications, sorted by soonest deadline.

## How it works
- The page is served privately from S3 through CloudFront
- API Gateway and a Python Lambda function handle adding, listing, updating and deleting entries
- DynamoDB stores the data
- The whole stack is defined as code in AWS SAM (`template.yaml`)

## Project structure
- `template.yaml`: AWS infrastructure
- `src/app.py`: Lambda function (Python)
- `frontend/index.html`: web page

## Deploy
Requires an AWS account, the AWS CLI and the AWS SAM CLI.

```
sam build
sam deploy --guided
aws s3 sync frontend/ s3://YOUR_BUCKET_NAME
```

The bucket name is shown in the stack outputs after deploying.

## Limitations and next steps
- There's no login yet, so anyone with the link can edit entries. Adding Amazon Cognito is the next step.

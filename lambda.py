import os
import boto3
lambda_handlers = {
    "{}_denormalize_topics".format(os.environ.get("RUNTIME_ENVIRONMENT")),
    "{}_denormalize_polls".format(os.environ.get("RUNTIME_ENVIRONMENT")),
    "{}_denormalize_feedback_requests".format(os.environ.get("RUNTIME_ENVIRONMENT")),
    "{}_denormalize_reviews".format(os.environ.get("RUNTIME_ENVIRONMENT")),
    "{}_denormalize_feedbacks".format(os.environ.get("RUNTIME_ENVIRONMENT")),
    "{}_denormalize_new_goals".format(os.environ.get("RUNTIME_ENVIRONMENT")),
    "{}_denormalize_goals".format(os.environ.get("RUNTIME_ENVIRONMENT")),
    "{}_denormalize_applications".format(os.environ.get("RUNTIME_ENVIRONMENT")),
    "{}_denormalize_employee_login".format(os.environ.get("RUNTIME_ENVIRONMENT")),
    "{}_denormalize_new_surveys_stream".format(os.environ.get("RUNTIME_ENVIRONMENT")),
    "{}_regress_surveys_stream".format(os.environ.get("RUNTIME_ENVIRONMENT")),
    "{}_denormalize_cron".format(os.environ.get("RUNTIME_ENVIRONMENT")),
    "{}_denormalize_conversations".format(os.environ.get("RUNTIME_ENVIRONMENT")),
    "{}_denormalize_reward_redemptions".format(os.environ.get("RUNTIME_ENVIRONMENT"))
}
s3 = boto3.client("s3")
filename = "Archive.zip"
bucket = "reflektive-denormalizer-packages"
with open(filename, "rb") as f:
    zipped_code = f.read()

params = {
    "Bucket": bucket,
    "Key": filename,
}
sent = s3.put_object(Body=zipped_code, **params)

lambda_client = boto3.client("lambda")
for lambda_name in lambda_handlers:
    print(lambda_name)
    result = lambda_client.update_function_code(
        FunctionName=lambda_name,
        S3Bucket=bucket,
        S3Key=filename
    )

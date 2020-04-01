import boto3
lambda_handlers = {
    # "integration_denormalize_topics",
    "integration_denormalize_polls",
    # "integration_denormalize_feedback_requests",
    # "integration_denormalize_reviews",
    # "integration_denormalize_feedbacks",
    # "integration_denormalize_new_goals",
    # "integration_denormalize_goals",
    # "integration_denormalize_applications",
    # "integration_denormalize_employee_login",
    # "integration_denormalize_new_surveys_stream",
    # "integration_regress_surveys_stream",
    # "integration_denormalize_cron",
    # "integration_denormalize_conversations",
    # "integration_denormalize_reward_redemptions"
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

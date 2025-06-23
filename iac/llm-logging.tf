# zip the source code
data "archive_file" "llm_logs" {
  type        = "zip"
  source_file = "llm-logging.py"
  output_path = ".archive/lambda.zip"
}

resource "aws_lambda_function" "log_to_s3" {
  function_name    = "${var.name}-llm-logs-s3"
  description      = "filters app logs for llm logs and writes them to s3"
  runtime          = "python3.13"
  filename         = data.archive_file.llm_logs.output_path
  source_code_hash = filebase64sha256(data.archive_file.llm_logs.output_path)
  handler          = "llm-logging.lambda_handler"
  role             = aws_iam_role.lambda_llm_logs.arn
  environment {
    variables = {
      S3_BUCKET = aws_s3_bucket.llm_logs.id
    }
  }
}

resource "aws_iam_role" "lambda_llm_logs" {
  name = "${var.name}_llm_logs_lambda_execution_role"

  assume_role_policy = jsonencode({
    Version = "2012-10-17",
    Statement = [{
      Effect = "Allow",
      Principal = {
        Service = "lambda.amazonaws.com"
      },
      Action = "sts:AssumeRole"
    }]
  })
}

# allow lambda to write to bucket
resource "aws_iam_role_policy" "lambda_llm_logs" {
  name = "${var.name}_llm_logs_lambda_execution_role"
  role = aws_iam_role.lambda_llm_logs.id
  policy = jsonencode({
    Version = "2012-10-17",
    Statement = [{
      Effect   = "Allow"
      Action   = "s3:PutObject"
      Resource = "${aws_s3_bucket.llm_logs.arn}/*"
    }]
  })
}

# run the lambda against each log
resource "aws_cloudwatch_log_subscription_filter" "llm_logs" {
  name            = "${var.name}-llm-logs-s3"
  log_group_name  = "${module.ecs_cluster.cloudwatch_log_group_name}/${var.container_name}"
  destination_arn = aws_lambda_function.log_to_s3.arn
  filter_pattern  = ""
  depends_on      = [module.ecs_service]
}

resource "aws_lambda_permission" "llm_logs" {
  statement_id   = "invoked_by_container_app_logs"
  action         = "lambda:InvokeFunction"
  principal      = "logs.${local.region}.amazonaws.com"
  function_name  = aws_lambda_function.log_to_s3.function_name
  source_arn     = "${module.ecs_cluster.cloudwatch_log_group_arn}/${var.container_name}:*"
  source_account = local.account_id
}

resource "aws_iam_role_policy_attachment" "lambda_basic_execution" {
  role       = aws_iam_role.lambda_llm_logs.name
  policy_arn = "arn:aws:iam::aws:policy/service-role/AWSLambdaBasicExecutionRole"
}

resource "aws_iam_role_policy_attachment" "cw_subscription" {
  role       = aws_iam_role.lambda_llm_logs.name
  policy_arn = "arn:aws:iam::aws:policy/CloudWatchLogsFullAccess"
}

resource "aws_cloudwatch_log_group" "llm_logs" {
  name              = "/aws/lambda/${aws_lambda_function.log_to_s3.function_name}"
  retention_in_days = 7
}

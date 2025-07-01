locals {

  https_endpoint = aws_apigatewayv2_api.main.api_endpoint
  callback_path  = "auth/callback"

  cognito_domain = "${aws_cognito_user_pool_domain.main.domain}.auth.${local.region}.amazoncognito.com"
}

resource "aws_cognito_user_pool" "main" {
  name = "${var.name}-user-pool"

  # Password policy
  password_policy {
    minimum_length    = 8
    require_lowercase = true
    require_numbers   = true
    require_symbols   = true
    require_uppercase = true
  }

  # Username configuration
  username_configuration {
    case_sensitive = false
  }

  # MFA configuration
  mfa_configuration = "OFF"

  # Account recovery setting
  account_recovery_setting {
    recovery_mechanism {
      name     = "verified_email"
      priority = 1
    }
  }

  # Email configuration
  email_configuration {
    email_sending_account = "COGNITO_DEFAULT"
  }

  # Schema attributes
  schema {
    name                = "email"
    attribute_data_type = "String"
    mutable             = true
    required            = true

    string_attribute_constraints {
      min_length = 3
      max_length = 255
    }
  }

  # Auto verify attributes
  auto_verified_attributes = ["email"]
}

# Create an app client
resource "aws_cognito_user_pool_client" "client" {
  name         = "${var.name}-client"
  user_pool_id = aws_cognito_user_pool.main.id

  generate_secret = true

  explicit_auth_flows = [
    "ALLOW_USER_PASSWORD_AUTH",
    "ALLOW_USER_SRP_AUTH",
    "ALLOW_REFRESH_TOKEN_AUTH"
  ]

  # Add these new parameters
  allowed_oauth_flows                  = ["code"]
  allowed_oauth_flows_user_pool_client = true
  allowed_oauth_scopes = [
    "email",
    "openid",
    "profile"
  ]

  callback_urls = [
    "http://localhost:8080/auth/callback",
    "${local.https_endpoint}/${local.callback_path}",
  ]
  logout_urls = [
    "http://localhost:8080/index",
    "${local.https_endpoint}/index",
  ]

  supported_identity_providers = ["COGNITO"]

  # Enable managed login for this client
  auth_session_validity         = 15 # Session validity in minutes
  enable_token_revocation       = true
  prevent_user_existence_errors = "ENABLED"
}

# Create admin group
resource "aws_cognito_user_group" "admin" {
  name         = "admin"
  user_pool_id = aws_cognito_user_pool.main.id
  description  = "Admin group with elevated privileges"
  precedence   = 1
}

# Create default group
resource "aws_cognito_user_group" "default" {
  name         = "default"
  user_pool_id = aws_cognito_user_pool.main.id
  description  = "Default group for regular users"
  precedence   = 2
}

# Add a domain for the Cognito User Pool (required for managed login)
resource "aws_cognito_user_pool_domain" "main" {
  domain       = "${var.name}-login-${random_string.domain_suffix.result}"
  user_pool_id = aws_cognito_user_pool.main.id
}

# Random string to ensure domain uniqueness
resource "random_string" "domain_suffix" {
  length  = 8
  special = false
  upper   = false
}

# Configure the managed login branding
resource "awscc_cognito_managed_login_branding" "main" {
  user_pool_id = aws_cognito_user_pool.main.id
  client_id    = aws_cognito_user_pool_client.client.id

  # Note: Settings format depends on the specific Cognito UI version you're using
  settings = jsonencode({})
}

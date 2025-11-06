locals {
  model_id_haiku_3_5  = "anthropic.claude-3-5-haiku-20241022-v1:0"
  model_id_haiku_4_5  = "anthropic.claude-haiku-4-5-20251001-v1:0"
  model_id_sonnet_3_5 = "anthropic.claude-3-5-sonnet-20241022-v2:0"
  model_id_sonnet_4_0 = "anthropic.claude-sonnet-4-20250514-v1:0"
  model_id_sonnet_4_5 = "anthropic.claude-sonnet-4-5-20250929-v1:0"
  model_id_nova_sonic = "amazon.nova-sonic-v1:0"

  inference_region1 = "us-east-1"
  inference_region2 = "us-east-2"
  inference_region3 = "us-west-2"

  bedrock_arn_root = "arn:aws:bedrock:${local.region}:${local.account_id}"
}

resource "awscc_bedrock_prompt" "interview_summary" {
  name            = "${var.name}_interview_summary"
  description     = "Prompt used to generate an interview summary for reviewing"
  default_variant = "variant"

  variants = [
    {
      name          = "variant"
      template_type = "TEXT"
      model_id      = local.model_id_haiku_3_5
      inference_configuration = {
        text = {
          temperature = 1
        }
      }
      template_configuration = {
        text = {
          input_variables = [
            {
              name = "topic"
              type = "string"
            },
            {
              name = "interview"
              type = "string"

            }
          ]
          text = file("${path.module}/../shared/prompts/interview_summary.md")
        }
      }
    }
  ]
}

resource "awscc_bedrock_prompt" "interview_pdfgen" {
  name            = "${var.name}_interview_pdfgen"
  description     = "Prompt used to generate a PDF from an interview"
  default_variant = "variant"

  variants = [
    {
      name          = "variant"
      template_type = "TEXT"
      model_id      = local.model_id_sonnet_3_5
      inference_configuration = {
        text = {
          temperature = 1
        }
      }
      template_configuration = {
        text = {
          input_variables = [
            {
              name = "topic"
              type = "string"
            },
            {
              name = "interview"
              type = "string"
            }
          ]
          text = file("${path.module}/../shared/prompts/interview_pdfgen.md")
        }
      }
    }
  ]
}

resource "awscc_bedrock_prompt" "interview_user" {
  name            = "${var.name}_interview_user"
  description     = "User prompt used to start an interview"
  default_variant = "variant"

  variants = [
    {
      name          = "variant"
      template_type = "TEXT"
      model_id      = local.model_id_haiku_3_5
      inference_configuration = {
        text = {
          temperature = 1
        }
      }
      template_configuration = {
        text = {
          input_variables = [
            {
              name = "topic"
              type = "string"
            },
            {
              name = "areas"
              type = "string"
            }
          ]
          text = file("${path.module}/../shared/prompts/interview_user.md")
        }
      }
    }
  ]
}

resource "awscc_bedrock_prompt" "interview_system" {
  name            = "${var.name}_interview_system"
  description     = "System prompt used for interview"
  default_variant = "variant"

  variants = [
    {
      name          = "variant"
      template_type = "TEXT"
      model_id      = local.model_id_haiku_3_5
      inference_configuration = {
        text = {
          temperature = 1
        }
      }
      template_configuration = {
        text = {
          text = file("${path.module}/../shared/prompts/interview_system.md")
        }
      }
    }
  ]
}

resource "awscc_bedrock_prompt" "chat_system" {
  name            = "${var.name}_chat_system"
  description     = "System prompt used for chatbot"
  default_variant = "variant"

  variants = [
    {
      name          = "variant"
      template_type = "TEXT"
      model_id      = local.model_id_haiku_3_5
      inference_configuration = {
        text = {
          temperature = 1
        }
      }
      template_configuration = {
        text = {
          text = file("${path.module}/../shared/prompts/chat_system.md")
        }
      }
    }
  ]
}

resource "awscc_bedrock_prompt" "chat_user" {
  name            = "${var.name}_chat_user"
  description     = "User prompt used for chatbot"
  default_variant = "variant"

  variants = [
    {
      name          = "variant"
      template_type = "TEXT"
      model_id      = local.model_id_haiku_3_5
      inference_configuration = {
        text = {
          temperature = 1
        }
      }
      template_configuration = {
        text = {
          text = file("${path.module}/../shared/prompts/chat_user.md")
        }
      }
    }
  ]
}

resource "awscc_bedrock_prompt" "chat_reword" {
  name            = "${var.name}_chat_reword"
  description     = "reword prompt used for chatbot"
  default_variant = "variant"

  variants = [
    {
      name          = "variant"
      template_type = "TEXT"
      model_id      = local.model_id_haiku_3_5
      inference_configuration = {
        text = {
          temperature = 1
        }
      }
      template_configuration = {
        text = {
          text = file("${path.module}/../shared/prompts/chat_reword.md")
        }
      }
    }
  ]
}

resource "awscc_bedrock_prompt" "interview_voice" {
  name            = "${var.name}_interview_voice"
  description     = "Prompt used for voice interviews"
  default_variant = "variant"

  variants = [
    {
      name          = "variant"
      template_type = "TEXT"
      model_id      = local.model_id_haiku_3_5
      inference_configuration = {
        text = {
          temperature = 1
        }
      }
      template_configuration = {
        text = {
          input_variables = [
            {
              name = "topic"
              type = "string"
            },
            {
              name = "areas"
              type = "string"
            }
          ]
          text = file("${path.module}/../shared/prompts/interview_voice.md")
        }
      }
    }
  ]
}

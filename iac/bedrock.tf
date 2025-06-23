locals {
  model_id_haiku_3_5  = "anthropic.claude-3-5-haiku-20241022-v1:0"
  model_id_sonnet_3_5 = "anthropic.claude-3-5-sonnet-20241022-v2:0"

  inference_region1 = "us-east-1"
  inference_region2 = "us-east-2"
  inference_region3 = "us-west-2"

  bedrock_arn_root = "arn:aws:bedrock:${local.region}:${local.account_id}"
}

resource "awscc_bedrock_prompt" "scribe_summary" {
  name        = "${var.name}-ScribeSummary"
  description = "Prompt used to generate an interview summary for reviewing"

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

resource "awscc_bedrock_prompt" "kb_generator" {
  name        = "${var.name}-KBGenerator"
  description = "[NOT CURRENTLY USED] Prompt used to generate a doc for the KB"

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
          text = file("${path.module}/../shared/prompts/interview_kb.md")
        }
      }
    }
  ]
}

resource "awscc_bedrock_prompt" "document_generator" {
  name        = "${var.name}-DocumentGenerator"
  description = "Prompt used to generate a PDF from an interview"

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
  name        = "${var.name}-ScribeInterviewUser"
  description = "User prompt used to start an interview"

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
          text = file("${path.module}/../shared/prompts/user_interview.md")
        }
      }
    }
  ]
}

resource "awscc_bedrock_prompt" "interview_system" {
  name        = "${var.name}-ScribeInterviewSystem"
  description = "System prompt used for interview"

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
          text = file("${path.module}/../shared/prompts/system_interview.md")
        }
      }
    }
  ]
}

resource "awscc_bedrock_prompt" "chat_system" {
  name        = "${var.name}-ScribeChatSystem"
  description = "System prompt used for chatbot"

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
          text = file("${path.module}/../shared/prompts/system_chat.md")
        }
      }
    }
  ]
}

resource "awscc_bedrock_prompt" "chat_user" {
  name        = "${var.name}-ScribeChatUser"
  description = "User prompt used for chatbot"

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
          text = file("${path.module}/../shared/prompts/user_chat.md")
        }
      }
    }
  ]
}

resource "awscc_bedrock_prompt" "chat_reword" {
  name        = "${var.name}-ScribeChatReword"
  description = "reword prompt used for chatbot"

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
          text = file("${path.module}/../shared/prompts/reword_chat.md")
        }
      }
    }
  ]
}

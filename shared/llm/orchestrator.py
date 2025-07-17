import json
import logging
import boto3
import datetime

from shared.config import config
from shared import log
from shared.llm import bedrock_llm
from shared.llm import bedrock_kb
from shared.data.data_models import Question
from shared import pdf_generator

prompts = boto3.client('bedrock-agent')


def get_prompt(id: str):
    """Get a prompt from Bedrock by ID."""
    logging.info(f"get_prompt() for id: {id}")
    if id is None:
        error_msg = "Prompt ID is None. This likely means a required environment variable is missing."
        logging.error(error_msg)
        raise ValueError(error_msg)
    try:
        response = prompts.get_prompt(promptIdentifier=id)
        return response['variants'][0]['templateConfiguration']['text']['text']
    except Exception as e:
        logging.error(f"Error getting prompt with ID {id}: {str(e)}")
        raise


def start_interview(topic, areas):
    logging.info(f"starting interview for topic: {topic}, areas: {areas}")

    user_prompt_interview = get_prompt(config.prompt_interview_user)
    prompt = user_prompt_interview.replace("{{topic}}", topic)
    prompt = prompt.replace("{{areas}}", json.dumps(areas, indent=2))
    messages = [user_message(prompt)]

    log.info(messages)
    return bedrock_llm.generate_message(
        messages, system_prompt=get_prompt(config.prompt_interview_system))


def orchestrate_answer(questions: list[Question], topic, areas: list[str]):
    logging.info(f"orchestrate_answer() for topic: {topic}, areas: {areas}")

    # rebuild initial prompt (since it's not stored)
    user_prompt_interview = get_prompt(config.prompt_interview_user)
    prompt = user_prompt_interview.replace("{{topic}}", topic)
    prompt = prompt.replace("{{areas}}", json.dumps(areas, indent=2))
    messages = [user_message(prompt)]

    # translate conversation history to messages
    # ai is asking the questions, users are providing the answers
    for q in questions:
        messages.append(assistant_message(q.question))
        if q.answer != "":
            messages.append(user_message(q.answer))
    log.info(messages)

    return bedrock_llm.generate_message(
        messages, system_prompt=get_prompt(config.prompt_interview_system))


def orchestrate_chat(conversation_history, new_question, scope_name):
    """Orchestrates RAG workflow based on conversation history
    and a new question. Returns an answer and a list of
    source documents."""

    system_prompt = get_prompt(config.prompt_chat_system)
    user_prompt = get_prompt(config.prompt_chat_user)
    reword_prompt = get_prompt(config.prompt_chat_reword)

    query = new_question

    # Log the scope_name that was passed in
    logging.info(f"Using knowledge scope: {scope_name}")

    # for follow up questions, use llm to re-word with context from
    # previous questions in the conversation
    if len(conversation_history["questions"]) > 0:
        past_q = [question["q"]
                  for question in conversation_history["questions"]]
        p = reword_prompt.format(
            past_questions=json.dumps(past_q, indent=2),
            new_question=new_question,
        )
        messages = [user_message(p)]
        query = bedrock_llm.generate_message(messages)

    # retrieve data from vector db based on question
    docs = bedrock_kb.get_relevant_docs(query, 6, scope_name)

    # normalize source documents
    sources = bedrock_kb.format_sources(docs)

    # build prompt based on new question and search results
    context = json.dumps(docs)
    prompt = user_prompt.format(context=context, question=new_question)

    # translate conversation history to messages
    messages = []
    for question in conversation_history["questions"]:
        messages.append(user_message(question["q"]))
        messages.append(assistant_message(question["a"]))

    # add new question message
    messages.append(user_message(prompt))

    # invoke LLM
    response = bedrock_llm.generate_message(
        messages, system_prompt=system_prompt)

    return response, sources

    # invoke LLM
    response = bedrock_llm.generate_message(
        messages,
        system_prompt=system_prompt
    )

    return response, sources


def user_message(msg):
    return {"role": "user", "content": [{"text": msg}]}


def assistant_message(msg):
    return {"role": "assistant", "content": [{"text": msg}]}


def generate_interview_summary(questions: list[Question], topic: str) -> str:
    """Generates a summary of the interview"""

    logging.info(f"Generating  summary for topic: {topic}")

    # Build context from Q&A pairs
    qa_pairs = []
    for q in questions:
        qa_pairs.append(f"Q: {q.question}\nA: {q.answer}")
    interview = "\n\n".join(qa_pairs)

    prompt = get_prompt(config.scribe_summary_id)
    summary = prompt.replace("{{topic}}", topic)
    summary = summary.replace("{{interview}}", interview)
    messages = [user_message(summary)]

    return bedrock_llm.generate_message(
        messages,
        model_id=bedrock_llm.Model.CLAUDE_3_5_SONNET_V2.value,
    )


def generate_pdf(topic: str, questions: list[Question]):
    """Generates a PDF document for the interview"""

    logging.info("Generating PDF document for interview")

    # format conversation
    qa_pairs = []
    for q in questions:
        qa_pairs.append(f"Q: {q.question}\nA: {q.answer}")
    interview = "\n\n".join(qa_pairs)

    # build prompt
    prompt = get_prompt(config.document_generator_id)
    prompt = prompt.replace("{{topic}}", topic)
    prompt = prompt.replace("{{interview}}", interview)
    prompt = prompt.replace("{{date}}", datetime.datetime.now().strftime("%b %-d, %Y"))
    messages = [user_message(prompt)]

    tool_config = {
        "tools": [{
            "toolSpec": {
                "name": "generate_pdf",
                "description": "Generate structured data used for creating a PDF report with hierarchical elements.",
                "inputSchema": {
                    "json": {
                        "type": "object",
                        "properties": {
                            "title": {
                                "type": "string",
                                "description": "The main title of the PDF document."
                            },
                            "subtitle": {
                                "type": "string",
                                "description": "Optional subtitle for the document."
                            },
                            "author": {
                                "type": "string",
                                "description": "Optional author of the document."
                            },
                            "date": {
                                "type": "string",
                                "description": "Optional date of the document creation."
                            },
                            "sections": {
                                "type": "array",
                                "description": "Array of sections that make up the document.",
                                "items": {
                                    "type": "object",
                                    "properties": {
                                        "heading": {
                                            "type": "string",
                                            "description": "Section heading text."
                                        },
                                        "level": {
                                            "type": "integer",
                                            "description": "Heading level (1-3, where 1 is most prominent).",
                                            "default": 1
                                        },
                                        "content": {
                                            "type": "array",
                                            "description": "Array of content elements within this section.",
                                            "items": {
                                                "type": "object",
                                                "properties": {
                                                    "type": {
                                                        "type": "string",
                                                        "enum": ["paragraph", "bullet_list", "table", "image", "spacer"],
                                                        "description": "Type of content element."
                                                    },
                                                    "text": {
                                                        "type": "string",
                                                        "description": "Text content for paragraph elements."
                                                    },
                                                    "items": {
                                                        "type": "array",
                                                        "description": "Array of strings for bullet list items.",
                                                        "items": {
                                                            "type": "string"
                                                        }
                                                    },
                                                    "table_data": {
                                                        "type": "array",
                                                        "description": "2D array representing table data, first row is header.",
                                                        "items": {
                                                            "type": "array",
                                                            "items": {
                                                                "type": "string"
                                                            }
                                                        }
                                                    },
                                                    "image_path": {
                                                        "type": "string",
                                                        "description": "Path to image file for image elements."
                                                    },
                                                    "width": {
                                                        "type": "number",
                                                        "description": "Width for images or tables in inches."
                                                    },
                                                    "height": {
                                                        "type": "number",
                                                        "description": "Height for images or spacers in inches."
                                                    },
                                                    "style": {
                                                        "type": "object",
                                                        "description": "Optional styling information for this element.",
                                                        "properties": {
                                                            "font_name": {
                                                                "type": "string",
                                                                "description": "Font name for text elements."
                                                            },
                                                            "font_size": {
                                                                "type": "number",
                                                                "description": "Font size for text elements."
                                                            },
                                                            "alignment": {
                                                                "type": "string",
                                                                "enum": ["left", "center", "right", "justify"],
                                                                "description": "Text alignment."
                                                            },
                                                            "color": {
                                                                "type": "string",
                                                                "description": "Text color (name or hex code)."
                                                            },
                                                            "background": {
                                                                "type": "string",
                                                                "description": "Background color (name or hex code)."
                                                            }
                                                        }
                                                    }
                                                },
                                                "required": ["type"]
                                            }
                                        }
                                    },
                                    "required": ["heading", "content"]
                                }
                            },
                            "page_settings": {
                                "type": "object",
                                "description": "Optional page settings for the PDF.",
                                "properties": {
                                    "page_size": {
                                        "type": "string",
                                        "description": "Page size (e.g., 'letter', 'A4').",
                                        "default": "letter"
                                    },
                                    "margin_top": {
                                        "type": "number",
                                        "description": "Top margin in points.",
                                        "default": 72
                                    },
                                    "margin_bottom": {
                                        "type": "number",
                                        "description": "Bottom margin in points.",
                                        "default": 72
                                    },
                                    "margin_left": {
                                        "type": "number",
                                        "description": "Left margin in points.",
                                        "default": 72
                                    },
                                    "margin_right": {
                                        "type": "number",
                                        "description": "Right margin in points.",
                                        "default": 72
                                    },
                                    "include_page_numbers": {
                                        "type": "boolean",
                                        "description": "Whether to include page numbers.",
                                        "default": False
                                    }
                                }
                            },
                            "output_filename": {
                                "type": "string",
                                "description": "Name of the output PDF file.",
                                "default": "output.pdf"
                            }
                        },
                        "required": [
                            "title",
                            "sections"
                        ]
                    }
                }
            }
        }]
    }

    # invoke the model
    response = bedrock_llm.converse(
        messages,
        model_id=bedrock_llm.Model.CLAUDE_3_5_SONNET_V2.value,
        tool_config=tool_config,
    )

    # handle response
    output_message = response['output']['message']
    content = output_message['content']
    stop_reason = response['stopReason']
    if stop_reason != "tool_use":
        raise Exception(
            f"invalid stopReason returned from model: {stop_reason}")
    for tool_request in content:
        if "toolUse" in tool_request:
            tool = tool_request["toolUse"]
            logging.info(
                f"Requesting tool {tool['name']}. Request: {tool['toolUseId']}")
            if tool["name"] == "generate_pdf":
                logging.info("Generating report: start")
                pdf = pdf_generator.generate_pdf(tool["input"])
                return pdf
                logging.info("Generating report: end")

    # there's a problem if we made it here
    raise Exception("No PDF generated")

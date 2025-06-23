# Template Refactoring Documentation

## Overview
This document explains the template refactoring implemented for the Scribe application to eliminate code duplication and improve maintainability.

## Template Structure

### Base Template
- `base.html`: Contains the common HTML structure, including:
  - Document head with meta tags, CSS, and JavaScript imports
  - Navigation bar
  - Main content container
  - Block definitions for extending templates

### Page Templates
These templates extend the base template:
- `index.html`: Home page
- `chatbot.html`: Chat interface
- `interviews.html`: Interviews interface
- `admin.html`: Admin interface
- `reviews.html`: Reviews interface
- `documents.html`: Documents interface

### Partial Templates
These templates are included within page templates:
- `chatbot.body.html`: Chat interface content
- `chatbot.chat.html`: Chat conversation display
- `interviews.conversation.body.html`: Interviews interface content
- `interviews.conversation.chat.html`: Interview conversation display
- `conversations.html`: List of conversations
- `new.html`: New conversation button
- `spinner.html`: Loading indicator

## Template Blocks
The base template defines several blocks that can be overridden by child templates:
- `title`: Page title
- `extra_head`: Additional head content
- `content`: Main page content
- `pre_content`: Content before the main content
- `post_content`: Content after the main content
- `scripts`: Additional scripts

## Active Page Highlighting
Navigation highlighting is implemented using the `active_page` variable:
```jinja
{% set active_page = 'page_name' %}
```

This variable is used in the base template to add the 'active' class to the current page's navigation link.

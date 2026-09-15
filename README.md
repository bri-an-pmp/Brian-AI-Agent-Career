# Brian AI Agent Career

An AI-powered chatbot that represents my career background, skills, and experience; all built with Gradio, OpenAI, and grounded on a resume and career summary. Visitors can chat with "Brian" to learn about his professional background, and the agent records unanswered questions and visitor contact details for follow-up.

## Live Demo

Try the live demo on Hugging Face Spaces:

[![Hugging Face Spaces](https://img.shields.io/badge/%F0%9F%A4%97%20Hugging%20Face-Spaces-blue)](https://huggingface.co/spaces/cousinbrian/careerbotbrian)

## How It Works

Built with Gradio (https://www.gradio.app/) for the chat UI, deployed on Hugging Face Spaces. Uses the OpenAI API (gpt-4o-mini) to power the conversation, with a system prompt grounded on a resume PDF (me/Athey_Brian_Resume.pdf) and a written career summary (me/summary.txt).

The agent uses OpenAI function/tool calling for two behaviors: record_user_details captures a visitor's email/name when they want to get in touch, and record_unknown_question logs any question the agent couldn't answer. Recorded events are pushed to a phone via Pushover (https://pushover.net/) notifications.

## Tech Stack

Python, Gradio, the OpenAI API (openai, openai-agents), pypdf for parsing the resume PDF, Pushover for notifications, and python-dotenv for local environment config.

## Project Structure

app.py is the main Gradio app and agent logic. requirements.txt lists the Python dependencies. The me/ folder holds Athey_Brian_Resume.pdf (resume used as agent context) and summary.txt (career summary used as agent context).

## Setup

Clone the repo and install dependencies with pip install -r requirements.txt. Create a .env file with OPENAI_API_KEY, PUSHOVER_TOKEN, and PUSHOVER_USER. Add your own career materials to a me/ folder: me/<your-resume>.pdf (your resume, matching the filename read in app.py) and me/summary.txt (a short written summary of your background). Then run locally with python app.py.

## Deployment

This project is deployed as a Hugging Face Space (https://huggingface.co/spaces/cousinbrian/careerbotbrian) using the Gradio SDK.

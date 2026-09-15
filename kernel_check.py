"""Run from terminal if the notebook kernel stays Pending: uv run 1_foundations/kernel_check.py"""
from dotenv import load_dotenv
from openai import OpenAI
from anthropic import Anthropic

load_dotenv(override=True)
print("Kernel check OK — imports work outside the notebook.")


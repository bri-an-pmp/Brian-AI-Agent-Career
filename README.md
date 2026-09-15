# Brian-AI-Agent-Career


## Live Demo

Try the live demo on Hugging Face Spaces:

[![Hugging Face Spaces](https://img.shields.io/badge/%F0%9F%A4%97%20Hugging%20Face-Spaces-blue)](https://huggingface.co/spaces/cousinbrian/careerbotbrian)
# Brian AI Agent Career

An AI-powered chatbot that represents Brian Athey's career background, skills, and experience — built with Gradio, OpenAI, and grounded on a LinkedIn profile and career summary. Visitors can chat with "Brian" to learn about his professional background, and the agent records unanswered questions and visitor contact details for follow-up.

## Live Demo

Try the live demo on Hugging Face Spaces:

[![Hugging Face Spaces](https://img.shields.io/badge/%F0%9F%A4%97%20Hugging%20Face-Spaces-blue)](https://huggingface.co/spaces/cousinbrian/careerbotbrian)

## How It Works

- Built with [Gradio](https://www.gradio.app/) for the chat UI and deployed on Hugging Face Spaces.
- - Uses the OpenAI API (`gpt-4o-mini`) to power the conversation, with a system prompt grounded on:
  -   - A LinkedIn profile PDF (`me/linkedin.pdf`)
      -   - A written career summary (`me/summary.txt`)
          - - Uses OpenAI function/tool calling for two behaviors:
            -   - `record_user_details` — captures a visitor's email/name when they want to get in touch
                -   - `record_unknown_question` — logs any question the agent couldn't answer
                    - - Recorded events are pushed to a phone via [Pushover](https://pushover.net/) notifications.
                     
                      - ## Tech Stack
                     
                      - - Python
                        - - [Gradio](https://www.gradio.app/)
                          - - [OpenAI API](https://platform.openai.com/) (`openai`, `openai-agents`)
                            - - [pypdf](https://pypi.org/project/pypdf/) for parsing the LinkedIn PDF
                              - - [Pushover](https://pushover.net/) for notifications
                                - - `python-dotenv` for local environment config
                                 
                                  - ## Project Structure
                                 
                                  - ```
                                    app.py              # Main Gradio app and agent logic
                                    requirements.txt     # Python dependencies
                                    me/
                                      linkedin.pdf       # Exported LinkedIn profile (used as agent context)
                                      summary.txt        # Career summary (used as agent context)
                                    ```

                                    ## Setup

                                    1. Clone the repo and install dependencies:
                                    2.    ```bash
                                             pip install -r requirements.txt
                                             ```
                                          2. Create a `.env` file with the following variables:
                                          3.    ```
                                                   OPENAI_API_KEY=your_openai_api_key
                                                   PUSHOVER_TOKEN=your_pushover_app_token
                                                   PUSHOVER_USER=your_pushover_user_key
                                                   ```
                                                3. Add your own career materials to a `me/` folder:
                                                4.    - `me/linkedin.pdf` — your exported LinkedIn profile
                                                      -    - `me/summary.txt` — a short written summary of your background
                                                           - 4. Run locally:
                                                             5.    ```bash
                                                                      python app.py
                                                                      ```

                                                                   ## Deployment

                                                               This project is deployed as a [Hugging Face Space](https://huggingface.co/spaces/cousinbrian/careerbotbrian) using the Gradio SDK.
                                                             

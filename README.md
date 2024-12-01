# Retail-GPT

This repository contains the source code for Retail-GPT, a open-source RAG-based chatbot designed to guide users through product recommendations and assist with cart operations, aiming to enhance user engagement with retail e-commerce and serve as a virtual sales agent. The goal of this system is to test the viability of such an assistant and provide an adaptable framework for implementing sales chatbots across different retail businesses.

For demonstration and test purposes, the chatbot implemented in this repository is contextualized to work as a sales agent for a fictional Foo convenience store.   Nevertheless, the implementation is not dependant of this domain and could be adapted to work with other type of businesses. 

The project paper can be read at [retailGPT PDF](/retailGPT.pdf)

The complete project is composed of 4 different applications that can be run separately:

- **Chat interface:** Front-end application for demonstration purposes built primarily with [`Streamlit`](https://streamlit.io/). This application is optional, as the chatbot can be executed directly from the terminal.
- **Rasa chatbot:** [`Rasa`](https://rasa.com/) application that serves as a base for all the chatbot. Responsible for processing chit-chat, extracting entities and delegating tasks to the RAG subsystem
- **Rasa actions server:** [`Rasa`](https://rasa.com/)'s custom actions server, in which validations and the RAG system is implemented
- **Redis database:** Database for storing conversation histories and users' carts.

For powering the Rag system implemented in the actions server, Open AI's `gpt-4o` model was used through the [`Open AI API`](https://openai.com/index/openai-api/) for its response quality and hability to perform function calls. Function calls are the primary feature used for integrating the model with external tools due to its simplicity of use and efectiveness, but it would be possible to achieve similar results by replacing them with techniques such as ReAct prompting.

# Installation and Usage

## Chat Interface

To install and run the chatbot demo interface, follow the steps below:

1. Clone the repository
2. Run `cd chat_interface` to go to the interface directory
3. [Install poetry](https://python-poetry.org/docs/#installing-with-the-official-installer) for dependency management
4. Install the dependencies with ```poetry install``` in your current active environment (using a separate python environment is advisable)
5. Go to the app's folder with ```cd src```
6. Run the interface application with ```streamlit run app.py```

The chatbot demo interface will be available at http://localhost:8501. You can interact with the chatbot by typing messages in the input box and pressing Enter.

## Rasa Chatbot

To install the dependencies and execute the chatbot:

1. Run `cd retailGPT/rasa_chatbot` to go to the Rasa chatbot directory
2. Run `poetry install` to install the dependencies in your current active environment (using a separate python environment is advisable)
3. Run `python -m spacy download en_core_web_lg` to download the [`spacy`](https://spacy.io/) model used
4. Run `rasa train` for training the model
5. Run `rasa run` if you want to run the application as an API.

Alternatively, instead of running `rasa run`, you can run `rasa shell` (can add `--debug` option to get more logs) for running the application and starting a chat directly in the terminal. This option can be useful if you don't want to run the separate interface application.

## Rasa's Actions Server

To install the dependencies and execute the actions server:

1. Run `cd retailGPT/actions_server` to go to the Rasa chatbot directory
2. Run `poetry install` to install the dependencies in your current active environment (using a separate python environment is advisable)
3. Make sure you have an environment variable `OPENAI_API_KEY` set with your API key value
   1. If you prefer using Open AI through Microsoft Azure, make sure you edit the boolean use_azure in llm_handler to True and set the following environment variables: 
       1. `AZURE_OPENAI_API_KEY`: key for azure Open AI
       2. `AZURE_RESOURCE`: Azure resource in which the model is deployed
       3. `AZURE_API_VERSION`: Api version of the deployment
4. Run `python -m rasa_sdk --actions actions` for running the server

## Database

The database is run as a Redis container. For running the database:

1. Make sure you have [Docker]() installed in your machine
2. Run `docker-compose up database`

The database will run at port 6379 and will be ready to use by the other applications

## Running with Docker

You can also run everything through Docker using the compose file at the root of the project. Be aware that, in order for the containers to communicate between each other in the Docker network, you will also need to update the endpoints in the project. In this, sense, do:

In ```chat_interface/src/chatbot.py```: Change "localhost" to "rasa" in the Rasa chatbot URLs and "localhost" to "database" in the single Redis-related URL.

In ```retailGPT/rasa_chatbot/endpoints.tml```: Change "localhost" to "actions" 

In ```retailGPT/actions_server/src/LLMChatbot/services/chatbot.py```: Change "localhost" to "database"

## Code Architecture

If this is your first time working on this repository, you will probably need to get familiar with the files and directories listed below. Please note that not all the project's files are listed, only the most important ones.

- `chat_interface` : Interface application 
- `retailGPT` : Contains all the chatbot's logic
  - `rasa_chatbot` : [`Rasa`](https://rasa.com/) project
    - `endpoints.yml` : Contains the endpoints for the     bot, such as the action server and the tracker store.
    - `domain.yml` : Contains the domain of the bot, including intents, entities, actions, and responses.
    - `config.yml` : NLP pipeline used by Rasa
    - `data`
      - `nlu.yml` : Contains the NLU training data.
      - `stories.yml` : Contains the stories for the bot.
      - `rules.yml` : Contains the rules for the bot.
    - `models` : Contains the trained models for classifing intents and extracting slots.
  - `datasets` : fictional datasets that are used for testing and providing the available e-commerce products
  - `actions_server` : [`Rasa`](https://rasa.com/)'s custom actions server
    - `src`
      - `LLMChatbot`: implements the RAG-based subsystem
        - `chatbot.py` : Contains the code for the LLM-based chatbot.
        - `prompts.py` : Contains the prompts for the LLM-based chatbot.
        - `services`
            - `database.py` : Contains the code for the database service.
            - `product_handler.py` : Contains the code for product-related features.
            - `memory_handler.py` : Contains the code for memory-related features.
            - `cart_handler.py` : Contains the code for cart-related features.
            - `llm_handler.py` : Contains the code for LLM-related features
            - `guardrails` : Contains guardrails implementation

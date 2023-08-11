![Screenshot 2023-07-25 at 3 48 43 AM](https://github.com/zozoheir/tiny-llm/assets/42655961/f2db0c02-c18c-45a8-8054-6cd4da474e1e)

# 🕸️ tinyllm (beta)
tinyllm is a lightweight framework for developing, debugging and monitoring LLM powered applications at scale. It is designed based on a Finite State Machine and Compute Graph model and sits as a layer between your Web application and your LLM libraries. The tinyllm tech stack:
- **Python library**: the tinyllm library + CLI commands
- **Backend**: a neo4j backend database for debugging, logging and storing your LLM runs
- **TinyLLM Agent**: your copilot for using tinyllm


## Install
package
```
pip install git+https://github.com/zozoheir/tinyllm.git
```

## Tinyllm agent v0
```
tinyllm agent
```
![Screenshot 2023-07-28 at 2 06 05 AM](https://github.com/zozoheir/tinyllm/assets/42655961/7c5a9d62-4c79-499c-9d85-8a9a4a285190)


## Tracing
tinyllm is integrated with Langfuse for tracing chains, functions and agents.
![Screenshot 2023-08-11 at 12 45 07 PM](https://github.com/zozoheir/tinyllm/assets/42655961/4d7c6ae9-e9a3-4795-9496-ad7905bc361e)

## ⚡ Features
* Integrate tiny-llm with any LLM library or existing python code or pipelines
* Compose, debug and track LLM calls and chains at scale
* High level abstraction of LLM/API chaining/interactions through a standardized I/O interface

## ⚡ Background and goals
Many of the LLM libraries today (langchain, llama-index, deep pavlov...) have made serious software design commitments which I believe were too early to make given the infancy of the industry.
The goals of tinyllm are:
* **Solve painpoints from current libraries**: lack of composability (within + between libraries), complex software designs, code readability, debugging and logging.
* **High level, robust abstractions**: tinyllm is designed to be as simple as possible to use and integrate with existing and living codebases.
* **Human and machine readable code** to enable AI powered and autonomous chain development


## ⚡ Concurrency vs Parallelism vs Chaining
These tend to be confusing across the board. Here's a quick explanation:
- **Concurrency** : This means more than 1 Input/Ouput request at a time. Just like you can download 10 files 
concurrently on your web browser, you can call 10 APIs concurrently.
- **Chaining** : An ordered list of Functions where a Function's output is the input of the next Function in the chain.
- **Parallelism** : compute/calculations being performed on more than 1 process/CPU Core on the same machine. This is what 
model providers like OpenAI do using large GPU clusters (Nvidia, AMD...). This is used for "CPU Bound" tasks.

Tinyllm does not care about Parallelism. Parallelism is implemented by LLM providers
on a GPU/CPU level and should be abstracted away using an LLM microservice.
Tinyllm only cares about Concurrency, Chaining and organizing IO Bound tasks.

## ⚡ Codebase
The TinyLLM library consists of several key components that work together to facilitate the creation and management of Language Model Microservices (LLMs):
* **Function**: The base class for all LLM functions. It handles the execution of the LLM and the transition between different states in the LLM's lifecycle.
* **Validator**: A utility class used to validate input and output data for LLM functions.
* **Chain**: A function that allows the chaining of multiple LLM functions together to form a pipeline of calls.
* **Concurrent**: A function that enables concurrent execution of multiple LLM functions, useful for ensembling/comparing from different LLMs or speeding up IO bound task execution.
* **Decision**: A function that represents a decision point in the chain, allowing different paths to be taken based on the output of a previous LLM function.


### Tinyllm Vector Store
The library uses a Postgres DB with the pgvector extension as a vector store. After lots of exploration, this felt like the most flexible and cost-friendly solution for managing and owning your embeddings. No need to integrate with 100 vector stores. A single good vector store works fine.


### Tinyllm Configs
Configs are managed through a tinyllm.yaml file. It gets picked up at runtime in tinyllm.__init__ and can be placed in any of /Documents, the root folder, or the current working directory. Here is a sample yaml config file:
```yaml
LLM_PROVIDERS:
  OPENAI_API_KEY: ""
LANGFUSE:
  LANGFUSE_PUBLIC_KEY: ""
  LANGFUSE_SECRET_KEY: ""
POSTGRES:
  TINYLLM_POSTGRES_USERNAME: ""
  TINYLLM_POSTGRES_PASSWORD: ""
  TINYLLM_POSTGRES_HOST: ""
  TINYLLM_POSTGRES_PORT: 
  TINYLLM_POSTGRES_NAME: ""
```


### Logging
```
INFO - 2023-07-28 01:52:34,785: [Concurrent: On good credit] transition to: States.OUTPUT_VALIDATION
INFO - 2023-07-28 01:52:34,786: [Concurrent: On good credit] transition to: States.COMPLETE
INFO - 2023-07-28 01:52:34,786: [Concurrent: On good credit] Pushing to db
INFO - 2023-07-28 01:52:34,945: [Concurrent: On good credit] Creating relationship between Concurrent: On good credit and Email notification
INFO - 2023-07-28 01:52:35,163: [Concurrent: On good credit] Creating relationship between Concurrent: On good credit and Background check
INFO - 2023-07-28 01:52:35,666: [Chain: Loan application] transition to: States.OUTPUT_VALIDATION
INFO - 2023-07-28 01:52:35,666: [Chain: Loan application] transition to: States.COMPLETE
INFO - 2023-07-28 01:52:35,666: [Chain: Loan application] Pushing to db
```

## ⚡ Examples

### Chaining
* ####  [Classifying a credit application](https://github.com/zozoheir/tiny-llm/blob/main/tinyllm/examples/credit_analysis.py)
### Chat
* ####  [A basic openaichat](https://github.com/zozoheir/tinyllm/blob/main/tinyllm/examples/openai_chat.py)
### Retrieval
* ####  [The tinyllm agent](https://github.com/zozoheir/tinyllm/blob/main/tinyllm/agent.py)


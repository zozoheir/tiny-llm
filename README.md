![Screenshot 2023-07-25 at 2 41 40 AM](https://github.com/zozoheir/tiny-llm/assets/42655961/73ab8f68-faaf-4bda-96cb-0703bc8a911a)

# 🕸️ tinyllm
tinyllm is a lightweight framework for developing, debugging and monitoring LLM powered applications at scale. It is designed based on a Finite State Machine and Compute graph_chain model. 

## ⚡ Goal of the library
Many of the LLM libraries today (langchain, llama-index, deep pavlov...) have made serious software design commitments which I believe were too early to make given the infancy of the industry. The goal of tiny LLM is to 2 fold:
* Solve painpoints from current libraries: lack of composability (within + between libraries), complex software designs, code readability, debugging and logging.
* Stay as universal and general as possible, with the fewest lines of code and requirements as possible.
* Make code as readable and writable as possible for LLMs to enable AI powered and autonomous chain development. e.g:
```
tinyllm.helper("Write a chain to automate the following business process: etc...")
```

## ⚡ Features
* Integrate tiny-llm with any LLM library or existing python code or pipelines
* Compose, debug and track LLM calls and chains at scale
* Visualize chains in 1 line of code
* High level abstraction of LLM/API chaining/interactions through a standardized I/O interface

## ⚡ Architecture
The TinyLLM library consists of several key components that work together to facilitate the creation and management of Language Model Microservices (LLMs):
* **Function**: The base class for all LLM functions. It handles the execution of the LLM and the transition between different states in the LLM's lifecycle.
* **Validator**: A utility class used to validate input and output data for LLM functions.
* **Chain**: A function that allows the chaining of multiple LLM functions together to form a pipeline of calls.
* **Concurrent**: A function that enables concurrent execution of multiple LLM functions, useful for ensembling/comparing from different LLMs or speeding up IO bound task execution.
* **Decision**: A function that represents a decision point in the chain, allowing different paths to be taken based on the output of a previous LLM function.
* **LLMCall**: A function for making API calls to external language model services.
* **Prompt**: A function for generating prompts from templates and user inputs.


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


## ⚡ Examples
* #### Instantiating a tinyllm Function instance
  * Functions have 3 components:
    * run_function: takes in a dictionary of inputs and returns a dictionary of outputs 
    * input_validator: validates the input dictionary
    * output_validator: validates the output dictionary
```python
class SentimentClassifierInput(Validator):
    content: str
class SentimentClassifierOutput(Validator):
    sentiment: float
    
async def classify_content_sentiment(**kwargs):
    content = kwargs['content']
    sentiment = 0 if 'bad' in content else 1
    return {'sentiment':sentiment}

sentiment_classifier = Function(
    name="Sentiment classifier",
    run_function=classify_content_sentiment,
    input_validator=SentimentClassifierInput,
    output_validator=SentimentClassifierOutput
)
```


### Chaining
* #### [Generating jokes](https://github.com/zozoheir/tiny-llm/blob/main/tinyllm/examples/credit_analysis.py): a basic role/character

* ####  [Classifying a credit application](https://github.com/zozoheir/tiny-llm/blob/main/tinyllm/examples/credit_analysis.py): automating a business process with an LLM function call

* #### Graphing a chain in 1 line of code:

```python
chain.graph_chain()
```
![Figure_1](https://github.com/zozoheir/tiny-llm/assets/42655961/c49669dd-a1b1-4a9c-ab9c-2029628a6b3c)




## Todos:
* [ ] More tests
* [ ] Add .from_params() method to Functions for easy initialization
* [ ] Prettify graph_chain visualization (concurrent vs parallel chaining + styling)
* [ ] Implement backend database 
* [ ] Implement redis caching
* [ ] Dockerize backend db + cache
* [ ] Dockerize tinyllm microservice
* [ ] Write docker compose
* [ ] Implement visualization/monitoring layer
* [ ] Create tinyllm trained AI powered helpers

import os

from langgraph.graph import StateGraph ,START , END
from typing import TypedDict,Annotated
from langchain_core.prompts import PromptTemplate
import operator
from langchain_ollama import ChatOllama
class AIConfig(TypedDict):
    message: Annotated[list[str],operator.add]

graph=StateGraph(AIConfig)
def generate_response(state: AIConfig):
    messages=state["message"]
    model=ChatOllama(model="minimax-m3:cloud",api_key=os.getenv("OLLAMA_API_KEY"))
    response=model.invoke(messages)
    return {"message":[response]}

    
graph.add_node("generate_response",generate_response);
graph.add_edge(START,"generate_response")
graph.add_edge("generate_response",END)

workflow=graph.compile()

initial_state={"message":["Generate an reminder for the following details: \n\nSubject: Task Update till 12 june task name is Taskino to Robin"]}
final_state=workflow.invoke(initial_state)
print(final_state["message"][-1].content)
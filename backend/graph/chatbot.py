from typing import TypedDict, Annotated, Literal, Optional
from langgraph.graph import StateGraph, START, END, add_messages
from langchain_core.messages import AnyMessage, SystemMessage, HumanMessage, AIMessage, RemoveMessage
from langchain_groq import ChatGroq
from langgraph.checkpoint.memory import InMemorySaver
from pydantic import BaseModel, Field
from .prompt import CHATBOT_PROMPT, HINT_PROMPT, META_PROMPT, QUESTION_PROMPT
from .utils import draw_mermaid

from pprint import pprint  # remove this later

import dotenv, os


dotenv.load_dotenv()

class ChatbotState(TypedDict):
    messages: Annotated[list[AnyMessage], add_messages]
    user_message: HumanMessage  # this and below is for storing the last interaction to be able to log into database and also remove trash
    ai_message: AIMessage

    secret: str
    done: bool
    turn: int
    n_guardrails_triggered: int

    selected_route: str
    proposed_guess: str 
    is_guess_correct: bool


RouteName = Literal[
    "question",
    "hint",
    "guess",
    "meta",
    "guardrail",
]

class RouteDecision(BaseModel):
    selected_route: RouteName = Field(
        description="The route that should handle the user's latest message."
    )
    proposed_guess: str | None = Field(
        default=None,
        description=(
            "The word proposed by the player when selected_route is guess. "
            "Otherwise, return null."
        ),
    )


class Chatbot:
    def __init__(self):
        self.model = ChatGroq(
            model="qwen/qwen3-32b",
            api_key=os.environ["GROQ_API_KEY"],
            reasoning_format='hidden',
        )
        self.checkpointer = InMemorySaver()
        self.graph = self._build_graph()

    def handle_message(self, game_id=None, message=None, secret=None):
        config = {
            "configurable": {
                "thread_id": game_id,
            }
        }

        result = self.graph.invoke(
            {
                "messages": [HumanMessage(content=message)],
                "secret": secret,
            },
            config=config,
        )
        
        return result["ai_message"].content
    
    def _print_history(self, game_id):
        config = {
            "configurable": {
                "thread_id": game_id,
            }
        }
        pprint(self.graph.get_state(config).values)

    def _store_user_message(self, state: ChatbotState) -> dict:
        return {
            "user_message": state["messages"][-1],
        }
    
    def llm_route(self, state: ChatbotState) -> dict:
        decision = self.model.with_structured_output(
            RouteDecision,
            include_raw=False,
        ).invoke([
            SystemMessage(content=CHATBOT_PROMPT),
            *state["messages"],
        ])
        return {
            "selected_route": decision.selected_route,
            "proposed_guess": decision.proposed_guess,
        }

    def choose_route(self, state: ChatbotState) -> str:
        return state["selected_route"]
    
    def done_check_route(self, state: ChatbotState) -> str:
        return 'after_done' if state.get('done', False) else 'llm_router'
    

    # Responses
    def _message_after_done(self, state: ChatbotState) -> dict:
        return {
            "messages": RemoveMessage(state["messages"][-1].id),
            "ai_message": AIMessage(content="Start a new game!"),
        }
    
    def _question(self, state: ChatbotState) -> dict:
        response = self.model.invoke([
            SystemMessage(content=QUESTION_PROMPT.format(secret=state["secret"])),
            *state["messages"],
        ])
        return {
            "messages": response,
            "ai_message": response,
        }

    def _hint(self, state: ChatbotState) -> dict:
        response = self.model.invoke([
            SystemMessage(content=HINT_PROMPT.format(secret=state["secret"])),
            *state["messages"],
        ])
        return {
            "messages": response,
            "ai_message": response,
        }

    def _meta(self, state: ChatbotState) -> dict:
        response = self.model.invoke([
            SystemMessage(content=META_PROMPT),
            *state["messages"],
        ])
        return {
            "messages": RemoveMessage(state["messages"][-1].id),
            "ai_message": response,
        }

    def _guess(self, state: ChatbotState) -> dict:
        is_guess_correct = state['proposed_guess'].lower() == state["secret"].lower()
        return {
            "is_guess_correct": is_guess_correct,
            "done": is_guess_correct,
        }
   
    def _guardrail(self, state: ChatbotState) -> dict:
        response = AIMessage(content="Let's not talk about this here.")
        return {
            "messages": RemoveMessage(state["messages"][-1].id),
            "ai_message": response,
        }
    
    def _format_guess(self, state: ChatbotState) -> dict:
        # stub
        response = AIMessage(content=f"Your guess is {'' if state["is_guess_correct"] else 'not '}correct!" )
        return {
            "messages": RemoveMessage(state["messages"][-1].id),
            "ai_message": response,
        }


    def _build_graph(self):
        builder = StateGraph(ChatbotState)

        builder.add_node("llm_router", self.llm_route)
        builder.add_node("after_done", self._message_after_done)
        builder.add_node("store_user_message", self._store_user_message)
        
        builder.add_edge(START, "store_user_message")
        builder.add_conditional_edges(
            "store_user_message",
            self.done_check_route,
        )
        builder.add_edge("after_done", END)

        builder.add_node("question", self._question)
        builder.add_node("hint", self._hint)
        builder.add_node("guess", self._guess)
        builder.add_node("meta", self._meta)
        builder.add_node("guardrail", self._guardrail)
        builder.add_conditional_edges(
            "llm_router",
            self.choose_route,
        ) 

        builder.add_edge("question", END)
        builder.add_edge("hint", END)
        builder.add_edge("meta", END)
        builder.add_edge("guardrail", END)

        builder.add_node("guess_formatter", self._format_guess)
        builder.add_edge("guess", "guess_formatter")

        builder.add_edge("guess_formatter", END)

        graph = builder.compile(
            checkpointer=self.checkpointer
        )

        # draw_mermaid(graph, "chatpot.png")

        return graph
    

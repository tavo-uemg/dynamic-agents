from typing import Any

from agno.agent import Agent

from ..schemas.ui_protocol import UISchema


class UIGenerator:
    @staticmethod
    def create_agent(model: Any, debug: bool = False) -> Agent:
        return Agent(
            model=model,
            response_model=UISchema,
            description="You are an expert UI Designer. Generate structured UI definitions.",
            instructions=[
                "You must return a valid JSON object matching the UISchema.",
                "Use container components (Stack, Group, Card) to organize layout.",
                "Use consistent spacing and hierarchy.",
            ],
            debug=debug,
        )

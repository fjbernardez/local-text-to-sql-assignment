from typing import Any, Literal

from pydantic import BaseModel, Field, field_validator


class AskRequest(BaseModel):
    question: str = Field(
        ...,
        json_schema_extra={
            "example": "What are the top 5 products by quantity sold?"
        },
    )
    max_rows: int = Field(default=50, ge=1, le=100)
    include_natural_answer: bool = True

    @field_validator("question")
    @classmethod
    def question_must_not_be_blank(cls, value: str) -> str:
        if not value.strip():
            raise ValueError("question cannot be blank")
        return value.strip()


class AskResponse(BaseModel):
    type: Literal["query", "ambiguous", "unsupported"]
    message: str
    sql: str | None
    data: list[dict[str, Any]] | None
    natural_message: str | None = None

    model_config = {
        "json_schema_extra": {
            "examples": [
                {
                    "type": "query",
                    "message": "Query executed successfully.",
                    "sql": "SELECT product_name, SUM(quantity) AS total_quantity FROM sales GROUP BY product_name ORDER BY total_quantity DESC LIMIT 5",
                    "data": [{"product_name": "Coffee", "total_quantity": 213}],
                    "natural_message": "Coffee is the top product by quantity sold, with 213 units.",
                },
                {
                    "type": "ambiguous",
                    "message": "The question is ambiguous. Please submit a new complete question clarifying whether 'best customers' means highest total spending, most invoices, or highest average invoice value.",
                    "sql": None,
                    "data": None,
                    "natural_message": None,
                },
                {
                    "type": "unsupported",
                    "message": "This question cannot be answered from the sales table.",
                    "sql": None,
                    "data": None,
                    "natural_message": None,
                },
            ]
        }
    }

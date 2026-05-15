from fastapi import APIRouter, Depends

from app.dependencies import build_ask_service
from app.schemas.ask import AskRequest, AskResponse
from app.services.ask_service import AskService

router = APIRouter(tags=["ask"])


def get_ask_service() -> AskService:
    return build_ask_service()


@router.post(
    "/ask",
    response_model=AskResponse,
    summary="Ask a natural language question about sales data",
    description=(
        "Receives a natural language analytics question, asks the configured "
        "LLM provider for a structured SQL decision, validates any generated "
        "SQL as read-only PostgreSQL over the sales allowlist, and returns "
        "query data or a domain outcome."
    ),
    responses={
        200: {
            "description": "Domain outcome: query, ambiguous, or unsupported.",
            "content": {
                "application/json": {
                    "examples": {
                        "query": {
                            "summary": "Successful SQL execution",
                            "value": {
                                "type": "query",
                                "message": "Query executed successfully.",
                                "sql": "SELECT product_name, SUM(quantity) AS total_quantity FROM sales GROUP BY product_name ORDER BY total_quantity DESC LIMIT 5",
                                "data": [
                                    {
                                        "product_name": "Coffee",
                                        "total_quantity": 213,
                                    }
                                ],
                                "natural_message": "Coffee is the top product by quantity sold, with 213 units.",
                            },
                        },
                        "ambiguous": {
                            "summary": "Ambiguous question",
                            "value": {
                                "type": "ambiguous",
                                "message": "The question is ambiguous. Please submit a new complete question clarifying whether 'best customers' means highest total spending, most invoices, or highest average invoice value.",
                                "sql": None,
                                "data": None,
                                "natural_message": None,
                            },
                        },
                        "unsupported": {
                            "summary": "Unsupported question",
                            "value": {
                                "type": "unsupported",
                                "message": "This question cannot be answered from the sales table.",
                                "sql": None,
                                "data": None,
                                "natural_message": None,
                            },
                        },
                    }
                }
            },
        },
        422: {"description": "Unsafe SQL or SQL that cannot be safely validated."},
        503: {"description": "LLM provider unavailable or timed out."},
    },
    openapi_extra={
        "requestBody": {
            "content": {
                "application/json": {
                    "examples": {
                        "top_products_by_quantity": {
                            "summary": "Top products by quantity sold",
                            "value": {
                                "question": "What are the top 5 products by quantity sold?",
                                "max_rows": 50,
                                "include_natural_answer": True,
                            },
                        }
                    }
                }
            }
        }
    },
)
def ask(request: AskRequest, service: AskService = Depends(get_ask_service)) -> AskResponse:
    return service.ask(
        question=request.question,
        max_rows=request.max_rows,
        include_natural_answer=request.include_natural_answer,
    )

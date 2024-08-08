from pydantic import BaseModel, Field


class RasaButton(BaseModel):
    """A button that will be displayed to the user.

    Attributes:

    title: str
        The text that will be displayed on the button

    payload: str
        The payload that will be sent to the chatbot when the button is clicked
    """

    title: str = Field(..., description="The text that will be displayed on the button")
    payload: str = Field(
        ...,
        description="The payload that will be sent to the chatbot when the button is clicked",
    )


class ChatbotResponse(BaseModel):
    """The response from the chatbot.

    Attributes:

    text: str
        The text response from the chatbot

    buttons: List[RasaButton]
        The buttons that will be displayed to the user
    """

    text: str = Field(..., description="The text response from the chatbot")
    buttons: list[RasaButton]


class Product(BaseModel):
    """A product that can be recommended to the user.

    Attributes:

    row_id: int
        The ID of the product

    product_name: str
        The name of the product

    full_price: float
        The price of the product

    product_volume_in_hectoliters: float
        The volume of the product in hectoliters

    """

    row_id: int = Field(..., description="The ID of the product")
    product_name: str = Field(..., description="The name of the product")
    full_price: float = Field(..., description="The price of the product")
    product_volume_in_hectoliters: float = Field(
        ..., description="The volume of the product in hectoliters"
    )

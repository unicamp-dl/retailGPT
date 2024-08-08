import json
from pathlib import Path
from typing import List

import aiohttp
from ..prompts import product_search_prompt
from ..schemas import Product
from .database import Database
from .llm_handler import LLMHandler


class ProductHandler:
    """Handles the product recommendation based on the user's demand."""

    _mocked_products_path: str = (
        Path(__file__).resolve().parent.parent.parent.parent.parent
        / "datasets"
        / "mocked_products.json"
    )

    _purchase_history_path: str = (
        Path(__file__).resolve().parent.parent.parent.parent.parent
        / "datasets"
        / "purchase_history.json"
    )

    _product_not_found_message: str = (
        "Sorry, we couldn't find any product in the catalog that meets your demand."
    )
    _recommendation_max_size: int = 5

    @staticmethod
    def _get_product_catalog(zipcode) -> str:
        """Gets the product catalog available in the user location from the mocked products dataset.
        Only considers the first digit of the zipcode to determine the catalog.

        Returns:

        The product catalog.
        """

        catalog_string = ""
        if zipcode[0] == "0":
            return catalog_string

        with open(ProductHandler._mocked_products_path, "r") as file:
            mocked_products_dataset = json.load(file)
            products = mocked_products_dataset["products"]

            for index, product in enumerate(products):
                if zipcode[0] == "9" and index % 3 > 0:
                    continue
                name = product["product_name"]
                unit_price = round(product["full_price"], 2)
                catalog_string += f"Name: {name} - Price: R${unit_price}\n"

        return catalog_string

    @staticmethod
    def _get_purchase_history_dataset() -> List[str]:
        """Gets the user purchase history dataset.

        Returns:
            List[str]: A list of strings where each string represents a purchase history,
                       formatted as a json.
        """

        with open(ProductHandler._purchase_history_path, "r") as file:
            dataset = json.load(file)

        purchase_history_dataset = []

        for transaction in dataset["purchase_histories"]:
            transaction_json = json.dumps(transaction)
            purchase_history_dataset.append(transaction_json)

        return purchase_history_dataset

    @staticmethod
    def _get_purchase_history(zipcode) -> str:
        """Gets the user purchase history.
        We do it in a fake way based on the user location, just for showing that including
        history-based recommendations is a possible feature.

        Returns:

        The user's purchase history.
        """

        purchase_history_dataset = ProductHandler._get_purchase_history_dataset()

        index = int(zipcode[-1])
        if index >= len(purchase_history_dataset):
            return ""

        return purchase_history_dataset[index]

    @staticmethod
    async def _mocked_search_engine(
        product_query: str,
        zipcode: str,
        session: aiohttp.ClientSession | None = None,
    ) -> list[Product]:
        """Mocks the search engine for product recommendations.

        Args:

        product_query: The user's demand for a product, e.g. 'A light beer'.
        zipcode: The user's ZIP code.
        session: The aiohttp ClientSession used for concurrent searching.

        Returns:

        The product recommendations based on the user's demand, in the form of a list of dicts.
        """

        catalog = ProductHandler._get_product_catalog(zipcode)
        purchase_history = ProductHandler._get_purchase_history(zipcode)

        system_prompt = product_search_prompt.format(
            product_catalog=catalog,
            search=product_query,
            purchase_history=purchase_history,
        )

        llm_response = await LLMHandler.call_completions_api(
            [{"role": "system", "content": system_prompt}],
            session=session,
            response_format={"type": "json_object"},
        )

        llm_response = json.loads(llm_response["content"])

        with open(ProductHandler._mocked_products_path, "r") as file:
            mocked_products_dataset = json.load(file)

        available_products = mocked_products_dataset["products"]
        recommended_products = [
            product.lower() for product in llm_response["recommended_products"]
        ]

        recommendation = []
        for product in available_products:
            if product["product_name"].lower() in recommended_products:
                recommendation.append(product)

        return recommendation[: ProductHandler._recommendation_max_size]

    @staticmethod
    def _format_product_recommendation(raw_recommendation: list[Product]) -> str:
        """Formats the product recommendation into a string.

        Args:

        raw_recommendation: The raw product recommendation.

        Returns:

        The formatted product recommendation.
        """

        formatted_recommendation = ""
        for product in raw_recommendation:
            product_price = round(product["full_price"], 2)
            formatted_recommendation += (
                f"{product['product_name']} - R${product_price} per unit\n"
            )

        return formatted_recommendation

    @staticmethod
    def _add_recommended_product_data(user_id: str, product_data: dict) -> None:
        """Adds a new recommended product to the database that tracks the user's recommended products.

        Args:

        product_data: The product data to be added in the database.
        """

        user_data = Database.get_data(user_id)

        if "recommended_products" in user_data:
            user_data["recommended_products"].append(product_data)
        else:
            user_data["recommended_products"] = [product_data]

        Database.set_data(user_id, user_data)

    @staticmethod
    def _get_recommendations_data(user_id: str) -> list[Product]:
        """Gets all the data from products that were already recommended to the user.

        Args:

        user_id: The user's ID.

        Returns:

        List containing the recommended products' data stored in the database.
        """

        user_data = Database.get_data(user_id)
        if "recommended_products" in user_data:
            return user_data["recommended_products"]
        else:
            return []

    @staticmethod
    def _get_product_data(user_id: str, product_name: str) -> dict | None:
        """Gets the data of a product using the recommendations in the user conversation.

        Args:

        user_id: The user's ID.
        product_name: The name of the product.

        Returns:

        The data of the product or None, if the product doesn't exist in the recommendations.
        """

        recommended_products = ProductHandler._get_recommendations_data(user_id)

        for product in recommended_products:
            if product["product_name"].lower() == product_name.lower():
                return product

        return None

    @staticmethod
    def product_was_recommended(user_id: str, product_name: str) -> bool:
        """Checks if a product was already recommended to the user.

        Args:

        user_id: The user's ID.
        product_name: The name of the product.

        Returns:

        True if the product was already recommended to the user, False otherwise.
        """

        product_data = ProductHandler._get_product_data(user_id, product_name)

        return product_data is not None

    @staticmethod
    def get_product_unit_price(user_id: str, product_name: str) -> float | None:
        """Gets the unit price of a product using the recommendations in the user conversation.

        Args:

        user_id: The user's ID.
        product_name: The name of the product.

        Returns:

        The price of the product or None, if the product doesn't exist in the recommendations.
        """

        product_data = ProductHandler._get_product_data(user_id, product_name)

        if product_data is not None:
            product_price = round(product_data["full_price"], 2)
            return product_price

        return None

    @staticmethod
    def get_product_unit_volume(user_id: str, product_name: str) -> float | None:
        """Gets the unit volume of a product in liters using the recommendations in the user conversation.

        Args:

        user_id: The user's ID.
        product_name: The name of the product.

        Returns:

        The volume of the product in liters or None, if the product doesn't exist in the recommendations.
        """

        product_data = ProductHandler._get_product_data(user_id, product_name)

        if product_data is not None:
            product_volume = round(
                100 * product_data["product_volume_in_hectoliters"], 3
            )
            return product_volume

        return None

    @staticmethod
    async def get_product_recommendation(
        user_id: str,
        product_query: str,
        zipcode: str,
        session: aiohttp.ClientSession | None = None,
    ) -> str:
        """Searches for a product recommendation based on the user's demand.

        Args:

        session: The aiohttp ClientSession used for concurrent searching.
        user_id: The user's ID.
        product_query: The user's demand for a product, e.g. 'A light beer'.
        zipcode: The user's ZIP code.

        Returns:

        The product recommendation based on the user's demand.
        """

        search_output = await ProductHandler._mocked_search_engine(
            product_query, zipcode, session
        )

        if not search_output:
            return ProductHandler._product_not_found_message

        for product in search_output:
            ProductHandler._add_recommended_product_data(user_id, product)

        formatted_recommendation = ProductHandler._format_product_recommendation(
            search_output
        )

        print("final recommendation", formatted_recommendation)

        return formatted_recommendation

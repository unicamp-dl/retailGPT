from typing import List

from .database import Database
from .product_handler import ProductHandler


class CartHandler:
    """
    Manages the user's cart, which is a list of products.
    """

    _max_volume_liters: float = 15

    # Predefined messages:
    _successful_removal_message: str = (
        "Product units successfully removed from the cart!"
    )
    _below_zero_removal_message: str = (
        "The number of units to remove is greater than the number of units in the cart. Therefore, this operation only completely removed the product."
    )
    _successful_addition_message: str = "Product successfully added to the cart!"

    @staticmethod
    def _set_cart(user_id: str, cart: dict) -> None:
        """
        Sets the user's cart.

        Args:

        user_id: The user's ID.
        cart: The user's cart.
        """
        user_data = Database.get_data(user_id)
        user_data["cart"] = cart
        Database.set_data(user_id, user_data)

    @staticmethod
    def _get_cart(user_id: str) -> List:
        """
        Gets the user's cart.

        Args:

        user_id: The user's ID.

        Returns:

        List of Products representing the user's cart.
        """
        user_data = Database.get_data(user_id)
        cart = []
        if "cart" in user_data:
            cart = user_data["cart"]
        return cart

    @staticmethod
    def get_cart_summary(user_id: str) -> str:
        """Formats the cart's dict into a string summary.

        Args:

        cart: The user's cart.

        Returns:

        Summary of the cart's content.
        """

        cart_total_price = 0
        cart_total_volume_liters = 0
        summary = "Your cart summary:\n"

        cart = CartHandler._get_cart(user_id)
        for product in cart:

            # TODO: Retrieve product by ID instead of name
            product_name = product["product_name"]
            number_of_units = product["number_of_units"]
            price_per_unit = product["price_per_unit"]
            volume_per_unit = product["volume_per_unit"]

            product_volume = volume_per_unit * number_of_units
            cart_total_volume_liters += product_volume

            total_product_price = price_per_unit * number_of_units
            cart_total_price += total_product_price

            summary += f"- {product_name}, "
            if number_of_units > 1:
                summary += f"{number_of_units} units, "
                summary += f"each at R${price_per_unit:.2f}  \n"
            else:
                summary += f"1 unit, at R${price_per_unit:.2f}  \n"

        summary += f"Total cart value: R${cart_total_price:.2f}  \n"
        summary += f"Total cart volume: {round(cart_total_volume_liters, 3)}L"

        return summary

    @staticmethod
    def get_should_send_cart_summary(user_id: str) -> bool:
        """
        Gets the flag that indicates if the cart summary should be sent to the user.

        Args:

        user_id: The user's ID.

        Returns:

        The flag that indicates if the cart summary should be sent to the user.
        """
        user_data = Database.get_data(user_id)
        should_send_cart_summary = False
        if "should_send_cart_summary" in user_data:
            should_send_cart_summary = user_data["should_send_cart_summary"]
        return should_send_cart_summary

    @staticmethod
    def set_should_send_cart_summary(
        user_id: str, should_send_cart_summary: bool
    ) -> None:
        """
        Sets the flag that indicates if the cart summary should be sent to the user.

        Args:

        user_id: The user's ID.
        should_send_cart_summary: The flag that indicates if the cart summary should be sent to the user.
        """
        user_data = Database.get_data(user_id)
        user_data["should_send_cart_summary"] = should_send_cart_summary
        Database.set_data(user_id, user_data)

    @staticmethod
    def process_cart_operation(
        user_id: str, operation: str, product_name: str, number_of_units: int
    ) -> str:
        """Processes a cart operation.

        Args:

        user_id: The user's ID.
        operation: The operation to be performed on the cart.
        product_name: The product to be added or removed from the cart.
        number_of_units: The amount of the product to be added or removed from the cart.

        Returns:

        Summary of the operation result and the current state of the cart.
        """

        cart = CartHandler._get_cart(user_id)

        if operation == "add":
            output_string = CartHandler._process_addition(
                user_id, cart, product_name, number_of_units
            )
        elif operation == "remove":
            output_string = CartHandler._process_removal(
                cart, product_name, number_of_units
            )
        else:
            output_string = "Invalid operation"

        CartHandler._set_cart(user_id, cart)

        return output_string

    @staticmethod
    def _add_to_cart(
        cart: List[dict],
        product_name: str,
        number_of_units: int,
        price_per_unit: float,
        volume_per_unit: float,
    ) -> None:
        """Updates the cart list with the addition of a product.

        Args:

        cart: The user's cart.
        product_name: The product to be added to the cart.
        number_of_units: The amount of the product to be added to the cart.
        price_per_unit: The price of the product per unit.
        volume_per_unit: The volume of the product per unit.
        """

        if any(product_name == product["product_name"] for product in cart):
            for product in cart:
                if product["product_name"] == product_name:
                    product["number_of_units"] += number_of_units
        else:
            cart.append(
                {
                    "product_name": product_name,
                    "number_of_units": number_of_units,
                    "price_per_unit": price_per_unit,
                    "volume_per_unit": volume_per_unit,
                }
            )

    @staticmethod
    def _max_volume_exceeded(cart: List[dict], additional_volume: float) -> bool:
        """
        Checks if the addition of a product to the cart would exceed the maximum volume allowed.

        Args:

        cart: The user's cart.
        additional_volume: The volume to be added to the cart.

        Returns:

        True if the addition would exceed the maximum volume allowed, False otherwise.
        """
        total_volume = additional_volume

        for product in cart:
            total_volume += product["volume_per_unit"] * product["number_of_units"]

        return total_volume > CartHandler._max_volume_liters

    @staticmethod
    def _get_max_allowed_units(
        cart: List[dict], additional_volume_per_unit: float
    ) -> int:
        """
        Gets the maximum number of units of a product that can be added to the cart.

        Args:

        cart: The user's cart.
        additional_volume_per_unit: The volume of the unit of the product to be added to the cart.

        Returns:

        The maximum number of units of a product that can be added to the cart.
        """

        current_volume = 0
        for product in cart:
            current_volume += product["volume_per_unit"] * product["number_of_units"]
        remaining_volume = CartHandler._max_volume_liters - current_volume
        max_units = remaining_volume // additional_volume_per_unit
        return int(max_units)

    @staticmethod
    def _process_addition(
        user_id: str, cart: dict, product_name: str, number_of_units: int
    ) -> str:
        """
        Processes the addition of a product to the user's cart.

        Args:

        user_id: The user's ID.
        cart: The user's cart.
        product_name: The product to be added to the cart.
        number_of_units: The amount of the product to be added to the cart.

        Returns:

        Summary of the operation result.
        """

        price_per_unit = ProductHandler.get_product_unit_price(user_id, product_name)
        volume_per_unit = ProductHandler.get_product_unit_volume(user_id, product_name)

        additional_volume = volume_per_unit * number_of_units

        if CartHandler._max_volume_exceeded(cart, additional_volume):

            number_of_units = CartHandler._get_max_allowed_units(cart, volume_per_unit)
            max_volume_liters = CartHandler._max_volume_liters

            if number_of_units > 0:
                output_string = f"The maximum volume of {max_volume_liters} liters per order has been exceeded. The number of units has been adjusted to {number_of_units}.\n"
            else:
                output_string = f"The maximum volume of {max_volume_liters} liters per order has been exceeded. The product was not added to the cart.\n"

        else:
            output_string = CartHandler._successful_addition_message

        if number_of_units > 0:
            CartHandler._add_to_cart(
                cart, product_name, number_of_units, price_per_unit, volume_per_unit
            )

        return output_string

    @staticmethod
    def _process_removal(cart: dict, product_name: str, number_of_units: int) -> str:
        """
        Processes the removal of a product from the user's cart.

        Args:

        cart: The user's cart.
        product_name: The product to be removed from the cart.
        amount: The amount of the product to be removed from the cart.

        Returns:

        Summary of the operation result.
        """

        output_string = "Product not found in the cart."
        for product in cart:
            if product["product_name"] == product_name:
                product["number_of_units"] -= number_of_units
                if product["number_of_units"] <= 0:
                    cart.remove(product)
                if product["number_of_units"] < 0:
                    output_string = CartHandler._below_zero_removal_message
                else:
                    output_string = CartHandler._successful_removal_message

        return output_string

    @staticmethod
    def set_should_finish_purchase(user_id: str, should_finish_purchase: bool) -> None:
        """
        Sets the flag that indicates if the purchase should be finished.

        Args:

        user_id: The user's ID.
        should_finish_purchase: The flag that indicates if the purchase should be finished.
        """
        user_data = Database.get_data(user_id)
        user_data["should_finish_purchase"] = should_finish_purchase
        Database.set_data(user_id, user_data)

    @staticmethod
    def get_should_finish_purchase(user_id: str) -> bool:
        """
        Gets the flag that indicates if the purchase should be finished.

        Args:

        user_id: The user's ID.

        Returns:

        The flag that indicates if the purchase should be finished.
        """
        user_data = Database.get_data(user_id)
        should_finish_purchase = False
        if "should_finish_purchase" in user_data:
            should_finish_purchase = user_data["should_finish_purchase"]
        return should_finish_purchase

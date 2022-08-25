import requests
from argparse import ArgumentParser

from moltin_api import SimpleMoltinApiClient


def create_product(moltin: SimpleMoltinApiClient, product: dict):
    name = product["name"]
    description = product["description"]
    sku = product["id"]
    price = product["price"]
    image_url = product["product_image"]["url"]

    new_product_id = moltin.create_product(
        name, price, description, sku=sku, manage_stock=False
    )
    new_product_image = moltin.create_image_from_url(image_url)
    moltin.attach_image_to_product(new_product_id, new_product_image)
    return new_product_id


def create_restaurant_flow(moltin: SimpleMoltinApiClient):
    restaurant_flow_id = moltin.create_flow(
        "Restaurant", "Flow describing avaliable restaurant"
    )
    print(f"Created restaurant flow: {create_restaurant_flow}")
    restaurant_fields = {
        "restaurant_address": {
            "type": "string",
            "description": "Full address of the restaurant",
        },
        "restaurant_alias": {
            "type": "string",
            "description": "Distinct name of the restaurant",
        },
        "restaurant_lon": {
            "type": "float",
            "description": "Longitude part of restaurant coordinates",
        },
        "restaurant_lat": {
            "type": "float",
            "description": "Latitude part of restaurant coordinates",
        },
        "restaurant_courier": {
            "type": "integer",
            "description": "Telegram ID of restaurant courier",
        },
    }
    for field_name, field_options in restaurant_fields.items():
        new_field_id = moltin.create_flow_field(
            restaurant_flow_id,
            field_name,
            field_options["type"],
            field_options["description"],
        )
        print(f"New field created {new_field_id}")


def create_customer_address_flow(moltin: SimpleMoltinApiClient):
    customer_address_flow_id = moltin.create_flow(
        "Customer Address", "Stores location of customers"
    )
    print(f"Created Customer Address flow: {create_restaurant_flow}")
    customer_address_fields = {
        "telegram_id": {
            "type": "integer",
            "description": "Customer telegram ID",
        },
        "lon": {
            "type": "float",
            "description": "Longitude part of customer coordinates",
        },
        "lat": {
            "type": "float",
            "description": "Latitude part of customer coordinates",
        },
    }
    for field_name, field_options in customer_address_fields.items():
        new_field_id = moltin.create_flow_field(
            customer_address_flow_id,
            field_name,
            field_options["type"],
            field_options["description"],
        )
        print(f"New field created {new_field_id}")


def main():
    parser = ArgumentParser()

    parser.add_argument("id", type=str, help="Moltin Client ID for API access")
    parser.add_argument("secret", type=str, help="Moltin Client Secret for API access")
    parser.add_argument(
        "-P",
        "--load-products-url",
        type=str,
        help="URL address with JSON catalog of products to parse",
    )
    parser.add_argument(
        "-R",
        "--load-restaurants-url",
        type=str,
        help="URL address with JSON catalog register of restaurants to parse",
    )
    parser.add_argument(
        "--default-courier-id",
        type=int,
        help="Default courier telegram id for testing purposes",
    )

    args = parser.parse_args()

    moltin_clinet = SimpleMoltinApiClient(args.id, client_secret=args.secret)

    try:
        create_customer_address_flow(moltin_clinet)
    except requests.exceptions.HTTPError:
        print(
            "Cannot create Customer Address flow. It either exists or API call has failed."
        )

    try:
        create_restaurant_flow(moltin_clinet)
    except requests.exceptions.HTTPError:
        print("Cannot create restaurant flow. It either exists or API call has failed.")

    if products_url := args.load_products_url:
        response = requests.get(products_url)
        response.raise_for_status()
        product_catalog = response.json()
        for product in product_catalog:
            new_product_id = create_product(moltin_clinet, product)
            print(f"New product created: {new_product_id}")

    if restaurants_url := args.load_restaurants_url:
        if not (default_courier_id := args.default_courier_id):
            raise ValueError("Default courier ID must be provided")
        response = requests.get(restaurants_url)
        response.raise_for_status()
        restaurant_register = response.json()
        for restaurant in restaurant_register:
            new_restaurant_id = moltin_clinet.create_flow_entry(
                "restaurant",
                restaurant_alias=restaurant["alias"],
                restaurant_address=restaurant["address"]["full"],
                restaurant_lon=float(restaurant["coordinates"]["lon"]),
                restaurant_lat=float(restaurant["coordinates"]["lat"]),
                restaurant_courier=default_courier_id,
            )
            print(f"New restaurant created: {new_restaurant_id}")


if __name__ == "__main__":
    main()

import stripe
import json
from stripe import InvalidRequestError


def export_subscriptions(api_key):
    stripe.api_key = api_key
    cursor = None
    subscriptions = []

    while True:
        results = stripe.Subscription.list(limit=100, starting_after=cursor)
        cursor = results.data[-1].id
        subscriptions.extend(results.data)

        if not results.has_more:
            break

    return subscriptions


def export_plans(old_key, new_key):
    stripe.api_key = old_key
    plans = stripe.Plan.list(limit=100)
    plan_mapping = {}

    stripe.api_key = new_key
    for plan in plans:
        try:
            new_plan = stripe.Plan.create(
                amount=plan.amount,
                currency=plan.currency,
                interval=plan.interval,
                product=plan.product,
                nickname=plan.nickname,
                id=plan.id,
            )
            plan_mapping[plan.id] = new_plan.id
        except InvalidRequestError as e:
            if 'A plan or price with this ID already exists.' in str(e):
                print(f"Plan {plan.id} skipped as it already exists.")
            else:
                raise

    return plan_mapping


def export_products_prices(old_key, new_key):
    stripe.api_key = old_key
    products = stripe.Product.list(limit=100)
    product_mapping = {}

    for product in products:
        new_product = None
        stripe.api_key = new_key
        try:
            new_product = stripe.Product.create(
                name=product.name,
                type=product.type,
                id=product.id,
            )
            product_mapping[product.id] = new_product.id
        except InvalidRequestError as e:
            if 'Product already exists.' in str(e):
                print(f"Product {product.id} skipped as it already exists.")
                new_product = product
            else:
                raise

        stripe.api_key = old_key
        prices = stripe.Price.list(product=product.id)
        for price in prices:
            stripe.api_key = new_key
            try:
                stripe.Price.create(
                    product=new_product.id,
                    unit_amount=price.unit_amount,
                    currency=price.currency,
                    recurring=price.recurring,
                    nickname=price.nickname,
                )
            except InvalidRequestError as e:
                if 'Price already exists.' in str(e):
                    print(f"Price {price.id} skipped as it already exists.")
                else:
                    raise

    return product_mapping


def transfer_customers(api_key_old, api_key_new, old_subscriptions, *args, **kwargs):
    stripe.api_key = api_key_old

    for old_subs in old_subscriptions:
        old_customer = stripe.Customer.retrieve(old_subs["customer"])

        stripe.api_key = api_key_new
        new_customer = stripe.Customer.list(email=old_customer["email"])

        items_data = old_subs["items"]["data"]
        for item in items_data:
            del item["plan"]
            del item["subscription"]
            del item["created"]
            del item["id"]
            del item["object"]

            for new_custom in new_customer:
                recreated_subscription = stripe.Subscription.create(
                    customer=new_custom.id,
                    items=items_data,
                    trial_end=old_subs["current_period_end"],
                )

        print(f"Customer {old_customer.id} transferred to the new account.")

    print("Transfer completed.")


OLD_SECRET_KEY = ''
NEW_SECRET_KEY = ''

old_subs = export_subscriptions(OLD_SECRET_KEY)
product_mapping = export_products_prices(OLD_SECRET_KEY, NEW_SECRET_KEY)
plan_mapping = export_plans(OLD_SECRET_KEY, NEW_SECRET_KEY)
transfer_customers(OLD_SECRET_KEY, NEW_SECRET_KEY, old_subs,)

"""ELITE - Premium Shopping House terminal application."""

from elite_shop_core import AccountStore, MYSTERY_BOXES, PRODUCTS, ShopError, membership, next_tier, purchase, purchase_box

balence = 10000  # Legacy spelling retained for compatibility with the prototype.
cart = []
store = None


def _header(title):
    border = "═" * 58
    print(f"\n╔{border}╗\n║{title.center(58)}║\n╚{border}╝")


def _show_catalogue():
    _header("✦ ELITE COLLECTIONS ✦")
    categories = {}
    for product in PRODUCTS.values():
        categories.setdefault(product.category, []).append(product)
    for category, products in categories.items():
        print(f"\n{category}")
        for product in products:
            print(f"  {product.product_id}  {product.name:<25} ₹{product.price:>6}  {product.description}")


def _shop(account):
    selected = {}
    while True:
        _header("SHOPPING CART")
        print("Enter a product ID to add it, CART to checkout, or BACK to return.")
        choice = input("ELITE > ").strip().upper()
        if choice == "BACK":
            return
        if choice == "CART":
            if not selected:
                print("Your cart is empty.")
                continue
            print("Items:", ", ".join(f"{key} x{value}" for key, value in selected.items()))
            try:
                points = int(input("Reward points to redeem (0 for none): ") or "0")
                result = purchase(account, selected, points)
            except ValueError:
                print("Please enter a whole number.")
                continue
            except ShopError as error:
                print(f"Transaction declined: {error}")
                continue
            print(f"\n✦ PAYMENT COMPLETE  #{result['id'][:10]}  Total: ₹{result['total']}")
            print(f"Membership: {result['membership']} | Purchase points: {result['purchase_points']}")
            for title, reward in result["achievements"]:
                print(f"✦ NEW HONOUR: {title} (+{reward} points)")
            selected.clear()
            store.save()
            continue
        if choice not in PRODUCTS:
            print("That product ID is not in the catalogue.")
            continue
        try:
            quantity = int(input("Quantity: ") or "1")
        except ValueError:
            print("Quantity must be a positive whole number.")
            continue
        if quantity <= 0:
            print("Quantity must be positive.")
        else:
            selected[choice] = selected.get(choice, 0) + quantity


def _mystery(account):
    _header("ELITE PRIVATE VAULT")
    for key, box in MYSTERY_BOXES.items():
        contents = ", ".join(PRODUCTS[item].name for item in box["contents"])
        print(f"{key.upper():10} ₹{box['price']:<5} {box['classification']:<10} | Disclosed: {contents}")
    choice = input("Box name, or BACK: ").strip().lower()
    if choice == "back":
        return
    try:
        result = purchase_box(account, choice)
    except ShopError as error:
        print(f"Vault purchase declined: {error}")
        return
    print("\n✦ VAULT REVEAL ✦", " + ".join(result["contents"]))
    for title, reward in result["achievements"]:
        print(f"✦ NEW HONOUR: {title} (+{reward} points)")
    store.save()


def _dashboard(account):
    tier, discount = membership(account)
    upcoming, needed = next_tier(account)
    _header("ELITE MEMBERSHIP")
    next_status = f"{upcoming} ({needed} needed)" if upcoming else "Signature status reached"
    print(f"Username: {account['username']}\nMember ID: ELITE-{account['username'].upper()}\nTier: {tier} ({discount}% discount)\nEligible spending: ₹{account['eligible_spending']}\nNext tier: {next_status}")


def _transactions(account):
    rows = [f"{item['id'][:10]} | {item['type']} | ₹{item['total']}" for item in account["transactions"]]
    print("\n".join(rows) or "No transactions yet.")


def in_ELITE():
    global store
    store = AccountStore()
    _header("✦ ELITE ✦\nPREMIUM SHOPPING HOUSE")
    username = input("Username (new account if not found): ").strip()
    password = input("Password: ")
    try:
        account = store.authenticate(username, password)
    except ShopError:
        try:
            account = store.register(username, password)
        except ShopError as error:
            print(error)
            return
    while True:
        _header("ELITE HOUSE")
        print("1. USER PROFILE\n2. EXPLORE COLLECTIONS\n3. SHOPPING CART\n4. ELITE MEMBERSHIP\n5. MYSTERY COLLECTION\n6. ELITE HONOURS\n7. REWARD POINTS\n8. SPECIAL OFFERS\n9. TRANSACTION HISTORY\n10. HELP & SUPPORT\n0. EXIT")
        choice = input("ELITE > ").strip()
        if choice == "1":
            print(f"{account['username']} | Balance ₹{account['balance']} | Inventory {sum(account['inventory'].values())} items")
        elif choice == "2":
            _show_catalogue()
        elif choice == "3":
            _shop(account)
        elif choice == "4":
            _dashboard(account)
        elif choice == "5":
            _mystery(account)
        elif choice == "6":
            print("Honours:", ", ".join(account["achievements"]) or "No honours yet.")
        elif choice == "7":
            print(f"Available points: {account['points']} | Lifetime earned: {account['lifetime_points']} | Redeemed: {account['points_redeemed']}")
        elif choice == "8":
            print("Silver members and above receive early access to selected collections.")
        elif choice == "9":
            _transactions(account)
        elif choice == "10":
            print("Support: review the catalogue, add products by ID, and checkout from your cart.")
        elif choice == "0":
            store.save()
            print("Thank you for visiting ELITE.")
            return
        else:
            print("Invalid menu choice.")


def shop():
    in_ELITE()


def daily_use_items():
    _show_catalogue()


def food_items():
    _show_catalogue()


def electric_accesories():
    _show_catalogue()


def checkout():
    print("Checkout is available from the Shopping Cart menu.")


def cash():
    print("Cash checkout is not supported; account balance is used securely.")


def card():
    print("Card checkout is not supported; account balance is used securely.")


if __name__ == "__main__":
    in_ELITE()
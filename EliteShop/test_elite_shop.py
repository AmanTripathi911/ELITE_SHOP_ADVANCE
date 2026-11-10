import tempfile
import unittest
from pathlib import Path

from elite_shop_core import AccountStore, PRODUCTS, ShopError, membership, purchase, purchase_box, refund


class EliteShopTests(unittest.TestCase):
    def setUp(self):
        self.directory = tempfile.TemporaryDirectory()
        self.store = AccountStore(Path(self.directory.name) / "accounts.json")
        self.account = self.store.register("alice", "secret", 20000)

    def tearDown(self):
        self.directory.cleanup()

    def test_purchase_discount_points_and_idempotent_refund(self):
        self.account["eligible_spending"] = 5000
        result = purchase(self.account, {"FAS-01": 1})
        self.assertEqual(result["total"], 8075)
        self.assertEqual(self.account["points"], 135)
        refund(self.account, result["id"])
        self.assertEqual(self.account["balance"], 20000)
        with self.assertRaises(ShopError): refund(self.account, result["id"])

    def test_insufficient_balance_is_atomic(self):
        self.account["balance"] = 1
        with self.assertRaises(ShopError): purchase(self.account, {"FAS-01": 1})
        self.assertEqual(self.account["inventory"], {})

    def test_membership_upgrade_and_separate_accounts(self):
        purchase(self.account, {"FAS-01": 1})
        self.assertEqual(membership(self.account), ("Gold", 5))
        other = self.store.register("bob", "secret", 100)
        self.assertEqual(other["balance"], 100)
        self.assertEqual(other["inventory"], {})

    def test_mystery_box_discloses_contents_and_updates_inventory(self):
        result = purchase_box(self.account, "classic")
        self.assertEqual(result["contents"], [PRODUCTS["LIF-02"].name, PRODUCTS["LIF-05"].name])
        self.assertEqual(self.account["inventory"]["LIF-02"], 1)

    def test_corrupted_json_recovers(self):
        path = Path(self.directory.name) / "broken.json"
        path.write_text("not json", encoding="utf-8")
        store = AccountStore(path)
        self.assertEqual(store.data, {"accounts": {}})

    def test_points_redemption_and_persistence(self):
        purchase(self.account, {"FAS-01": 1})
        self.assertEqual(self.account["points"], 135)
        purchase(self.account, {"LIF-02": 1}, 100)
        self.assertEqual(self.account["points_redeemed"], 100)
        self.store.save()
        reloaded = AccountStore(Path(self.directory.name) / "accounts.json")
        self.assertEqual(reloaded.authenticate("alice", "secret")["balance"], 11082)


if __name__ == "__main__":
    unittest.main()
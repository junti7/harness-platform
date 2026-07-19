import tempfile
import unittest
from pathlib import Path

from core.recommerce_workspace import (
    WorkspaceConflictError,
    WorkspaceValidationError,
    get_workspace,
    mutate_workspace,
)


class RecommerceWorkspaceTests(unittest.TestCase):
    def setUp(self):
        self.tempdir = tempfile.TemporaryDirectory()
        self.path = Path(self.tempdir.name) / "workspace.json"

    def tearDown(self):
        self.tempdir.cleanup()

    def mutate(self, action, payload, version=0):
        return mutate_workspace(
            self.path,
            expected_version=version,
            action=action,
            payload=payload,
            actor="ceo",
        )

    def test_default_workspace_has_locked_execution_phases(self):
        view = get_workspace(self.path)
        self.assertEqual(view["workspace_version"], 0)
        self.assertEqual([phase["state"] for phase in view["phases"][-2:]], ["locked", "locked"])
        self.assertNotIn("paid_demand", view)

    def test_cas_rejects_stale_writer_without_lost_update(self):
        first = self.mutate("add_supplier", {"name": "A 공급처"})
        self.assertEqual(first["workspace_version"], 1)
        with self.assertRaises(WorkspaceConflictError) as ctx:
            self.mutate("add_supplier", {"name": "B 공급처"}, version=0)
        self.assertEqual(ctx.exception.workspace["workspace_version"], 1)
        self.assertEqual(len(get_workspace(self.path)["suppliers"]), 1)

    def test_restricted_product_is_server_blocked(self):
        with self.assertRaisesRegex(WorkspaceValidationError, "restricted product indicator"):
            self.mutate("add_sku", self.valid_sku(name="어린이 전기 장난감"))

    def test_restricted_legacy_product_is_quarantined_on_read(self):
        view = self.mutate("add_sku", self.valid_sku())
        raw = self.path.read_text(encoding="utf-8").replace("데스크 정리 트레이", "어린이 전기 트레이")
        self.path.write_text(raw, encoding="utf-8")
        self.assertEqual(get_workspace(self.path)["sku_candidates"], [])

    def test_disallowed_category_is_server_blocked(self):
        with self.assertRaisesRegex(WorkspaceValidationError, "category is not allowed"):
            self.mutate("add_sku", self.valid_sku(category="food"))

    def test_zero_cost_requires_explicit_confirmation(self):
        payload = self.valid_sku()
        payload["zero_cost_confirmed"] = False
        with self.assertRaisesRegex(WorkspaceValidationError, "zero cost"):
            self.mutate("add_sku", payload)

    def test_full_cost_contribution_and_score_are_computed(self):
        view = self.mutate("add_sku", self.valid_sku())
        sku = view["sku_candidates"][0]
        self.assertEqual(sku["full_variable_cost"], 24000)
        self.assertEqual(sku["contribution"], 16000)
        self.assertEqual(sku["contribution_rate"], 40.0)
        self.assertTrue(sku["cost_review_condition_met"])

    def test_supplier_cannot_be_deleted_while_referenced(self):
        first = self.mutate("add_supplier", {"name": "A 공급처"})
        supplier_id = first["suppliers"][0]["id"]
        sku = self.valid_sku()
        sku["supplier_id"] = supplier_id
        second = self.mutate("add_sku", sku, version=1)
        with self.assertRaisesRegex(WorkspaceValidationError, "referenced"):
            self.mutate("delete_supplier", {"id": supplier_id}, version=second["workspace_version"])

    @staticmethod
    def valid_sku(**overrides):
        payload = {
            "name": "데스크 정리 트레이",
            "supplier_id": "",
            "category": "storage_organization",
            "conservative_sale_price": 40000,
            "unit_purchase_cost": 16000,
            "platform_fee": 1200,
            "inbound_shipping": 800,
            "outbound_shipping": 3000,
            "packaging_cost": 500,
            "ad_coupon_cost": 0,
            "return_defect_reserve": 800,
            "labor_cost": 1000,
            "aging_markdown_loss": 500,
            "dispute_tax_reserve": 200,
            "zero_cost_confirmed": True,
            "evidence_status": "verified",
            "scores": {key: 4 for key in ("demand", "supply", "competition", "shipping", "returns", "evidence", "turnover", "content")},
            "note": "비규제 수납용품",
        }
        payload.update(overrides)
        return payload


if __name__ == "__main__":
    unittest.main()

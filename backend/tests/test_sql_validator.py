import re
import unittest

from app.services.sql_validator import SQLValidationError, validate_sql

VALID_PMPM = """
SELECT dm.county, SUM(fc.paid_amount) / NULLIF(SUM(fmm.member_months), 0) AS pmpm
FROM fact_claim fc
JOIN dim_member dm ON fc.member_id = dm.member_id
JOIN fact_member_month fmm ON dm.member_id = fmm.member_id
WHERE dm.county = 'Alameda'
GROUP BY dm.county
"""

VALID_PENDING = """
SELECT COUNT(*) AS pending_claims_count
FROM fact_claim fc
WHERE fc.claim_status = 'PENDING'
"""

VALID_UNQUALIFIED_WHERE = """
SELECT COUNT(*) FROM fact_claim WHERE claim_status = 'PENDING'
"""


class TestSQLValidator(unittest.TestCase):
    def test_valid_pmpm_query(self):
        validate_sql(VALID_PMPM)

    def test_valid_pending_query(self):
        validate_sql(VALID_PENDING)

    def test_valid_unqualified_where_column(self):
        validate_sql(VALID_UNQUALIFIED_WHERE)

    def test_rejects_unknown_table(self):
        with self.assertRaises(SQLValidationError) as ctx:
            validate_sql("SELECT * FROM secret_table")
        self.assertIn("Unknown table", str(ctx.exception))

    def test_rejects_unknown_qualified_column(self):
        with self.assertRaises(SQLValidationError) as ctx:
            validate_sql(
                """
                SELECT dm.date_of_birth
                FROM fact_claim fc
                JOIN dim_member dm ON fc.member_id = dm.member_id
                """
            )
        self.assertIn("Unknown column", str(ctx.exception))

    def test_rejects_unknown_unqualified_column(self):
        with self.assertRaises(SQLValidationError) as ctx:
            validate_sql(
                """
                SELECT birth_date
                FROM dim_member dm
                GROUP BY birth_date
                """
            )
        self.assertIn("Unknown column", str(ctx.exception))

    def test_rejects_unknown_alias_column(self):
        with self.assertRaises(SQLValidationError) as ctx:
            validate_sql(
                """
                SELECT d.county
                FROM fact_claim fc
                JOIN dim_member dm ON fc.member_id = dm.member_id
                """
            )
        self.assertIn("Unknown table or alias", str(ctx.exception))

    def test_rejects_insert(self):
        with self.assertRaises(SQLValidationError):
            validate_sql("INSERT INTO fact_claim VALUES (1)")

    def test_rejects_delete(self):
        with self.assertRaises(SQLValidationError):
            validate_sql("DELETE FROM fact_claim")


if __name__ == "__main__":
    unittest.main()

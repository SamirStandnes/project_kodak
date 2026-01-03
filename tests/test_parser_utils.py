"""Tests for scripts/shared/parser_utils.py"""
import pytest
from kodak.shared.parser_utils import (
    create_empty_transaction,
    validate_transaction,
    validate_parser_output,
    clean_num,
    VALID_TRANSACTION_TYPES
)


class TestCreateEmptyTransaction:
    """Tests for the create_empty_transaction function."""

    def test_returns_dict(self):
        """Should return a dictionary."""
        txn = create_empty_transaction()
        assert isinstance(txn, dict)

    def test_has_required_keys(self):
        """Should have all required keys."""
        txn = create_empty_transaction()
        required_keys = [
            'external_id', 'account_external_id', 'isin', 'symbol',
            'date', 'type', 'quantity', 'price', 'amount', 'currency',
            'amount_local', 'exchange_rate', 'description', 'source_file',
            'fee', 'fee_currency', 'fee_local'
        ]
        for key in required_keys:
            assert key in txn, f"Missing key: {key}"

    def test_has_unique_external_id(self):
        """Each call should generate a unique external_id."""
        txn1 = create_empty_transaction()
        txn2 = create_empty_transaction()
        assert txn1['external_id'] != txn2['external_id']

    def test_numeric_defaults(self):
        """Numeric fields should default to 0.0 or 1.0."""
        txn = create_empty_transaction()
        assert txn['quantity'] == 0.0
        assert txn['price'] == 0.0
        assert txn['amount'] == 0.0
        assert txn['amount_local'] == 0.0
        assert txn['exchange_rate'] == 1.0
        assert txn['fee'] == 0.0
        assert txn['fee_local'] == 0.0


class TestValidateTransaction:
    """Tests for the validate_transaction function."""

    def test_valid_transaction(self):
        """Valid transaction should return no errors."""
        txn = {
            'date': '2024-01-15',
            'type': 'BUY',
            'account_external_id': 'ACC001',
            'quantity': 10.0,
            'price': 100.0,
            'amount': -1000.0,
            'currency': 'USD',
            'amount_local': -10000.0,
            'exchange_rate': 10.0
        }
        errors = validate_transaction(txn)
        assert len(errors) == 0

    def test_missing_date(self):
        """Missing date should return an error."""
        txn = {
            'type': 'BUY',
            'account_external_id': 'ACC001'
        }
        errors = validate_transaction(txn)
        assert any('date' in e.lower() for e in errors)

    def test_missing_type(self):
        """Missing type should return an error."""
        txn = {
            'date': '2024-01-15',
            'account_external_id': 'ACC001'
        }
        errors = validate_transaction(txn)
        assert any('type' in e.lower() for e in errors)

    def test_invalid_type(self):
        """Unknown transaction type should return an error."""
        txn = {
            'date': '2024-01-15',
            'type': 'INVALID_TYPE',
            'account_external_id': 'ACC001'
        }
        errors = validate_transaction(txn)
        assert any('type' in e.lower() for e in errors)

    def test_invalid_date_format(self):
        """Invalid date format should return an error."""
        txn = {
            'date': 'invalid',
            'type': 'BUY',
            'account_external_id': 'ACC001'
        }
        errors = validate_transaction(txn)
        assert any('date' in e.lower() for e in errors)

    def test_invalid_numeric_field(self):
        """Non-numeric value in numeric field should return an error."""
        txn = {
            'date': '2024-01-15',
            'type': 'BUY',
            'account_external_id': 'ACC001',
            'quantity': 'not a number'
        }
        errors = validate_transaction(txn)
        assert any('numeric' in e.lower() for e in errors)

    def test_invalid_currency_code(self):
        """Invalid currency code should return an error."""
        txn = {
            'date': '2024-01-15',
            'type': 'BUY',
            'account_external_id': 'ACC001',
            'currency': 'INVALID'
        }
        errors = validate_transaction(txn)
        assert any('currency' in e.lower() for e in errors)


class TestValidateParserOutput:
    """Tests for the validate_parser_output function."""

    def test_valid_output(self):
        """Valid parser output should pass validation."""
        transactions = [
            {
                'date': '2024-01-15',
                'type': 'BUY',
                'account_external_id': 'ACC001',
                'quantity': 10.0,
                'currency': 'USD'
            }
        ]
        is_valid, errors = validate_parser_output(transactions, "test_parser")
        assert is_valid
        assert len(errors) == 0

    def test_non_list_output(self):
        """Non-list output should fail validation."""
        is_valid, errors = validate_parser_output("not a list", "test_parser")
        assert not is_valid
        assert len(errors) > 0

    def test_empty_list(self):
        """Empty list should pass with warning."""
        is_valid, errors = validate_parser_output([], "test_parser")
        assert is_valid

    def test_invalid_row(self):
        """Invalid row should be caught."""
        transactions = [
            {
                'date': '2024-01-15',
                'type': 'INVALID_TYPE',
                'account_external_id': 'ACC001'
            }
        ]
        is_valid, errors = validate_parser_output(transactions, "test_parser")
        assert not is_valid
        assert len(errors) > 0


class TestCleanNum:
    """Tests for the clean_num wrapper."""

    def test_basic_usage(self):
        """Should work like the shared clean_num."""
        assert clean_num("100.50") == 100.5
        assert clean_num(None) == 0.0

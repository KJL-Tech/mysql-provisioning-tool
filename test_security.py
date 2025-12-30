import unittest
import backend
import re

class TestSecurityFunctions(unittest.TestCase):

    def test_validate_identifier_valid(self):
        """Test that valid identifiers pass validation."""
        valid_ids = ["Project_1", "MyApp", "PROD_ENV", "user123"]
        for identifier in valid_ids:
            self.assertEqual(backend.validate_identifier(identifier), identifier)

    def test_validate_identifier_invalid(self):
        """Test that invalid identifiers raise ValueError."""
        invalid_ids = ["Project 1", "Drop;Table", "User-Name", "v$@riable"]
        for identifier in invalid_ids:
            with self.assertRaises(ValueError):
                backend.validate_identifier(identifier)

    def test_get_privileges_by_role(self):
        """Test RBAC mapping."""
        self.assertEqual(backend.get_privileges_by_role("admin"), "ALL PRIVILEGES")
        self.assertEqual(backend.get_privileges_by_role("DBO"), "ALL PRIVILEGES")
        self.assertEqual(backend.get_privileges_by_role("read"), "SELECT")
        self.assertEqual(backend.get_privileges_by_role("app_user"), "SELECT, INSERT, UPDATE, DELETE, EXECUTE, SHOW VIEW")

    def test_generate_password_security(self):
        """Test password complexity and length."""
        pwd = backend.generate_password(length=20)
        self.assertEqual(len(pwd), 20)
        self.assertTrue(any(c.islower() for c in pwd))
        self.assertTrue(any(c.isupper() for c in pwd))
        self.assertTrue(sum(c.isdigit() for c in pwd) >= 3)
        self.assertTrue(any(c in "!@#$%^&*" for c in pwd))

if __name__ == '__main__':
    unittest.main()

from datetime import date, timedelta

from odoo import fields
from odoo.exceptions import ValidationError
from odoo.tests.common import TransactionCase

from ..models.loan import LOAN_PERIOD_DAYS, FINE_PER_DAY


class TestLibraryLoanLogic(TransactionCase):
    @classmethod
    def setUpClass(cls):
        super().setUpClass()
        cls.book = cls.env["library.book"].create(
            {
                "name": "Test Book",
                "author": "Test Author",
            }
        )
        cls.copy = cls.env["library.copy"].create(
            {
                "book_id": cls.book.id,
                "inventory_number": "TEST-001",
            }
        )
        cls.member = cls.env["library.member"].create(
            {
                "name": "Test Member",
                "membership_number": "TEST-M-001",
            }
        )

    def _create_loan(self, **values):
        loan_values = {
            "copy_id": self.copy.id,
            "member_id": self.member.id,
            "loan_date": fields.Date.today(),
        }
        loan_values.update(values)
        return self.env["library.loan"].create(loan_values)

    def test_changing_loan_date_recomputes_due_date(self):
        loan = self._create_loan()
        new_loan_date = fields.Date.today() - timedelta(days=30)

        loan.write({"loan_date": new_loan_date})

        self.assertEqual(
            loan.due_date,
            new_loan_date + timedelta(days=LOAN_PERIOD_DAYS),
        )

    def test_practical_date_and_fine_examples(self):
        loan_date = date(2026, 9, 1)
        loan = self._create_loan(loan_date=loan_date)

        self.assertEqual(loan.due_date, date(2026, 9, 15))

        loan.write({"return_date": date(2026, 9, 14)})
        self.assertEqual(loan.fine_amount, 0.0)

        loan.write({"return_date": date(2026, 9, 18)})
        self.assertEqual(loan.fine_amount, 15.0)

        loan.write({"return_date": date(2026, 9, 25)})
        self.assertEqual(loan.fine_amount, 50.0)

    def test_past_and_today_loan_dates_are_allowed(self):
        today = fields.Date.context_today(self.env["library.loan"])
        past_loan = self._create_loan(loan_date=today - timedelta(days=1))
        today_loan = self._create_loan(
            copy_id=self.env["library.copy"].create(
                {
                    "book_id": self.book.id,
                    "inventory_number": "TEST-TODAY-001",
                }
            ).id,
            loan_date=today,
        )

        self.assertEqual(past_loan.loan_date, today - timedelta(days=1))
        self.assertEqual(today_loan.loan_date, today)

    def test_future_loan_date_is_rejected_on_create_and_write(self):
        today = fields.Date.context_today(self.env["library.loan"])
        tomorrow = today + timedelta(days=1)

        with self.assertRaises(ValidationError):
            self._create_loan(loan_date=tomorrow)

        future_copy = self.env["library.copy"].create(
            {
                "book_id": self.book.id,
                "inventory_number": "TEST-FUTURE-001",
            }
        )
        with self.assertRaises(ValidationError):
            self._create_loan(
                copy_id=future_copy.id,
                loan_date=today + timedelta(days=30),
            )

        loan = self._create_loan()
        with self.assertRaises(ValidationError):
            loan.write({"loan_date": today + timedelta(days=30)})

    def test_today_return_date_is_allowed_and_future_return_is_rejected(self):
        today = fields.Date.context_today(self.env["library.loan"])
        loan = self._create_loan(loan_date=today - timedelta(days=1))

        loan.write({"return_date": today})
        self.assertEqual(loan.return_date, today)

        with self.assertRaises(ValidationError):
            loan.write({"return_date": today + timedelta(days=1)})
        with self.assertRaises(ValidationError):
            loan.write({"return_date": today + timedelta(days=30)})

    def test_future_dates_show_onchange_warning_only(self):
        tomorrow = fields.Date.context_today(
            self.env["library.loan"]
        ) + timedelta(days=1)
        loan = self.env["library.loan"].with_context(lang="uk_UA").new(
            {
                "copy_id": self.copy.id,
                "member_id": self.member.id,
                "loan_date": tomorrow,
            }
        )

        result = loan._onchange_dates_not_in_future()

        self.assertEqual(set(result), {"warning"})
        self.assertEqual(result["warning"]["title"], "Некоректна дата")
        self.assertIn("Дата видачі не може бути в майбутньому", result["warning"]["message"])
        self.assertEqual(loan.loan_date, tomorrow)

    def test_future_due_date_remains_valid(self):
        today = fields.Date.context_today(self.env["library.loan"])
        loan = self._create_loan(loan_date=today)

        self.assertEqual(
            loan.due_date,
            today + timedelta(days=LOAN_PERIOD_DAYS),
        )

    def test_changing_loan_date_recomputes_existing_fine(self):
        loan = self._create_loan(
            loan_date=date(2026, 10, 1),
            return_date=date(2026, 10, 18),
        )
        self.assertEqual(loan.fine_amount, 15.0)

        loan.write({"loan_date": date(2026, 10, 5)})

        self.assertEqual(loan.due_date, date(2026, 10, 19))
        self.assertEqual(loan.fine_amount, 0.0)

    def test_return_date_after_due_date_recomputes_fine(self):
        today = fields.Date.context_today(self.env["library.loan"])
        loan = self._create_loan(
            loan_date=today - timedelta(days=LOAN_PERIOD_DAYS + 5)
        )
        loan.write({"return_date": loan.due_date + timedelta(days=3)})

        self.assertEqual(loan.fine_amount, 3 * FINE_PER_DAY)

    def test_return_by_due_date_has_no_fine(self):
        today = fields.Date.context_today(self.env["library.loan"])
        loan = self._create_loan(
            loan_date=today - timedelta(days=LOAN_PERIOD_DAYS)
        )
        loan.write({"return_date": today})

        self.assertEqual(loan.fine_amount, 0.0)

    def test_fine_amount_is_searchable(self):
        past_loan_date = fields.Date.context_today(
            self.env["library.loan"]
        ) - timedelta(days=LOAN_PERIOD_DAYS + 5)
        loan = self._create_loan(loan_date=past_loan_date)
        loan.write({"return_date": loan.due_date + timedelta(days=2)})
        other_copy = self.env["library.copy"].create(
            {
                "book_id": self.book.id,
                "inventory_number": "TEST-FINE-002",
            }
        )
        lower_fine_loan = self._create_loan(
            copy_id=other_copy.id,
            loan_date=past_loan_date,
        )
        lower_fine_loan.write(
            {"return_date": lower_fine_loan.due_date + timedelta(days=1)}
        )

        matching_loans = self.env["library.loan"].search(
            [
                ("id", "in", [loan.id, lower_fine_loan.id]),
                ("fine_amount", ">", 0),
            ],
            order="fine_amount desc",
        )

        self.assertEqual(matching_loans[:2].ids, [loan.id, lower_fine_loan.id])

    def test_second_active_loan_for_copy_is_rejected(self):
        self._create_loan()

        with self.assertRaises(ValidationError):
            self._create_loan()

    def test_second_loan_for_overdue_copy_is_rejected(self):
        old_loan_date = fields.Date.context_today(
            self.env["library.loan"]
        ) - timedelta(days=LOAN_PERIOD_DAYS + 1)
        overdue_loan = self._create_loan(loan_date=old_loan_date)
        self.assertEqual(overdue_loan.state, "active")
        self.assertEqual(overdue_loan.display_status, "overdue")

        with self.assertRaises(ValidationError):
            self._create_loan()

    def test_first_active_loan_is_saved_without_false_positive(self):
        loan = self._create_loan()
        loan.write({"state": "active"})

        self.assertTrue(loan.exists())
        self.assertEqual(loan.state, "active")

    def test_copy_onchange_only_returns_warning(self):
        self._create_loan()
        new_loan = self.env["library.loan"].with_context(lang="uk_UA").new(
            {
                "copy_id": self.copy.id,
                "member_id": self.member.id,
            }
        )

        result = new_loan._onchange_copy_id()

        self.assertIn("warning", result)
        self.assertEqual(set(result), {"warning"})
        self.assertEqual(result["warning"]["title"], "Увага!")
        self.assertEqual(
            result["warning"]["message"],
            "Цей примірник уже видано іншому читачеві.",
        )

    def test_return_date_before_loan_date_is_rejected(self):
        loan_date = fields.Date.today()

        with self.assertRaises(ValidationError):
            self._create_loan(
                loan_date=loan_date,
                return_date=loan_date - timedelta(days=1),
            )

    def test_is_overdue_for_unreturned_past_due_or_late_return(self):
        past_date = fields.Date.today() - timedelta(days=LOAN_PERIOD_DAYS + 1)
        active_loan = self._create_loan(loan_date=past_date)
        active_current_loan = self._create_loan(
            copy_id=self.env["library.copy"].create(
                {
                    "book_id": self.book.id,
                    "inventory_number": "TEST-002",
                }
            ).id,
        )
        returned_loan = self._create_loan(
            copy_id=self.env["library.copy"].create(
                {
                    "book_id": self.book.id,
                    "inventory_number": "TEST-003",
                }
            ).id,
            loan_date=past_date,
            return_date=past_date + timedelta(days=LOAN_PERIOD_DAYS),
            state="returned",
        )

        self.assertTrue(active_loan.is_overdue)
        self.assertFalse(active_current_loan.is_overdue)
        self.assertFalse(returned_loan.is_overdue)

    def test_display_status_active_when_not_overdue(self):
        loan = self._create_loan(
            loan_date=fields.Date.today() - timedelta(days=LOAN_PERIOD_DAYS)
        )

        self.assertEqual(loan.state, "active")
        self.assertEqual(loan.display_status, "active")

    def test_display_status_is_overdue_while_state_remains_active(self):
        past_due_date = fields.Date.today() - timedelta(days=1)
        loan = self._create_loan(
            loan_date=past_due_date - timedelta(days=LOAN_PERIOD_DAYS)
        )

        self.assertEqual(loan.state, "active")
        self.assertEqual(loan.display_status, "overdue")
        self.assertTrue(loan.is_overdue)

    def test_display_status_returned_when_returned_by_due_date(self):
        old_loan_date = fields.Date.today() - timedelta(days=LOAN_PERIOD_DAYS)
        returned_loan = self._create_loan(
            loan_date=old_loan_date,
            return_date=fields.Date.today(),
        )

        self.assertEqual(returned_loan.state, "returned")
        self.assertEqual(returned_loan.display_status, "returned")
        self.assertFalse(returned_loan.is_overdue)

    def test_late_return_sets_returned_and_preserves_fine(self):
        today = fields.Date.context_today(self.env["library.loan"])
        loan_date = today - timedelta(days=LOAN_PERIOD_DAYS + 5)
        loan = self._create_loan(loan_date=loan_date)

        loan.write({"return_date": today})

        self.assertEqual(loan.state, "returned")
        self.assertEqual(loan.display_status, "overdue")
        self.assertTrue(loan.is_overdue)
        self.assertEqual(loan.fine_amount, 5 * FINE_PER_DAY)

    def test_fixed_late_return_example_and_automatic_status(self):
        loan = self._create_loan(
            loan_date=date(2026, 10, 5),
        )
        self.assertEqual(loan.due_date, date(2026, 10, 19))
        loan.write({"return_date": date(2026, 10, 20)})

        self.assertEqual(loan.state, "returned")
        self.assertEqual(loan.display_status, "overdue")
        self.assertTrue(loan.is_overdue)
        self.assertEqual(loan.fine_amount, 5.0)

    def test_manually_setting_inconsistent_state_is_rejected(self):
        loan = self._create_loan()

        with self.assertRaises(ValidationError):
            loan.write({"state": "returned"})

    def test_ukrainian_field_labels_are_loaded(self):
        fields_info = self.env["library.loan"].with_context(
            lang="uk_UA"
        ).fields_get(
            [
                "copy_id",
                "member_id",
                "loan_date",
                "due_date",
                "return_date",
                "fine_amount",
                "display_status",
                "state",
            ]
        )

        self.assertEqual(fields_info["copy_id"]["string"], "Примірник")
        self.assertEqual(fields_info["member_id"]["string"], "Читач")
        self.assertEqual(fields_info["loan_date"]["string"], "Дата видачі")
        self.assertEqual(fields_info["due_date"]["string"], "Термін повернення")
        self.assertEqual(
            fields_info["return_date"]["string"],
            "Дата фактичного повернення",
        )
        self.assertEqual(fields_info["fine_amount"]["string"], "Сума штрафу (грн)")
        self.assertEqual(fields_info["display_status"]["string"], "Статус видачі")
        self.assertEqual(
            dict(fields_info["state"]["selection"]),
            {
                "active": "Активна",
                "returned": "Повернена",
            },
        )
        self.assertEqual(
            dict(fields_info["display_status"]["selection"]),
            {
                "active": "Активна",
                "overdue": "Прострочена",
                "returned": "Повернена",
            },
        )
        self.assertEqual(
            self.env.ref("library_rental.menu_library_root").with_context(
                lang="uk_UA"
            ).name,
            "Бібліотечний прокат",
        )
        self.assertEqual(
            self.env.ref("library_rental.action_library_book").with_context(
                lang="uk_UA"
            ).name,
            "Книги",
        )
        self.assertIn(
            "Книги",
            self.env.ref("library_rental.view_library_book_list").with_context(
                lang="uk_UA"
            ).arch,
        )
        self.assertIn(
            "Прострочена",
            self.env.ref("library_rental.view_library_loan_form").with_context(
                lang="uk_UA"
            ).arch,
        )
        for view_xmlid, expected_title in (
            ("view_library_book_list", "Книги"),
            ("view_library_copy_list", "Примірники"),
            ("view_library_member_list", "Читачі"),
            ("view_library_loan_list", "Видачі"),
        ):
            localized_view = self.env.ref(
                f"library_rental.{view_xmlid}"
            ).with_context(lang="uk_UA")
            self.assertIn(expected_title, localized_view.arch)

        localized_loan = self._create_loan().with_context(lang="uk_UA")
        self.assertIn("Видача №", localized_loan.display_name)

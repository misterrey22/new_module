from datetime import date, timedelta

from odoo import api, fields, models
from odoo.exceptions import ValidationError
from odoo.tools import _


LOAN_PERIOD_DAYS = 14
FINE_PER_DAY = 5.0


class LibraryLoan(models.Model):
    _name = "library.loan"
    _description = "Library Loan"

    def _compute_display_name(self):
        for loan in self:
            book_name = loan.copy_id.book_id.name or _("Unknown book")
            loan.display_name = _("Loan #%(loan_id)s - %(book)s") % {
                "loan_id": loan.id if isinstance(loan.id, int) else _("New record"),
                "book": book_name,
            }

    copy_id = fields.Many2one(
        "library.copy",
        required=True,
        ondelete="restrict",
        string="Copy",
    )
    member_id = fields.Many2one(
        "library.member",
        required=True,
        ondelete="restrict",
        string="Member",
    )
    book_author = fields.Char(
        related="copy_id.book_id.author",
        string="Book Author",
    )
    loan_date = fields.Date(string="Loan Date", default=fields.Date.today, required=True)
    due_date = fields.Date(
        string="Due Date",
        compute="_compute_due_date",
        store=True,
    )
    fine_amount = fields.Float(
        string="Fine Amount (UAH)",
        compute="_compute_fine_amount",
        store=True,
    )
    is_overdue = fields.Boolean(
        string="Is Overdue",
        compute="_compute_is_overdue",
        store=False,
    )
    display_status = fields.Selection(
        [
            ("active", "Active"),
            ("overdue", "Overdue"),
            ("returned", "Returned"),
        ],
        string="Loan Status",
        compute="_compute_display_status",
        store=False,
    )
    return_date = fields.Date(string="Return Date")
    state = fields.Selection(
        [
            ("active", "Active"),
            ("returned", "Returned"),
        ],
        string="Status",
        default="active",
        required=True,
        readonly=True,
    )

    @api.depends("loan_date")
    def _compute_due_date(self):
        for loan in self:
            loan.due_date = (
                loan.loan_date + timedelta(days=LOAN_PERIOD_DAYS)
                if isinstance(loan.loan_date, date)
                else False
            )

    @api.depends("return_date", "due_date")
    def _compute_fine_amount(self):
        for loan in self:
            return_date = loan.return_date
            due_date = loan.due_date
            if (
                isinstance(return_date, date)
                and isinstance(due_date, date)
                and return_date > due_date
            ):
                loan.fine_amount = (return_date - due_date).days * FINE_PER_DAY
            else:
                loan.fine_amount = 0.0

    # Non-stored: used for dynamic UI highlighting, not searching or aggregation.
    @api.depends("state", "due_date", "return_date")
    def _compute_is_overdue(self):
        for loan in self:
            today = fields.Date.today()
            loan.is_overdue = bool(
                loan.due_date
                and (
                    (
                        loan.state == "active"
                        and not loan.return_date
                        and loan.due_date < today
                    )
                    or (
                        loan.return_date
                        and loan.return_date > loan.due_date
                    )
                )
            )

    @api.depends("state", "return_date", "due_date")
    def _compute_display_status(self):
        today = fields.Date.today()
        for loan in self:
            if loan.return_date and loan.due_date and loan.return_date > loan.due_date:
                loan.display_status = "overdue"
            elif loan.return_date or loan.state == "returned":
                loan.display_status = "returned"
            elif (
                loan.state == "active"
                and loan.due_date
                and loan.due_date < today
            ):
                loan.display_status = "overdue"
            else:
                loan.display_status = "active"

    @api.onchange("copy_id")
    def _onchange_copy_id(self):
        """This is only a UI hint; the actual protection is the @api.constrains."""
        if not self.copy_id:
            return {}
        # New records have a NewId and are not in the database; persisted edits
        # use _origin.id to exclude the existing row from the search.
        origin_id = self._origin.id
        domain = [
            ("copy_id", "=", self.copy_id.id),
            ("state", "=", "active"),
        ]
        if origin_id:
            domain.append(("id", "!=", origin_id))
        duplicate = self.sudo().search(domain, limit=1)
        if duplicate:
            return {
                "warning": {
                    "title": _("Attention!"),
                    "message": _("This copy is already checked out to another member."),
                }
            }
        return {}

    @api.onchange("loan_date", "return_date")
    def _onchange_dates_not_in_future(self):
        for loan in self:
            today = fields.Date.context_today(loan)
            if isinstance(loan.loan_date, date) and loan.loan_date > today:
                return {
                    "warning": {
                        "title": _("Invalid date"),
                        "message": (
                            _("The loan date cannot be in the future. "
                              "Choose today or an earlier date.")
                        ),
                    }
                }
            if isinstance(loan.return_date, date) and loan.return_date > today:
                return {
                    "warning": {
                        "title": _("Invalid date"),
                        "message": (
                            _("The return date cannot be in the future. "
                              "Choose today or an earlier date.")
                        ),
                    }
                }
        return {}

    def _lock_active_loan_copies(self, copy_ids):
        """Serialize active-loan writes per copy to close the concurrent-create race."""
        copy_ids = sorted(set(copy_ids))
        if copy_ids:
            self.env.cr.execute(
                """
                SELECT id
                FROM library_copy
                WHERE id = ANY(%s)
                ORDER BY id
                FOR UPDATE
                """,
                [copy_ids],
            )

    @api.model_create_multi
    def create(self, vals_list):
        vals_list = [dict(vals) for vals in vals_list]
        for vals in vals_list:
            vals["state"] = "returned" if vals.get("return_date") else "active"
        active_copy_ids = [
            vals["copy_id"]
            for vals in vals_list
            if vals.get("copy_id")
            and vals.get("state", "active") == "active"
        ]
        self._lock_active_loan_copies(active_copy_ids)
        return super().create(vals_list)

    def write(self, vals):
        vals = dict(vals)
        if "state" in vals and not ({"loan_date", "return_date"} & vals.keys()):
            for loan in self:
                expected_state = "returned" if loan.return_date else "active"
                if vals["state"] != expected_state:
                    raise ValidationError(
                        _("The loan status is automatic and cannot be changed manually.")
                    )
        if not ({"loan_date", "return_date", "state"} & vals.keys()):
            active_copy_ids = [
                vals.get("copy_id", loan.copy_id.id)
                for loan in self
                if "copy_id" in vals and loan.state == "active"
            ]
            self._lock_active_loan_copies(active_copy_ids)
            return super().write(vals)

        grouped_loans = {}
        for loan in self:
            return_date = vals.get("return_date", loan.return_date)
            target_state = "returned" if return_date else "active"
            grouped_loans.setdefault(target_state, self.browse())
            grouped_loans[target_state] |= loan

        for target_state, loans in grouped_loans.items():
            write_values = dict(vals, state=target_state)
            target_copy_ids = [
                write_values.get("copy_id", loan.copy_id.id)
                for loan in loans
                if target_state == "active"
            ]
            self._lock_active_loan_copies(target_copy_ids)
            super(LibraryLoan, loans).write(write_values)
        return True

    @api.constrains("copy_id", "state")
    def _check_one_active_loan_per_copy(self):
        for loan in self:
            if loan.state != "active" or not loan.copy_id:
                continue
            duplicate = self.sudo().search(
                [
                    ("copy_id", "=", loan.copy_id.id),
                    ("state", "=", "active"),
                    ("id", "!=", loan.id),
                ],
                limit=1,
            )
            if duplicate:
                raise ValidationError(
                    _("A copy cannot have more than one active or overdue loan.")
                )

    @api.constrains("return_date", "state")
    def _check_returned_loan_state(self):
        for loan in self:
            if loan.return_date and loan.state != "returned":
                raise ValidationError(
                    _("A loan with a return date must have the Returned status.")
                )

    @api.constrains("loan_date", "due_date")
    def _check_due_date_after_loan_date(self):
        # With the current positive term this is normally true by construction,
        # but this guards against a non-positive term if the policy changes.
        for loan in self:
            loan_date = loan.loan_date
            due_date = loan.due_date
            if (
                isinstance(loan_date, date)
                and isinstance(due_date, date)
                and due_date <= loan_date
            ):
                raise ValidationError(
                    _("The due date must be later than the loan date.")
                )

    @api.constrains("loan_date", "return_date")
    def _check_return_date_not_before_loan_date(self):
        for loan in self:
            loan_date = loan.loan_date
            return_date = loan.return_date
            if (
                isinstance(loan_date, date)
                and isinstance(return_date, date)
                and return_date < loan_date
            ):
                raise ValidationError(
                    _("The return date cannot be earlier than the loan date.")
                )

    @api.constrains("loan_date")
    def _check_loan_date_not_in_future(self):
        for loan in self:
            today = fields.Date.context_today(loan)
            if isinstance(loan.loan_date, date) and loan.loan_date > today:
                raise ValidationError(
                    _("The loan date cannot be in the future. "
                      "Choose today or an earlier date.")
                )

    @api.constrains("return_date")
    def _check_return_date_not_in_future(self):
        for loan in self:
            today = fields.Date.context_today(loan)
            if isinstance(loan.return_date, date) and loan.return_date > today:
                raise ValidationError(
                    _("The return date cannot be in the future. "
                      "Choose today or an earlier date.")
                )

    @api.constrains("state", "return_date")
    def _check_status_matches_dates(self):
        for loan in self:
            expected_state = "returned" if loan.return_date else "active"
            if loan.state != expected_state:
                raise ValidationError(
                    _("The status must match the loan dates and return date.")
                )

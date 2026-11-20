from odoo import fields, models
from odoo.exceptions import UserError


class LibraryReturnWizard(models.TransientModel):
    _name = "library.return.wizard"
    _description = "Library Loan Return"

    loan_id = fields.Many2one(
        "library.loan",
        string="Loan",
        required=True,
    )
    condition_on_return = fields.Selection(
        [
            ("new", "New"),
            ("good", "Good"),
            ("damaged", "Damaged"),
        ],
        string="Condition on Return",
        required=True,
    )
    notes = fields.Text(string="Notes")

    def default_get(self, fields_list):
        values = super().default_get(fields_list)
        if self.env.context.get("active_model") == "library.loan":
            active_id = self.env.context.get("active_id")
            if active_id:
                values["loan_id"] = active_id
        return values

    def action_confirm(self):
        self.ensure_one()
        if self.loan_id.state == "returned":
            raise UserError("This loan has already been returned.")

        return_date = fields.Date.today()
        self.loan_id.write({
            "state": "returned",
            "return_date": return_date,
        })
        self.loan_id.copy_id.condition = self.condition_on_return
        return {"type": "ir.actions.act_window_close"}

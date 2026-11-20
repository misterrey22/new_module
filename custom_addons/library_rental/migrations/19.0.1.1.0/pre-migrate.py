def migrate(cr, version):
    cr.execute(
        "UPDATE library_loan SET state = 'active' WHERE state = 'overdue'"
    )
    cr.execute(
        """
        DELETE FROM ir_cron
        WHERE id IN (
            SELECT res_id
            FROM ir_model_data
            WHERE module = %s
              AND name = %s
              AND model = %s
        )
        """,
        ("library_rental", "ir_cron_mark_library_loans_overdue", "ir.cron"),
    )
    cr.execute(
        """
        DELETE FROM ir_model_data
        WHERE module = %s
          AND name = %s
          AND model = %s
        """,
        ("library_rental", "ir_cron_mark_library_loans_overdue", "ir.cron"),
    )

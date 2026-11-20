from odoo import fields, models


class LibraryBook(models.Model):
    _name = "library.book"
    _description = "Library Book"
    _rec_name = "name"

    name = fields.Char(string="Title", required=True)
    author = fields.Char(string="Author")
    isbn = fields.Char(string="ISBN")
    publish_year = fields.Integer(string="Publication Year")
    copy_ids = fields.One2many("library.copy", "book_id", string="Copies")

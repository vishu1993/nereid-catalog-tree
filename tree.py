# -*- coding: utf-8 -*-
'''
    Nereid Catalog Tree

    Products catalogue on a tree

    :copyright: (c) 2013 by Openlabs Technologies & Consulting (P) Ltd.
    :license: GPLv3, see LICENSE for more details

'''

from nereid import abort, render_template, route
from nereid.helpers import slugify
from nereid.contrib.pagination import Pagination

from trytond.model import ModelView, ModelSQL, fields
from trytond.exceptions import UserError
from trytond.pool import Pool, PoolMeta
from trytond.pyson import Eval

__all__ = [
    'Product', 'Node', 'ProductNodeRelationship',
    'Website', 'WebsiteTreeNode'
]
__metaclass__ = PoolMeta


class Product:
    "Product extension for nereid"
    __name__ = 'product.product'

    nodes = fields.Many2Many(
        'product.product-product.tree_node',
        'product', 'node', 'Tree Nodes'
    )


class Node(ModelSQL, ModelView):
    """
    Tree Node
    A tree is a hierachcial way to group products together.
    A vertex or node is the fundamental unit of which graphs/trees are formed
    """
    __name__ = "product.tree_node"

    name = fields.Char('Name', required=True, select=True, translate=True)
    slug = fields.Char(
        'Slug', depends=['name'], on_change_with=['name', 'slug', 'parent'],
        required=True, select=True, translate=True
    )
    type_ = fields.Selection([
        ('catalog', 'Catalog'),
    ], 'Type', required=True, select=True)
    parent = fields.Many2One(
        'product.tree_node', 'Parent', select=True,
        depends=['type_'],
        domain=[('type_', '=', Eval('type_'))],
        left='left', right='right', ondelete="RESTRICT",
    )
    children = fields.One2Many(
        'product.tree_node', 'parent', 'Children',
        depends=['id'], add_remove=[('id', '!=', Eval('id'))],
    )
    left = fields.Integer('Left', select=True)
    right = fields.Integer('Right', select=True)
    products = fields.Many2Many(
        'product.product-product.tree_node',
        'node', 'product', 'Products',
    )
    products_per_page = fields.Integer('Products per Page')

    @classmethod
    def validate(cls, nodes):
        super(Node, cls).validate(nodes)
        cls.check_recursion(nodes, rec_name='name')

    def on_change_with_slug(self):
        """
        On change the name and slug, ensure that the slug field is auto
        filled with a generated slug, if the field is empty
        """
        if not self.slug:
            self.slug = slugify(self.get_rec_name('rec_name'))
        return self.slug

    def get_rec_name(self, name=None):
        if self.parent:
            return self.parent.rec_name + ' / ' + self.name
        return self.name

    @staticmethod
    def default_left():
        return 0

    @staticmethod
    def default_right():
        return 0

    @staticmethod
    def default_products_per_page():
        return 10

    def get_products(self, page=1, per_page=None):
        """
        Return a pagination object of active records of products in the tree
        and all of its branches.

        A pagination object is returned so that the user can implement
        interfaces like infinite scroll which will need advance information of
        the number of pages that will exist.

        It is recommended to use this method instead of directly reading from
        the products (many2many) field for scalability. In addition, if a
        product is made inactive or not displayed on eshop, it will be
        overlooked by the many2many field.

        Example usage::

            {% for product in node.get_products() %}
            <li>{{ product.name }}</li>
            {% endfor %}

        :param page: The page for which the products have to be displayed
        :param per_page: The number of products to be returned in each page
        """
        Product = Pool().get('product.product')

        if per_page is None:
            per_page = self.products_per_page

        products = Pagination(Product, [
            ('displayed_on_eshop', '=', True),
            ('nodes.left', '>=', self.left),
            ('nodes.right', '<=', self.right),
            ('template.active', '=', True),
        ], page=page, per_page=per_page)
        return products

    @route('/nodes/<int:active_id>/<slug>/<int:page>')
    @route('/nodes/<int:active_id>/<slug>')
    def render(self, slug=None, page=1):
        """
        Renders a page of products in the tree and all of its branches

        :param slug: slug of the browse node to be shown
        :param page: page of the products to be displayed
        """
        Product = Pool().get('product.product')

        try:
            self.slug
        except UserError:
            abort(404)

        if self.type_ != 'catalog':
            # Display only catalog nodes
            abort(403)

        products = Pagination(Product, [
            ('displayed_on_eshop', '=', True),
            ('nodes.left', '>=', self.left),
            ('nodes.right', '<=', self.right),
            ('template.active', '=', True),
        ], page=page, per_page=self.products_per_page)

        return render_template(
            'catalog/node.html', products=products, node=self
        )


class ProductNodeRelationship(ModelSQL):
    """
    This is the relation between a node in a tree
    and a product
    """
    __name__ = 'product.product-product.tree_node'

    product = fields.Many2One(
        'product.product', 'Product',
        domain=[
            ('displayed_on_eshop', '=', True),
            ('template.active', '=', True),
        ],
        ondelete='CASCADE', select=True, required=True,
    )
    node = fields.Many2One(
        'product.tree_node', 'Node',
        domain=[('type_', '=', 'catalog')],
        ondelete='CASCADE', select=True, required=True
    )


class Website:
    """
    Extend site to add templates for product listing and
    category listing
    """
    __name__ = 'nereid.website'

    featured_products_node = fields.Many2One(
        'product.tree_node', 'Featured Products Node',
        domain=[('type_', '=', 'catalog')]
    )
    latest_products_node = fields.Many2One(
        'product.tree_node', 'Latest Products Node',
        domain=[('type_', '=', 'catalog')]
    )
    upcoming_products_node = fields.Many2One(
        'product.tree_node', 'Upcoming Products Node',
        domain=[('type_', '=', 'catalog')]
    )
    root_tree_node = fields.Many2One(
        "product.tree_node", 'Root Tree Node', select=True, states={
            "required": Eval('root_navigation_model') == 'product.tree_node',
            "invisible": Eval('root_navigation_model') != 'product.tree_node',
        }
    )

    @classmethod
    def get_root_navigation_model(cls):
        """
        Add catalog tree as a alternative way to manage
        """
        rv = super(Website, cls).get_root_navigation_model()
        item = ('product.tree_node', 'Product Tree Node')
        if item not in rv:
            rv.append(item)
        return rv


class WebsiteTreeNode(ModelSQL):
    "Root Tree Nodes on a Website"
    __name__ = 'nereid.website-product.tree_node'
    _table = 'website_tree_node_rel'

    website = fields.Many2One(
        'nereid.website', 'Website',
        ondelete='CASCADE', select=True, required=True
    )
    node = fields.Many2One(
        'product.tree_node', 'Tree Nodes',
        domain=[('type_', '=', 'catalog')],
        ondelete='CASCADE', select=True, required=True
    )

# -*- coding: utf-8 -*-
"""
test_tree

:copyright: (c) 2013-2015 by Openlabs Technologies & Consulting (P) Limited
:license: BSD, see LICENSE for more details.
"""
from decimal import Decimal
import unittest
from itertools import chain

from lxml import objectify
import trytond.tests.test_tryton
from trytond.tests.test_tryton import POOL, USER, DB_NAME, CONTEXT, \
    test_view, test_depends
from nereid.testing import NereidTestCase
from trytond.transaction import Transaction
from trytond.exceptions import UserError


class TestTree(NereidTestCase):
    """
    Test Tree
    """

    def setup_defaults(self):
        """
        Setup defaults
        """
        Node = POOL.get('product.tree_node')

        usd, = self.Currency.create([{
            'name': 'US Dollar',
            'code': 'USD',
            'symbol': '$',
        }])

        with Transaction().set_context(company=None):
            party1, = self.Party.create([{
                'name': 'Openlabs',
            }])

            company, = self.Company.create([{
                'party': party1.id,
                'currency': usd.id
            }])

            party2, = self.Party.create([{
                'name': 'Guest User'
            }])

        self.category, = self.Category.create([{
            'name': 'CategoryA',
        }])

        en_us, = self.Language.search([('code', '=', 'en_US')])

        self.locale_en_us, = self.Locale.create([{
            'code': 'en_US',
            'language': en_us.id,
            'currency': usd.id
        }])
        self.default_node, = Node.create([{
            'name': 'root',
            'slug': 'root',
        }])

        self.Site.create([{
            'name': 'localhost',
            'company': company.id,
            'application_user': USER,
            'default_locale': self.locale_en_us.id,
            'currencies': [('add', [usd.id])],
        }])

    def setUp(self):
        """
        Set up data used in the tests
        this method is called before each test execution
        """
        trytond.tests.test_tryton.install_module('nereid_catalog_tree')

        self.Currency = POOL.get('currency.currency')
        self.Site = POOL.get('nereid.website')
        self.Product = POOL.get('product.product')
        self.Company = POOL.get('company.company')
        self.NereidUser = POOL.get('nereid.user')
        self.Language = POOL.get('ir.lang')
        self.Party = POOL.get('party.party')
        self.Category = POOL.get('product.category')
        self.Template = POOL.get('product.template')
        self.Uom = POOL.get('product.uom')
        self.Locale = POOL.get('nereid.website.locale')

        self.templates = {
            'catalog/node.html':
            '{{ products.count }}||' +
            '{{ make_tree_crumbs(node=node)|join(", ", attribute="1") }}',
            'product.jinja': "{{ node and node.name or 'no-node' }}",
        }

    def test_0005_test_view(self):
        """
        Test the views
        """
        test_view('nereid_catalog_tree')

    def test_007_test_depends(self):
        """
        The Depends
        """
        test_depends()

    def test_0010_create_product_node_in_tree(self):
        """
        Test if a product can be created which can be
        associated to a node
        """
        Node = POOL.get('product.tree_node')

        with Transaction().start(DB_NAME, USER, context=CONTEXT):
            self.setup_defaults()
            uom, = self.Uom.search([], limit=1)

            values1 = {
                'name': 'Product-1',
                'category': self.category.id,
                'type': 'goods',
                'list_price': Decimal('10'),
                'cost_price': Decimal('5'),
                'default_uom': uom.id,
                'products': [
                    ('create', [{
                        'uri': 'product-1',
                        'displayed_on_eshop': True
                    }])
                ]
            }

            template1, = self.Template.create([values1])

            node1, = Node.create([{
                'name': 'Node1',
                'slug': 'node1',
                'products': [('create', [
                    {'product': product} for product in template1.products
                ])]
            }])

            self.assert_(node1)

            # Check if default tree node type is 'catalog'
            self.assertEqual(node1.type_, 'catalog')
            # Check if node1 is active by default
            self.assertTrue(node1.active)
            # Check if default display is product variant
            self.assertEqual(node1.display, 'product.product')

    def test_0020_create_product_node_with_children(self):
        """
        Test if a product can be created to find
        its children
        """
        Node = POOL.get('product.tree_node')

        with Transaction().start(DB_NAME, USER, context=CONTEXT):
            self.setup_defaults()
            uom, = self.Uom.search([], limit=1)

            values1 = {
                'name': 'Product-1',
                'category': self.category.id,
                'type': 'goods',
                'list_price': Decimal('10'),
                'cost_price': Decimal('5'),
                'default_uom': uom.id,
                'products': [
                    ('create', [{
                        'uri': 'product-1',
                        'displayed_on_eshop': True
                    }])
                ]
            }

            values2 = {
                'name': 'Product-2',
                'category': self.category.id,
                'list_price': Decimal('10'),
                'cost_price': Decimal('5'),
                'default_uom': uom.id,
                'products': [
                    ('create', [{
                        'uri': 'product-2',
                        'displayed_on_eshop': True
                    }])
                ]
            }

            template1, template2 = self.Template.create([values1, values2])

            node1, = Node.create([{
                'name': 'Node1',
                'type_': 'catalog',
                'slug': 'node1',
                'products': [('create', [
                    {'product': product} for product in template1.products
                ])]
            }])

            self.assert_(node1)

            node2, = Node.create([{
                'name': 'Node2',
                'type_': 'catalog',
                'slug': 'node2',
                'products': [('create', [
                    {'product': product} for product in template2.products
                ])]
            }])

            self.assert_(node2)

            Node.write([node2], {
                'parent': node1
            })
            self.assertEqual(node2.parent, node1)
            self.assertTrue(node2 in node1.children)
            self.assertEqual(len(node2.children), 0)

    def test_0030_nereid_render_method(self):
        """
        Test if the url for the active id of the current node
        returns all the children and its branches
        """
        Node = POOL.get('product.tree_node')

        with Transaction().start(DB_NAME, USER, context=CONTEXT):
            self.setup_defaults()
            uom, = self.Uom.search([], limit=1)

            values1 = {
                'name': 'Product-1',
                'category': self.category.id,
                'type': 'goods',
                'list_price': Decimal('10'),
                'cost_price': Decimal('5'),
                'default_uom': uom.id,
                'products': [
                    ('create', [{
                        'uri': 'product-1',
                        'displayed_on_eshop': True
                    }])
                ]
            }

            values2 = {
                'name': 'Product-2',
                'category': self.category.id,
                'list_price': Decimal('10'),
                'cost_price': Decimal('5'),
                'default_uom': uom.id,
                'products': [
                    ('create', [{
                        'uri': 'product-2',
                        'displayed_on_eshop': True
                    }, {
                        'uri': 'product-21',
                        'displayed_on_eshop': True
                    }])
                ]
            }

            values3 = {
                'name': 'Product-3',
                'category': self.category.id,
                'list_price': Decimal('10'),
                'cost_price': Decimal('5'),
                'default_uom': uom.id,
                'products': [
                    ('create', [{
                        'uri': 'product-3',
                        'displayed_on_eshop': False
                    }, {
                        'uri': 'product-3_2',
                        'active': False,
                        'displayed_on_eshop': True,
                    }])
                ]
            }

            template1, template2, template3, = self.Template.create([
                values1, values2, values3
            ])

            node1, = Node.create([{
                'name': 'Node1',
                'type_': 'catalog',
                'slug': 'node1',
                'products': [('create', [
                    {'product': product} for product in template1.products
                ])]
            }])

            self.assert_(node1)

            node2, = Node.create([{
                'name': 'Node2',
                'type_': 'catalog',
                'slug': 'node2',
                'display': 'product.template',
                'products': [('create', [
                    {'product': product} for product in template2.products
                ])]
            }])

            self.assert_(node2)

            node3, = Node.create([{
                'name': 'Node3',
                'type_': 'catalog',
                'slug': 'node3',
            }])

            Node.write([node2], {
                'parent': node1
            })

            Node.write([node3], {
                'parent': node2
            })

            self.assert_(node2)

            app = self.get_app()

            with app.test_client() as c:
                url = 'nodes/{0}/{1}/{2}'.format(
                    node1.id, node1.slug, 1
                )
                rv = c.get(url)
                self.assertEqual(rv.status_code, 200)
                # Test is if there are 3 products.
                # 1 from node1 and 2 from node2
                # Get the node record by searching it, because current one
                # is cached.
                node1, = Node.search([('id', '=', node1.id)])
                self.assertEqual(
                    node1.get_products(per_page=10).all_items(),
                    list(template1.products + template2.products)
                )
                self.assertEqual(rv.data[0], '3')

                url = 'nodes/{0}/{1}/{2}'.format(
                    node2.id, node2.slug, 1
                )
                rv = c.get(url)
                self.assertEqual(rv.status_code, 200)
                # Test if products length is 1 as display of
                # node2 is set to 'product.template'
                node2, = Node.search([('id', '=', node2.id)])
                self.assertEqual(
                    Node(node2.id).get_products().all_items(),
                    [template2]
                )
                self.assertEqual(rv.data[0], '1')

    def test_0035_product_render_method(self):
        """
        Check injection of node into template context on product rendering
        """
        Node = POOL.get('product.tree_node')

        with Transaction().start(DB_NAME, USER, context=CONTEXT):
            self.setup_defaults()
            uom, = self.Uom.search([], limit=1)

            values1 = {
                'name': 'Product-1',
                'category': self.category.id,
                'type': 'goods',
                'list_price': Decimal('10'),
                'cost_price': Decimal('5'),
                'default_uom': uom.id,
                'products': [
                    ('create', [{
                        'uri': 'product-1',
                        'displayed_on_eshop': True
                    }])
                ]
            }

            template1, = self.Template.create([values1])

            node1, = Node.create([{
                'name': 'Node1',
                'type_': 'catalog',
                'slug': 'node1',
                'products': [('create', [
                    {'product': product} for product in template1.products
                ])]
            }])

            self.assert_(node1)

            app = self.get_app()

            with app.test_client() as c:
                url = '/product/%s' % product.uri

                # With no node argument
                rv = c.get('%s' % url)
                self.assertEqual(rv.status_code, 200)
                self.assertEqual(rv.data, 'no-node')

                # With one valid node
                rv = c.get('%s?node=%d' % (url, node1))
                self.assertEqual(rv.status_code, 200)
                self.assertEqual(rv.data, node1.name)

                # With one invalid node
                rv = c.get('%s?node=999999' % url)
                self.assertEqual(rv.status_code, 200)
                self.assertEqual(rv.data, 'no-node')

                # With one invalid node
                rv = c.get('%s?node=sometext' % url)
                self.assertEqual(rv.status_code, 200)
                self.assertEqual(rv.data, 'no-node')

    def test_0040_create_product_with_parent_as_itself(self):
        """
        This test creates a node and sets the product as
        the parent of itself, which shouldn't happen
        """
        Node = POOL.get('product.tree_node')

        with Transaction().start(DB_NAME, USER, context=CONTEXT):
            self.setup_defaults()
            uom, = self.Uom.search([], limit=1)

            values1 = {
                'name': 'Product-1',
                'category': self.category.id,
                'type': 'goods',
                'list_price': Decimal('10'),
                'cost_price': Decimal('5'),
                'default_uom': uom.id,
                'products': [
                    ('create', [{
                        'uri': 'product-1',
                        'displayed_on_eshop': True
                    }])
                ]
            }

            template1, = self.Template.create([values1])

            node1, = Node.create([{
                'name': 'Node1',
                'type_': 'catalog',
                'slug': 'node1',
                'products': [('create', [
                    {'product': product} for product in template1.products
                ])]
            }])

            self.assert_(node1)
            self.assertRaises(UserError, Node.write, [node1], {
                'parent': node1
            })

    def test_0050_product_template_disabled(self):
        """
        Ensure that the products are not listed when the template is
        disabled
        """
        Node = POOL.get('product.tree_node')

        with Transaction().start(DB_NAME, USER, context=CONTEXT):
            self.setup_defaults()
            uom, = self.Uom.search([], limit=1)

            values1 = {
                'name': 'Product-1',
                'category': self.category.id,
                'type': 'goods',
                'list_price': Decimal('10'),
                'cost_price': Decimal('5'),
                'default_uom': uom.id,
                'products': [
                    ('create', [{
                        'uri': 'product-1',
                        'displayed_on_eshop': True
                    }])
                ]
            }

            template1, = self.Template.create([values1])

            node1, = Node.create([{
                'name': 'Node1',
                'type_': 'catalog',
                'slug': 'node1',
                'products': [('create', [
                    {'product': product} for product in template1.products
                ])]
            }])

            app = self.get_app()

            with app.test_client() as c:
                rv = c.get('nodes/%d/_/1' % node1.id)
                self.assertEqual(rv.status_code, 200)
                self.assertEqual(rv.data[0], '1')

            node1, = Node.search([('id', '=', node1.id)])
            self.assertEqual(node1.get_products().count, 1)
            self.assertEqual(len(node1.products), 1)

            template1.active = False
            template1.save()

            with app.test_client() as c:
                rv = c.get('nodes/%d/_/1' % node1.id)
                self.assertEqual(rv.status_code, 200)
                self.assertEqual(rv.data[0], '0')

            node1, = Node.search([('id', '=', node1.id)])
            self.assertEqual(node1.get_products().count, 0)
            self.assertEqual(len(node1.products), 1)

    def test_0060_make_tree_crumbs(self):
        """
        Test to get breadcrumbs on node template
        """
        Node = POOL.get('product.tree_node')

        with Transaction().start(DB_NAME, USER, context=CONTEXT):
            self.setup_defaults()
            app = self.get_app()

            parent_node, = Node.create([{
                'name': 'Node1',
                'type_': 'catalog',
                'slug': 'node1',
                'parent': self.default_node,
            }])

            child_node, = Node.create([{
                'name': 'Node2',
                'type_': 'catalog',
                'slug': 'node2',
                'parent': parent_node,
            }])

            with app.test_client() as c:
                rv = c.get('nodes/%d/node2' % child_node.id)
                self.assertEqual(
                    rv.data[3:], "Home, root, Node1, Node2"
                )

    def test_0070_tree_sitemap_index(self):
        """
        Assert that the sitemap index returns 1 result
        """
        Node = POOL.get('product.tree_node')

        with Transaction().start(DB_NAME, USER, context=CONTEXT):
            self.setup_defaults()
            uom, = self.Uom.search([], limit=1)
            app = self.get_app()

            values1 = {
                'name': 'Product-1',
                'category': self.category.id,
                'type': 'goods',
                'list_price': Decimal('10'),
                'cost_price': Decimal('5'),
                'default_uom': uom.id,
                'products': [
                    ('create', [{
                        'uri': 'product-1',
                        'displayed_on_eshop': True
                    }])
                ]
            }

            values2 = {
                'name': 'Product-2',
                'category': self.category.id,
                'list_price': Decimal('10'),
                'cost_price': Decimal('5'),
                'default_uom': uom.id,
                'products': [
                    ('create', [{
                        'uri': 'product-2',
                        'displayed_on_eshop': True
                    }])
                ]
            }

            template1, template2 = self.Template.create([values1, values2])

            node1, = Node.create([{
                'name': 'Node1',
                'type_': 'catalog',
                'slug': 'node1',
                'products': [('create', [
                    {'product': product}
                    for product in template1.products + template2.products
                ])]
            }])

            self.assert_(node1)

            with app.test_client() as c:
                rv = c.get('/sitemaps/tree-index.xml')
                xml = objectify.fromstring(rv.data)
                self.assertTrue(xml.tag.endswith('sitemapindex'))
                self.assertEqual(len(xml.getchildren()), 1)

                rv = c.get(
                    xml.sitemap.loc.pyval.split('localhost/', 1)[-1]
                )
                xml = objectify.fromstring(rv.data)
                self.assertTrue(xml.tag.endswith('urlset'))
                self.assertEqual(len(xml.getchildren()), 2)

    def test_0080_node_menu_items(self):
        """
        Test to return record of tree node
        """
        Node = POOL.get('product.tree_node')

        with Transaction().start(DB_NAME, USER, context=CONTEXT):
            self.setup_defaults()
            app = self.get_app()

            node, = Node.create([{
                'name': 'Node1',
                'type_': 'catalog',
                'slug': 'node1',
                'parent': self.default_node,
            }])

            with app.test_request_context('/'):
                rv = node.get_menu_item(max_depth=10)

            self.assertEqual(rv['title'], u'Node1')

    def test_0090_product_sequence(self):
        """
        Ensure that the products are displayed according to the sequence
        """
        Node = POOL.get('product.tree_node')

        with Transaction().start(DB_NAME, USER, context=CONTEXT):
            self.setup_defaults()
            uom, = self.Uom.search([], limit=1)

            template1, = self.Template.create([{
                'name': 'Product-1',
                'category': self.category.id,
                'type': 'goods',
                'list_price': Decimal('10'),
                'cost_price': Decimal('5'),
                'default_uom': uom.id,
                'products': [
                    ('create', [
                        {
                            'uri': 'product-1',
                            'displayed_on_eshop': True
                        },
                        {
                            'uri': 'product-2',
                            'displayed_on_eshop': True
                        },
                        {
                            'uri': 'product-3',
                            'displayed_on_eshop': True
                        },
                        {
                            'uri': 'product-4',
                            'displayed_on_eshop': True
                        },
                        {
                            'uri': 'product-5',
                            'displayed_on_eshop': True
                        },
                    ])
                ]
            }])

            prod1, prod2, prod3, prod4, prod5 = template1.products

            node1, node2 = Node.create([{
                'name': 'Node 1',
                'type_': 'catalog',
                'slug': 'node1',
                'products': [('create', [
                    {'product': prod4, 'sequence': 10},
                    {'product': prod1, 'sequence': 20},
                ])]
            }, {
                'name': 'Node 2',
                'type_': 'catalog',
                'slug': 'node2',
                'products': [('create', [
                    {'product': prod3, 'sequence': 10},
                    {'product': prod2, 'sequence': 20},
                    {'product': prod1, 'sequence': 5},
                ])]
            }])

            self.assert_(node1)
            self.assert_(node2)

            node1, = Node.search([('id', '=', node1.id)])
            node2, = Node.search([('id', '=', node2.id)])

            self.assertEqual(
                node1.get_products().items(),
                [prod4, prod1]
            )
            self.assertEqual(
                node2.get_products().items(),
                [prod1, prod3, prod2]
            )

    def test_0100_product_distinct(self):
        """
        Ensure that template pagination really works
        """
        Node = POOL.get('product.tree_node')

        with Transaction().start(DB_NAME, USER, context=CONTEXT):
            self.setup_defaults()
            uom, = self.Uom.search([], limit=1)

            templates = self.Template.create([{
                'name': 'Product-%s' % x,
                'category': self.category.id,
                'type': 'goods',
                'list_price': Decimal('10'),
                'cost_price': Decimal('5'),
                'default_uom': uom.id,
                'products': [
                    ('create', [
                        {
                            'uri': 'product-%s-%s' % (x, v),
                            'displayed_on_eshop': True
                        } for v in xrange(0, 10)
                    ])
                ]
            } for x in xrange(0, 10)])

            node1, = Node.create([{
                'name': 'Node 1',
                'type_': 'catalog',
                'slug': 'node1',
                'display': 'product.product',
                'products': [
                    ('create', [
                        {'product': prod.id, 'sequence': 10}
                        for prod in chain(*[t.products for t in templates])
                    ]
                    )
                ]
            }])

            self.assert_(node1)

            node1, = Node.search([('id', '=', node1.id)])

            self.assertEqual(len(node1.get_products().all_items()), 100)
            self.assertEqual(node1.get_products().count, 100)
            self.assertEqual(len(node1.get_products().items()), 10)
            self.assertEqual(len(node1.get_products(page=10).items()), 10)

            node1.display = 'product.template'
            node1.save()

            self.assertEqual(len(node1.get_products().all_items()), 10)
            self.assertEqual(len(node1.get_products().items()), 10)


def suite():
    "Node test suite"
    test_suite = unittest.TestSuite()
    test_suite.addTests(
        unittest.TestLoader().loadTestsFromTestCase(TestTree)
    )
    return test_suite


if __name__ == '__main__':
    unittest.TextTestRunner(verbosity=2).run(suite())

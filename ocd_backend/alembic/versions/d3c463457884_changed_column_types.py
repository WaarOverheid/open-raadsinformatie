"""changed column types

Revision ID: d3c463457884
Revises: c99750caba39
Create Date: 2019-06-27 12:27:57.269695

"""
from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision = 'd3c463457884'
down_revision = 'c99750caba39'
branch_labels = None
depends_on = None


def upgrade():
    # ### commands auto generated by Alembic - please adjust! ###
    op.add_column('property', sa.Column('prop_float', sa.Float(), nullable=True))
    op.drop_constraint(u'property_prop_resource_fkey', 'property', type_='foreignkey')
    op.drop_column('property', 'prop_text')
    op.drop_column('property', 'prop_resource')
    # ### end Alembic commands ###


def downgrade():
    # ### commands auto generated by Alembic - please adjust! ###
    op.add_column('property', sa.Column('prop_resource', sa.INTEGER(), autoincrement=False, nullable=True))
    op.add_column('property', sa.Column('prop_text', sa.TEXT(), autoincrement=False, nullable=True))
    op.create_foreign_key(u'property_prop_resource_fkey', 'property', 'resource', ['prop_resource'], ['id'])
    op.drop_column('property', 'prop_float')
    # ### end Alembic commands ###

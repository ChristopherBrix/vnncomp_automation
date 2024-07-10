"""Removed obsolete flag

Revision ID: bdc8ea60b5de
Revises: d7a046431109
Create Date: 2024-07-10 17:09:43.318909

"""
from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision = 'bdc8ea60b5de'
down_revision = 'd7a046431109'
branch_labels = None
depends_on = None


def upgrade():
    # ### commands auto generated by Alembic - please adjust! ###
    with op.batch_alter_table('instances', schema=None) as batch_op:
        batch_op.drop_column('_db_disabled')

    # ### end Alembic commands ###


def downgrade():
    # ### commands auto generated by Alembic - please adjust! ###
    with op.batch_alter_table('instances', schema=None) as batch_op:
        batch_op.add_column(sa.Column('_db_disabled', sa.BOOLEAN(), nullable=True))

    # ### end Alembic commands ###

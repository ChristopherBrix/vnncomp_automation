"""Safe eni per task

Revision ID: f9555f1eaf96
Revises: 292e90b0cc7d
Create Date: 2024-07-09 14:48:02.543068

"""
from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision = 'f9555f1eaf96'
down_revision = '292e90b0cc7d'
branch_labels = None
depends_on = None


def upgrade():
    # ### commands auto generated by Alembic - please adjust! ###
    with op.batch_alter_table('toolkit_tasks', schema=None) as batch_op:
        batch_op.add_column(sa.Column('_db_eni', sa.String(), nullable=True))

    # ### end Alembic commands ###


def downgrade():
    # ### commands auto generated by Alembic - please adjust! ###
    with op.batch_alter_table('toolkit_tasks', schema=None) as batch_op:
        batch_op.drop_column('_db_eni')

    # ### end Alembic commands ###

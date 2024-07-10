"""Allow pause after postinstallation script

Revision ID: d7a046431109
Revises: f9555f1eaf96
Create Date: 2024-07-10 14:09:03.003004

"""
from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision = 'd7a046431109'
down_revision = 'f9555f1eaf96'
branch_labels = None
depends_on = None


def upgrade():
    # ### commands auto generated by Alembic - please adjust! ###
    with op.batch_alter_table('toolkit_tasks', schema=None) as batch_op:
        batch_op.add_column(sa.Column('_db_pause_after_postinstallation', sa.Boolean(), nullable=True))

    # ### end Alembic commands ###


def downgrade():
    # ### commands auto generated by Alembic - please adjust! ###
    with op.batch_alter_table('toolkit_tasks', schema=None) as batch_op:
        batch_op.drop_column('_db_pause_after_postinstallation')

    # ### end Alembic commands ###

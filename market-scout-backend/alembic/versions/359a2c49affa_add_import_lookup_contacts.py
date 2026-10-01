from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


revision: str = '359a2c49affa'
down_revision: Union[str, Sequence[str], None] = 'e683f19c0df3'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    with op.batch_alter_table('imports', schema=None) as batch_op:
        batch_op.add_column(sa.Column('lookup_contacts', sa.Boolean(), server_default=sa.text('0'), nullable=False))


def downgrade() -> None:
    with op.batch_alter_table('imports', schema=None) as batch_op:
        batch_op.drop_column('lookup_contacts')


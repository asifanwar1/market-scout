from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


revision: str = '26131fec10e6'
down_revision: Union[str, Sequence[str], None] = '3d33b1b972ab'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.create_table('app_settings',
    sa.Column('key', sa.String(), nullable=False),
    sa.Column('value', sa.JSON(), nullable=False),
    sa.Column('updated_at', sa.DateTime(timezone=True), server_default=sa.text('(CURRENT_TIMESTAMP)'), nullable=True),
    sa.PrimaryKeyConstraint('key')
    )


def downgrade() -> None:
    op.drop_table('app_settings')

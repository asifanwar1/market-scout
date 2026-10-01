from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


revision: str = '5eb57503b6fe'
down_revision: Union[str, Sequence[str], None] = '26131fec10e6'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.create_table('business_snapshots',
    sa.Column('id', sa.Integer(), nullable=False),
    sa.Column('business_id', sa.Integer(), nullable=False),
    sa.Column('run_id', sa.Integer(), nullable=True),
    sa.Column('seen_at', sa.DateTime(timezone=True), nullable=False),
    sa.Column('rating', sa.Float(), nullable=True),
    sa.Column('review_count', sa.Integer(), nullable=True),
    sa.ForeignKeyConstraint(['business_id'], ['businesses.id'], ondelete='CASCADE'),
    sa.ForeignKeyConstraint(['run_id'], ['runs.id'], ondelete='SET NULL'),
    sa.PrimaryKeyConstraint('id'),
    sa.UniqueConstraint('business_id', 'run_id', name='uq_business_snapshots_business_run')
    )
    with op.batch_alter_table('business_snapshots', schema=None) as batch_op:
        batch_op.create_index(batch_op.f('ix_business_snapshots_business_id'), ['business_id'], unique=False)
        batch_op.create_index(batch_op.f('ix_business_snapshots_id'), ['id'], unique=False)
        batch_op.create_index(batch_op.f('ix_business_snapshots_run_id'), ['run_id'], unique=False)
        batch_op.create_index(batch_op.f('ix_business_snapshots_seen_at'), ['seen_at'], unique=False)


def downgrade() -> None:
    with op.batch_alter_table('business_snapshots', schema=None) as batch_op:
        batch_op.drop_index(batch_op.f('ix_business_snapshots_seen_at'))
        batch_op.drop_index(batch_op.f('ix_business_snapshots_run_id'))
        batch_op.drop_index(batch_op.f('ix_business_snapshots_id'))
        batch_op.drop_index(batch_op.f('ix_business_snapshots_business_id'))

    op.drop_table('business_snapshots')

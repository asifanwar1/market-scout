from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa
revision: str = '0eef66d854ef'
down_revision: Union[str, Sequence[str], None] = '4d2efea36ebe'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None

def upgrade() -> None:
    op.create_table('alerts',
    sa.Column('id', sa.Integer(), nullable=False),
    sa.Column('kind', sa.String(), nullable=False),
    sa.Column('business_id', sa.Integer(), nullable=False),
    sa.Column('profile_id', sa.Integer(), nullable=True),
    sa.Column('run_id', sa.Integer(), nullable=True),
    sa.Column('user_id', sa.Integer(), nullable=True),
    sa.Column('dedupe_key', sa.String(), nullable=False),
    sa.Column('message', sa.Text(), nullable=False),
    sa.Column('detail', sa.JSON(), nullable=False),
    sa.Column('created_at', sa.DateTime(timezone=True), server_default=sa.text('(CURRENT_TIMESTAMP)'), nullable=False),
    sa.ForeignKeyConstraint(['business_id'], ['businesses.id'], ondelete='CASCADE'),
    sa.ForeignKeyConstraint(['profile_id'], ['profiles.id'], ondelete='SET NULL'),
    sa.ForeignKeyConstraint(['run_id'], ['runs.id'], ondelete='SET NULL'),
    sa.ForeignKeyConstraint(['user_id'], ['users.id'], ondelete='CASCADE'),
    sa.PrimaryKeyConstraint('id'),
    sa.UniqueConstraint('kind', 'business_id', 'dedupe_key', name='uq_alerts_kind_business_key')
    )
    with op.batch_alter_table('alerts', schema=None) as batch_op:
        batch_op.create_index(batch_op.f('ix_alerts_business_id'), ['business_id'], unique=False)
        batch_op.create_index(batch_op.f('ix_alerts_created_at'), ['created_at'], unique=False)
        batch_op.create_index(batch_op.f('ix_alerts_id'), ['id'], unique=False)
        batch_op.create_index(batch_op.f('ix_alerts_kind'), ['kind'], unique=False)
        batch_op.create_index(batch_op.f('ix_alerts_user_id'), ['user_id'], unique=False)

    op.create_table('alert_reads',
    sa.Column('alert_id', sa.Integer(), nullable=False),
    sa.Column('user_id', sa.Integer(), nullable=False),
    sa.Column('read_at', sa.DateTime(timezone=True), server_default=sa.text('(CURRENT_TIMESTAMP)'), nullable=False),
    sa.ForeignKeyConstraint(['alert_id'], ['alerts.id'], ondelete='CASCADE'),
    sa.ForeignKeyConstraint(['user_id'], ['users.id'], ondelete='CASCADE'),
    sa.PrimaryKeyConstraint('alert_id', 'user_id')
    )

def downgrade() -> None:
    op.drop_table('alert_reads')
    with op.batch_alter_table('alerts', schema=None) as batch_op:
        batch_op.drop_index(batch_op.f('ix_alerts_user_id'))
        batch_op.drop_index(batch_op.f('ix_alerts_kind'))
        batch_op.drop_index(batch_op.f('ix_alerts_id'))
        batch_op.drop_index(batch_op.f('ix_alerts_created_at'))
        batch_op.drop_index(batch_op.f('ix_alerts_business_id'))

    op.drop_table('alerts')

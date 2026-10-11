from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa

revision: str = 'bd2e941b01dd'
down_revision: Union[str, Sequence[str], None] = '66cfb9d3b7c1'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None

def upgrade() -> None:
    op.create_table('api_keys',
    sa.Column('id', sa.Integer(), nullable=False),
    sa.Column('name', sa.String(), nullable=False),
    sa.Column('prefix', sa.String(), nullable=False),
    sa.Column('key_hash', sa.String(), nullable=False),
    sa.Column('can_write', sa.Boolean(), nullable=False),
    sa.Column('created_by_id', sa.Integer(), nullable=True),
    sa.Column('created_at', sa.DateTime(timezone=True), server_default=sa.text('(CURRENT_TIMESTAMP)'), nullable=False),
    sa.Column('last_used_at', sa.DateTime(timezone=True), nullable=True),
    sa.Column('revoked_at', sa.DateTime(timezone=True), nullable=True),
    sa.ForeignKeyConstraint(['created_by_id'], ['users.id'], ondelete='SET NULL'),
    sa.PrimaryKeyConstraint('id'),
    sa.UniqueConstraint('key_hash')
    )
    with op.batch_alter_table('api_keys', schema=None) as batch_op:
        batch_op.create_index(batch_op.f('ix_api_keys_id'), ['id'], unique=False)

    op.create_table('webhooks',
    sa.Column('id', sa.Integer(), nullable=False),
    sa.Column('name', sa.String(), nullable=False),
    sa.Column('url', sa.String(), nullable=False),
    sa.Column('secret', sa.String(), nullable=False),
    sa.Column('events', sa.JSON(), nullable=False),
    sa.Column('is_active', sa.Boolean(), nullable=False),
    sa.Column('consecutive_failures', sa.Integer(), nullable=False),
    sa.Column('last_delivery_at', sa.DateTime(timezone=True), nullable=True),
    sa.Column('last_status_code', sa.Integer(), nullable=True),
    sa.Column('last_error', sa.String(), nullable=True),
    sa.Column('created_by_id', sa.Integer(), nullable=True),
    sa.Column('created_at', sa.DateTime(timezone=True), server_default=sa.text('(CURRENT_TIMESTAMP)'), nullable=False),
    sa.Column('updated_at', sa.DateTime(timezone=True), nullable=True),
    sa.ForeignKeyConstraint(['created_by_id'], ['users.id'], ondelete='SET NULL'),
    sa.PrimaryKeyConstraint('id')
    )
    with op.batch_alter_table('webhooks', schema=None) as batch_op:
        batch_op.create_index(batch_op.f('ix_webhooks_id'), ['id'], unique=False)

    op.create_table('webhook_deliveries',
    sa.Column('id', sa.Integer(), nullable=False),
    sa.Column('webhook_id', sa.Integer(), nullable=False),
    sa.Column('event', sa.String(), nullable=False),
    sa.Column('payload', sa.JSON(), nullable=False),
    sa.Column('status', sa.String(), nullable=False),
    sa.Column('attempts', sa.Integer(), nullable=False),
    sa.Column('next_attempt_at', sa.DateTime(timezone=True), nullable=False),
    sa.Column('response_status', sa.Integer(), nullable=True),
    sa.Column('error', sa.Text(), nullable=True),
    sa.Column('created_at', sa.DateTime(timezone=True), server_default=sa.text('(CURRENT_TIMESTAMP)'), nullable=False),
    sa.Column('delivered_at', sa.DateTime(timezone=True), nullable=True),
    sa.ForeignKeyConstraint(['webhook_id'], ['webhooks.id'], ondelete='CASCADE'),
    sa.PrimaryKeyConstraint('id')
    )
    with op.batch_alter_table('webhook_deliveries', schema=None) as batch_op:
        batch_op.create_index('ix_webhook_deliveries_due', ['status', 'next_attempt_at'], unique=False)
        batch_op.create_index('ix_webhook_deliveries_hook_created', ['webhook_id', 'created_at'], unique=False)
        batch_op.create_index(batch_op.f('ix_webhook_deliveries_id'), ['id'], unique=False)

def downgrade() -> None:
    with op.batch_alter_table('webhook_deliveries', schema=None) as batch_op:
        batch_op.drop_index(batch_op.f('ix_webhook_deliveries_id'))
        batch_op.drop_index('ix_webhook_deliveries_hook_created')
        batch_op.drop_index('ix_webhook_deliveries_due')

    op.drop_table('webhook_deliveries')
    with op.batch_alter_table('webhooks', schema=None) as batch_op:
        batch_op.drop_index(batch_op.f('ix_webhooks_id'))

    op.drop_table('webhooks')
    with op.batch_alter_table('api_keys', schema=None) as batch_op:
        batch_op.drop_index(batch_op.f('ix_api_keys_id'))

    op.drop_table('api_keys')

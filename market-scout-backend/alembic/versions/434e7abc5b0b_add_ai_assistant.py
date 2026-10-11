from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


revision: str = '434e7abc5b0b'
down_revision: Union[str, Sequence[str], None] = '74c70b5a452b'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.create_table('ai_batches',
    sa.Column('id', sa.Integer(), nullable=False),
    sa.Column('profile_id', sa.Integer(), nullable=True),
    sa.Column('created_by_id', sa.Integer(), nullable=True),
    sa.Column('status', sa.String(), nullable=False),
    sa.Column('business_ids', sa.JSON(), nullable=False),
    sa.Column('refresh', sa.Boolean(), nullable=False),
    sa.Column('total', sa.Integer(), nullable=False),
    sa.Column('done', sa.Integer(), nullable=False),
    sa.Column('analyzed', sa.Integer(), nullable=False),
    sa.Column('skipped', sa.Integer(), nullable=False),
    sa.Column('declined', sa.Integer(), nullable=False),
    sa.Column('failed', sa.Integer(), nullable=False),
    sa.Column('spent_usd', sa.Float(), nullable=False),
    sa.Column('error', sa.Text(), nullable=True),
    sa.Column('error_samples', sa.JSON(), nullable=False),
    sa.Column('created_at', sa.DateTime(timezone=True), server_default=sa.text('(CURRENT_TIMESTAMP)'), nullable=False),
    sa.Column('started_at', sa.DateTime(timezone=True), nullable=True),
    sa.Column('finished_at', sa.DateTime(timezone=True), nullable=True),
    sa.ForeignKeyConstraint(['created_by_id'], ['users.id'], ondelete='SET NULL'),
    sa.ForeignKeyConstraint(['profile_id'], ['profiles.id'], ondelete='SET NULL'),
    sa.PrimaryKeyConstraint('id')
    )
    with op.batch_alter_table('ai_batches', schema=None) as batch_op:
        batch_op.create_index(batch_op.f('ix_ai_batches_id'), ['id'], unique=False)
        batch_op.create_index(batch_op.f('ix_ai_batches_status'), ['status'], unique=False)

    op.create_table('ai_usage',
    sa.Column('id', sa.Integer(), nullable=False),
    sa.Column('business_id', sa.Integer(), nullable=True),
    sa.Column('model', sa.String(), nullable=False),
    sa.Column('input_tokens', sa.Integer(), nullable=False),
    sa.Column('output_tokens', sa.Integer(), nullable=False),
    sa.Column('cost_usd', sa.Float(), nullable=False),
    sa.Column('status', sa.String(), nullable=False),
    sa.Column('created_at', sa.DateTime(timezone=True), server_default=sa.text('(CURRENT_TIMESTAMP)'), nullable=False),
    sa.ForeignKeyConstraint(['business_id'], ['businesses.id'], ondelete='SET NULL'),
    sa.PrimaryKeyConstraint('id')
    )
    with op.batch_alter_table('ai_usage', schema=None) as batch_op:
        batch_op.create_index(batch_op.f('ix_ai_usage_created_at'), ['created_at'], unique=False)
        batch_op.create_index(batch_op.f('ix_ai_usage_id'), ['id'], unique=False)

    op.create_table('lead_ai_results',
    sa.Column('id', sa.Integer(), nullable=False),
    sa.Column('business_id', sa.Integer(), nullable=False),
    sa.Column('profile_id', sa.Integer(), nullable=False),
    sa.Column('status', sa.String(), nullable=False),
    sa.Column('summary', sa.Text(), nullable=True),
    sa.Column('segment_slug', sa.String(), nullable=True),
    sa.Column('segment_reason', sa.Text(), nullable=True),
    sa.Column('fit_score', sa.Integer(), nullable=True),
    sa.Column('fit_reason', sa.Text(), nullable=True),
    sa.Column('confidence', sa.String(), nullable=True),
    sa.Column('model', sa.String(), nullable=True),
    sa.Column('pages_read', sa.Integer(), nullable=False),
    sa.Column('truncated', sa.Boolean(), nullable=False),
    sa.Column('error', sa.Text(), nullable=True),
    sa.Column('analyzed_at', sa.DateTime(timezone=True), nullable=False),
    sa.Column('analyzed_by_id', sa.Integer(), nullable=True),
    sa.ForeignKeyConstraint(['analyzed_by_id'], ['users.id'], ondelete='SET NULL'),
    sa.ForeignKeyConstraint(['business_id'], ['businesses.id'], ondelete='CASCADE'),
    sa.ForeignKeyConstraint(['profile_id'], ['profiles.id'], ondelete='CASCADE'),
    sa.PrimaryKeyConstraint('id'),
    sa.UniqueConstraint('business_id', 'profile_id', name='uq_lead_ai_results_business_profile')
    )
    with op.batch_alter_table('lead_ai_results', schema=None) as batch_op:
        batch_op.create_index(batch_op.f('ix_lead_ai_results_business_id'), ['business_id'], unique=False)
        batch_op.create_index(batch_op.f('ix_lead_ai_results_fit_score'), ['fit_score'], unique=False)
        batch_op.create_index(batch_op.f('ix_lead_ai_results_id'), ['id'], unique=False)
        batch_op.create_index(batch_op.f('ix_lead_ai_results_profile_id'), ['profile_id'], unique=False)

    with op.batch_alter_table('profiles', schema=None) as batch_op:
        batch_op.add_column(sa.Column('ideal_customer', sa.Text(), nullable=True))


def downgrade() -> None:
    with op.batch_alter_table('profiles', schema=None) as batch_op:
        batch_op.drop_column('ideal_customer')

    with op.batch_alter_table('lead_ai_results', schema=None) as batch_op:
        batch_op.drop_index(batch_op.f('ix_lead_ai_results_profile_id'))
        batch_op.drop_index(batch_op.f('ix_lead_ai_results_id'))
        batch_op.drop_index(batch_op.f('ix_lead_ai_results_fit_score'))
        batch_op.drop_index(batch_op.f('ix_lead_ai_results_business_id'))

    op.drop_table('lead_ai_results')
    with op.batch_alter_table('ai_usage', schema=None) as batch_op:
        batch_op.drop_index(batch_op.f('ix_ai_usage_id'))
        batch_op.drop_index(batch_op.f('ix_ai_usage_created_at'))

    op.drop_table('ai_usage')
    with op.batch_alter_table('ai_batches', schema=None) as batch_op:
        batch_op.drop_index(batch_op.f('ix_ai_batches_status'))
        batch_op.drop_index(batch_op.f('ix_ai_batches_id'))

    op.drop_table('ai_batches')

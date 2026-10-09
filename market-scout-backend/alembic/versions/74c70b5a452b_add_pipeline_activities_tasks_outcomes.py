from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


revision: str = '74c70b5a452b'
down_revision: Union[str, Sequence[str], None] = '359a2c49affa'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.create_table('lead_activities',
    sa.Column('id', sa.Integer(), nullable=False),
    sa.Column('business_id', sa.Integer(), nullable=False),
    sa.Column('kind', sa.String(), nullable=False),
    sa.Column('summary', sa.Text(), nullable=True),
    sa.Column('from_value', sa.String(), nullable=True),
    sa.Column('to_value', sa.String(), nullable=True),
    sa.Column('created_by_id', sa.Integer(), nullable=True),
    sa.Column('created_at', sa.DateTime(timezone=True), server_default=sa.text('(CURRENT_TIMESTAMP)'), nullable=False),
    sa.ForeignKeyConstraint(['business_id'], ['businesses.id'], ondelete='CASCADE'),
    sa.ForeignKeyConstraint(['created_by_id'], ['users.id'], ondelete='SET NULL'),
    sa.PrimaryKeyConstraint('id')
    )
    with op.batch_alter_table('lead_activities', schema=None) as batch_op:
        batch_op.create_index('ix_lead_activities_business_created', ['business_id', 'created_at'], unique=False)
        batch_op.create_index(batch_op.f('ix_lead_activities_id'), ['id'], unique=False)
        batch_op.create_index(batch_op.f('ix_lead_activities_kind'), ['kind'], unique=False)

    op.create_table('lead_outcomes',
    sa.Column('id', sa.Integer(), nullable=False),
    sa.Column('business_id', sa.Integer(), nullable=False),
    sa.Column('kind', sa.String(), nullable=False),
    sa.Column('value', sa.Float(), nullable=True),
    sa.Column('product', sa.String(), nullable=True),
    sa.Column('loss_reason', sa.String(), nullable=True),
    sa.Column('note', sa.Text(), nullable=True),
    sa.Column('closed_at', sa.DateTime(timezone=True), nullable=False),
    sa.Column('closed_by_id', sa.Integer(), nullable=True),
    sa.ForeignKeyConstraint(['business_id'], ['businesses.id'], ondelete='CASCADE'),
    sa.ForeignKeyConstraint(['closed_by_id'], ['users.id'], ondelete='SET NULL'),
    sa.PrimaryKeyConstraint('id'),
    sa.UniqueConstraint('business_id')
    )
    with op.batch_alter_table('lead_outcomes', schema=None) as batch_op:
        batch_op.create_index(batch_op.f('ix_lead_outcomes_id'), ['id'], unique=False)
        batch_op.create_index(batch_op.f('ix_lead_outcomes_kind'), ['kind'], unique=False)

    op.create_table('lead_tasks',
    sa.Column('id', sa.Integer(), nullable=False),
    sa.Column('business_id', sa.Integer(), nullable=False),
    sa.Column('title', sa.String(), nullable=False),
    sa.Column('due_on', sa.Date(), nullable=False),
    sa.Column('assigned_to_id', sa.Integer(), nullable=True),
    sa.Column('created_by_id', sa.Integer(), nullable=True),
    sa.Column('completed_at', sa.DateTime(timezone=True), nullable=True),
    sa.Column('completed_by_id', sa.Integer(), nullable=True),
    sa.Column('created_at', sa.DateTime(timezone=True), server_default=sa.text('(CURRENT_TIMESTAMP)'), nullable=False),
    sa.ForeignKeyConstraint(['assigned_to_id'], ['users.id'], ondelete='SET NULL'),
    sa.ForeignKeyConstraint(['business_id'], ['businesses.id'], ondelete='CASCADE'),
    sa.ForeignKeyConstraint(['completed_by_id'], ['users.id'], ondelete='SET NULL'),
    sa.ForeignKeyConstraint(['created_by_id'], ['users.id'], ondelete='SET NULL'),
    sa.PrimaryKeyConstraint('id')
    )
    with op.batch_alter_table('lead_tasks', schema=None) as batch_op:
        batch_op.create_index(batch_op.f('ix_lead_tasks_assigned_to_id'), ['assigned_to_id'], unique=False)
        batch_op.create_index(batch_op.f('ix_lead_tasks_business_id'), ['business_id'], unique=False)
        batch_op.create_index(batch_op.f('ix_lead_tasks_id'), ['id'], unique=False)
        batch_op.create_index('ix_lead_tasks_open_due', ['completed_at', 'due_on'], unique=False)


def downgrade() -> None:
    with op.batch_alter_table('lead_tasks', schema=None) as batch_op:
        batch_op.drop_index('ix_lead_tasks_open_due')
        batch_op.drop_index(batch_op.f('ix_lead_tasks_id'))
        batch_op.drop_index(batch_op.f('ix_lead_tasks_business_id'))
        batch_op.drop_index(batch_op.f('ix_lead_tasks_assigned_to_id'))

    op.drop_table('lead_tasks')
    with op.batch_alter_table('lead_outcomes', schema=None) as batch_op:
        batch_op.drop_index(batch_op.f('ix_lead_outcomes_kind'))
        batch_op.drop_index(batch_op.f('ix_lead_outcomes_id'))

    op.drop_table('lead_outcomes')
    with op.batch_alter_table('lead_activities', schema=None) as batch_op:
        batch_op.drop_index(batch_op.f('ix_lead_activities_kind'))
        batch_op.drop_index(batch_op.f('ix_lead_activities_id'))
        batch_op.drop_index('ix_lead_activities_business_created')

    op.drop_table('lead_activities')

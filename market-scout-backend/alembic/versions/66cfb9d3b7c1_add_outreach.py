from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa

revision: str = '66cfb9d3b7c1'
down_revision: Union[str, Sequence[str], None] = 'f39264d003e1'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None

def upgrade() -> None:
    op.create_table('message_templates',
    sa.Column('id', sa.Integer(), nullable=False),
    sa.Column('name', sa.String(), nullable=False),
    sa.Column('channel', sa.String(), nullable=False),
    sa.Column('subject', sa.String(), nullable=True),
    sa.Column('body', sa.Text(), nullable=False),
    sa.Column('created_by_id', sa.Integer(), nullable=True),
    sa.Column('created_at', sa.DateTime(timezone=True), server_default=sa.text('(CURRENT_TIMESTAMP)'), nullable=False),
    sa.Column('updated_at', sa.DateTime(timezone=True), nullable=True),
    sa.ForeignKeyConstraint(['created_by_id'], ['users.id'], ondelete='SET NULL'),
    sa.PrimaryKeyConstraint('id'),
    sa.UniqueConstraint('name')
    )
    with op.batch_alter_table('message_templates', schema=None) as batch_op:
        batch_op.create_index(batch_op.f('ix_message_templates_channel'), ['channel'], unique=False)
        batch_op.create_index(batch_op.f('ix_message_templates_id'), ['id'], unique=False)

    op.create_table('outreach_messages',
    sa.Column('id', sa.Integer(), nullable=False),
    sa.Column('business_id', sa.Integer(), nullable=False),
    sa.Column('template_id', sa.Integer(), nullable=True),
    sa.Column('template_name', sa.String(), nullable=True),
    sa.Column('channel', sa.String(), nullable=False),
    sa.Column('to_value', sa.String(), nullable=False),
    sa.Column('subject', sa.String(), nullable=True),
    sa.Column('body', sa.Text(), nullable=False),
    sa.Column('status', sa.String(), nullable=False),
    sa.Column('created_by_id', sa.Integer(), nullable=True),
    sa.Column('created_at', sa.DateTime(timezone=True), server_default=sa.text('(CURRENT_TIMESTAMP)'), nullable=False),
    sa.Column('decided_at', sa.DateTime(timezone=True), nullable=True),
    sa.ForeignKeyConstraint(['business_id'], ['businesses.id'], ondelete='CASCADE'),
    sa.ForeignKeyConstraint(['created_by_id'], ['users.id'], ondelete='SET NULL'),
    sa.ForeignKeyConstraint(['template_id'], ['message_templates.id'], ondelete='SET NULL'),
    sa.PrimaryKeyConstraint('id')
    )
    with op.batch_alter_table('outreach_messages', schema=None) as batch_op:
        batch_op.create_index('ix_outreach_messages_business_created', ['business_id', 'created_at'], unique=False)
        batch_op.create_index(batch_op.f('ix_outreach_messages_created_by_id'), ['created_by_id'], unique=False)
        batch_op.create_index(batch_op.f('ix_outreach_messages_id'), ['id'], unique=False)
        batch_op.create_index(batch_op.f('ix_outreach_messages_status'), ['status'], unique=False)

    with op.batch_alter_table('businesses', schema=None) as batch_op:
        batch_op.add_column(sa.Column('contact_name', sa.String(), nullable=True))

def downgrade() -> None:
    with op.batch_alter_table('businesses', schema=None) as batch_op:
        batch_op.drop_column('contact_name')

    with op.batch_alter_table('outreach_messages', schema=None) as batch_op:
        batch_op.drop_index(batch_op.f('ix_outreach_messages_status'))
        batch_op.drop_index(batch_op.f('ix_outreach_messages_id'))
        batch_op.drop_index(batch_op.f('ix_outreach_messages_created_by_id'))
        batch_op.drop_index('ix_outreach_messages_business_created')

    op.drop_table('outreach_messages')
    with op.batch_alter_table('message_templates', schema=None) as batch_op:
        batch_op.drop_index(batch_op.f('ix_message_templates_id'))
        batch_op.drop_index(batch_op.f('ix_message_templates_channel'))

    op.drop_table('message_templates')

from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa
revision: str = 'f39264d003e1'
down_revision: Union[str, Sequence[str], None] = '0eef66d854ef'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None

def upgrade() -> None:
    op.create_table('quality_tasks',
    sa.Column('id', sa.Integer(), nullable=False),
    sa.Column('kind', sa.String(), nullable=False),
    sa.Column('status', sa.String(), nullable=False),
    sa.Column('business_ids', sa.JSON(), nullable=True),
    sa.Column('refresh', sa.Boolean(), server_default=sa.text('0'), nullable=False),
    sa.Column('total', sa.Integer(), nullable=False),
    sa.Column('done', sa.Integer(), nullable=False),
    sa.Column('counts', sa.JSON(), nullable=False),
    sa.Column('error', sa.Text(), nullable=True),
    sa.Column('created_by_id', sa.Integer(), nullable=True),
    sa.Column('created_at', sa.DateTime(timezone=True), server_default=sa.text('(CURRENT_TIMESTAMP)'), nullable=False),
    sa.Column('started_at', sa.DateTime(timezone=True), nullable=True),
    sa.Column('finished_at', sa.DateTime(timezone=True), nullable=True),
    sa.ForeignKeyConstraint(['created_by_id'], ['users.id'], ondelete='SET NULL'),
    sa.PrimaryKeyConstraint('id')
    )
    with op.batch_alter_table('quality_tasks', schema=None) as batch_op:
        batch_op.create_index(batch_op.f('ix_quality_tasks_id'), ['id'], unique=False)
        batch_op.create_index(batch_op.f('ix_quality_tasks_status'), ['status'], unique=False)

    op.create_table('duplicate_candidates',
    sa.Column('id', sa.Integer(), nullable=False),
    sa.Column('business_a_id', sa.Integer(), nullable=False),
    sa.Column('business_b_id', sa.Integer(), nullable=False),
    sa.Column('reason', sa.String(), nullable=False),
    sa.Column('similarity', sa.Integer(), nullable=False),
    sa.Column('confidence', sa.String(), nullable=False),
    sa.Column('status', sa.String(), nullable=False),
    sa.Column('decided_by_id', sa.Integer(), nullable=True),
    sa.Column('decided_at', sa.DateTime(timezone=True), nullable=True),
    sa.Column('created_at', sa.DateTime(timezone=True), server_default=sa.text('(CURRENT_TIMESTAMP)'), nullable=False),
    sa.ForeignKeyConstraint(['business_a_id'], ['businesses.id'], ondelete='CASCADE'),
    sa.ForeignKeyConstraint(['business_b_id'], ['businesses.id'], ondelete='CASCADE'),
    sa.ForeignKeyConstraint(['decided_by_id'], ['users.id'], ondelete='SET NULL'),
    sa.PrimaryKeyConstraint('id'),
    sa.UniqueConstraint('business_a_id', 'business_b_id', name='uq_duplicate_candidates_pair')
    )
    with op.batch_alter_table('duplicate_candidates', schema=None) as batch_op:
        batch_op.create_index(batch_op.f('ix_duplicate_candidates_business_a_id'), ['business_a_id'], unique=False)
        batch_op.create_index(batch_op.f('ix_duplicate_candidates_business_b_id'), ['business_b_id'], unique=False)
        batch_op.create_index(batch_op.f('ix_duplicate_candidates_id'), ['id'], unique=False)
        batch_op.create_index(batch_op.f('ix_duplicate_candidates_status'), ['status'], unique=False)

    with op.batch_alter_table('businesses', schema=None) as batch_op:
        batch_op.add_column(sa.Column('website_status', sa.String(), nullable=True))
        batch_op.add_column(sa.Column('website_check_note', sa.String(), nullable=True))
        batch_op.add_column(sa.Column('website_checked_at', sa.DateTime(timezone=True), nullable=True))

    with op.batch_alter_table('contact_points', schema=None) as batch_op:
        batch_op.add_column(sa.Column('check_status', sa.String(), nullable=True))
        batch_op.add_column(sa.Column('check_note', sa.String(), nullable=True))
        batch_op.add_column(sa.Column('checked_at', sa.DateTime(timezone=True), nullable=True))

def downgrade() -> None:
    with op.batch_alter_table('contact_points', schema=None) as batch_op:
        batch_op.drop_column('checked_at')
        batch_op.drop_column('check_note')
        batch_op.drop_column('check_status')

    with op.batch_alter_table('businesses', schema=None) as batch_op:
        batch_op.drop_column('website_checked_at')
        batch_op.drop_column('website_check_note')
        batch_op.drop_column('website_status')

    with op.batch_alter_table('duplicate_candidates', schema=None) as batch_op:
        batch_op.drop_index(batch_op.f('ix_duplicate_candidates_status'))
        batch_op.drop_index(batch_op.f('ix_duplicate_candidates_id'))
        batch_op.drop_index(batch_op.f('ix_duplicate_candidates_business_b_id'))
        batch_op.drop_index(batch_op.f('ix_duplicate_candidates_business_a_id'))

    op.drop_table('duplicate_candidates')
    with op.batch_alter_table('quality_tasks', schema=None) as batch_op:
        batch_op.drop_index(batch_op.f('ix_quality_tasks_status'))
        batch_op.drop_index(batch_op.f('ix_quality_tasks_id'))

    op.drop_table('quality_tasks')

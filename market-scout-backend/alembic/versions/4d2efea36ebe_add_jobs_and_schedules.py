from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa
revision: str = '4d2efea36ebe'
down_revision: Union[str, Sequence[str], None] = '434e7abc5b0b'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None

def upgrade() -> None:
    op.create_table('jobs',
    sa.Column('id', sa.Integer(), nullable=False),
    sa.Column('kind', sa.String(), nullable=False),
    sa.Column('ref_id', sa.Integer(), nullable=False),
    sa.Column('status', sa.String(), nullable=False),
    sa.Column('attempts', sa.Integer(), nullable=False),
    sa.Column('run_after', sa.DateTime(timezone=True), nullable=False),
    sa.Column('claimed_by', sa.String(), nullable=True),
    sa.Column('lease_expires_at', sa.DateTime(timezone=True), nullable=True),
    sa.Column('error', sa.Text(), nullable=True),
    sa.Column('created_at', sa.DateTime(timezone=True), server_default=sa.text('(CURRENT_TIMESTAMP)'), nullable=False),
    sa.Column('started_at', sa.DateTime(timezone=True), nullable=True),
    sa.Column('finished_at', sa.DateTime(timezone=True), nullable=True),
    sa.PrimaryKeyConstraint('id')
    )
    with op.batch_alter_table('jobs', schema=None) as batch_op:
        batch_op.create_index(batch_op.f('ix_jobs_id'), ['id'], unique=False)
        batch_op.create_index('ix_jobs_pick', ['kind', 'status', 'run_after'], unique=False)
        batch_op.create_index('ix_jobs_ref', ['kind', 'ref_id'], unique=False)
        batch_op.create_index(batch_op.f('ix_jobs_status'), ['status'], unique=False)

    op.create_table('schedules',
    sa.Column('id', sa.Integer(), nullable=False),
    sa.Column('name', sa.String(), nullable=False),
    sa.Column('profile_id', sa.Integer(), nullable=True),
    sa.Column('profile_name', sa.String(), nullable=False),
    sa.Column('created_by_id', sa.Integer(), nullable=True),
    sa.Column('is_active', sa.Boolean(), server_default=sa.text('1'), nullable=False),
    sa.Column('frequency', sa.String(), nullable=False),
    sa.Column('geography_ids', sa.JSON(), nullable=False),
    sa.Column('source_keys', sa.JSON(), nullable=False),
    sa.Column('segment_slugs', sa.JSON(), nullable=True),
    sa.Column('enrich_websites', sa.Boolean(), nullable=False),
    sa.Column('max_paid_requests', sa.Integer(), nullable=True),
    sa.Column('next_run_at', sa.DateTime(timezone=True), nullable=False),
    sa.Column('last_run_at', sa.DateTime(timezone=True), nullable=True),
    sa.Column('consecutive_failures', sa.Integer(), nullable=False),
    sa.Column('last_error', sa.Text(), nullable=True),
    sa.Column('created_at', sa.DateTime(timezone=True), server_default=sa.text('(CURRENT_TIMESTAMP)'), nullable=False),
    sa.Column('updated_at', sa.DateTime(timezone=True), server_default=sa.text('(CURRENT_TIMESTAMP)'), nullable=False),
    sa.ForeignKeyConstraint(['created_by_id'], ['users.id'], ondelete='SET NULL'),
    sa.ForeignKeyConstraint(['profile_id'], ['profiles.id'], ondelete='SET NULL'),
    sa.PrimaryKeyConstraint('id')
    )
    with op.batch_alter_table('schedules', schema=None) as batch_op:
        batch_op.create_index(batch_op.f('ix_schedules_id'), ['id'], unique=False)
        batch_op.create_index(batch_op.f('ix_schedules_is_active'), ['is_active'], unique=False)
        batch_op.create_index(batch_op.f('ix_schedules_next_run_at'), ['next_run_at'], unique=False)
        batch_op.create_index(batch_op.f('ix_schedules_profile_id'), ['profile_id'], unique=False)

    with op.batch_alter_table('runs', schema=None) as batch_op:
        batch_op.add_column(sa.Column('schedule_id', sa.Integer(), nullable=True))
        batch_op.add_column(sa.Column('schedule_name', sa.String(), nullable=True))
        batch_op.create_index(batch_op.f('ix_runs_schedule_id'), ['schedule_id'], unique=False)
        batch_op.create_foreign_key('fk_runs_schedule_id_schedules', 'schedules', ['schedule_id'], ['id'], ondelete='SET NULL')

def downgrade() -> None:
    with op.batch_alter_table('runs', schema=None) as batch_op:
        batch_op.drop_constraint('fk_runs_schedule_id_schedules', type_='foreignkey')
        batch_op.drop_index(batch_op.f('ix_runs_schedule_id'))
        batch_op.drop_column('schedule_name')
        batch_op.drop_column('schedule_id')

    with op.batch_alter_table('schedules', schema=None) as batch_op:
        batch_op.drop_index(batch_op.f('ix_schedules_profile_id'))
        batch_op.drop_index(batch_op.f('ix_schedules_next_run_at'))
        batch_op.drop_index(batch_op.f('ix_schedules_is_active'))
        batch_op.drop_index(batch_op.f('ix_schedules_id'))

    op.drop_table('schedules')
    with op.batch_alter_table('jobs', schema=None) as batch_op:
        batch_op.drop_index(batch_op.f('ix_jobs_status'))
        batch_op.drop_index('ix_jobs_ref')
        batch_op.drop_index('ix_jobs_pick')
        batch_op.drop_index(batch_op.f('ix_jobs_id'))

    op.drop_table('jobs')

from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


revision: str = 'e683f19c0df3'
down_revision: Union[str, Sequence[str], None] = '5eb57503b6fe'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.create_table('imports',
    sa.Column('id', sa.Integer(), nullable=False),
    sa.Column('label', sa.String(), nullable=False),
    sa.Column('filename', sa.String(), nullable=False),
    sa.Column('profile_id', sa.Integer(), nullable=True),
    sa.Column('profile_name', sa.String(), nullable=False),
    sa.Column('segment_slug', sa.String(), nullable=True),
    sa.Column('default_geography_id', sa.Integer(), nullable=True),
    sa.Column('default_geography_name', sa.String(), nullable=True),
    sa.Column('require_contact', sa.Boolean(), nullable=False),
    sa.Column('mapping', sa.JSON(), nullable=False),
    sa.Column('created_by_id', sa.Integer(), nullable=True),
    sa.Column('status', sa.String(), nullable=False),
    sa.Column('rows_total', sa.Integer(), nullable=False),
    sa.Column('rows_to_import', sa.Integer(), nullable=False),
    sa.Column('rows_done', sa.Integer(), nullable=False),
    sa.Column('skipped', sa.JSON(), nullable=False),
    sa.Column('stats', sa.JSON(), nullable=False),
    sa.Column('error', sa.Text(), nullable=True),
    sa.Column('created_at', sa.DateTime(timezone=True), server_default=sa.text('(CURRENT_TIMESTAMP)'), nullable=True),
    sa.Column('started_at', sa.DateTime(timezone=True), nullable=True),
    sa.Column('finished_at', sa.DateTime(timezone=True), nullable=True),
    sa.ForeignKeyConstraint(['created_by_id'], ['users.id'], ondelete='SET NULL'),
    sa.ForeignKeyConstraint(['default_geography_id'], ['geographies.id'], ondelete='SET NULL'),
    sa.ForeignKeyConstraint(['profile_id'], ['profiles.id'], ondelete='SET NULL'),
    sa.PrimaryKeyConstraint('id')
    )
    with op.batch_alter_table('imports', schema=None) as batch_op:
        batch_op.create_index(batch_op.f('ix_imports_id'), ['id'], unique=False)
        batch_op.create_index(batch_op.f('ix_imports_label'), ['label'], unique=False)
        batch_op.create_index(batch_op.f('ix_imports_profile_id'), ['profile_id'], unique=False)
        batch_op.create_index(batch_op.f('ix_imports_status'), ['status'], unique=False)


def downgrade() -> None:
    with op.batch_alter_table('imports', schema=None) as batch_op:
        batch_op.drop_index(batch_op.f('ix_imports_status'))
        batch_op.drop_index(batch_op.f('ix_imports_profile_id'))
        batch_op.drop_index(batch_op.f('ix_imports_label'))
        batch_op.drop_index(batch_op.f('ix_imports_id'))

    op.drop_table('imports')

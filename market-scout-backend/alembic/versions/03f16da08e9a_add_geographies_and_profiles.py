from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


revision: str = '03f16da08e9a'
down_revision: Union[str, Sequence[str], None] = 'fb8c165e80a2'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.create_table('geographies',
    sa.Column('id', sa.Integer(), nullable=False),
    sa.Column('name', sa.String(), nullable=False),
    sa.Column('slug', sa.String(), nullable=False),
    sa.Column('level', sa.String(), nullable=False),
    sa.Column('parent_id', sa.Integer(), nullable=True),
    sa.Column('latitude', sa.Float(), nullable=True),
    sa.Column('longitude', sa.Float(), nullable=True),
    sa.Column('radius_km', sa.Float(), nullable=True),
    sa.Column('bbox', sa.JSON(), nullable=True),
    sa.Column('created_at', sa.DateTime(timezone=True), server_default=sa.text('(CURRENT_TIMESTAMP)'), nullable=True),
    sa.Column('updated_at', sa.DateTime(timezone=True), nullable=True),
    sa.ForeignKeyConstraint(['parent_id'], ['geographies.id'], ),
    sa.PrimaryKeyConstraint('id'),
    sa.UniqueConstraint('parent_id', 'name', name='uq_geographies_parent_name')
    )
    with op.batch_alter_table('geographies', schema=None) as batch_op:
        batch_op.create_index(batch_op.f('ix_geographies_id'), ['id'], unique=False)
        batch_op.create_index(batch_op.f('ix_geographies_level'), ['level'], unique=False)
        batch_op.create_index(batch_op.f('ix_geographies_name'), ['name'], unique=False)
        batch_op.create_index(batch_op.f('ix_geographies_parent_id'), ['parent_id'], unique=False)
        batch_op.create_index(batch_op.f('ix_geographies_slug'), ['slug'], unique=True)

    op.create_table('profiles',
    sa.Column('id', sa.Integer(), nullable=False),
    sa.Column('name', sa.String(), nullable=False),
    sa.Column('slug', sa.String(), nullable=False),
    sa.Column('description', sa.Text(), nullable=True),
    sa.Column('is_active', sa.Boolean(), nullable=False),
    sa.Column('scoring_config', sa.JSON(), nullable=False),
    sa.Column('created_at', sa.DateTime(timezone=True), server_default=sa.text('(CURRENT_TIMESTAMP)'), nullable=True),
    sa.Column('updated_at', sa.DateTime(timezone=True), nullable=True),
    sa.PrimaryKeyConstraint('id'),
    sa.UniqueConstraint('name')
    )
    with op.batch_alter_table('profiles', schema=None) as batch_op:
        batch_op.create_index(batch_op.f('ix_profiles_id'), ['id'], unique=False)
        batch_op.create_index(batch_op.f('ix_profiles_slug'), ['slug'], unique=True)

    op.create_table('profile_segments',
    sa.Column('id', sa.Integer(), nullable=False),
    sa.Column('profile_id', sa.Integer(), nullable=False),
    sa.Column('name', sa.String(), nullable=False),
    sa.Column('slug', sa.String(), nullable=False),
    sa.Column('description', sa.Text(), nullable=True),
    sa.Column('match_rules', sa.JSON(), nullable=False),
    sa.Column('sort_order', sa.Integer(), nullable=False),
    sa.ForeignKeyConstraint(['profile_id'], ['profiles.id'], ondelete='CASCADE'),
    sa.PrimaryKeyConstraint('id'),
    sa.UniqueConstraint('profile_id', 'slug', name='uq_profile_segments_profile_slug')
    )
    with op.batch_alter_table('profile_segments', schema=None) as batch_op:
        batch_op.create_index(batch_op.f('ix_profile_segments_id'), ['id'], unique=False)
        batch_op.create_index(batch_op.f('ix_profile_segments_profile_id'), ['profile_id'], unique=False)

    op.create_table('profile_search_terms',
    sa.Column('id', sa.Integer(), nullable=False),
    sa.Column('profile_id', sa.Integer(), nullable=False),
    sa.Column('segment_id', sa.Integer(), nullable=False),
    sa.Column('text', sa.String(), nullable=False),
    sa.Column('osm_filter', sa.JSON(), nullable=True),
    sa.Column('language', sa.String(), nullable=False),
    sa.Column('is_active', sa.Boolean(), nullable=False),
    sa.ForeignKeyConstraint(['profile_id'], ['profiles.id'], ondelete='CASCADE'),
    sa.ForeignKeyConstraint(['segment_id'], ['profile_segments.id'], ondelete='CASCADE'),
    sa.PrimaryKeyConstraint('id'),
    sa.UniqueConstraint('segment_id', 'text', 'language', name='uq_profile_search_terms_segment_text_language')
    )
    with op.batch_alter_table('profile_search_terms', schema=None) as batch_op:
        batch_op.create_index(batch_op.f('ix_profile_search_terms_id'), ['id'], unique=False)
        batch_op.create_index(batch_op.f('ix_profile_search_terms_profile_id'), ['profile_id'], unique=False)
        batch_op.create_index(batch_op.f('ix_profile_search_terms_segment_id'), ['segment_id'], unique=False)


def downgrade() -> None:
    with op.batch_alter_table('profile_search_terms', schema=None) as batch_op:
        batch_op.drop_index(batch_op.f('ix_profile_search_terms_segment_id'))
        batch_op.drop_index(batch_op.f('ix_profile_search_terms_profile_id'))
        batch_op.drop_index(batch_op.f('ix_profile_search_terms_id'))

    op.drop_table('profile_search_terms')
    with op.batch_alter_table('profile_segments', schema=None) as batch_op:
        batch_op.drop_index(batch_op.f('ix_profile_segments_profile_id'))
        batch_op.drop_index(batch_op.f('ix_profile_segments_id'))

    op.drop_table('profile_segments')
    with op.batch_alter_table('profiles', schema=None) as batch_op:
        batch_op.drop_index(batch_op.f('ix_profiles_slug'))
        batch_op.drop_index(batch_op.f('ix_profiles_id'))

    op.drop_table('profiles')
    with op.batch_alter_table('geographies', schema=None) as batch_op:
        batch_op.drop_index(batch_op.f('ix_geographies_slug'))
        batch_op.drop_index(batch_op.f('ix_geographies_parent_id'))
        batch_op.drop_index(batch_op.f('ix_geographies_name'))
        batch_op.drop_index(batch_op.f('ix_geographies_level'))
        batch_op.drop_index(batch_op.f('ix_geographies_id'))

    op.drop_table('geographies')

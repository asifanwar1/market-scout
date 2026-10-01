from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


revision: str = '3d33b1b972ab'
down_revision: Union[str, Sequence[str], None] = '53c412ab4455'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.create_table('do_not_contact',
    sa.Column('id', sa.Integer(), nullable=False),
    sa.Column('business_id', sa.Integer(), nullable=True),
    sa.Column('phone', sa.String(), nullable=True),
    sa.Column('email', sa.String(), nullable=True),
    sa.Column('reason', sa.Text(), nullable=True),
    sa.Column('added_by_id', sa.Integer(), nullable=True),
    sa.Column('created_at', sa.DateTime(timezone=True), server_default=sa.text('(CURRENT_TIMESTAMP)'), nullable=True),
    sa.ForeignKeyConstraint(['added_by_id'], ['users.id'], ondelete='SET NULL'),
    sa.ForeignKeyConstraint(['business_id'], ['businesses.id'], ondelete='SET NULL'),
    sa.PrimaryKeyConstraint('id')
    )
    with op.batch_alter_table('do_not_contact', schema=None) as batch_op:
        batch_op.create_index(batch_op.f('ix_do_not_contact_business_id'), ['business_id'], unique=False)
        batch_op.create_index(batch_op.f('ix_do_not_contact_email'), ['email'], unique=False)
        batch_op.create_index(batch_op.f('ix_do_not_contact_id'), ['id'], unique=False)
        batch_op.create_index(batch_op.f('ix_do_not_contact_phone'), ['phone'], unique=False)


def downgrade() -> None:
    with op.batch_alter_table('do_not_contact', schema=None) as batch_op:
        batch_op.drop_index(batch_op.f('ix_do_not_contact_phone'))
        batch_op.drop_index(batch_op.f('ix_do_not_contact_id'))
        batch_op.drop_index(batch_op.f('ix_do_not_contact_email'))
        batch_op.drop_index(batch_op.f('ix_do_not_contact_business_id'))

    op.drop_table('do_not_contact')

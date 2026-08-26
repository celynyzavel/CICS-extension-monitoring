"""add barangay to programs

Revision ID: a296cbd077b3
Revises: d932e979a1b1
Create Date: 2026-08-26 19:44:35.864973

"""
from alembic import op
import sqlalchemy as sa

revision = 'a296cbd077b3'
down_revision = 'd932e979a1b1'
branch_labels = None
depends_on = None


def upgrade():
    with op.batch_alter_table('programs', schema=None) as batch_op:
        batch_op.add_column(sa.Column('barangay', sa.String(length=100), nullable=False))


def downgrade():
    with op.batch_alter_table('programs', schema=None) as batch_op:
        batch_op.drop_column('barangay')


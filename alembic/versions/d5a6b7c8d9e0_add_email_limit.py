"""add_email_limit

Revision ID: d5a6b7c8d9e0
Revises: c4d72f6e4d5a
Create Date: 2026-02-06 00:40:00.000000

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = 'd5a6b7c8d9e0'
down_revision: Union[str, Sequence[str], None] = 'c4d72f6e4d5a'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    # Add email_limit column with default 4
    op.add_column('users', sa.Column('email_limit', sa.Integer(), nullable=False, server_default='4'))


def downgrade() -> None:
    op.drop_column('users', 'email_limit')

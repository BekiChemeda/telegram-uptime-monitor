"""add_email_verification_fields

Revision ID: 61c2df339bc7
Revises: d5a6b7c8d9e0
Create Date: 2026-02-06 01:22:07.965337

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = '61c2df339bc7'
down_revision: Union[str, Sequence[str], None] = 'd5a6b7c8d9e0'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    """Upgrade schema."""
    op.add_column('users', sa.Column('is_email_verified', sa.Boolean(), nullable=False, server_default='false'))
    op.add_column('users', sa.Column('email_verification_code', sa.String(), nullable=True))
    op.add_column('users', sa.Column('email_verification_expiry', sa.DateTime(timezone=True), nullable=True))
    op.add_column('users', sa.Column('verification_attempts_count', sa.Integer(), nullable=False, server_default='0'))
    op.add_column('users', sa.Column('last_verification_attempt_date', sa.DateTime(timezone=True), nullable=True))


def downgrade() -> None:
    """Downgrade schema."""
    op.drop_column('users', 'last_verification_attempt_date')
    op.drop_column('users', 'verification_attempts_count')
    op.drop_column('users', 'email_verification_expiry')
    op.drop_column('users', 'email_verification_code')
    op.drop_column('users', 'is_email_verified')

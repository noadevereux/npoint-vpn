"""add user login tokens table

Revision ID: 5c0a0e9d8f0f
Revises: 2b231de97dc3
Create Date: 2024-12-29 00:00:00.000000

"""
from alembic import op
import sqlalchemy as sa

# revision identifiers, used by Alembic.
revision = '5c0a0e9d8f0f'
down_revision = '2b231de97dc3'
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.create_table(
        'user_login_tokens',
        sa.Column('id', sa.Integer(), primary_key=True),
        sa.Column('user_id', sa.Integer(), sa.ForeignKey('users.id'), nullable=False),
        sa.Column('token_hash', sa.String(length=128), nullable=False),
        sa.Column('created_at', sa.DateTime(), nullable=False, server_default=sa.func.now()),
        sa.Column('expires_at', sa.DateTime(), nullable=False),
        sa.Column('used_at', sa.DateTime(), nullable=True),
        sa.Column('requested_ip', sa.String(length=45), nullable=True),
        sa.Column('requested_user_agent', sa.String(length=512), nullable=True),
        sa.Column('consumed_ip', sa.String(length=45), nullable=True),
        sa.Column('consumed_user_agent', sa.String(length=512), nullable=True),
    )
    op.create_index(
        'ix_user_login_tokens_token_hash',
        'user_login_tokens',
        ['token_hash'],
        unique=True,
    )
    op.create_index(
        'ix_user_login_tokens_user_id',
        'user_login_tokens',
        ['user_id'],
    )


def downgrade() -> None:
    op.drop_index('ix_user_login_tokens_user_id', table_name='user_login_tokens')
    op.drop_index('ix_user_login_tokens_token_hash', table_name='user_login_tokens')
    op.drop_table('user_login_tokens')

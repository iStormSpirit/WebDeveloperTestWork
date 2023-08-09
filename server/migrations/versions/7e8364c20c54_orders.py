"""orders

Revision ID: 7e8364c20c54
Revises: 
Create Date: 2023-03-29 14:27:28.957135

"""
import sqlalchemy as sa
from alembic import op
from sqlalchemy.dialects import postgresql

# revision identifiers, used by Alembic.
revision = '7e8364c20c54'
down_revision = None
branch_labels = None
depends_on = None


def upgrade() -> None:
    # ### commands auto generated by Alembic - please adjust! ###
    op.create_table('orders',
    sa.Column('uuid', postgresql.UUID(as_uuid=True), nullable=False),
    sa.Column('instrument', postgresql.ENUM('eur_usd', 'eur_rub', 'usd_rub', name='instrument'), nullable=False),
    sa.Column('side', postgresql.ENUM('buy', 'sell', name='orderside'), nullable=False),
    sa.Column('status', postgresql.ENUM('active', 'filled', 'rejected', 'cancelled', name='orderstatus'), nullable=False),
    sa.Column('amount', sa.Integer(), nullable=False),
    sa.Column('price', sa.DECIMAL(), nullable=False),
    sa.Column('address', sa.String(), nullable=False),
    sa.Column('creation_time', sa.DateTime(), nullable=False),
    sa.Column('change_time', sa.DateTime(), nullable=False),
    sa.PrimaryKeyConstraint('uuid')
    )
    # ### end Alembic commands ###


def downgrade() -> None:
    # ### commands auto generated by Alembic - please adjust! ###
    op.drop_table('orders')
    # ### end Alembic commands ###

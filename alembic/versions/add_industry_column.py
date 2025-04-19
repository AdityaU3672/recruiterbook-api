"""add industry column to companies table

Revision ID: add_industry_column
Revises: 
Create Date: 2023-06-01 00:00:00.000000

"""
from alembic import op
import sqlalchemy as sa
from sqlalchemy.sql import table, column


# revision identifiers, used by Alembic.
revision = 'add_industry_column'
down_revision = None
branch_labels = None
depends_on = None


def upgrade():
    # Add the industry column
    op.add_column('companies', sa.Column('industry', sa.String(), nullable=True))
    
    # Create a reference to the companies table for batch updates
    companies = table('companies',
        column('id', sa.String),
        column('name', sa.String),
        column('industry', sa.String)
    )
    
    # Create a comment explaining the column's intended values
    op.create_check_constraint(
        "industry_check",
        "companies",
        "industry IN ('Tech', 'Finance', 'Consulting', 'Healthcare', 'Unknown', NULL)"
    )


def downgrade():
    # Drop the constraint first
    op.drop_constraint("industry_check", "companies", type_="check")
    
    # Drop the column
    op.drop_column('companies', 'industry') 
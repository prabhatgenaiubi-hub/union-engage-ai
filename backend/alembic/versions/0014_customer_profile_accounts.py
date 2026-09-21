from alembic import op
import sqlalchemy as sa

revision="0014"; down_revision="0013"; branch_labels=None; depends_on=None

def upgrade():
    op.add_column("customers",sa.Column("profile_verified",sa.Boolean(),nullable=False,server_default=sa.true()))
    op.add_column("customers",sa.Column("kyc_status",sa.String(length=30),nullable=False,server_default="Up to date"))
    op.add_column("customers",sa.Column("kyc_updated_at",sa.DateTime(),nullable=True))
    op.add_column("customers",sa.Column("trusted_customer",sa.Boolean(),nullable=False,server_default=sa.true()))
    op.create_table("bank_accounts",sa.Column("id",sa.Integer(),primary_key=True),sa.Column("customer_id",sa.Integer(),sa.ForeignKey("customers.id"),nullable=False),sa.Column("account_number",sa.String(length=30),nullable=False),sa.Column("account_type",sa.String(length=40),nullable=False,server_default="Savings Account"),sa.Column("balance",sa.Float(),nullable=False,server_default="0"),sa.Column("status",sa.String(length=20),nullable=False,server_default="Active"),sa.Column("created_at",sa.DateTime(),nullable=False),sa.Column("updated_at",sa.DateTime(),nullable=False))
    op.create_index("ix_bank_accounts_customer_id","bank_accounts",["customer_id"])
    op.create_index("ix_bank_accounts_account_number","bank_accounts",["account_number"],unique=True)
    op.create_table("account_transactions",sa.Column("id",sa.Integer(),primary_key=True),sa.Column("account_id",sa.Integer(),sa.ForeignKey("bank_accounts.id"),nullable=False),sa.Column("transaction_date",sa.DateTime(),nullable=False),sa.Column("description",sa.String(length=160),nullable=False),sa.Column("reference",sa.String(length=40),nullable=False),sa.Column("debit",sa.Float(),nullable=False,server_default="0"),sa.Column("credit",sa.Float(),nullable=False,server_default="0"),sa.Column("balance",sa.Float(),nullable=False,server_default="0"))
    op.create_index("ix_account_transactions_account_id","account_transactions",["account_id"])
    op.create_index("ix_account_transactions_transaction_date","account_transactions",["transaction_date"])
    op.create_unique_constraint("uq_account_transactions_reference","account_transactions",["reference"])

def downgrade():
    op.drop_table("account_transactions");op.drop_table("bank_accounts")
    op.drop_column("customers","trusted_customer");op.drop_column("customers","kyc_updated_at");op.drop_column("customers","kyc_status");op.drop_column("customers","profile_verified")

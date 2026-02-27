"""${message}"""

# revision identifiers, used by Alembic
revision = '${up_revision}'
down_revision = '${down_revision}'
branch_labels = None
depends_on = None


from alembic import op
import sqlalchemy as sa


def upgrade():
    ${upgrades if upgrades else "pass"}


def downgrade():
    ${downgrades if downgrades else "pass"}

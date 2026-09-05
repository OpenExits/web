"""rename site to object

The record type is an object (the cliff, the bridge, the antenna, the
building) — BASE vocabulary, matching specification v2.0.2. Tables, columns,
indexes and the persisted submission kind follow.

SQLite batch mode recreates a table per batch and matches indexes against the
reflected columns, so a column rename and an index on the new name cannot
share one batch: drop indexes, rename table, rename column, then re-index.

Revision ID: b7e2a9c4d1f0
Revises: 737135f24457
Create Date: 2026-09-05 12:00:00.000000

"""
from __future__ import annotations

from alembic import op


revision = 'b7e2a9c4d1f0'
down_revision = '737135f24457'
branch_labels = None
depends_on = None


def _rename(old_table: str, new_table: str, old_col: str, new_col: str,
            drop_indexes: list[str], create_indexes: list[tuple[str, list[str]]],
            drop_unique: str | None = None, create_unique: tuple[str, list[str]] | None = None) -> None:
    with op.batch_alter_table(old_table, schema=None) as batch_op:
        for name in drop_indexes:
            batch_op.drop_index(name)
        if drop_unique:
            batch_op.drop_constraint(drop_unique, type_='unique')
    op.rename_table(old_table, new_table)
    with op.batch_alter_table(new_table, schema=None) as batch_op:
        batch_op.alter_column(old_col, new_column_name=new_col)
    with op.batch_alter_table(new_table, schema=None) as batch_op:
        if create_unique:
            batch_op.create_unique_constraint(create_unique[0], create_unique[1])
        for name, cols in create_indexes:
            batch_op.create_index(name, cols, unique=False)


def upgrade() -> None:
    with op.batch_alter_table('submissions', schema=None) as batch_op:
        batch_op.alter_column('target_site_id', new_column_name='target_object_id')
        batch_op.alter_column('published_site_id', new_column_name='published_object_id')
    op.execute("UPDATE submissions SET kind = 'new_object' WHERE kind = 'new_site'")

    _rename('site_comments', 'object_comments', 'site_id', 'object_id',
            drop_indexes=['ix_site_comments_site_created'],
            create_indexes=[('ix_object_comments_object_created', ['object_id', 'created_at'])])
    _rename('site_confirmations', 'object_confirmations', 'site_id', 'object_id',
            drop_indexes=['ix_confirmations_site_date'],
            create_indexes=[('ix_confirmations_object_date', ['object_id', 'confirmed_on'])],
            drop_unique='uq_confirmation_site_user',
            create_unique=('uq_confirmation_object_user', ['object_id', 'user_id']))
    _rename('site_reports', 'object_reports', 'site_id', 'object_id',
            drop_indexes=['ix_site_reports_site', 'ix_site_reports_status_created'],
            create_indexes=[('ix_object_reports_object', ['object_id']),
                            ('ix_object_reports_status_created', ['status', 'created_at'])])


def downgrade() -> None:
    _rename('object_reports', 'site_reports', 'object_id', 'site_id',
            drop_indexes=['ix_object_reports_status_created', 'ix_object_reports_object'],
            create_indexes=[('ix_site_reports_site', ['site_id']),
                            ('ix_site_reports_status_created', ['status', 'created_at'])])
    _rename('object_confirmations', 'site_confirmations', 'object_id', 'site_id',
            drop_indexes=['ix_confirmations_object_date'],
            create_indexes=[('ix_confirmations_site_date', ['site_id', 'confirmed_on'])],
            drop_unique='uq_confirmation_object_user',
            create_unique=('uq_confirmation_site_user', ['site_id', 'user_id']))
    _rename('object_comments', 'site_comments', 'object_id', 'site_id',
            drop_indexes=['ix_object_comments_object_created'],
            create_indexes=[('ix_site_comments_site_created', ['site_id', 'created_at'])])

    op.execute("UPDATE submissions SET kind = 'new_site' WHERE kind = 'new_object'")
    with op.batch_alter_table('submissions', schema=None) as batch_op:
        batch_op.alter_column('target_object_id', new_column_name='target_site_id')
        batch_op.alter_column('published_object_id', new_column_name='published_site_id')

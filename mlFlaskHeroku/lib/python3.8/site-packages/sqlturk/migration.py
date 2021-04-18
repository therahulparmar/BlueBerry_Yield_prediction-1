# -*- encoding: utf-8 -*-
#
# Copyright 2009 Max Ischenko
#           2015 Jedynak Jaroslaw (small fixes)
# 
# Licensed under the Apache License, Version 2.0 (the “License”); you may not use this
# file except in compliance with the License. You may obtain a copy of the License at
# 
#    http://www.apache.org/licenses/LICENSE-2.0
# 
# Unless required by applicable law or agreed to in writing, software distributed under
# the License is distributed on an “AS IS” BASIS, WITHOUT WARRANTIES OR CONDITIONS OF ANY
# KIND, either express or implied. See the License for the specific language governing
# permissions and limitations under the License.

"""Public API.

Instantiate a tool, specifying the database
`uri <http://www.sqlalchemy.org/docs/05/dbengine.html#create-engine-url-arguments>`_
and directory that contains migration
files:

    >>> tool = MigrationTool('sqlite://', migration_dir='testmigrations')

Create database table to track schema changes (safe to call multiple times):

    >>> tool.install()

Let's find if we have any migrations that need to be run:

    >>> len(tool.find_migrations())
    3

Migration files are named according to a convention, <migration number>-<text>.sql.
This is important so that they are run in a guranteed order:

    >>> tool.find_migrations()
    ['1_foobar', '2_foobar_data', '10_foobar_delete']

Let's run them and verify we're up-to-date.

    >>> tool.run_migrations()
    3
    >>> tool.find_migrations()
    []

Verify that the migrations were actually ran:

    >>> tool.engine.execute("select * from foobar").fetchall()
    [(1, u'test')]
"""

__all__ = ['MigrationTool']

import re
import glob
import os.path
import datetime
from sqlalchemy import create_engine, types, MetaData, Table, Column

import logging

log = logging.getLogger(__name__)

metadata = MetaData()


def sql_transaction(connection, f):
    """Wraps function call into an SQL transaction.

    Basically copied verbatim from the `SQLAlchemy documentation
    <http://www.sqlalchemy.org/docs/05/dbengine.html#using-transactions-with-connection>`_.
    """
    trans = connection.begin()
    try:
        retval = f()
        trans.commit()
        return retval
    except:
        trans.rollback()
        raise


def execute_batch(engine, sql,
                  regex=r"(?mx) ([^';]* (?:'[^']*'[^';]*)*)",
                  comment_regex=r"(?mx) (?:^\s*$)|(?:--.*$)"):
    """
    Takes a SQL file and executes it as many separate statements.
    (Some backends, such as Postgres, don't work otherwise.)

    This function is taken from South, 
    http://south.aeracode.org/browser/south/db/generic.py
    """
    # Be warned: This function is full of dark magic. Make sure you really
    # know regexes before trying to edit it.
    # First, strip comments
    sql = "\n".join([x.strip().replace("%", "%%") for x in re.split(comment_regex, sql) if x.strip()])
    # Now execute each statement
    for st in re.split(regex, sql)[1:][::2]:
        engine.execute(st)


def apply_migration(engine, sql):
    """Runs a single migration in a database transaction.

    >>> sql = open('testmigrations/test_rollback.sql', 'rt').read()
    >>> engine = create_engine('sqlite://', echo=True)
    >>> apply_migration(engine, sql)
    Traceback (most recent call last):
    ...
    OperationalError: (OperationalError) no such table: asdf23 '\\ndelete from asdf23' ()
    
    XXX: SQLite does not support commit/rollback, how 'd I test it?
    """
    conn = engine.connect()
    f = lambda: execute_batch(conn, sql)
    try:
        sql_transaction(conn, f)
    finally:
        conn.close()


class MigrationFile(object):
    """Helper class that abstracts migration file object.
    """

    NAME_RE = re.compile(r'(?P<number>[0-9]+)(?P<sep>[-_])(?P<comment>[^.]+)\.sql')

    def __init__(self, fname):
        self.fname = fname
        basename = os.path.basename(fname)
        m = self.NAME_RE.match(basename)
        if not m:
            raise ValueError(fname)
        self.number = int(m.group('number'))
        self.comment = m.group('comment')
        sep = m.group('sep')
        self.name = "%d%s%s" % (self.number, sep, self.comment)

    def get_content(self):
        fd = open(self.fname, 'rt')
        try:
            return fd.read()
        finally:
            fd.close()

    def __lt__(self, other):
        if other.number == self.number:
            return self.comment < other.comment
        return self.number < other.number

    def __str__(self):
        return self.name

    def __repr__(self):
        return repr(str(self))


class MigrationTool(object):
    """Provides high-level API to manage migrations.
    """

    def __init__(self, dburi, migration_dir, schema_table='sql_migration'):
        self.dburi = dburi
        self.engine = create_engine(dburi)
        self.migration_dir = migration_dir
        self.table = Table(schema_table, metadata,
                           Column('id', types.Integer, primary_key=True),
                           Column('migration', types.String(80)),
                           Column('applied', types.DateTime, default=datetime.datetime.now),
                           )

    def install(self):
        """Creates database table to track schema changes.

        It is safe to call it multiple times.
        """
        metadata.create_all(self.engine)
        log.info("Migration database table created as %s", self.table.name)

    def find_migrations(self):
        """Lists migrations that have not been applied yet.
        """
        applied_migrations = self.find_applied_migrations()
        pattern = os.path.join(self.migration_dir, "*.sql")
        names = []
        for name in glob.glob(pattern):
            fname = os.path.abspath(name)
            try:
                migration = MigrationFile(fname)
            except ValueError:
                log.warn("Unrecognized migration file pattern %s", fname)
                continue
            if str(migration) not in applied_migrations:
                names.append(migration)
            log.debug("Skip migration %s: already applied", migration)
        names.sort()  # MigrationFile defines its own ordering
        return names

    def find_applied_migrations(self):
        s = self.table.select()
        s = s.order_by("id")
        rs = self.engine.execute(s).fetchall()
        return [row.migration for row in rs]

    def run_migrations(self):
        """Finds and applies migrations that haven't been run yet.
        """
        migrations = self.find_migrations()
        for mfile in migrations:
            try:
                apply_migration(self.engine, mfile.get_content())
                ins = self.table.insert().values(migration=str(mfile))
                self.engine.execute(ins)
                log.info("Successfully ran migration %s", mfile)
            except Exception as e:
                log.error("Failed to run migration %s: %s", mfile, e)
                raise
        return len(migrations)

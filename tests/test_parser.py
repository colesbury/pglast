# -*- coding: utf-8 -*-
# :Project:   pglast -- Test the parser.pyx module
# :Created:   ven 04 ago 2017 08:37:10 CEST
# :Author:    Lele Gaifax <lele@metapensiero.it>
# :License:   GNU General Public License version 3 or later
# :Copyright: © 2017, 2018, 2019, 2021 Lele Gaifax
#

import pytest

from pglast import Error, ast, parse_plpgsql, parse_sql
from pglast.parser import ParseError, fingerprint, get_postgresql_version, scan, split


def test_basic():
    assert parse_sql('') == ()
    assert parse_sql('-- nothing') == ()
    with pytest.raises(ParseError):
        parse_sql('foo')

    ptree = parse_sql('SELECT 1')
    assert isinstance(ptree, tuple)
    assert len(ptree) == 1
    rawstmt = ptree[0]
    assert isinstance(rawstmt, ast.RawStmt)

    ptree = parse_plpgsql('CREATE FUNCTION add (a integer, b integer)'
                          ' RETURNS integer AS $$ BEGIN RETURN a + b; END; $$'
                          ' LANGUAGE plpgsql')
    assert len(ptree) == 1
    function = ptree[0]
    assert isinstance(function, dict)
    assert function.keys() == {'PLpgSQL_function'}


def test_fingerprint():
    sql1 = "SELECT a as b, c as d FROM atable AS btable WHERE a = 1 AND b in (1, 2)"
    sql2 = "SELECT a, c FROM atable WHERE a = 2 AND b IN (2, 3, 4) "
    assert fingerprint(sql1) == fingerprint(sql2)


def test_errors():
    with pytest.raises(Error) as exc:
        parse_sql('FooBar')
    assert exc.typename == 'ParseError'
    assert exc.value.location == 1
    assert 'syntax error ' in str(exc.value)

    with pytest.raises(Error) as exc:
        parse_sql('SELECT foo FRON bar')
    assert exc.typename == 'ParseError'
    assert exc.value.location == 17
    errmsg = str(exc.value)
    assert 'syntax error at or near "bar"' in errmsg
    assert 'location 17' in errmsg

    with pytest.raises(Error) as exc:
        parse_plpgsql('CREATE FUMCTION add (a integer, b integer)'
                      ' RETURNS integer AS $$ BEGIN RETURN a + b; END; $$'
                      ' LANGUAGE plpgsql')
    assert exc.typename == 'ParseError'
    assert exc.value.location == 8
    errmsg = str(exc.value)
    assert 'syntax error at or near "FUMCTION"' in errmsg
    assert 'location 8' in errmsg

    with pytest.raises(Error) as exc:
        fingerprint('SELECT foo FRON bar')
    assert exc.typename == 'ParseError'
    assert exc.value.location == 17
    errmsg = str(exc.value)
    assert 'syntax error at or near "bar"' in errmsg
    assert 'location 17' in errmsg


def test_unicode():
    ptree = parse_sql('SELECT 1 AS "Naïve"')
    target = ptree[0].stmt.targetList[0]
    assert target.name == "Naïve"


def test_pg_version():
    pg_version = get_postgresql_version()
    assert isinstance(pg_version, tuple)
    assert len(pg_version) == 2


def test_clone():
    from pglast import ast
    stmts = parse_sql('SELECT 1')
    stmt = stmts[0].stmt
    clone = ast.SelectStmt(stmt())
    assert clone is not stmt
    assert clone == stmt
    assert repr(clone) == repr(stmt)
    assert clone() == stmt()


def test_split():
    sql = 'select 1; select 2;    select "€€€€ ·";   select 4'
    expected = ('select 1', 'select 2', 'select "€€€€ ·"', 'select 4')
    assert split(sql) == expected
    assert tuple(sql[s] for s in split(sql, only_slices=True)) == expected


def test_scan():
    sql = 'select /* something here */ 1'
    expected = ((0, 6, 'SELECT', 'RESERVED_KEYWORD'),
                (7, 27, 'C_COMMENT', 'NO_KEYWORD'),
                (28, 29, 'ICONST', 'NO_KEYWORD'))
    result = scan(sql)
    assert result == expected
    assert sql[result[1].start:result[1].end] == '/* something here */'
